"""E06: whole-brain per-neuron perturbation (screening + rerank).

PRE-REGISTERED DESIGN (RESEARCH_LOG.md E06, registered before unblinding):
  Stage A (screen, k=8, seed=0):
    - top 1% by total degree, by in-strength, by PageRank (union)
    - ALL GABA neurons with degree >= 90th percentile of GABA degrees
      (hypothesis-relevant oversample)
    - 500 random background neurons (unbiased estimator of the CIS
      distribution; also the degree-matching pool's reference)
  Stage B (rerank, k=32, seeds 0/1 averaged):
    - top 150 by stage-A CIS + random 50 of the rest (anchor set for
      detecting screening bias)

Outputs:
  results/tables/e06_screen_k8.parquet      (full candidate CIS table)
  results/tables/e06_rerank_k32.parquet     (finalists + anchors)
  results/tables/e06_screen_summary.json
Checkpointed every 200 targets; resumable.

Run:  py -m src.experiments.run_e06
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT
from src.experiments.control_impact import PanelConfig, cis_bfs_panel

PROCESSED = PROJECT_ROOT / "data" / "processed"
TABLES = PROJECT_ROOT / "results" / "tables"
CKPT = TABLES / "e06_screen_checkpoint.parquet"


def build_graph() -> tuple[sp.csr_matrix, pd.Index, dict[int, int]]:
    pairs = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    nodes = pd.Index(pd.concat(
        [pairs["pre_root_id"], pairs["post_root_id"]])).unique()
    idx = {r: i for i, r in enumerate(nodes)}
    A = sp.csr_matrix(
        (np.ones(len(pairs)),
         (pairs["pre_root_id"].map(idx), pairs["post_root_id"].map(idx))),
        shape=(len(nodes), len(nodes)),
    )
    return A, nodes, idx


def preregister_targets(A: sp.csr_matrix, core: pd.DataFrame,
                        nodes: pd.Index, idx: dict[int, int],
                        rng_seed: int = 0) -> tuple[list[int], dict]:
    """Candidate list exactly as pre-registered. Returns (targets, manifest)."""
    rng = np.random.default_rng(rng_seed)
    n = A.shape[0]

    out_deg = np.asarray((A > 0).sum(axis=1)).ravel()
    in_deg = np.asarray((A > 0).sum(axis=0)).ravel()
    degree = out_deg + in_deg

    # PageRank on binary graph (reuse baseline implementation)
    from src.graph.baseline import pagerank
    pr = pagerank(A)

    top1 = max(1, int(0.01 * n))
    cand_deg = set(np.argsort(-degree)[:top1].tolist())
    cand_str = set(np.argsort(-(np.asarray(A.sum(axis=1)).ravel()
                                + np.asarray(A.sum(axis=0)).ravel()))[:top1].tolist())
    cand_pr = set(np.argsort(-pr)[:top1].tolist())
    union = cand_deg | cand_str | cand_pr

    # GABA oversample: GABA neurons with degree >= 90th pct of GABA degrees
    core_local = core.set_index("root_id").reindex(nodes)
    nt = core_local["nt_type"].to_numpy()
    gaba_mask = (nt == "GABA")
    gaba_idx = np.where(gaba_mask)[0]
    thr = np.percentile(degree[gaba_idx], 90) if len(gaba_idx) else np.inf
    gaba_hot = set(gaba_idx[degree[gaba_idx] >= thr].tolist())

    background = set(rng.choice(n, size=500, replace=False).tolist())

    targets = sorted(union | gaba_hot | background)
    manifest = {
        "n_total": n,
        "top1_size": top1,
        "n_union_degree_strength_pagerank": len(union),
        "gaba_degree_threshold": float(thr),
        "n_gaba_hot": len(gaba_hot - union),
        "n_background": 500,
        "n_targets_total": len(targets),
        "seed": rng_seed,
    }
    return targets, manifest


def run_screen(A: sp.csr_matrix, targets: list[int],
               k: int = 8, checkpoint_every: int = 200) -> pd.DataFrame:
    rows: list[dict] = []
    if CKPT.exists():
        old = pd.read_parquet(CKPT)
        rows = old.to_dict("records")
        done = {r["target"] for r in rows}
        targets = [t for t in targets if t not in done]
        print(f"  resuming: {len(done)} already done, {len(targets)} to go")

    t0 = time.perf_counter()
    cfg = PanelConfig(n_sources=k, seed=0)
    for start in range(0, len(targets), checkpoint_every):
        chunk = targets[start:start + checkpoint_every]
        res = cis_bfs_panel(A, targets=chunk, cfg=cfg)
        rows.extend(res.to_dict("records"))
        pd.DataFrame(rows).to_parquet(CKPT, index=False)
        el = time.perf_counter() - t0
        done_n = start + len(chunk)
        print(f"  {done_n}/{len(targets)} ({el:.0f}s elapsed, "
              f"eta {el / done_n * (len(targets) - done_n) / 60:.0f} min)")
    return pd.DataFrame(rows)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    print("[E06] building graph ...")
    A, nodes, idx = build_graph()
    core = pd.read_parquet(PROCESSED / "neuron_core.parquet")

    targets, manifest = preregister_targets(A, core, nodes, idx)
    print(f"[E06] pre-registered targets: {manifest}")
    (TABLES / "e06_preregistration.json").write_text(json.dumps(manifest, indent=2))

    print("[E06] stage A: screening at k=8 ...")
    screen = run_screen(A, targets, k=8)
    screen["root_id"] = nodes[screen["target"]].values
    screen.to_parquet(TABLES / "e06_screen_k8.parquet", index=False)

    print("[E06] stage B: rerank finalists at k=32 (seeds 0+1) ...")
    top150 = screen.nlargest(150, "cis")["target"].tolist()
    rest = screen[~screen["target"].isin(top150)]
    anchors = rest.sample(50, random_state=0)["target"].tolist()
    finalists = sorted(set(top150) | set(anchors))
    (TABLES / "e06_finalists.json").write_text(json.dumps(
        {"top150": top150, "anchors": anchors}, indent=2))
    rr_parts = []
    for seed in (0, 1):
        f_seed = TABLES / f"e06_rerank_k32_seed{seed}.parquet"
        if f_seed.exists():
            rr_parts.append(pd.read_parquet(f_seed))
            print(f"  seed {seed}: loaded from checkpoint")
            continue
        parts: list[pd.DataFrame] = []
        ck_seed = TABLES / f"e06_rerank_ckpt_seed{seed}.parquet"
        if ck_seed.exists():
            parts = [pd.read_parquet(ck_seed)]
            print(f"  seed {seed}: resuming from {len(parts[0])} rows")
        done = set(parts[0]["target"]) if parts else set()
        todo = [t for t in finalists if t not in done]
        CH = 80
        for s in range(0, len(todo), CH):
            chunk = todo[s:s + CH]
            part = cis_bfs_panel(A, targets=chunk,
                                 cfg=PanelConfig(n_sources=32, seed=seed)).assign(seed=seed)
            parts.append(part)
            pd.concat(parts, ignore_index=True).to_parquet(ck_seed, index=False)
            print(f"  seed {seed}: {min(s + CH, len(todo))}/{len(todo)}")
        part_all = pd.concat(parts, ignore_index=True)
        part_all.to_parquet(f_seed, index=False)
        rr_parts.append(part_all)
        print(f"  seed {seed}: computed and saved")
    rr = pd.concat(rr_parts, ignore_index=True)
    rr_summary = (rr.groupby("target")
                  .agg(cis_mean=("cis", "mean"), cis_std=("cis", "std"),
                       reach_drop_mean=("reach_drop", "mean"))
                  .reset_index())
    rr_summary["root_id"] = nodes[rr_summary["target"]].values
    rr_summary.to_parquet(TABLES / "e06_rerank_k32.parquet", index=False)

    summary = {
        "screen": {
            "n": len(screen),
            "cis_median": float(screen["cis"].median()),
            "cis_p90": float(screen["cis"].quantile(0.9)),
            "cis_p99": float(screen["cis"].quantile(0.99)),
            "cis_max": float(screen["cis"].max()),
        },
        "rerank": {
            "n": len(rr_summary),
            "spearman_screen_vs_rerank": float(
                screen.set_index("target").loc[rr_summary["target"], "cis"]
                .corr(rr_summary.set_index("target")["cis_mean"], method="spearman")
            ),
        },
    }
    (TABLES / "e06_screen_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("[E06] done.")


if __name__ == "__main__":
    main()
