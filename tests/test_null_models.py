"""Null-model regression tests (E10/E10B rewiring correctness).

Locks in the two bugs caught during E10B development:
  (1) swap partners must be distinct AND disjoint from the bad-edge set
      (repeated/overlapping partners corrupt the in-degree multiset);
  (2) repair limit-cycles must trigger rejection redraw - every ACCEPTED
      draw has exact degree sequences.

Adversarial fixtures stress the repair loop: hub-with-self-loop (guaranteed
self-loops after stub matching), dense random graph (high duplicate
pressure), and a tiny ring (minimal repair freedom).

Run:  py -m tests.test_null_models
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from src.experiments.run_e10 import config_model_null


def _fixtures() -> dict[str, sp.csr_matrix]:
    n = 50
    A = sp.random(n, n, density=0.15, format="csr", random_state=1)
    A = sp.csr_matrix((A.data, A.nonzero()))
    A.setdiag(0)
    A.eliminate_zeros()
    dense = A

    hub = sp.lil_matrix((n, n))
    hub[0, 1:] = 1          # hub with 49 unique targets
    hub[1:, 0] = 1          # reverse hub -> guaranteed self-loops to repair
    hub = hub.tocsr()

    ring = sp.lil_matrix((12, 12))
    for i in range(12):
        ring[i, (i + 1) % 12] = 1
    ring = ring.tocsr()

    return {"dense_random": dense, "hub_selfloop": hub, "ring": ring}


def test_degree_preservation_adversarial() -> None:
    """Exact in/out degree sequences under repair pressure, 20 seeds each."""
    for name, A in _fixtures().items():
        out_r = np.asarray((A > 0).sum(axis=1)).ravel()
        in_r = np.asarray((A > 0).sum(axis=0)).ravel()
        for seed in range(20):
            An = config_model_null(A, seed=seed)
            out_n = np.asarray((An > 0).sum(axis=1)).ravel()
            in_n = np.asarray((An > 0).sum(axis=0)).ravel()
            assert np.array_equal(out_r, out_n), \
                f"{name} seed{seed}: out-degree corrupted"
            assert np.array_equal(in_r, in_n), \
                f"{name} seed{seed}: in-degree corrupted"
    print("PASS  degree preservation (3 fixtures x 20 seeds)")


def test_no_self_loops_no_duplicates() -> None:
    """Accepted nulls contain no self-loops and no duplicate (u,v) edges."""
    for name, A in _fixtures().items():
        for seed in range(5):
            An = config_model_null(A, seed=seed)
            coo = An.tocoo()
            assert not np.any(coo.row == coo.col), \
                f"{name} seed{seed}: self-loop survived"
            keys = coo.row.astype(np.int64) * An.shape[0] + coo.col
            assert len(np.unique(keys)) == len(keys), \
                f"{name} seed{seed}: duplicate edge survived"
    print("PASS  no self-loops / no duplicate edges")


def test_deterministic_given_seed() -> None:
    """Same seed -> bitwise-identical null (reproducibility)."""
    A = _fixtures()["dense_random"]
    A1 = config_model_null(A, seed=123)
    A2 = config_model_null(A, seed=123)
    assert (A1 != A2).nnz == 0, "same seed produced different nulls"
    print("PASS  determinism given seed")


def main() -> None:
    test_degree_preservation_adversarial()
    test_no_self_loops_no_duplicates()
    test_deterministic_given_seed()
    print("ALL NULL-MODEL REGRESSION TESTS PASS")


if __name__ == "__main__":
    main()
