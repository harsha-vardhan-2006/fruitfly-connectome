"""Loaders for FlyWire FAFB v783 Princeton data products.

Phase-1 (Tier-1) files only. Raw files are NEVER modified; everything
downstream is written to data/processed/ and results/.

Known format quirks handled here (verified in review.md / research_plan.md):
- CRLF line endings (pandas handles transparently).
- `connections_*.csv.gz` rows are per (pre, post, neuropil) - collapse later
  in build_graph.py.
- `fafb_v783_princeton_synapse_table.csv.gz` has MANGLED root ids
  (header `pre_root_id_720575940`, 9-digit suffix values). Reconstruction:
  full_id = 720575940 * 10**9 + suffix. NOT used in Phase 1; provided for
  later tiers.
- `processed_labels.csv.gz` cells are Python-literal lists -> ast.literal_eval.
- `coordinates.csv.gz` positions are "[x y z]" strings -> parse to 3 floats.
- 18 SWC-orphan root_ids exist in the zip but not in the tables; the tables
  are authoritative, so joins are inner joins by construction.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

# Project root = parent of src/. Raw data lives at the project root itself.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT  # raw FAFB v783 files sit at the repo root

NEURON_TABLES = [
    "neurons",
    "names",
    "classification",
    "consolidated_cell_types",
    "visual_neuron_types",
    "cell_stats",
    "connectivity_tags",
]

EDGE_TABLES = {
    "princeton_thresholded": "connections_princeton.csv.gz",
    "princeton_no_threshold": "connections_princeton_no_threshold.csv.gz",
    "buhmann_no_threshold": "connections_buhmann_no_threshold.csv.gz",
}

ID_PREFIX = 720_575_940  # constant high 9 digits of every root_id


def _path(fname: str) -> Path:
    return DATA_DIR / fname


def load_neuron_table(name: str) -> pd.DataFrame:
    """Load a per-neuron table by bare name, e.g. 'neurons', 'classification'."""
    if name not in NEURON_TABLES:
        raise KeyError(f"unknown neuron table {name!r}; known: {NEURON_TABLES}")
    return pd.read_csv(_path(f"{name}.csv.gz"), dtype={"root_id": "int64"})


def load_neuron_core() -> pd.DataFrame:
    """Merged per-neuron metadata: group, NT, classification, side, type.

    Inner joins: typed tables cover subsets (138,327 / 95,079 rows), so the
    merged frame is smaller than 139,255 and has no NaN key collisions.
    """
    neurons = load_neuron_table("neurons")
    classification = load_neuron_table("classification")[
        ["root_id", "flow", "super_class", "class", "sub_class", "hemilineage", "side", "nerve"]
    ]
    names = load_neuron_table("names")[["root_id", "name"]]
    consolidated = load_neuron_table("consolidated_cell_types")[
        ["root_id", "primary_type"]
    ]
    visual = load_neuron_table("visual_neuron_types")[
        ["root_id", "type", "family", "subsystem"]
    ].rename(columns={"type": "visual_type", "family": "visual_family",
                      "subsystem": "visual_subsystem"})

    core = (
        neurons
        .merge(classification, on="root_id", how="left", validate="one_to_one")
        .merge(names, on="root_id", how="left", validate="one_to_one")
        .merge(consolidated, on="root_id", how="left", validate="one_to_one")
        .merge(visual, on="root_id", how="left", validate="one_to_one")
    )
    # Neurotransmitter sign policy (Phase 1; see research_plan.md Part 8 / lit matrix):
    #   GABA  -> inhibitory
    #   ACH   -> excitatory
    #   GLUT  -> reported separately (sign context-dependent in fly brain;
    #            largely excitatory ionotropic but we do NOT bin it into E/I here)
    #   DA / SER / OCT -> modulatory, kept separate
    nt_map = {
        "GABA": "inhibitory",
        "ACH": "excitatory",
        "GLUT": "glut",
        "DA": "modulatory",
        "SER": "modulatory",
        "OCT": "modulatory",
    }
    core["nt_sign"] = core["nt_type"].map(nt_map).fillna("unknown")
    return core


def load_edges(dataset: str = "princeton_thresholded") -> pd.DataFrame:
    """Load a connection table. Rows are per (pre, post, neuropil)."""
    if dataset not in EDGE_TABLES:
        raise KeyError(f"unknown dataset {dataset!r}; known: {list(EDGE_TABLES)}")
    df = pd.read_csv(
        _path(EDGE_TABLES[dataset]),
        dtype={"pre_root_id": "int64", "post_root_id": "int64"},
    )
    # normalize CRLF artefacts in string columns
    for col in ("neuropil", "nt_type"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    return df


def collapse_edges(edges: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-neuropil rows to one row per (pre, post) pair.

    syn_count is summed. nt_type is resolved to the majority across the
    pair's neuropil rows, where majority = largest summed syn_count per
    NT within the pair; ties fall back to pandas' stable sort order.
    Fully vectorized (groupby-apply over millions of pairs is too slow).
    """
    pair_keys = ["pre_root_id", "post_root_id"]

    syn = (edges.groupby(pair_keys, as_index=False)["syn_count"]
           .sum().rename(columns={"syn_count": "syn_count_total"}))

    nt = (edges.dropna(subset=["nt_type"])
          .groupby(pair_keys + ["nt_type"], as_index=False)["syn_count"]
          .sum()
          .sort_values(["syn_count"] + pair_keys, ascending=[False, True, True],
                       kind="stable")
          .drop_duplicates(pair_keys)
          [pair_keys + ["nt_type"]]
          .rename(columns={"nt_type": "nt_type_edge"}))

    n_neuropils = (edges.groupby(pair_keys, as_index=False)["neuropil"]
                   .nunique().rename(columns={"neuropil": "n_neuropils"}))

    out = syn.merge(nt, on=pair_keys, how="left")
    out = out.merge(n_neuropils, on=pair_keys, how="left")
    return out


def load_synapse_table_master(columns: list[str] | None = None,
                              chunksize: int = 2_000_000) -> pd.Iterator | pd.DataFrame:
    """Chunked loader for the 2.5 GB master synapse table (Tier 3).

    Reconstructs mangled root ids on the fly. NOT used in Phase 1.
    """
    usecols = columns or None

    def _fix(chunk: pd.DataFrame) -> pd.DataFrame:
        chunk = chunk.rename(columns={
            "pre_root_id_720575940": "pre_root_id",
            "post_root_id_720575940": "post_root_id",
        })
        chunk["pre_root_id"] = ID_PREFIX * 1_000_000_000 + chunk["pre_root_id"]
        chunk["post_root_id"] = ID_PREFIX * 1_000_000_000 + chunk["post_root_id"]
        return chunk

    reader = pd.read_csv(_path("fafb_v783_princeton_synapse_table.csv.gz"),
                         usecols=usecols, chunksize=chunksize)
    mapper = map(_fix, reader)
    return mapper  # iterate: for chunk in load_synapse_table_master(): ...


def load_processed_labels() -> pd.DataFrame:
    """processed_labels with Python-literal list cells parsed."""
    df = pd.read_csv(_path("processed_labels.csv.gz"), dtype={"root_id": "int64"})
    df["processed_labels"] = df["processed_labels"].apply(
        lambda s: ast.literal_eval(s) if isinstance(s, str) and s.startswith("[") else s
    )
    return df


def load_coordinates() -> pd.DataFrame:
    """coordinates.csv.gz with '[x y z]' positions parsed to x, y, z columns."""
    df = pd.read_csv(_path("coordinates.csv.gz"), dtype={"root_id": "int64"})
    pos = (
        df["position"].astype(str)
        .str.strip("[]")
        .str.split(r"\s+", n=2, expand=True)
        .astype(float)
    )
    df[["x", "y", "z"]] = pos
    return df.drop(columns=["position"])


def load_attachment_rates() -> pd.DataFrame:
    """synapse_attachment_rates (QC ratios per neuropil x pre/post side)."""
    return pd.read_csv(_path("synapse_attachment_rates.csv.gz"))


def validate_root_ids(df: pd.DataFrame, cols: tuple[str, ...] = ("root_id",)) -> dict:
    """Verify root_ids are 18-digit FAFB-style ids. Returns a summary dict."""
    report = {}
    for col in cols:
        if col not in df.columns:
            report[col] = "MISSING"
            continue
        s = df[col].dropna().astype("int64")
        as_str = s.astype(str)
        ok_pattern = as_str.str.fullmatch(r"720575940\d{9}").all()
        report[col] = {
            "n": int(len(s)),
            "min": int(s.min()),
            "max": int(s.max()),
            "all_18_digit_fafb_pattern": bool(ok_pattern),
        }
    return report
