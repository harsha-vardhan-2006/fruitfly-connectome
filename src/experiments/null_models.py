"""Experiment 4 (staged for Week 5): degree-preserving null models.

Maslov-Sneppen edge-swap randomization preserving the degree sequence;
per-neuron and per-class z-scores of control-impact and motif counts
against the null ensemble. FDR correction via Benjamini-Hochberg.

NOT yet executed — implemented in advance so the Week-5 run is scripted and
pre-registered. Run:  py -m src.experiments.null_models
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp


def maslov_sneppen_rewire(A: sp.csr_matrix, n_swaps_factor: int = 10,
                          seed: int = 0) -> sp.csr_matrix:
    """Rewire edges preserving in/out degree (Maslov & Sneppen 2002).

    Repeatedly picks two edges (u1->v1), (u2->v2) and swaps targets to
    (u1->v2), (u2->v1) when the result creates no self-loop or duplicate.
    Vectorized precompute of edge lists; swaps in a Python loop (fine for
    staged experiments; optimize later if profiling demands).
    """
    rng = np.random.default_rng(seed)
    A = A.tocoo()
    u, v = A.row.astype(np.int64), A.col.astype(np.int64)
    m = len(u)
    n_swaps = m * n_swaps_factor
    edge_set = set(zip(u.tolist(), v.tolist()))

    for _ in range(n_swaps):
        i1, i2 = rng.integers(0, m, size=2)
        u1, v1, u2, v2 = u[i1], v[i1], u[i2], v[i2]
        if u1 == u2 or v1 == v2:
            continue  # would create duplicate source/target patterns
        e1, e2 = (int(u1), int(v1)), (int(u2), int(v2))
        n1, n2 = (int(u1), int(v2)), (int(u2), int(v1))
        if n1[0] == n1[1] or n2[0] == n2[1]:
            continue  # self-loop
        if n1 in edge_set or n2 in edge_set:
            continue  # duplicate edge
        edge_set.discard(e1); edge_set.discard(e2)
        edge_set.add(n1); edge_set.add(n2)
        u[i1], v[i1], u[i2], v[i2] = u1, v2, u2, v1

    data = np.ones(m, dtype=np.float64)
    return sp.csr_matrix((data, (u, v)), shape=A.shape)


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    """BH-FDR corrected q-values."""
    p = np.asarray(pvals, dtype=np.float64)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(n)
    q[order] = np.clip(ranked, 0, 1)
    return q


def null_zscore(real_stat: float, null_stats: np.ndarray) -> tuple[float, float]:
    """z-score and two-sided permutation p-value against null ensemble."""
    mu, sd = null_stats.mean(), null_stats.std(ddof=1)
    z = (real_stat - mu) / sd if sd > 0 else 0.0
    p = 2 * min((null_stats >= real_stat).mean(), (null_stats <= real_stat).mean())
    p = max(p, 1.0 / (len(null_stats) + 1))
    return float(z), float(p)


def main() -> None:  # pragma: no cover - staged experiment
    raise NotImplementedError(
        "E04 runs in Week 5 after E03 chokepoint results. Functions are "
        "implemented and unit-testable; execution is pre-registered in "
        "RESEARCH_LOG.md."
    )


if __name__ == "__main__":
    main()
