"""Experiment 3 (staged for Week 4): chokepoint perturbation analysis.

Design per RESEARCH_LOG.md E03 and research_plan.md Part 8:

  Control Impact Score (CIS):
      CIS(i) = (perf(G) - perf(G - i)) / perf(G)
  where perf = global network efficiency (mean over node pairs of
  1/shortest_path_length, harmonically weighted by synapse strength).

  Targets : top 1% / 5% / 10% by each centrality measure (degree,
            in/out strength, PageRank, sampled betweenness).
  Controls: degree-matched excitatory neurons for each inhibitory target
            (±10% degree window), to test whether inhibitory identity
            predicts CIS beyond topology.
  Nulls   : degree-preserving Maslov-Sneppen rewires (see null_models.py).

NOT yet executed — this file implements the planned procedure so the
Week-4 run is scripted, reproducible, and pre-registered in the log.
Run:  py -m src.experiments.chokepoints
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT

PROCESSED = PROJECT_ROOT / "data" / "processed"
TABLES = PROJECT_ROOT / "results" / "tables"


def global_efficiency(A_bin: sp.csr_matrix, n_samples: int = 1_000,
                      seed: int = 0) -> float:
    """Sampled harmonic-mean efficiency of the unweighted digraph."""
    rng = np.random.default_rng(seed)
    n = A_bin.shape[0]
    indptr, indices = A_bin.indptr, A_bin.indices
    D = np.asarray(A_bin.sum(axis=1)).ravel()
    D[D == 0] = 1.0
    # D^-1 * A gives transition structure; BFS distances via csgraph
    dist = sp.csgraph.breadth_first_order(
        A_bin, i_start=int(rng.integers(n)), directed=True,
        return_predecessors=False,
    )
    # full pairwise is O(n^2) — sampled variant below is the default path
    sources = rng.choice(n, size=min(n_samples, n), replace=False)
    total, pairs = 0.0, 0
    Dmat = sp.csgraph.shortest_path(A_bin, method="D", directed=True,
                                    unweighted=True) if n <= 5_000 else None
    if Dmat is not None:
        inv = np.where(np.isfinite(Dmat) & (Dmat > 0), 1.0 / Dmat, 0.0)
        return float(inv.sum() / (n * (n - 1)))
    for s in sources:
        d = sp.csgraph.dijkstra(A_bin, indices=int(s), unweighted=True)
        d = d[np.isfinite(d) & (d > 0)]
        total += float(np.sum(1.0 / d))
        pairs += len(d)
    return float(total / max(pairs, 1))


def control_impact_scores(A_bin: sp.csr_matrix, targets: list[int],
                          baseline_eff: float | None = None) -> pd.DataFrame:
    """CIS for each target node by removal + efficiency re-measurement."""
    if baseline_eff is None:
        baseline_eff = global_efficiency(A_bin)
    rows = []
    for node in targets:
        keep = np.ones(A_bin.shape[0], dtype=bool)
        keep[node] = False
        A_sub = A_bin[keep][:, keep]
        eff = global_efficiency(A_sub)
        cis = (baseline_eff - eff) / baseline_eff
        rows.append({"target": int(node), "cis": cis})
    return pd.DataFrame(rows)


def degree_matched_pairs(metrics: pd.DataFrame, inhib_mask: pd.Series,
                         n_samples: int = 500, window: float = 0.10,
                         seed: int = 0) -> pd.DataFrame:
    """Match each high-impact inhibitory neuron to an excitatory control
    with degree within ±window. Returns inhib/excit root_id pairs."""
    rng = np.random.default_rng(seed)
    inh = metrics[inhib_mask]
    exc = metrics[metrics["nt_sign"] == "excitatory"]
    exc_deg = exc["degree"].to_numpy()
    exc_ids = exc["root_id"].to_numpy()
    out = []
    for _, row in inh.iterrows():
        lo, hi = row["degree"] * (1 - window), row["degree"] * (1 + window)
        cand = np.where((exc_deg >= lo) & (exc_deg <= hi))[0]
        if len(cand) == 0:
            continue
        pick = rng.choice(cand)
        out.append({"inhibitory_id": row["root_id"],
                    "control_id": exc_ids[pick],
                    "degree": row["degree"]})
    return pd.DataFrame(out)


def main() -> None:  # pragma: no cover - staged experiment
    raise NotImplementedError(
        "E03 runs in Week 4 after E02 baseline review. Functions are "
        "implemented and unit-testable; execution is pre-registered in "
        "RESEARCH_LOG.md."
    )


if __name__ == "__main__":
    main()
