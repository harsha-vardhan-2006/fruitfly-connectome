"""E10B: full 100-null protocol (pre-registered; resumable; parallel).

Each null (worker):
  1. directed configuration-model rewire (exact degree sequences, seed
     100+i, same construction as the E10 pilot);
  2. VERIFY degree preservation exactly (in/out degree sequences equal to
     the real graph) - abort on any mismatch;
  3. chunk-checkpointed panel CIS (k=4, seed 0) for all matched-pair nodes
     (same pairs as E08/E09 - exact comparability with the pilot);
  4. statistic: median(CIS_GABA) - median(CIS_ACh) and Cliff's delta;
  5. row written to results/tables/e10b_row_{i}.json, then merged into
     results/tables/e10b_nulls.csv by the driver.

Driver runs WORKERS nulls concurrently (scipy dijkstra is single-threaded,
so null-level parallelism scales to core count) and is fully resumable:
existing CSV rows, row JSONs, and per-null CIS checkpoints are all honored.

Run:    py -m src.experiments.run_e10b
Stats:  py -m src.experiments.run_e10b stats
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
N_NULLS = 100
K_PANEL = 4
WORKERS = 3
NULL_CSV = TABLES / "e10b_nulls.csv"


def verify_degree_preservation(A_real, A_null) -> dict:
    out_r = np.asarray((A_real > 0).sum(axis=1)).ravel()
    in_r = np.asarray((A_real > 0).sum(axis=0)).ravel()
    out_n = np.asarray((A_null > 0).sum(axis=1)).ravel()
    in_n = np.asarray((A_null > 0).sum(axis=0)).ravel()
    return {
        "out_degree_exact_match": bool(np.array_equal(out_r, out_n)),
        "in_degree_exact_match": bool(np.array_equal(in_r, in_n)),
        "n_edges_null": int(A_null.nnz),
    }


def run_one_null(i: int) -> dict:
    """Worker: one full null. Importable top-level (Windows spawn)."""
    from src.experiments.run_e06 import build_graph
    from src.experiments.run_e10 import (
        config_model_null,
        matched_pair_nodes,
        panel_cis_for_nodes,
        statistic_from_cis,
    )

    t0 = time.perf_counter()
    A, _nodes, _idx = build_graph()
    gaba_t, ctrl_t = matched_pair_nodes()
    all_pair_nodes = sorted(set(gaba_t.tolist()) | set(ctrl_t.tolist()))

    An = config_model_null(A, seed=100 + i)
    ver = verify_degree_preservation(A, An)
    if not (ver["out_degree_exact_match"] and ver["in_degree_exact_match"]):
        raise RuntimeError(f"degree preservation FAILED for null {i}: {ver}")

    cis_n = panel_cis_for_nodes(An, all_pair_nodes,
                                tag=f"e10b_null{i}", k=K_PANEL)
    st = statistic_from_cis(cis_n, gaba_t, ctrl_t)
    row = {"null_id": i, "seed": 100 + i, "n": int(A.shape[0]),
           "m_edges": int(An.nnz),
           "runtime_s": round(time.perf_counter() - t0, 1),
           "status": "ok", **ver, **st}
    (TABLES / f"e10b_row_{i}.json").write_text(json.dumps(row))
    (TABLES / f"e10_ckpt_e10b_null{i}.parquet").unlink(missing_ok=True)
    return row


def _adopt_and_merge() -> set[int]:
    """Merge worker row JSONs into NULL_CSV; return completed null_ids."""
    rows = []
    for f in sorted(TABLES.glob("e10b_row_*.json")):
        try:
            rows.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue  # partial write from a kill; worker rewrites on redo
    done: set[int] = set()
    if NULL_CSV.exists():
        old = pd.read_csv(NULL_CSV)
        done = set(old["null_id"].astype(int))
        rows.extend(old.to_dict("records"))
    if rows:
        df = pd.DataFrame(rows).drop_duplicates(subset="null_id", keep="last")
        df = df.sort_values("null_id")
        df.to_csv(NULL_CSV, index=False)
        done = set(df["null_id"].astype(int))
        for f in TABLES.glob("e10b_row_*.json"):
            f.unlink(missing_ok=True)
    return done


def run(n_nulls: int = N_NULLS, workers: int = WORKERS) -> None:
    from concurrent.futures import ProcessPoolExecutor, as_completed

    done = _adopt_and_merge()
    if done:
        print(f"[E10B] resuming: {len(done)}/{n_nulls} nulls already complete",
              flush=True)
    pending = [i for i in range(n_nulls) if i not in done]
    if not pending:
        print("[E10B] nothing to do; run `stats`")
        return

    t_start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_one_null, i): i for i in pending}
        n_ok = 0
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                row = fut.result()
                n_ok += 1
                el = time.perf_counter() - t_start
                eta = el / n_ok * (len(pending) - n_ok) / 3600
                print(f"[E10B] null {i}: delta={row['cliffs_delta']:.4f} "
                      f"diff={row['median_diff']:.2e} ({row['runtime_s']}s) "
                      f"| {n_ok}/{len(pending)} this run, ETA {eta:.1f} h",
                      flush=True)
            except Exception as exc:  # noqa: BLE001 - log and continue
                print(f"[E10B] null {i} FAILED: {exc!r}", flush=True)
    _adopt_and_merge()
    total = len(pd.read_csv(NULL_CSV))
    print(f"[E10B] run window complete; nulls in CSV: {total}/{n_nulls}",
          flush=True)


def stats() -> dict:
    """Observed vs null-distribution statistics from whatever nulls exist."""
    _adopt_and_merge()
    nulls = pd.read_csv(NULL_CSV)
    real = pd.read_parquet(TABLES / "e10_ckpt_real.parquet")
    from src.experiments.run_e10 import matched_pair_nodes, statistic_from_cis
    gaba_t, ctrl_t = matched_pair_nodes()
    obs = statistic_from_cis(real, gaba_t, ctrl_t)

    p_delta = (1 + int((nulls["cliffs_delta"] >= obs["cliffs_delta"]).sum())) \
        / (1 + len(nulls))
    p_diff = (1 + int((nulls["median_diff"] >= obs["median_diff"]).sum())) \
        / (1 + len(nulls))
    z_delta = ((obs["cliffs_delta"] - nulls["cliffs_delta"].mean())
               / nulls["cliffs_delta"].std(ddof=1))
    out = {
        "n_nulls_completed": int(len(nulls)),
        "observed": obs,
        "null_delta_mean": float(nulls["cliffs_delta"].mean()),
        "null_delta_sd": float(nulls["cliffs_delta"].std(ddof=1)),
        "null_delta_max": float(nulls["cliffs_delta"].max()),
        "null_delta_p95": float(nulls["cliffs_delta"].quantile(0.95)),
        "obs_delta_z_vs_null": float(z_delta),
        "empirical_p_delta": p_delta,
        "empirical_p_median_diff": p_diff,
        "null_median_diff_mean": float(nulls["median_diff"].mean()),
        "all_nulls_degree_verified": bool(nulls["in_degree_exact_match"].all()
                                          and nulls["out_degree_exact_match"].all()),
        "gate4_note": "observed effect vs degree-preserving nulls; p_delta "
                      ">= 0.05 => degree topology reproduces the GABA effect",
    }
    (TABLES / "e10b_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats()
    else:
        run()
