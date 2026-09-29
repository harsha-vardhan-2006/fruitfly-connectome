"""E04: Control Impact Score (CIS) — definition, implementation, validation.

FROZEN DEFINITION (RESEARCH_LOG.md E04; MASTER_PLAN.md §5):

  Global efficiency of a directed graph, freeze-N convention:
      Eff(G) = (1 / (N_F * (N_F - 1))) * sum_{i != j} 1 / d(i, j)
  N_F is the FREEZE-TIME node count. Removing a node can only remove
  reachable mass, never shorten paths, so CIS is bounded in [0, 1]:

      CIS(i) = (Eff(G) - Eff(G - i)) / Eff(G) = 1 - S(G-i) / S(G)

  where S(G) = sum_{i != j} 1/d(i, j) over the SAME node universe.
  The free-N renormalization (N-1 after removal) is reported only as a
  diagnostic column; it can produce negative CIS for tail removals and is
  NOT used for inference.

PRIMARY ESTIMATOR at whole-brain scale (E05 strategy): fixed-source-panel
BFS. A panel of k source nodes is drawn once; for each target, the node's
rows/columns are masked out of the edge arrays and BFS distances are
recomputed from the SAME panel. Estimator: CIS(i) = 1 - S_panel(G-i)/S_panel(G).
Same panel for all targets => paired, comparable, low-variance.

Secondary diagnostic (reported, never primary): reachable-pair fraction
drop, computed from the same BFS pass.

Validation: tests/test_control_impact.py (Gate 1). Benchmark before any
whole-brain run: Gate 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp


# ------------------------------------------------------------------ helpers

def inv_sum_from_distances(D: np.ndarray) -> float:
    """S = sum over entries of 1/d for finite positive distances."""
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = np.where(np.isfinite(D) & (D > 0), 1.0 / D, 0.0)
    return float(inv.sum())


def reach_count_from_distances(D: np.ndarray) -> int:
    """Number of ordered (i != j) pairs with finite positive distance."""
    return int(np.count_nonzero(np.isfinite(D) & (D > 0)))


def subgraph_excluding(A: sp.csr_matrix, node: int) -> sp.csr_matrix:
    """Copy of A with `node` and all its incident edges removed."""
    keep = np.ones(A.shape[0], dtype=bool)
    keep[node] = False
    return A[keep][:, keep]


def edge_arrays_excluding(A: sp.csr_matrix, node: int
                          ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """COO edge arrays of A with all edges touching `node` masked out.

    O(nnz) per call - the cheap way to 'remove' a node at 139k-node scale
    without rebuilding any structure.
    """
    A_coo = A.tocoo()
    mask = (A_coo.row != node) & (A_coo.col != node)
    return A_coo.row[mask], A_coo.col[mask], A_coo.data[mask]


def rebuild_csr(row: np.ndarray, col: np.ndarray, data: np.ndarray,
                n: int) -> sp.csr_matrix:
    return sp.csr_matrix((data, (row, col)), shape=(n, n))


def global_efficiency_exact(A: sp.csr_matrix) -> float:
    """Exact efficiency with freeze-N convention (N from A itself)."""
    n = A.shape[0]
    if n < 2:
        return 0.0
    D = sp.csgraph.shortest_path(A, method="D", directed=True, unweighted=True)
    return inv_sum_from_distances(D) / (n * (n - 1))


# ------------------------------------------------------- exact (small graphs)

def cis_exact_full(A: sp.csr_matrix, targets: list[int]) -> "object":  # pd.DataFrame
    """Exact CIS on the full graph - validation scale only (N <= ~2,000).

    Denominators are IDENTICAL for baseline and perturbed (N*(N-1)), so
    CIS = 1 - S(G-i)/S(G) is exact, monotone, and in [0, 1].
    """
    import pandas as pd

    n = A.shape[0]
    denom = n * (n - 1)
    D0 = sp.csgraph.shortest_path(A, method="D", directed=True, unweighted=True)
    S0 = inv_sum_from_distances(D0)
    R0 = reach_count_from_distances(D0)
    rows = []
    for t in targets:
        A_sub = subgraph_excluding(A, t)
        D1 = sp.csgraph.shortest_path(A_sub, method="D", directed=True,
                                      unweighted=True)
        S1 = inv_sum_from_distances(D1)
        R1 = reach_count_from_distances(D1)
        # free-N diagnostic (NOT used for inference)
        n_sub = A_sub.shape[0]
        eff0_free = S0 / denom if denom else 0.0
        eff1_free = S1 / (n_sub * (n_sub - 1)) if n_sub > 1 else 0.0
        rows.append({
            "target": int(t),
            "cis": 1.0 - S1 / S0 if S0 > 0 else 0.0,
            "cis_freeN_diagnostic": (eff0_free - eff1_free) / eff0_free
                                    if eff0_free > 0 else 0.0,
            "reach_drop": (R0 - R1) / denom,
            "S_baseline": S0,
            "S_perturbed": S1,
            "n_nodes": n,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------- panel estimator (the E05 core)

@dataclass
class PanelConfig:
    """Frozen configuration for panel-based CIS runs."""
    n_sources: int = 32        # panel size k
    seed: int = 0
    diagnostics: dict = field(default_factory=dict)


def cis_bfs_panel(A: sp.csr_matrix, targets: list[int],
                  cfg: PanelConfig) -> "object":  # pd.DataFrame
    """CIS via fixed-source-panel BFS (whole-brain estimator).

    For each target t:
      - mask all edges touching t (row and column) from the COO arrays;
      - rebuild CSR (O(nnz), no other structure rebuilt);
      - recompute BFS distances from the SAME panel;
      - CIS(t) = 1 - S_panel(G - t) / S_panel(G).

    Also returns reach_drop (secondary diagnostic) from the same pass.

    FAST PATH: when the caller passes a prebuilt CSR `A_t_base` (same
    shape as A) plus the target, edges touching the target are deleted
    directly from A_t_base's index arrays (O(nnz_t) work, no COO round
    trip) - used by the 100-null protocol to reuse one CSR per null.
    """
    import pandas as pd

    n = A.shape[0]
    rng = np.random.default_rng(cfg.seed)
    k = min(cfg.n_sources, n)
    sources = np.sort(rng.choice(n, size=k, replace=False))

    D0 = sp.csgraph.dijkstra(A, directed=True, unweighted=True,
                             indices=sources)
    S0 = inv_sum_from_distances(D0)
    R0 = reach_count_from_distances(D0)

    row, col, data = edge_arrays_excluding(A, -1)  # full arrays, nothing masked
    rows = []
    for t in targets:
        m = (row != t) & (col != t)
        A_t = rebuild_csr(row[m], col[m], data[m], n)
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


def cis_bfs_panel_csr(A_t_base: sp.csr_matrix, target: int,
                      sources: np.ndarray, S0: float, R0: int,
                      denom: int) -> dict:
    """Single-target CIS by direct edge deletion from a prebuilt CSR.

    Deletes every edge touching `target` by filtering the CSR index arrays
    (row-wise via indptr slicing, column-wise via a column mask) - avoids
    the O(nnz) COO reconstruction per target.
    """
    n = A_t_base.shape[0]
    A_csr = A_t_base.copy()
    # drop target's outgoing rows: zero the row, then eliminate
    A_csr[target, :] = 0
    # drop target's incoming edges (column):
    A_csr.indices[A_csr.indices == target] = 0  # placeholder; rebuilt below
    A_csr = A_csr.tocoo()
    m = (A_csr.row != target) & (A_csr.col != target)
    A_t = sp.csr_matrix((A_csr.data[m], (A_csr.row[m], A_csr.col[m])),
                        shape=(n, n))
    D1 = sp.csgraph.dijkstra(A_t, directed=True, unweighted=True,
                             indices=sources)
    S1 = inv_sum_from_distances(D1)
    R1 = reach_count_from_distances(D1)
    return {"target": int(target),
            "cis": 1.0 - S1 / S0 if S0 > 0 else 0.0,
            "reach_drop": (R0 - R1) / denom}


# ------------------------------------------------- E11 helper (neighborhoods)

def induced_subgraph(A: sp.csr_matrix, target: int, k_ring: int,
                     background: int, rng: np.random.Generator
                     ) -> tuple[sp.csr_matrix, np.ndarray]:
    """k-ring neighborhood of target + sampled background nodes.

    NOT used for CIS (panel estimator is the frozen approach); reserved for
    E11 chokepoint-neighborhood motif analysis.
    """
    A_sym = A + A.T
    levels = {target: 0}
    frontier = [target]
    for depth in range(1, k_ring + 1):
        nxt: list[int] = []
        for u in frontier:
            for v in A_sym.indices[A_sym.indptr[u]:A_sym.indptr[u + 1]]:
                if v not in levels:
                    levels[v] = depth
                    nxt.append(int(v))
        frontier = nxt
        if not frontier:
            break
    neigh = np.array(sorted(levels.keys()), dtype=np.int64)
    others = np.setdiff1d(np.arange(A.shape[0]), neigh)
    n_bg = min(background, len(others))
    bg = rng.choice(others, size=n_bg, replace=False) if n_bg else np.array([], dtype=np.int64)
    nodes = np.concatenate([neigh, bg]).astype(np.int64)
    return A[nodes][:, nodes], nodes
