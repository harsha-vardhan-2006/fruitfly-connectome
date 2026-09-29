"""E18: reproducibility manifest.

Records: raw-file SHA256s (dataset integrity), environment versions,
frozen parameters, experiment index with outputs, and repo inventory.
Run:  py -m src.experiments.run_e18_manifest
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy
import pandas
import scipy

from src.data.loaders import PROJECT_ROOT

RAW_FILES = [
    "neurons.csv.gz", "names.csv.gz", "classification.csv.gz",
    "consolidated_cell_types.csv.gz", "visual_neuron_types.csv.gz",
    "cell_stats.csv.gz", "coordinates.csv.gz", "column_assignment.csv.gz",
    "connectivity_tags.csv.gz", "connections_princeton.csv.gz",
    "connections_princeton_no_threshold.csv.gz",
    "connections_buhmann_no_threshold.csv.gz",
    "neuropil_synapse_table.csv.gz", "synapse_attachment_rates.csv.gz",
    "synapse_coordinates.csv.gz", "fafb_v783_princeton_synapse_table.csv.gz",
    "labels.csv.gz", "processed_labels.csv.gz", "sk_lod1_783_healed.zip",
]


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> None:
    TABLES = PROJECT_ROOT / "results" / "tables"

    print("hashing raw files (large; takes a few minutes) ...")
    checksums = {}
    for name in RAW_FILES:
        p = PROJECT_ROOT / name
        if p.exists():
            checksums[name] = sha256_of(p)
            print(f"  {name}: {checksums[name][:16]}...")

    experiments = {
        "E01": {"desc": "pipeline build", "status": "PASS",
                "outputs": ["data/processed/graph_pairs.parquet",
                            "data/processed/neuron_core.parquet",
                            "data/processed/build_report.json"]},
        "E02": {"desc": "baseline statistics", "status": "PASS",
                "outputs": ["results/tables/baseline_global.csv",
                            "results/tables/baseline_by_nt.csv",
                            "results/tables/baseline_edges_by_nt.csv",
                            "results/tables/baseline_node_metrics.parquet"]},
        "E04": {"desc": "CIS definition+validation+benchmark", "status": "GATE1 PASS 9/9",
                "outputs": ["results/tables/e04_benchmark.json",
                            "tests/test_control_impact.py"]},
        "E06": {"desc": "whole-brain perturbation (screen k=8, rerank k=32)",
                "status": "PASS",
                "outputs": ["results/tables/e06_preregistration.json",
                            "results/tables/e06_screen_k8.parquet",
                            "results/tables/e06_rerank_k32.parquet",
                            "results/tables/e06_screen_summary.json"]},
        "E07": {"desc": "NT annotation join", "status": "PASS",
                "outputs": ["results/tables/e07_annotated.parquet",
                            "results/tables/e07_annotation_quality.json"]},
        "E08": {"desc": "degree matching (pre-registered)", "status": "848 pairs",
                "outputs": ["results/tables/e08_matched_pairs.csv"]},
        "E09": {"desc": "statistics", "status": "PASS",
                "outputs": ["results/tables/e09_descriptives.csv",
                            "results/tables/e09_results.json"]},
        "E10": {"desc": "degree-preserving nulls (PILOT 5 nulls k=4)",
                "status": "PILOT COMPLETE - outcome B indicated",
                "outputs": ["results/tables/e10_results.json"]},
        "E11-E14": {"desc": "neighborhoods, enrichment, robustness, catalogue",
                    "status": "PASS",
                    "outputs": ["results/tables/e11_e14_results.json",
                                "results/tables/e14_chokepoint_catalogue.csv"]},
        "E15": {"desc": "figures 2-7", "status": "PASS",
                "outputs": [f"results/figures/fig{i}_" for i in range(2, 8)]},
        "E17": {"desc": "manuscript draft", "status": "DRAFT",
                "outputs": ["paper/manuscript.md"]},
    }

    manifest = {
        "generated": "2026-09-15",
        "dataset": {
            "name": "FlyWire FAFB v783 (Princeton exports)",
            "license": "CC BY-NC 4.0",
            "required_citations": [
                "Dorkenwald et al. Nature 634:124-144 (2024)",
                "Schlegel et al. Nature 634:153-170 (2024)",
                "Matsliah et al. Nature (2024)"],
            "raw_file_sha256": checksums,
        },
        "environment": {
            "python": platform.python_version(),
            "pandas": pandas.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "os": platform.platform(),
            "machine": platform.machine(),
        },
        "frozen_parameters": {
            "cis": "CIS(i) = 1 - S(G-i)/S(G); freeze-N; unweighted directed",
            "panel_k_screen": 8, "panel_k_rerank": 32, "panel_seeds": [0, 1],
            "matching": "1:1 greedy, total degree +/-10%, GABA->ACh, no replacement",
            "targets_preregistered": 3518,
            "null_pilot": {"n_nulls": 5, "k": 4,
                           "full_protocol_pending": ">=100 nulls at k>=8"},
            "random_seed": 0,
        },
        "experiments": experiments,
        "key_findings": {
            "hypothesis": "OUTCOME B - degree explains the GABA control effect",
            "top_chokepoint": {"cis": 0.024, "share_of_efficiency": "2.4%"},
            "anatomical_result": "top-50 chokepoints 11.7x enriched for "
                                 "visual centrifugal neurons",
            "ols_beta1_gaba": -0.025,
            "matched_pairs_cliffs_delta": 0.111,
            "null_pilot_delta_mean": 0.084,
        },
    }
    out = TABLES / "e18_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"manifest -> {out}")


if __name__ == "__main__":
    main()
