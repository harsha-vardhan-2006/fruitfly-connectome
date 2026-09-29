"""E10: degree-preserving null models (pilot: N=5 nulls, k=4 panel).

PILOT SCALE (documented): the user roadmap specifies 500 nulls eventually;
this run is the feasibility pilot (benchmark-then-scale, per E10.3).
Per null:
  1. directed configuration model preserving BOTH degree sequences exactly
     (vectorized stub matching + conflict repair);
  2. same matched pairs as E08 (degree sequences identical => the exact
     same 848 pre-registered pairs are available);
  3. panel CIS (k=4, seed=0) for all pair nodes, checkpointed;
  4. statistic: median(CIS_GABA) - median(CIS_ACh) over matched pairs
     + Cliff's delta.
Observed (real network) statistic compared against the null ensemble.

Run:  py -m src.experiments.run_e10
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
N_NULLS = 5
K_PANEL = 4


def config_model_null(A: sp.csr_matrix, seed: int) -> sp.csr_matrix:
    """Directed configuration model: preserves in- and out-degree sequences
    exactly; rewires via random stub matching with swap repair for
    self-loops and duplicate edges."""
    rng = np.random.default_rng(seed)
    n = A.shape[0]
    A_coo = A.tocoo()
    out_deg = np.asarray((A > 0).sum(axis=1)).ravel().astype(np.int64)
    in_deg = np.asarray((A > 0).sum(axis=0)).ravel().astype(np.int64)

    src = np.repeat(np.arange(n), out_deg)
    tgt_pool = np.repeat(np.arange(n), in_deg)
    tgt = rng.permutation(tgt_pool)

def _repair_permutation(src: np.ndarray, tgt_pool: np.ndarray, n: int,
                        rng: np.random.Generator, rounds: int = 300) -> np.ndarray | None:
    """One stub-matching draw + swap repair. Returns a repaired target array
    with EXACT in-degree preservation, or None if repair did not converge.

    Convergence failure mode (seen only on adversarial graphs): a single
    defect can enter a limit cycle under random 2-swaps. The caller redraws
    a fresh permutation on failure (rejection sampling); every ACCEPTED draw
    has exact degree sequences, which is the property the null requires.
    """
    tgt = rng.permutation(tgt_pool)
    for _ in range(rounds):
        self_loop = src == tgt
        keys = src.astype(np.int64) * n + tgt
        # mark every occurrence after the first of each duplicated (src,tgt)
        later_dup = pd.Series(keys).duplicated(keep="first").to_numpy()
        bad = np.where(self_loop | later_dup)[0]
        if len(bad) == 0:
            return tgt
        pool = rng.permutation(len(tgt))
        pool = pool[~np.isin(pool, bad)]
        if len(pool) < len(bad):
            return None
        swap_with = pool[:len(bad)]
        tgt[bad], tgt[swap_with] = tgt[swap_with].copy(), tgt[bad].copy()
    return None


def config_model_null(A: sp.csr_matrix, seed: int) -> sp.csr_matrix:
    """Directed configuration model: preserves in- and out-degree sequences
    exactly; rewires via random stub matching with swap repair for
    self-loops and duplicate edges. Non-converged repair rounds trigger a
    fresh permutation draw (max 20 attempts; deterministic given seed)."""
    rng = np.random.default_rng(seed)
    n = A.shape[0]
    out_deg = np.asarray((A > 0).sum(axis=1)).ravel().astype(np.int64)
    in_deg = np.asarray((A > 0).sum(axis=0)).ravel().astype(np.int64)

    src = np.repeat(np.arange(n), out_deg)
    tgt_pool = np.repeat(np.arange(n), in_deg)

    for _attempt in range(20):
        tgt = _repair_permutation(src, tgt_pool, n, rng)
        if tgt is not None:
            break
    else:
        raise RuntimeError("config_model_null: no draw converged in 20 attempts")
    # final safety check: multiset (in-degree sequence) must be intact
    if not np.array_equal(np.bincount(tgt, minlength=n), in_deg):
        raise RuntimeError("config_model_null: in-degree sequence corrupted")
    return sp.csr_matrix((np.ones(len(src)), (src, tgt)), shape=(n, n))


def matched_pair_nodes() -> tuple[np.ndarray, np.ndarray]:
    """The 848 pre-registered matched pairs from E08."""
    m = pd.read_csv(TABLES / "e08_matched_pairs.csv")
    return m["gaba_target"].to_numpy(), m["ctrl_target"].to_numpy()


def panel_cis_for_nodes(A: sp.csr_matrix, targets: list[int], tag: str,
                        k: int = K_PANEL) -> pd.DataFrame:
    """Checkpointed panel CIS for a list of nodes."""
    from src.experiments.control_impact import PanelConfig, cis_bfs_panel
    ck = TABLES / f"e10_ckpt_{tag}.parquet"
    rows = []
    done: set[int] = set()
    if ck.exists():
        old = pd.read_parquet(ck)
        rows = old.to_dict("records")
        done = set(old["target"])
        targets = [t for t in targets if t not in done]
    cfg = PanelConfig(n_sources=k, seed=0)
    CH = 100
    t0 = time.perf_counter()
    for s in range(0, len(targets), CH):
        chunk = targets[s:s + CH]
        res = cis_bfs_panel(A, targets=chunk, cfg=cfg)
        rows.extend(res.to_dict("records"))
        pd.DataFrame(rows).to_parquet(ck, index=False)
        el = time.perf_counter() - t0
        dn = s + len(chunk)
        print(f"    [{tag}] {dn}/{len(targets)} ({el:.0f}s, "
              f"eta {el / max(dn, 1) * (len(targets) - dn) / 60:.0f} min)", flush=True)
    return pd.DataFrame(rows)


def statistic_from_cis(cis_df: pd.DataFrame, gaba_t: np.ndarray,
                       ctrl_t: np.ndarray) -> dict:
    g = cis_df[cis_df["target"].isin(gaba_t)]["cis"].to_numpy()
    c = cis_df[cis_df["target"].isin(ctrl_t)]["cis"].to_numpy()
    from src.experiments.run_e07_e09 import cliffs_delta
    return {"median_gaba": float(np.median(g)),
            "median_ctrl": float(np.median(c)),
            "median_diff": float(np.median(g) - np.median(c)),
            "cliffs_delta": cliffs_delta(g, c),
            "n_g": len(g), "n_c": len(c)}


def main() -> None:
    from src.experiments.run_e06 import build_graph
    A, nodes, idx = build_graph()
    gaba_t, ctrl_t = matched_pair_nodes()
    all_pair_nodes = sorted(set(gaba_t.tolist()) | set(ctrl_t.tolist()))
    print(f"[E10] {len(all_pair_nodes)} pair nodes; {N_NULLS} nulls at k={K_PANEL}")

    # observed statistic (real network, SAME k for comparability)
    obs_cis = panel_cis_for_nodes(A, all_pair_nodes, "real")
    obs = statistic_from_cis(obs_cis, gaba_t, ctrl_t)
    print(f"[E10] observed (k={K_PANEL}): {obs}")

    nulls = []
    for i in range(N_NULLS):
        tag = f"null{i}"
        print(f"[E10] null {i + 1}/{N_NULLS} ...")
        t0 = time.perf_counter()
        An = config_model_null(A, seed=100 + i)
        print(f"    rewired in {time.perf_counter() - t0:.0f}s "
              f"({An.nnz} edges)")
        cis_n = panel_cis_for_nodes(An, all_pair_nodes, tag)
        st = statistic_from_cis(cis_n, gaba_t, ctrl_t)
        st["null_id"] = i
        nulls.append(st)
        print(f"    statistic: {st}")
        pd.DataFrame(nulls).to_csv(TABLES / "e10_nulls_checkpoint.csv", index=False)

    nd = pd.DataFrame(nulls)
    p_delta = (1 + int((nd["cliffs_delta"] >= obs["cliffs_delta"]).sum())) / (N_NULLS + 1)
    p_diff = (1 + int((nd["median_diff"] >= obs["median_diff"]).sum())) / (N_NULLS + 1)
    out = {
        "pilot_scale": {"n_nulls": N_NULLS, "k_panel": K_PANEL,
                        "n_pair_nodes": len(all_pair_nodes)},
        "observed_k4": obs,
        "nulls": nulls,
        "null_delta_mean": float(nd["cliffs_delta"].mean()),
        "null_delta_sd": float(nd["cliffs_delta"].std(ddof=1)),
        "null_median_diff_mean": float(nd["median_diff"].mean()),
        "empirical_p_delta": p_delta,
        "empirical_p_median_diff": p_diff,
        "verdict_note": "pilot: directional Gate-4 evidence only; full "
                        "protocol = 500 nulls at k=8-32 before publication",
    }
    (TABLES / "e10_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "nulls"}, indent=2))


if __name__ == "__main__":
    main()
