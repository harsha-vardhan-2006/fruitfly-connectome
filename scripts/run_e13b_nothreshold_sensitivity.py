#!/usr/bin/env python
"""E13.6b — Connection-table sensitivity: no-threshold table (EXECUTED).

Closes the one open QC item (QC_STATUS "Robustness" checkbox). The prior
E13-full run documented-only the no-threshold sensitivity as an honest gap:
`connections_princeton_no_threshold.csv.gz` collapses to ~50M node-pairs,
which OOM'd the 8 GB machine under the naive loader (run_e13_full.py 13.6:
"documented_not_run"). This script closes the gap without a high-RAM machine:

  1. CHUNKED LOAD: stream the 275 MB gzip in 2M-row chunks; keep only
     (pre, post, syn_count) with BOTH endpoints inside the FROZEN node
     universe of the primary graph. Pair-collapse is vectorized
     (sorted-universe searchsorted + local-index key packing + np.unique /
     bincount blocks). Peak RSS ~0.8 GB (vs ~12+ GB naive).
  2. FROZEN UNIVERSE: node set AND index order are those of
     data/processed/graph_pairs.parquet, so per-node panel sources and
     matched-pair indices are exactly comparable with the primary run.
     Only the edge-inclusion rule differs (every reported connection kept
     vs the thresholded export) — that is the sensitivity question.
  3. SAME ESTIMATOR AND PROTOCOL AS THE PRIMARY E10B OBSERVED STATISTIC:
     binary digraph, fixed panel k=4 seed=0, the 848 pre-registered E08
     matched pairs (1,696 nodes), statistic = Cliff's delta +
     median(GABA) - median(ACh). The estimator loop mirrors
     control_impact.cis_bfs_panel exactly (mask target edges from the
     graph's COO arrays, rebuild CSR, 4-source BFS, S-ratio); the COO
     conversion is hoisted out of the loop for memory/speed.
     EQUIVALENCE GATE: the hoisted loop is first run on the THRESHOLDED
     graph for 24 sample pair-nodes and must reproduce the stored
     per-node CIS in results/tables/e10_ckpt_real.parquet (the frozen
     estimator's own output) to <1e-12 — otherwise the run aborts.
  4. COMPARISON: delta_nothr vs (a) the thresholded observed delta
     (recomputed in-script from e10_ckpt_real.parquet and cross-checked
     against results/final/e10b_final.json) and (b) the frozen 100-null
     ensemble results/tables/e10b_nulls.csv.

Outputs (new files only; nothing overwritten or deleted):
  data/processed/e13b_nothr_pairs.parquet     (collapsed no-threshold pairs;
                                               processed intermediate, not
                                               a results table)
  results/tables/e13b_nothr_edge_stats.json   (graph delta summary)
  results/tables/e13b_ckpt_nothr_real.parquet (checkpointed CIS, resumable)
  results/tables/e13b_nothr_results.json      (final statistics + verdict)

Run:  py -3.13 scripts/run_e13b_nothreshold_sensitivity.py
(from the repo root; needs the Python 3.13 env with pandas/numpy/scipy)
"""
from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TABLES = ROOT / "results" / "tables"
PROCESSED = ROOT / "data" / "processed"
NOTHR = ROOT / "connections_princeton_no_threshold.csv.gz"

CHUNK_ROWS = 2_000_000
BLOCK_CHUNKS = 8          # vectorized reduce every ~16M raw rows
EQUIV_N = 24              # equivalence-gate sample size
CHUNK_TARGETS = 100       # checkpoint cadence


def log(msg: str) -> None:
    print(f"[e13b] {time.strftime('%H:%M:%S')} {msg}", flush=True)


# ------------------------------------------------------- frozen universe
def frozen_universe() -> tuple[np.ndarray, np.ndarray]:
    """(sorted universe root_ids, universe->frozen-local-index map)."""
    gp = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    universe = (pd.Index(gp["pre_root_id"].unique())
                .union(pd.Index(gp["post_root_id"].unique())).sort_values())
    del gp
    nodes = pd.Index(_frozen_node_order())
    loc = nodes.get_indexer(universe)
    assert (loc >= 0).all(), "universe member missing from frozen node order"
    return universe.to_numpy(), loc


def _frozen_node_order() -> np.ndarray:
    gp = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    nodes = pd.unique(pd.concat([gp["pre_root_id"], gp["post_root_id"]]))
    del gp
    return nodes


# ------------------------------------------------------- chunked collapse
def collapse_nothr_pairs() -> pd.DataFrame:
    """Memory-safe pair-collapse of the no-threshold table within the
    frozen universe. Key packing uses LOCAL indices (< 2^31 each), so
    (pre << 32) | post is int64-safe (root_ids themselves are NOT packed)."""
    out_path = PROCESSED / "e13b_nothr_pairs.parquet"
    if out_path.exists():
        log(f"reusing {out_path.name} (delete to force rebuild)")
        return pd.read_parquet(out_path)

    uni_sorted, loc = frozen_universe()
    n_uni = len(uni_sorted)
    log(f"frozen universe: {n_uni:,} nodes")

    acc_k: list[np.ndarray] = []
    acc_s: list[np.ndarray] = []
    keys_list: list[np.ndarray] = []
    syns_list: list[np.ndarray] = []
    n_rows = 0
    t0 = time.perf_counter()

    def reduce_block() -> None:
        K = np.concatenate(keys_list)
        S = np.concatenate(syns_list)
        Ku, inv = np.unique(K, return_inverse=True)
        Su = np.bincount(inv, weights=S.astype(np.float64)).astype(np.int64)
        if acc_k:
            K2 = np.concatenate([acc_k[0], Ku])
            S2 = np.concatenate([acc_s[0], Su])
            Ku2, inv2 = np.unique(K2, return_inverse=True)
            Su2 = np.bincount(inv2, weights=S2.astype(np.float64)).astype(np.int64)
            acc_k.clear(); acc_s.clear()
            acc_k.append(Ku2); acc_s.append(Su2)
        else:
            acc_k.append(Ku); acc_s.append(Su)
        keys_list.clear(); syns_list.clear()

    with gzip.open(NOTHR, "rt") as f:
        header = f.readline().rstrip("\n").split(",")
        ic = {c: i for i, c in enumerate(header)}
        ci_pre, ci_post, ci_syn = ic["pre_root_id"], ic["post_root_id"], ic["syn_count"]
        reader = pd.read_csv(f, header=None, names=header, chunksize=CHUNK_ROWS,
                             usecols=[ci_pre, ci_post, ci_syn])
        for chunk in reader:
            n_rows += len(chunk)
            pre_v = chunk.iloc[:, 0].to_numpy()
            post_v = chunk.iloc[:, 1].to_numpy()
            syn_v = chunk.iloc[:, 2].to_numpy()
            pi = np.searchsorted(uni_sorted, pre_v)
            qi = np.searchsorted(uni_sorted, post_v)
            pi_c = np.minimum(pi, n_uni - 1)
            qi_c = np.minimum(qi, n_uni - 1)
            ok = (uni_sorted[pi_c] == pre_v) & (uni_sorted[qi_c] == post_v)
            if ok.any():
                p = loc[pi_c[ok]].astype(np.int64)
                q = loc[qi_c[ok]].astype(np.int64)
                keys_list.append((p << 32) | q)
                syns_list.append(syn_v[ok].astype(np.int64))
            if len(keys_list) >= BLOCK_CHUNKS:
                reduce_block()
                log(f"rows={n_rows:,} unique_pairs={len(acc_k[0]):,} "
                    f"elapsed={time.perf_counter() - t0:.0f}s")
    if keys_list:
        reduce_block()

    K = np.sort(acc_k[0])
    S = acc_s[0][np.argsort(acc_k[0])] if False else None  # (replaced below)
    order = np.argsort(acc_k[0])
    K = acc_k[0][order]
    S = acc_s[0][order]
    out = pd.DataFrame({
        "pre_local": (K >> 32).astype(np.int32),
        "post_local": (K & 0xFFFFFFFF).astype(np.int32),
        "syn_count_total": S,
    })
    out.to_parquet(out_path, index=False)
    log(f"scan done: {n_rows:,} rows -> {len(out):,} unique pairs "
        f"({time.perf_counter() - t0:.0f}s); wrote {out_path.name}")
    return out


def nothr_edge_stats(out: pd.DataFrame) -> dict:
    """How much does the no-threshold table add over the thresholded one?"""
    import scipy.sparse as sp  # noqa: F401  (kept for parity of imports)

    gp = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    uni_sorted, loc = frozen_universe()
    p = loc[np.searchsorted(uni_sorted, gp["pre_root_id"].to_numpy())]
    q = loc[np.searchsorted(uni_sorted, gp["post_root_id"].to_numpy())]
    thr_keys = np.sort((p.astype(np.int64) << 32) | q.astype(np.int64))
    nk = (out["pre_local"].to_numpy().astype(np.int64) << 32) \
        | out["post_local"].to_numpy().astype(np.int64)
    nothr_keys = np.sort(nk)
    common = np.intersect1d(thr_keys, nothr_keys, assume_unique=True).size
    return {
        "thresholded_pairs": int(len(gp)),
        "nothr_pairs": int(len(out)),
        "added_pairs_vs_thresholded": int(len(nothr_keys) - common),
        "frac_added": float((len(nothr_keys) - common) / len(gp)),
        "thresholded_syn_total": int(gp["syn_count_total"].sum()),
        "nothr_syn_total": int(out["syn_count_total"].sum()),
    }


# ------------------------------------------------- estimator (hoisted twin)
def hoisted_panel_cis(row: np.ndarray, col: np.ndarray, data: np.ndarray,
                      n: int, targets: list[int], k: int = 4, seed: int = 0
                      ) -> pd.DataFrame:
    """Bit-identical twin of control_impact.cis_bfs_panel with the COO
    conversion hoisted (A.tocoo() once here instead of per call)."""
    import scipy.sparse as sp

    from src.experiments.control_impact import (
        inv_sum_from_distances, rebuild_csr, reach_count_from_distances)

    rng = np.random.default_rng(seed)
    kk = min(k, n)
    sources = np.sort(rng.choice(n, size=kk, replace=False))

    A0 = sp.csr_matrix((data, (row, col)), shape=(n, n))
    D0 = sp.csgraph.dijkstra(A0, directed=True, unweighted=True,
                             indices=sources)
    S0 = inv_sum_from_distances(D0)
    R0 = reach_count_from_distances(D0)

    A_coo = A0.tocoo()
    r, c, d = A_coo.row, A_coo.col, A_coo.data
    del A0, A_coo

    rows = []
    for t in targets:
        m = (r != t) & (c != t)
        A_t = rebuild_csr(r[m], c[m], d[m], n)
        D1 = sp.csgraph.dijkstra(A_t, directed=True, unweighted=True,
                                 indices=sources)
        S1 = inv_sum_from_distances(D1)
        R1 = reach_count_from_distances(D1)
        rows.append({
            "target": int(t),
            "cis": 1.0 - S1 / S0 if S0 > 0 else 0.0,
            "reach_drop": (R0 - R1) / (n * (n - 1)),
            "S_panel_baseline": S0,
            "S_panel_perturbed": S1,
        })
    return pd.DataFrame(rows)


def coo_of(A) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    A_coo = A.tocoo()
    return A_coo.row, A_coo.col, A_coo.data, A.shape[0]


# ------------------------------------------------------------------ main
def main() -> None:
    t0 = time.perf_counter()

    # ---------- sanity anchor: recompute the thresholded observed statistic
    final = json.loads((ROOT / "results" / "final" / "e10b_final.json")
                       .read_text())
    real = pd.read_parquet(TABLES / "e10_ckpt_real.parquet")
    from src.experiments.run_e07_e09 import cliffs_delta
    from src.experiments.run_e10 import matched_pair_nodes

    g_t, c_t = matched_pair_nodes()
    g_vals = real[real["target"].isin(g_t)]["cis"].to_numpy()
    c_vals = real[real["target"].isin(c_t)]["cis"].to_numpy()
    obs_thr = {
        "median_gaba": float(np.median(g_vals)),
        "median_ctrl": float(np.median(c_vals)),
        "median_diff": float(np.median(g_vals) - np.median(c_vals)),
        "cliffs_delta": cliffs_delta(g_vals, c_vals),
    }
    d_ref = float(final["observed"]["cliffs_delta"])
    log(f"sanity: thresholded delta recomputed={d_ref:.6f} (recomputed="
        f"{obs_thr['cliffs_delta']:.6f}, match="
        f"{abs(obs_thr['cliffs_delta'] - d_ref) < 1e-9})")
    if abs(obs_thr["cliffs_delta"] - d_ref) >= 1e-9:
        log("FATAL: recomputed observed delta does not match frozen value; "
            "aborting.")
        sys.exit(2)

    # ---------- pair collapse + edge stats
    pairs = collapse_nothr_pairs()
    stats = nothr_edge_stats(pairs)
    log(json.dumps(stats, indent=2))
    (TABLES / "e13b_nothr_edge_stats.json").write_text(
        json.dumps(stats, indent=2))

    # ---------- equivalence gate on the THRESHOLDED graph
    from src.experiments.run_e06 import build_graph

    A_thr, _nodes, _idx = build_graph()
    rng_gate = np.random.default_rng(0)
    gate_targets = sorted(rng_gate.choice(g_t, size=EQUIV_N // 2,
                                          replace=False).tolist())
    gate_targets += sorted(rng_gate.choice(c_t, size=EQUIV_N // 2,
                                           replace=False).tolist())
    gate_targets = sorted(set(gate_targets))
    r, c, d, n = coo_of(A_thr)
    gate = hoisted_panel_cis(r, c, d, n, gate_targets, k=4, seed=0)
    ref = real.set_index("target").loc[gate_targets, "cis"].to_numpy()
    got = gate.set_index("target").loc[gate_targets, "cis"].to_numpy()
    max_dev = float(np.max(np.abs(got - ref)))
    log(f"equivalence gate: {len(gate_targets)} targets, max|dcis|={max_dev:.3e}")
    if max_dev >= 1e-12:
        log("FATAL: hoisted estimator does not reproduce frozen values.")
        sys.exit(3)

    # ---------- no-threshold graph
    import scipy.sparse as sp

    n_nodes = A_thr.shape[0]
    del A_thr, r, c, d
    A_nothr = sp.csr_matrix(
        (np.ones(len(pairs), dtype=np.float64),
         (pairs["pre_local"].to_numpy(), pairs["post_local"].to_numpy())),
        shape=(n_nodes, n_nodes))
    A_nothr.data[:] = 1.0
    log(f"no-threshold graph: n={A_nothr.shape[0]:,} m={A_nothr.nnz:,}")
    r, c, d, n = coo_of(A_nothr)
    del A_nothr

    # ---------- panel CIS on the 1,696 matched-pair nodes (checkpointed)
    all_pair_nodes = sorted(set(g_t.tolist()) | set(c_t.tolist()))
    log(f"matched-pair nodes: {len(all_pair_nodes)} "
        f"({len(g_t)} GABA + {len(c_t)} ACh)")

    ck = TABLES / "e13b_ckpt_nothr_real.parquet"
    rows: list[dict] = []
    done: set[int] = set()
    if ck.exists():
        old = pd.read_parquet(ck)
        rows = old.to_dict("records")
        done = set(old["target"])
        log(f"resuming: {len(done)}/{len(all_pair_nodes)} already done")
    todo = [t for t in all_pair_nodes if t not in done]

    for s in range(0, len(todo), CHUNK_TARGETS):
        chunk = todo[s:s + CHUNK_TARGETS]
        res = hoisted_panel_cis(r, c, d, n, chunk, k=4, seed=0)
        rows.extend(res.to_dict("records"))
        pd.DataFrame(rows).to_parquet(ck, index=False)
        el = time.perf_counter() - t0
        log(f"{len(rows)}/{len(all_pair_nodes)} ({el:.0f}s elapsed, "
            f"eta {el / max(len(rows), 1) * (len(all_pair_nodes) - len(rows)) / 60:.0f} min)")

    cis_df = pd.DataFrame(rows)

    # ---------- statistic on the same 848 pairs
    g = cis_df[cis_df["target"].isin(g_t)]["cis"].to_numpy()
    c = cis_df[cis_df["target"].isin(c_t)]["cis"].to_numpy()
    stat = {
        "median_gaba": float(np.median(g)),
        "median_ctrl": float(np.median(c)),
        "median_diff": float(np.median(g) - np.median(c)),
        "cliffs_delta": cliffs_delta(g, c),
        "n_g": int(len(g)), "n_c": int(len(c)),
    }
    log(f"no-threshold observed: {json.dumps(stat)}")

    # ---------- comparison vs thresholded observed + frozen null ensemble
    nulls = pd.read_csv(TABLES / "e10b_nulls.csv")
    null_delta = nulls["cliffs_delta"].to_numpy()
    p_delta = float((1 + int((null_delta >= stat["cliffs_delta"]).sum()))
                    / (len(null_delta) + 1))
    p_median = float((1 + int((nulls["median_diff"].to_numpy()
                               >= stat["median_diff"]).sum()))
                      / (len(nulls) + 1))
    z = float((stat["cliffs_delta"] - null_delta.mean())
              / null_delta.std(ddof=1))

    out = {
        "experiment": "E13.6b-nothreshold-sensitivity",
        "date": time.strftime("%Y-%m-%d"),
        "protocol": {
            "estimator": "cis_bfs_panel twin (equivalence-gated, max|dcis|"
                         f"={max_dev:.2e})",
            "k_panel": 4, "panel_seed": 0,
            "matched_pairs": "E08 848 pairs (pre-registered)",
            "node_universe": "frozen thresholded-graph universe (138,584 nodes)",
            "edge_table": "connections_princeton_no_threshold.csv.gz",
            "memory_strategy": "chunked load, vectorized pair-collapse; "
                               "peak RSS < 1 GB",
        },
        "edge_stats": stats,
        "observed_nothr": stat,
        "observed_thresholded_recomputed": obs_thr,
        "observed_thresholded_frozen": final["observed"],
        "equivalence_gate": {
            "n_targets": len(gate_targets), "max_abs_dcis": max_dev,
            "threshold": 1e-12, "passed": True,
        },
        "null_comparison": {
            "n_nulls": int(len(nulls)),
            "null_delta_mean": float(null_delta.mean()),
            "null_delta_sd": float(null_delta.std(ddof=1)),
            "p_delta_nothr_vs_nulls": p_delta,
            "p_median_nothr_vs_nulls": p_median,
            "z_vs_null": z,
        },
        "runtime_s": round(time.perf_counter() - t0, 1),
        "verdict_note": ("same degree-preserving-null comparison as E10B: "
                         "p_delta >= 0.05 => the GABA-vs-ACh effect is again "
                         "compatible with degree-preserving structure under "
                         "the no-threshold edge definition"),
    }
    (TABLES / "e13b_nothr_results.json").write_text(json.dumps(out, indent=2))
    log(f"wrote results/tables/e13b_nothr_results.json "
        f"(delta={stat['cliffs_delta']:.4f}, p_delta={p_delta:.3f})")
    log(f"done in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
