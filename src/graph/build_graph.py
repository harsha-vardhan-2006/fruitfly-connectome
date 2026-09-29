"""Experiment 1 baseline: build the Phase-1 graph from Tier-1 files.

Input : connections_princeton.csv.gz + per-neuron metadata (via loaders.py)
Output: data/processed/graph_pairs.parquet
        data/processed/neuron_core.parquet
        data/processed/build_report.json

The graph is the PAIR-COLLAPSED weighted digraph: one row per (pre, post)
with summed syn_count and majority-NT. Neuron-level metadata is attached as
a separate table (node table), joined by root_id at analysis time.

Run:  py -m src.graph.build_graph
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from src.data.loaders import (
    DATA_DIR,
    PROJECT_ROOT,
    collapse_edges,
    load_edges,
    load_neuron_core,
    validate_root_ids,
)

PROCESSED = PROJECT_ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def main() -> None:
    t0 = time.time()
    report: dict = {"dataset": "FAFB v783 (Princeton)", "steps": {}}

    print("[1/5] Loading neuron metadata ...")
    core = load_neuron_core()
    report["steps"]["neuron_core"] = {
        "rows": len(core),
        "nt_sign_counts": core["nt_sign"].value_counts(dropna=False).to_dict(),
        "side_counts": core["side"].value_counts(dropna=False).to_dict(),
        "super_class_counts": core["super_class"].value_counts(dropna=False).head(15).to_dict(),
    }
    print(f"      {len(core):,} neurons with merged metadata")

    print("[2/5] Validating root_ids ...")
    report["steps"]["root_id_validation"] = validate_root_ids(
        core, cols=("root_id",)
    )

    print("[3/5] Loading edge list (connections_princeton, thresholded) ...")
    edges_raw = load_edges("princeton_thresholded")
    report["steps"]["edges_raw"] = {
        "rows": len(edges_raw),
        "pairs_before_collapse": int(
            edges_raw.groupby(["pre_root_id", "post_root_id"]).ngroups
        ),
        "unique_neurons_in_edges": int(
            pd.concat([edges_raw["pre_root_id"], edges_raw["post_root_id"]]).nunique()
        ),
        "nt_types": edges_raw["nt_type"].value_counts(dropna=False).to_dict(),
    }
    print(f"      {len(edges_raw):,} per-neuropil rows")

    print("[4/5] Collapsing to pairs and validating ...")
    pairs = collapse_edges(edges_raw)
    report["steps"]["edges_collapsed"] = {
        "rows": len(pairs),
        "self_loops": int((pairs["pre_root_id"] == pairs["post_root_id"]).sum()),
    }
    id_check = validate_root_ids(pairs, cols=("pre_root_id", "post_root_id"))
    report["steps"]["edges_collapsed"]["id_validation"] = id_check

    # edges referencing neurons missing from the metadata tables
    known = set(core["root_id"])
    pre_known = pairs["pre_root_id"].isin(known).mean()
    post_known = pairs["post_root_id"].isin(known).mean()
    report["steps"]["edges_collapsed"]["pre_in_metadata_frac"] = float(pre_known)
    report["steps"]["edges_collapsed"]["post_in_metadata_frac"] = float(post_known)

    print("[5/5] Writing processed outputs ...")
    core.to_parquet(PROCESSED / "neuron_core.parquet", index=False)
    pairs.to_parquet(PROCESSED / "graph_pairs.parquet", index=False)

    report["elapsed_seconds"] = round(time.time() - t0, 1)
    (PROCESSED / "build_report.json").write_text(json.dumps(report, indent=2, default=str))

    print(f"Done in {report['elapsed_seconds']}s -> {PROCESSED}")
    print(f"  neurons: {len(core):,} | collapsed pairs: {len(pairs):,}")


if __name__ == "__main__":
    main()
