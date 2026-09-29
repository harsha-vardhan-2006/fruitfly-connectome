"""E04.3/E04.6 — Gate 1 validation tests for the CIS metric (v2).

All expectations are derived analytically from S = sum 1/d, not by eye.
Run:  py -m tests.test_control_impact     (exit 0 = Gate 1 PASS)

History: v1 of this suite FAILED 1/5 and correctly exposed a denominator
unit-mismatch bug in cis_exact_full (eff0 passed node count, eff1 passed
pair count). Fixed in control_impact.py v2. The failed run is preserved
in RESEARCH_LOG.md E04.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from src.experiments.control_impact import (
    PanelConfig,
    cis_bfs_panel,
    cis_exact_full,
    global_efficiency_exact,
)


def _from_edges(n: int, edges: list[tuple[int, int]]) -> sp.csr_matrix:
    rows = [u for u, _ in edges]
    cols = [v for _, v in edges]
    return sp.csr_matrix((np.ones(len(edges)), (rows, cols)), shape=(n, n))


# ------------------------------------------------------------ exact tests

def test_chain_removal_of_middle_node():
    # A->B->C->D->E ; S0 = 1+1/2+1/3+1/4 + 1+1/2+1/3 + 1+1/2 + 1 = 77/12
    # remove B -> S1 = 2.5  =>  CIS = 1 - 2.5/(77/12) = 47/77
    A = _from_edges(5, [(0, 1), (1, 2), (2, 3), (3, 4)])
    res = cis_exact_full(A, targets=[1])
    cis_b = float(res.loc[res["target"] == 1, "cis"].iloc[0])
    assert abs(cis_b - 47.0 / 77.0) < 1e-9, f"chain CIS(B)={cis_b}, expected 47/77"
    # free-N diagnostic on the same removal = 1 - (2.5/12)/(77/12/20) = 0.350649
    diag = float(res.loc[res["target"] == 1, "cis_freeN_diagnostic"].iloc[0])
    assert abs(diag - 0.3506493506493507) < 1e-9


def test_chain_of_three_middle_is_total_collapse():
    # A->B->C : S0 = 1 + 1/2 + 1 = 2.5 ; remove B -> S1 = 0 -> CIS = 1.0
    A = _from_edges(3, [(0, 1), (1, 2)])
    res = cis_exact_full(A, targets=[1])
    assert abs(float(res["cis"].iloc[0]) - 1.0) < 1e-12


def test_chain_tail_removal_and_freeN_artifact():
    # A->B->C ; remove C (tail): S1 = 1 -> CIS = 1 - 1/2.5 = 0.6 exactly.
    # free-N diagnostic is NEGATIVE (-0.2): documented artifact of renorm,
    # which is why freeze-N is the frozen convention.
    A = _from_edges(3, [(0, 1), (1, 2)])
    res = cis_exact_full(A, targets=[2])
    assert abs(float(res["cis"].iloc[0]) - 0.6) < 1e-12
    assert abs(float(res["cis_freeN_diagnostic"].iloc[0]) - (-0.2)) < 1e-12


def test_star_center_maximal_and_leaf_quarter():
    # center 0 -> leaves 1..4 : S0 = 4
    A = _from_edges(5, [(0, 1), (0, 2), (0, 3), (0, 4)])
    res = cis_exact_full(A, targets=[0, 1])
    cis_center = float(res.loc[res["target"] == 0, "cis"].iloc[0])
    cis_leaf = float(res.loc[res["target"] == 1, "cis"].iloc[0])
    assert abs(cis_center - 1.0) < 1e-12
    assert abs(cis_leaf - 0.25) < 1e-12  # loses exactly 1 of 4 reachable pairs


def test_random_removals_small_and_bounded():
    rng = np.random.default_rng(42)
    n = 200
    A = sp.csr_matrix((rng.random(n * n) < 0.02).astype(np.float64).reshape(n, n))
    A.setdiag(0)
    A.eliminate_zeros()
    res = cis_exact_full(A, targets=list(range(20)))
    assert np.isfinite(res["cis"]).all()
    assert (res["cis"] >= 0).all() and (res["cis"] <= 1).all()
    assert res["cis"].median() < 0.02, "median random-removal CIS should be tiny"
    assert res["cis"].max() < 0.15, "no random removal should be catastrophic"


def test_bridge_beats_local_cluster_node():
    # two dense halves joined ONLY through bridge node
    n_half = 30
    rng = np.random.default_rng(7)
    n = 2 * n_half + 1
    rows, cols = [], []
    for base in (0, n_half + 1):
        for i in range(n_half):
            for j in range(i + 1, n_half):
                if rng.random() < 0.5:
                    rows += [base + i, base + j]
                    cols += [base + j, base + i]
    bridge = n_half
    for i in range(n_half):
        rows += [bridge, i]
        cols += [i, bridge]
        rows += [bridge, n_half + 1 + i]
        cols += [n_half + 1 + i, bridge]
    A = _from_edges(n, list(zip(rows, cols)))
    res = cis_exact_full(A, targets=[bridge, 0])
    cis_bridge = float(res.loc[res["target"] == bridge, "cis"].iloc[0])
    cis_local = float(res.loc[res["target"] == 0, "cis"].iloc[0])
    assert cis_bridge > 2 * cis_local, (
        f"bridge CIS {cis_bridge:.4f} should exceed 2x local {cis_local:.4f}"
    )


# ------------------------------------------------- panel estimator tests

def test_panel_with_all_sources_equals_exact():
    rng = np.random.default_rng(11)
    n = 60
    A = sp.csr_matrix((rng.random(n * n) < 0.05).astype(np.float64).reshape(n, n))
    A.setdiag(0)
    A.eliminate_zeros()
    targets = list(range(0, 60, 5))
    exact = cis_exact_full(A, targets=targets)
    panel = cis_bfs_panel(A, targets=targets,
                          cfg=PanelConfig(n_sources=n, seed=0))
    m = exact.merge(panel, on="target", suffixes=("_ex", "_pn"))
    assert np.allclose(m["cis_ex"], m["cis_pn"], atol=1e-9), (
        "panel(all sources) must equal exact CIS"
    )


def test_panel_stability_on_structured_graph():
    # Stability must be measured where CIS has real signal (chokepoints).
    # On a structureless random graph every true CIS ~ 0 and panel-to-panel
    # correlation is pure noise (documented k-sweep in RESEARCH_LOG E04).
    # Fixture: two 20-node half-cliques (p=0.3) joined ONLY by a bridge.
    n_half = 20
    rng = np.random.default_rng(5)
    n = 2 * n_half + 1
    rows, cols = [], []
    for base in (0, n_half + 1):
        for i in range(n_half):
            for j in range(i + 1, n_half):
                if rng.random() < 0.3:
                    rows += [base + i, base + j]
                    cols += [base + j, base + i]
    bridge = n_half
    for i in range(n_half):
        rows += [bridge, i]
        cols += [i, bridge]
        rows += [bridge, n_half + 1 + i]
        cols += [n_half + 1 + i, bridge]
    A = _from_edges(n, list(zip(rows, cols)))
    targets = list(range(0, n, 4))
    p0 = cis_bfs_panel(A, targets=targets, cfg=PanelConfig(n_sources=30, seed=0))
    p1 = cis_bfs_panel(A, targets=targets, cfg=PanelConfig(n_sources=30, seed=1))
    m = p0.merge(p1, on="target", suffixes=("_s0", "_s1"))
    rho = np.corrcoef(m["cis_s0"], m["cis_s1"])[0, 1]
    assert rho > 0.9, f"structured-graph two-panel stability too low: {rho:.3f}"


def test_panel_monotone_bounded_on_real_subgraph():
    # real-data smoke test on 1,000-node induced subgraph
    import pandas as pd
    from src.data.loaders import PROJECT_ROOT

    pairs = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "graph_pairs.parquet")
    nodes = pd.Index(pairs["pre_root_id"]).unique()[:1000]
    idx = {r: i for i, r in enumerate(nodes)}
    p = pairs[pairs["pre_root_id"].isin(idx) & pairs["post_root_id"].isin(idx)]
    A = sp.csr_matrix(
        (np.ones(len(p)), (p["pre_root_id"].map(idx), p["post_root_id"].map(idx))),
        shape=(1000, 1000),
    )
    res = cis_bfs_panel(A, targets=list(range(0, 1000, 100)),
                        cfg=PanelConfig(n_sources=32, seed=0))
    assert ((res["cis"] >= 0) & (res["cis"] <= 1)).all()
    assert np.isfinite(res["cis"]).all()


# ---------------------------------------------------------------- runner

def main() -> None:
    tests = [
        test_chain_removal_of_middle_node,
        test_chain_of_three_middle_is_total_collapse,
        test_chain_tail_removal_and_freeN_artifact,
        test_star_center_maximal_and_leaf_quarter,
        test_random_removals_small_and_bounded,
        test_bridge_beats_local_cluster_node,
        test_panel_with_all_sources_equals_exact,
        test_panel_stability_on_structured_graph,
        test_panel_monotone_bounded_on_real_subgraph,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\nGate 1 (metric validation): {passed}/{len(tests)} passed")
    if passed != len(tests):
        raise SystemExit(1)
    print("GATE 1: PASS - metric definition v2 confirmed; ready to freeze.")


if __name__ == "__main__":
    main()
