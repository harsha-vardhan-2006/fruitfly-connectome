"""E10B -> Kaggle: input package export + exactness verification.

Exports the MINIMAL inputs the E10B null workers need (no raw FAFB data):
  graph_edges.npz        binary directed adjacency (COO, node order frozen)
  nodes.csv              positional index -> root_id (order IS the identity)
  matched_pairs.csv      the 848 pre-registered (gaba_target, ctrl_target)
  experiment_config.json frozen protocol parameters + code version hash
  code/                  the exact pipeline modules (verbatim copies)

Everything is derived from data/processed/graph_pairs.parquet via the SAME
build_graph() code path (imported, not reimplemented), so the Kaggle workers
reproduce the local scientific protocol bit-for-bit by construction.

After export, the graph is reconstructed from the package and compared
EXACTLY (indices, shape, nnz, and all explicit edges) against build_graph().

Run:  py -m src.experiments.e10b_export
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
PROCESSED = PROJECT_ROOT / "data" / "processed"
PKG_DIR = PROJECT_ROOT / "kaggle_package" / "e10b_input"
CODE_DIR = PKG_DIR / "code" / "src"
N_NULLS = 100

CODE_FILES = [
    "src/__init__.py",
    "src/data/__init__.py",
    "src/data/loaders.py",
    "src/experiments/__init__.py",
    "src/experiments/control_impact.py",
    "src/experiments/run_e10.py",
    "src/experiments/run_e07_e09.py",
    "src/experiments/run_e06.py",
]

CLONE = "clones/GCAE/FAFB_v783"  # raw-table source reference only


def code_version_hash() -> str:
    """Stable identifier of the exact code shipped with the package."""
    h = hashlib.sha256()
    for rel in CODE_FILES:
        h.update((PROJECT_ROOT / rel).read_bytes())
    h.update((PROJECT_ROOT / "src" / "experiments" / "e10b_common.py")
             .read_bytes())
    return h.hexdigest()[:16]


def export() -> dict:
    from src.experiments.run_e06 import build_graph
    from src.experiments.run_e10 import matched_pair_nodes

    A, nodes, _idx = build_graph()
    gaba_t, ctrl_t = matched_pair_nodes()

    PKG_DIR.mkdir(parents=True, exist_ok=True)
    (PKG_DIR / "code").mkdir(parents=True, exist_ok=True)

    # graph: explicit binary edges in COO, node order frozen
    A_coo = sp.coo_matrix(A)
    np.savez_compressed(
        PKG_DIR / "graph_edges.npz",
        row=A_coo.row.astype(np.int64),
        col=A_coo.col.astype(np.int64),
        shape=np.asarray(A.shape, dtype=np.int64),
    )
    pd.DataFrame({"pos": np.arange(len(nodes)), "root_id": nodes.astype(str)}).to_csv(
        PKG_DIR / "nodes.csv", index=False)

    # matched pairs (positional node indices)
    pd.DataFrame({"gaba_target": gaba_t, "ctrl_target": ctrl_t}).to_csv(
        PKG_DIR / "matched_pairs.csv", index=False)

    for rel in CODE_FILES:
        dst = PKG_DIR / "code" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / rel, dst)
    # shared manifest/validation module (imported top-level by the worker)
    shutil.copy2(PROJECT_ROOT / "src" / "experiments" / "e10b_common.py",
                 PKG_DIR / "code" / "e10b_common.py")

    cfg = {
        "experiment": "E10B",
        "version": "E10B-v1",
        "code_version": code_version_hash(),
        "n_nulls": N_NULLS,
        "seed_base": 100,
        "k_panel": 4,
        "panel_seed": 0,
        "graph_sha256": hashlib.sha256(
            (PKG_DIR / "graph_edges.npz").read_bytes()).hexdigest(),
        "nodes_sha256": hashlib.sha256(
            (PKG_DIR / "nodes.csv").read_bytes()).hexdigest(),
        "matched_pairs_sha256": hashlib.sha256(
            (PKG_DIR / "matched_pairs.csv").read_bytes()).hexdigest(),
        "n_nodes": int(A.shape[0]),
        "n_edges": int(A.nnz),
        "n_pair_nodes": int(len(set(gaba_t.tolist()) | set(ctrl_t.tolist()))),
        "raw_source_ref": CLONE,
        "note": "graph derived from data/processed/graph_pairs.parquet "
                "via the frozen build_graph(); raw FAFB v783 stays local",
    }
    (PKG_DIR / "experiment_config.json").write_text(json.dumps(cfg, indent=2))
    return cfg


def verify_exactness() -> dict:
    """Rebuild from the package and compare EXACTLY against build_graph()."""
    from src.experiments.run_e06 import build_graph
    from src.experiments.run_e10 import matched_pair_nodes

    A_local, nodes_local, _ = build_graph()

    z = np.load(PKG_DIR / "graph_edges.npz")
    A_pkg = sp.coo_matrix(
        (np.ones(len(z["row"]), dtype=np.int8), (z["row"], z["col"])),
        shape=tuple(z["shape"])).tocsr()
    nodes_pkg = pd.read_csv(PKG_DIR / "nodes.csv")["root_id"].to_numpy()
    mp_pkg = pd.read_csv(PKG_DIR / "matched_pairs.csv")
    gaba_pkg, ctrl_pkg = matched_pair_nodes()
    mp_local = pd.DataFrame({"gaba_target": gaba_pkg, "ctrl_target": ctrl_pkg})

    checks = {
        "shape_exact": A_local.shape == A_pkg.shape,
        "nnz_exact": A_local.nnz == A_pkg.nnz,
        "edges_exact": (A_local != A_pkg).nnz == 0,
        # compare as str on both sides (CSV round-trip restores int64 dtype;
        # 18-digit ids are far below int64 max, so no precision loss)
        "nodes_exact": bool(
            (nodes_local.astype(str) == nodes_pkg.astype(str)).all()),
        "pairs_exact": mp_local.reset_index(drop=True).equals(
            mp_pkg.reset_index(drop=True)),
    }
    ok = all(checks.values())
    out = {"checks": checks, "all_exact": ok}
    (PKG_DIR / "exactness_verification.json").write_text(json.dumps(out, indent=2))
    return out


def main() -> None:
    print("[export] exporting package ...", flush=True)
    cfg = export()
    print(json.dumps(cfg, indent=2))
    print("[export] verifying exactness ...", flush=True)
    ver = verify_exactness()
    print(json.dumps(ver, indent=2))
    if not ver["all_exact"]:
        raise SystemExit("EXPORT NOT EXACT - do not ship to Kaggle")
    print("[export] package ready at", PKG_DIR)


if __name__ == "__main__":
    main()
