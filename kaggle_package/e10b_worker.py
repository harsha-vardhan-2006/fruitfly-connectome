from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

IN_DIR = Path(os.environ.get("E10B_INPUT_DIR", "/kaggle/input/e10b-input"))
OUT_DIR = Path(os.environ.get("E10B_OUT_DIR", "/kaggle/working"))
RESULTS = OUT_DIR / "results"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_inputs() -> tuple[sp.csr_matrix, dict, pd.DataFrame, str]:
    cfg = json.loads((IN_DIR / "experiment_config.json").read_text())
    z = np.load(IN_DIR / "graph_edges.npz")
    A = sp.coo_matrix(
        (np.ones(len(z["row"]), dtype=np.int8), (z["row"], z["col"])),
        shape=tuple(z["shape"])).tocsr()
    mp = pd.read_csv(IN_DIR / "matched_pairs.csv")
    return A, cfg, mp, cfg["code_version"]


def check_input_hashes(cfg: dict) -> None:
    """Abort unless the shipped inputs hash-match the frozen package."""
    import hashlib
    for fname, key in [("graph_edges.npz", "graph_sha256"),
                       ("nodes.csv", "nodes_sha256"),
                       ("matched_pairs.csv", "matched_pairs_sha256")]:
        h = hashlib.sha256((IN_DIR / fname).read_bytes()).hexdigest()
        if h != cfg[key]:
            raise SystemExit(f"INPUT HASH MISMATCH for {fname}: {h} != {cfg[key]}")


def assignment_ids(worker_id: str) -> list[int] | None:
    """Per-kernel disjoint assignment (pushed as assignment.json next to
    this script by e10b_submit). Kaggle kernels cannot see each other's
    working dirs, so cross-kernel claims are impossible - disjoint ranges
    generated at submit time are the coordination mechanism."""
    p = Path(__file__).resolve().parent / "assignment.json"
    if not p.exists():
        return None
    a = json.loads(p.read_text())
    return [int(x) for x in a.get("null_ids", [])]


def claim_pending(manifest: dict, worker_id: str) -> int | None:
    """Claim one pending null via a per-worker claim file.

    Returns the null_id to run, or None if nothing pending is claimable.
    """
    claims = RESULTS / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    now = time.time()
    allowed = assignment_ids(worker_id)
    allowed_set = set(allowed) if allowed is not None else None
    for job in manifest["jobs"]:
        if job["status"] != "pending":
            continue
        nid = job["null_id"]
        if allowed_set is not None and nid not in allowed_set:
            continue
        result_file = RESULTS / f"null_{nid:04d}.json"
        if result_file.exists():
            job["status"] = "complete"  # adopted from a previous session
            continue
        mine = claims / f"null_{nid:04d}.{worker_id}.claim"
        others = [p for p in claims.glob(f"null_{nid:04d}.*.claim")
                  if p != mine]
        fresh_other = [p for p in others
                       if now - p.stat().st_mtime < 3 * 3600]
        if fresh_other:
            continue
        # claim (overwrite stale foreign claims atomically)
        tmp = mine.with_suffix(".claim.tmp")
        tmp.write_text(utcnow())
        os.replace(tmp, mine)
        return nid
    return None


def run_null(A: sp.csr_matrix, cfg: dict, mp: pd.DataFrame,
             null_id: int) -> dict:
    """One E10B null - the SAME code path as the local run (functions are
    imported verbatim from the shipped, hash-pinned src/ modules)."""

    from src.experiments.run_e10 import (
        config_model_null,
        panel_cis_for_nodes,
        statistic_from_cis,
    )

    seed = cfg["seed_base"] + null_id
    gaba_t = mp["gaba_target"].to_numpy()
    ctrl_t = mp["ctrl_target"].to_numpy()
    all_pair_nodes = sorted(set(gaba_t.tolist()) | set(ctrl_t.tolist()))

    t0_perf = time.perf_counter()
    t0_wall = time.time()
    An = config_model_null(A, seed=seed)
    rewired_edges = An.nnz

    # structural verification (recomputed HERE, embedded in the record)
    coo = An.tocoo()
    rw_row, rw_col = coo.row.astype(np.int64), coo.col.astype(np.int64)
    n = A.shape[0]
    real_out = np.bincount(A.tocoo().row, minlength=n)
    real_in = np.bincount(A.tocoo().col, minlength=n)
    out_deg_exact = bool(np.array_equal(np.bincount(rw_row, minlength=n),
                                        real_out))
    in_deg_exact = bool(np.array_equal(np.bincount(rw_col, minlength=n),
                                       real_in))
    no_self = bool(not np.any(rw_row == rw_col))
    keys = rw_row * n + rw_col
    no_dup = bool(len(np.unique(keys)) == len(keys))
    if not (out_deg_exact and in_deg_exact and no_self and no_dup):
        raise RuntimeError(
            f"null {null_id}: structural verification failed "
            f"(out={out_deg_exact} in={in_deg_exact} self={no_self} "
            f"dup={no_dup})")

    cis_n = panel_cis_for_nodes(An, all_pair_nodes,
                                tag=f"kw_null{null_id}", k=cfg["k_panel"])
    st = statistic_from_cis(cis_n, gaba_t, ctrl_t)

    g = cis_n[cis_n["target"].isin(gaba_t)]["cis"].to_numpy()
    k_cis = cis_n[cis_n["target"].isin(ctrl_t)]["cis"].to_numpy()
    return {
        "experiment": "E10B",
        "code_version": cfg["code_version"],
        "null_id": null_id,
        "seed": seed,
        "worker_id": os.environ.get("WORKER_ID", "kw0"),
        "started_utc": datetime.fromtimestamp(t0_wall, timezone.utc)
                         .isoformat(timespec="seconds"),
        "runtime_s": round(time.perf_counter() - t0_perf, 1),
        "n_nodes": int(n),
        "n_edges_null": int(rewired_edges),
        "n_pair_nodes": int(len(all_pair_nodes)),
        "n_gaba": int(len(g)), "n_ctrl": int(len(k_cis)),
        "gaba_cis": [float(x) for x in g],
        "ctrl_cis": [float(x) for x in k_cis],
        **{k2: v for k2, v in st.items()},
        "out_degree_exact_match": out_deg_exact,
        "in_degree_exact_match": in_deg_exact,
        "no_self_loops": no_self,
        "no_duplicate_edges": no_dup,
        "status": "complete",
    }


def main() -> None:
    t_start = time.perf_counter()
    worker_id = os.environ.get("WORKER_ID", "kw0")
    max_nulls = int(os.environ.get("MAX_NULLS", "12"))
    os.environ.setdefault("WORKER_ID", worker_id)
    RESULTS.mkdir(parents=True, exist_ok=True)

    print(f"[worker {worker_id}] loading inputs from {IN_DIR} ...", flush=True)
    check_input_hashes(json.loads((IN_DIR / "experiment_config.json").read_text()))
    A, cfg, mp, code_version = load_inputs()
    print(f"[worker {worker_id}] graph {A.shape} nnz={A.nnz} "
          f"code_version={code_version}", flush=True)

    # add src/ (shipped inside the dataset) to the import path.
    # NOTE: the shipped copy is a truncated pilot tree; only add it if it
    # actually contains the run_e10 module used below.
    code_src = IN_DIR / "code"
    code_src_has_run_e10 = code_src.exists() and (
        code_src / "src" / "experiments" / "run_e10.py").exists()
    if code_src_has_run_e10:
        sys.path.insert(0, str(code_src.parent))
        sys.path.insert(0, str(code_src))

    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        from e10b_common import new_manifest
        manifest = new_manifest(code_version, cfg["n_nulls"], cfg["seed_base"])
        manifest["jobs"] = [j for j in manifest["jobs"]
                            if not (RESULTS / f"null_{j['null_id']:04d}.json")
                            .exists()]

    # panel_cis_for_nodes writes checkpoints to
    #   code/src/experiments/results/tables/e10_ckpt_<tag>.parquet
    # i.e. <IN_DIR>/code/results/tables. That path must exist, otherwise
    # panel_cis_for_nodes raises:
    #   OSError: Cannot save file into a non-existent directory: '.../results/tables'
    _ckpt_dir = code_src / "results" / "tables"
    _ckpt_dir.mkdir(parents=True, exist_ok=True)



    _done = 0
    try:
        while _done < max_nulls:
            nid = claim_pending(manifest, worker_id)
            if nid is None:
                print(f"[worker {worker_id}] no pending jobs left", flush=True)
                break
            from e10b_common import mark
            mark(manifest, nid, status="running", worker_id=worker_id,
                 updated_utc=utcnow())
            print(f"[worker {worker_id}] claimed null_{nid:04d}", flush=True)
            try:
                rec = run_null(A, cfg, mp, nid)
                # atomic result write: never a half-written "complete"
                tmp = RESULTS / f"null_{nid:04d}.json.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(rec, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, RESULTS / f"null_{nid:04d}.json")
                mark(manifest, nid, status="complete",
                     result_file=f"results/null_{nid:04d}.json",
                     updated_utc=utcnow())
                _done += 1
                print(f"[worker {worker_id}] null_{nid:04d} COMPLETE "
                      f"delta={rec['cliffs_delta']:.4f} "
                      f"({rec['runtime_s']}s)", flush=True)
            except Exception as exc:  # noqa: BLE001
                mark(manifest, nid, status="failed", error=repr(exc)[:500],
                     updated_utc=utcnow())
                print(f"[worker {worker_id}] null_{nid:04d} FAILED: {exc!r}",
                      flush=True)
            finally:
                from e10b_common import save_manifest_atomic
                save_manifest_atomic(manifest, manifest_path)
    finally:
        from e10b_common import save_manifest_atomic
        save_manifest_atomic(manifest, manifest_path)
        el = time.perf_counter() - t_start
        print(f"[worker {worker_id}] session end: {_done} nulls in "
              f"{el / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
