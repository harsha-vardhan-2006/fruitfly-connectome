"""E10B controller: local authority for the 100-null experiment.

Responsibilities:
  - owns the canonical manifest (results/tables/e10b_manifest.json);
  - ADOPTS completed nulls from local workers (row JSONs) and downloaded
    Kaggle outputs, VALIDATING each record before acceptance (never trusts);
  - appends adopted nulls to results/tables/e10b_nulls.csv (the stats
    source used by run_e10b.stats) - NEVER overwrites an existing row;
  - archives full remote records locally (the only copy lives HERE);
  - compares the Kaggle benchmark null against the local null 0.

Subcommands:
  status                       summary of manifest + CSV
  adopt [DIR]                  adopt row JSONs (default: local worker jsons
                               in results/tables + kaggle_package/downloads)
  compare-benchmark            local_test_out null_0000 vs CSV null 0
  stats                        final statistics (delegates to run_e10b.stats)

Run:  py -m src.experiments.e10b_controller <subcommand>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loaders import PROJECT_ROOT
from src.experiments import e10b_common as common

TABLES = PROJECT_ROOT / "results" / "tables"
MANIFEST = TABLES / "e10b_manifest.json"
NULLS_CSV = TABLES / "e10b_nulls.csv"
PKG = PROJECT_ROOT / "kaggle_package"
IN_DIR = PKG / "e10b_input"
ARCHIVE = TABLES / "e10b_remote_records"

CSV_COLS = ["null_id", "seed", "n", "m_edges", "runtime_s", "status",
            "out_degree_exact_match", "in_degree_exact_match",
            "n_edges_null", "median_gaba", "median_ctrl", "median_diff",
            "cliffs_delta", "n_g", "n_c"]


def _graph_arrays() -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    z = np.load(IN_DIR / "graph_edges.npz")
    return z["row"], z["col"], tuple(int(x) for x in z["shape"])


def _cfg() -> dict:
    return json.loads((IN_DIR / "experiment_config.json").read_text())


def get_manifest(rebuild: bool = False) -> dict:
    if MANIFEST.exists() and not rebuild:
        return common.load_manifest(MANIFEST)
    cfg = _cfg()
    m = common.new_manifest(cfg["code_version"], cfg["n_nulls"],
                            cfg["seed_base"])
    # reconcile with existing CSV rows (local run may be ahead of manifest)
    if NULLS_CSV.exists():
        done = set(pd.read_csv(NULLS_CSV)["null_id"].astype(int))
        for j in m["jobs"]:
            if j["null_id"] in done:
                j["status"] = "complete"
                j["worker_id"] = "local_e10b"
                j["result_file"] = "results/tables/e10b_nulls.csv"
    common.save_manifest_atomic(m, MANIFEST)
    return m


def _record_to_csv_row(rec: dict) -> dict:
    return {
        "null_id": rec["null_id"], "seed": rec["seed"],
        "n": rec["n_nodes"], "m_edges": rec["n_edges_null"],
        "runtime_s": rec.get("runtime_s"), "status": "ok",
        "out_degree_exact_match": rec["out_degree_exact_match"],
        "in_degree_exact_match": rec["in_degree_exact_match"],
        "n_edges_null": rec["n_edges_null"],
        "median_gaba": rec["median_gaba"], "median_ctrl": rec["median_ctrl"],
        "median_diff": rec["median_diff"],
        "cliffs_delta": rec["cliffs_delta"],
        "n_g": rec["n_gaba"], "n_c": rec["n_ctrl"],
    }


def adopt_records(records: list[tuple[dict, str]], source: str) -> dict:
    """Validate + adopt records; returns adoption summary.

    records: list of (record_dict, origin_label). Existing CSV rows are
    NEVER modified or replaced - only missing null_ids are appended.
    """
    cfg = _cfg()
    row, col, shape = _graph_arrays()
    mp = pd.read_csv(IN_DIR / "matched_pairs.csv")
    existing: set[int] = set()
    if NULLS_CSV.exists():
        existing = set(pd.read_csv(NULLS_CSV)["null_id"].astype(int))

    m = get_manifest()
    adopted, rejected, skipped = [], [], []
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for rec, origin in records:
        nid = rec.get("null_id")
        if nid is None or not isinstance(nid, int) or nid < 0 \
                or nid >= cfg["n_nulls"]:
            rejected.append((origin, "bad null_id"))
            continue
        if nid in existing:
            skipped.append((origin, f"null {nid} already in CSV"))
            continue
        ver = common.validate_null_record(rec, cfg, row, col, shape, mp)
        if not ver["ok"]:
            rejected.append((origin, f"validation failed: "
                                     f"{[k for k, v in ver['checks'].items() if not v]}"))
            continue
        # archive full record (permanent local copy) then append CSV row
        shutil.copy2(Path(origin), ARCHIVE / f"null_{nid:04d}.json") \
            if Path(origin).exists() else \
            (ARCHIVE / f"null_{nid:04d}.json").write_text(json.dumps(rec))
        new_row = pd.DataFrame([_record_to_csv_row(rec)])
        pd.concat([pd.read_csv(NULLS_CSV), new_row],
                  ignore_index=True).to_csv(NULLS_CSV, index=False) \
            if NULLS_CSV.exists() else new_row.to_csv(NULLS_CSV, index=False)
        existing.add(nid)
        common.mark(m, nid, status="complete", worker_id=rec.get("worker_id"),
                    result_file=f"e10b_remote_records/null_{nid:04d}.json")
        adopted.append((origin, nid))
    common.save_manifest_atomic(m, MANIFEST)
    return {"adopted": adopted, "rejected": rejected, "skipped": skipped}


def gather_candidate_records(extra_dir: Path | None = None
                             ) -> list[tuple[dict, str]]:
    """Collect (record, origin) pairs from local workers + downloads."""
    out: list[tuple[dict, str]] = []
    sources: list[Path] = [TABLES]  # local worker row jsons
    dl = PKG / "downloads"
    if dl.exists():
        sources.extend(sorted(p for p in dl.iterdir() if p.is_dir()))
    if extra_dir:
        sources.append(extra_dir)
    for s in sources:
        for f in sorted(s.glob("e10b_row_*.json")) + \
                sorted(s.glob("null_*.json")):
            try:
                rec = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue  # corrupted checkpoint: rejected, never trusted
            if isinstance(rec, dict) and rec.get("experiment") == "E10B" \
                    and rec.get("status") == "complete":
                out.append((rec, str(f)))
    return out


def cmd_status() -> None:
    m = get_manifest()
    from collections import Counter
    c = Counter(j["status"] for j in m["jobs"])
    csv_n = len(pd.read_csv(NULLS_CSV)) if NULLS_CSV.exists() else 0
    print(f"manifest: {dict(c)} | csv rows: {csv_n} | "
          f"code_version={m['code_version']}")


def cmd_adopt(extra: str | None) -> None:
    recs = gather_candidate_records(Path(extra) if extra else None)
    print(f"candidate records: {len(recs)}")
    res = adopt_records(recs, "adopt")
    print(json.dumps({k: [list(x) if isinstance(x, tuple) else x for x in v]
                      for k, v in res.items()}, indent=2, default=str))
    cmd_status()


def cmd_compare_benchmark() -> None:
    bench = PKG / "local_test_out" / "results" / "null_0000.json"
    if not bench.exists():
        raise SystemExit("benchmark result not found - run the worker "
                         "locally first (see E10B_KAGGLE.md)")
    rec = json.loads(bench.read_text())
    csv0 = pd.read_csv(NULLS_CSV)
    row0 = csv0[csv0["null_id"] == 0]
    if row0.empty:
        raise SystemExit("local null 0 missing from CSV")
    d_delta = abs(rec["cliffs_delta"] - float(row0["cliffs_delta"].iloc[0]))
    d_diff = abs(rec["median_diff"] - float(row0["median_diff"].iloc[0]))
    ok = d_delta <= 1e-9 and d_diff <= 1e-12
    out = {"remote_delta": rec["cliffs_delta"],
           "local_delta": float(row0["cliffs_delta"].iloc[0]),
           "abs_delta_diff": d_delta,
           "remote_median_diff": rec["median_diff"],
           "local_median_diff": float(row0["median_diff"].iloc[0]),
           "abs_median_diff_diff": d_diff,
           "match": bool(ok)}
    (PKG / "benchmark_comparison.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    if not ok:
        raise SystemExit("BENCHMARK MISMATCH - do not launch remote workers")


def cmd_stats() -> None:
    from src.experiments.run_e10b import stats
    stats()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        cmd_status()
    elif cmd == "adopt":
        cmd_adopt(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "compare-benchmark":
        cmd_compare_benchmark()
    elif cmd == "stats":
        cmd_stats()
    else:
        raise SystemExit(f"unknown subcommand {cmd}")


if __name__ == "__main__":
    main()
