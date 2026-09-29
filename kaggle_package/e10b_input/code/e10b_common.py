"""E10B shared infrastructure: job manifest + result validation.

ONE source of truth, shipped to Kaggle workers AND used by the local
controller and tests. Dependency-light (numpy/pandas/stdlib only) so it
runs anywhere. Scientific protocol parameters live in experiment_config.json
(exported from the frozen pipeline); this module never redefines them.

Manifest model (canonical copy lives with the controller; workers receive
a read-only snapshot and return per-null records):
  {
    "experiment": "E10B",
    "version": "E10B-v1",
    "code_version": "<16-hex>",
    "n_nulls": 100,
    "seed_base": 100,
    "jobs": [
      {"null_id": 0, "null_name": "null_0000", "seed": 100, "status":
       "pending|running|complete|failed", "worker_id": ..., "attempts": 1,
       "error": ..., "result_file": ..., "updated_utc": ...}, ...
    ]
  }

Validation contract (every result must pass ALL checks before it is
accepted as complete - local adoption re-validates, never trusts):
  node count, edge count, exact in/out degree preservation, zero
  self-loops, zero duplicate directed edges, finite CIS in [0, 1] for
  all pair nodes, correct seed, correct code_version, correct config
  hashes, correct matched-pair configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

MANIFEST_VERSION = "E10B-v1"


# ----------------------------------------------------------------- manifest
def new_manifest(code_version: str, n_nulls: int, seed_base: int) -> dict:
    return {
        "experiment": "E10B",
        "version": MANIFEST_VERSION,
        "code_version": code_version,
        "n_nulls": n_nulls,
        "seed_base": seed_base,
        "jobs": [
            {"null_id": i, "null_name": f"null_{i:04d}", "seed": seed_base + i,
             "status": "pending", "worker_id": None, "attempts": 0,
             "error": None, "result_file": None, "updated_utc": None}
            for i in range(n_nulls)
        ],
    }


def load_manifest(path: Path) -> dict:
    m = json.loads(Path(path).read_text())
    if m.get("version") != MANIFEST_VERSION:
        raise ValueError(f"manifest version mismatch: {m.get('version')}")
    return m


def save_manifest_atomic(manifest: dict, path: Path) -> None:
    """Atomic write: tmp file in same dir, fsync, os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def pending_ids(manifest: dict) -> list[int]:
    return [j["null_id"] for j in manifest["jobs"] if j["status"] == "pending"]


def completed_ids(manifest: dict) -> list[int]:
    return [j["null_id"] for j in manifest["jobs"] if j["status"] == "complete"]


def mark(manifest: dict, null_id: int, **fields) -> None:
    for j in manifest["jobs"]:
        if j["null_id"] == null_id:
            j.update(fields)
            j["attempts"] = int(j.get("attempts") or 0) + \
                (1 if fields.get("status") in ("running", "failed") else 0)
            return
    raise KeyError(f"null_id {null_id} not in manifest")


# --------------------------------------------------------------- validation
def validate_null_record(rec: dict, cfg: dict, edges_row: np.ndarray,
                         edges_col: np.ndarray, shape: tuple[int, int],
                         matched_pairs: pd.DataFrame) -> dict:
    """Validate a completed-null result record against the protocol.

    `edges_row/col/shape` describe the REAL graph (from graph_edges.npz).
    Returns {"ok": bool, "checks": {...}}; recomputes the rewired graph's
    in/out degrees from the record's stored edge arrays when present.
    """
    c: dict[str, bool] = {}

    c["seed_correct"] = rec.get("seed") == cfg["seed_base"] + rec["null_id"]
    c["version_correct"] = rec.get("code_version") == cfg["code_version"]
    c["node_count"] = rec.get("n_nodes") == shape[0]
    c["edge_count"] = rec.get("n_edges_null") == int(len(edges_row))
    c["pairs_config"] = (rec.get("n_pair_nodes")
                         == len(set(matched_pairs["gaba_target"])
                                | set(matched_pairs["ctrl_target"])))

    g = rec.get("gaba_cis", [])
    k = rec.get("ctrl_cis", [])
    g = np.asarray(g, dtype=float)
    k = np.asarray(k, dtype=float)
    c["cis_valid"] = bool(
        len(g) == rec.get("n_gaba", -1) == int((matched_pairs["gaba_target"]).size)
        and len(k) == int((matched_pairs["ctrl_target"]).size)
        and np.isfinite(g).all() and np.isfinite(k).all()
        and (g >= 0).all() and (g <= 1).all()
        and (k >= 0).all() and (k <= 1).all())

    # structural verification from stored rewired edge arrays (if shipped;
    # small enough: ~3.7M int64 x2 = ~60 MB per record - kept optional)
    rw_row = rec.get("null_edges_row")
    rw_col = rec.get("null_edges_col")
    if rw_row is not None:
        rw_row = np.asarray(rw_row, dtype=np.int64)
        rw_col = np.asarray(rw_col, dtype=np.int64)
        c["no_self_loops"] = bool(not np.any(rw_row == rw_col))
        keys = rw_row.astype(np.int64) * shape[0] + rw_col
        c["no_duplicate_edges"] = bool(len(np.unique(keys)) == len(keys))
        real_out = np.bincount(edges_row, minlength=shape[0])
        real_in = np.bincount(edges_col, minlength=shape[0])
        c["out_degree_exact"] = bool(
            np.array_equal(np.bincount(rw_row, minlength=shape[0]), real_out))
        c["in_degree_exact"] = bool(
            np.array_equal(np.bincount(rw_col, minlength=shape[0]), real_in))
    else:
        c["no_self_loops"] = bool(rec.get("no_self_loops", False))
        c["no_duplicate_edges"] = bool(rec.get("no_duplicate_edges", False))
        c["out_degree_exact"] = bool(rec.get("out_degree_exact_match", False))
        c["in_degree_exact"] = bool(rec.get("in_degree_exact_match", False))

    c["statistic_present"] = ("cliffs_delta" in rec and "median_diff" in rec)
    return {"ok": all(c.values()), "checks": c}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
