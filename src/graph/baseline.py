"""Experiment 1 baseline: global + neuron-level network statistics.

Consumes data/processed/graph_pairs.parquet + neuron_core.parquet (built by
src.graph.build_graph) and writes results/tables/baseline_*.{parquet,csv}.

All metrics computed with scipy sparse + numpy (no NetworkX: too slow and
memory-heavy at 139k nodes, per project plan section 27).

Metrics:
  Global : n_nodes, n_edges, mean degree, density, reciprocity,
           weakly connected components, edge NT composition
  Node   : in/out degree (binary), in/out strength (synapse-weighted),
           PageRank
  Biological : metric summaries grouped by nt_sign (later: super_class, side)

Betweenness (sampled Brandes) lives in src/experiments/chokepoints.py where
it is needed for the control-impact analysis; baseline stays vectorized.

Run:  py -m src.graph.baseline
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT

PROCESSED = PROJECT_ROOT / "data" / "processed"
TABLES = PROJECT_ROOT / "results" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)


def build_sparse_adj(pairs: pd.DataFrame, node_index: dict[int, int],
                     weight_col: str = "syn_count_total",
                     binary: bool = False) -> sp.csr_matrix:
    """CSR adjacency from the pair table using the given node index mapping."""
    rows = pairs["pre_root_id"].map(node_index).to_numpy()
    cols = pairs["post_root_id"].map(node_index).to_numpy()
    if binary:
        data = np.ones(len(pairs), dtype=np.float64)
    else:
        data = pairs[weight_col].to_numpy(dtype=np.float64)
    n = len(node_index)
    return sp.csr_matrix((data, (rows, cols)), shape=(n, n))


def pagerank(A_bin: sp.csr_matrix, alpha: float = 0.85,
             max_iter: int = 100, tol: float = 1e-10) -> np.ndarray:
    """PageRank via power iteration on the row-normalized adjacency."""
    n = A_bin.shape[0]
    P = A_bin.astype(np.float64).tocsr(copy=True)
    row_sums = np.asarray(P.sum(axis=1)).ravel()
    dangling = row_sums == 0
    safe = row_sums.copy()
    safe[dangling] = 1.0
    P = sp.diags(1.0 / safe) @ P

    r = np.full(n, 1.0 / n)
    for _ in range(max_iter):
        r_new = (1.0 - alpha) / n + alpha * (P.T @ r)
        r_new += alpha * (r[dangling].sum() / n) if dangling.any() else 0.0
        if np.abs(r_new - r).sum() < tol:
            return r_new
        r = r_new
    return r


def main() -> None:
    t0 = time.time()
    pairs = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    core = pd.read_parquet(PROCESSED / "neuron_core.parquet")

    # Node universe: union of metadata neurons and edge-list neurons.
    all_nodes = pd.Index(
        pd.concat([core["root_id"], pairs["pre_root_id"], pairs["post_root_id"]])
    ).unique()
    node_index = {rid: i for i, rid in enumerate(all_nodes)}
    n = len(node_index)
    meta = core.set_index("root_id").reindex(all_nodes).reset_index()
    meta = meta.rename(columns={"index": "root_id"}) if "index" in meta.columns else meta

    A_w = build_sparse_adj(pairs, node_index, binary=False)
    A_b = build_sparse_adj(pairs, node_index, binary=True)
    print(f"Graph: {n:,} nodes | {len(pairs):,} edges")

    # ---------------- global stats
    B = A_b > 0
    nnz = B.nnz
    reciprocity = float(B.multiply(B.T).nnz / 2 / nnz) if nnz else 0.0

    A_sym = A_b + A_b.T
    n_components, labels = sp.csgraph.connected_components(
        A_sym, directed=False, return_labels=True
    )
    comp_sizes = pd.Series(labels).value_counts()

    # ---------------- node metrics (vectorized)
    out_deg = np.asarray(B.sum(axis=1)).ravel()
    in_deg = np.asarray(B.sum(axis=0)).ravel()
    out_str = np.asarray(A_w.sum(axis=1)).ravel()
    in_str = np.asarray(A_w.sum(axis=0)).ravel()
    pr = pagerank(A_b)

    metrics = pd.DataFrame({
        "root_id": all_nodes,
        "in_degree": in_deg.astype(np.int64),
        "out_degree": out_deg.astype(np.int64),
        "degree": (in_deg + out_deg).astype(np.int64),
        "in_strength": in_str,
        "out_strength": out_str,
        "pagerank": pr,
        "log_in_strength": np.log10(in_str + 1.0),
        "log_out_strength": np.log10(out_str + 1.0),
    })

    meta_cols = [c for c in ["root_id", "nt_type", "nt_sign", "nt_type_score",
                             "super_class", "class", "side", "primary_type",
                             "name"] if c in core.columns]
    metrics = metrics.merge(core[meta_cols], on="root_id", how="left")

    print("Writing baseline tables ...")
    metrics.to_parquet(TABLES / "baseline_node_metrics.parquet", index=False)

    by_nt = metrics.groupby("nt_sign", dropna=False).agg(
        n=("root_id", "size"),
        median_in_degree=("in_degree", "median"),
        median_out_degree=("out_degree", "median"),
        median_pagerank=("pagerank", "median"),
        mean_in_strength=("in_strength", "mean"),
        mean_out_strength=("out_strength", "mean"),
    )
    by_nt.to_csv(TABLES / "baseline_by_nt.csv")

    nt_edge_counts = (
        pairs.groupby("nt_type_edge", dropna=False).size()
        .rename("n_edges").reset_index()
    )
    nt_edge_counts.to_csv(TABLES / "baseline_edges_by_nt.csv", index=False)

    global_rows = [
        {"metric": "n_nodes", "value": float(n)},
        {"metric": "n_edges_pairs", "value": float(len(pairs))},
        {"metric": "mean_out_degree", "value": float(out_deg.mean())},
        {"metric": "mean_in_degree", "value": float(in_deg.mean())},
        {"metric": "density", "value": len(pairs) / (n * (n - 1))},
        {"metric": "reciprocity", "value": reciprocity},
        {"metric": "n_weak_components", "value": float(n_components)},
        {"metric": "largest_component_frac",
         "value": float(comp_sizes.iloc[0] / n)},
        {"metric": "median_pagerank", "value": float(np.median(pr))},
    ]
    pd.DataFrame(global_rows).to_csv(TABLES / "baseline_global.csv", index=False)

    print(f"Done in {time.time() - t0:.1f}s -> {TABLES}")
    print(global_rows)


if __name__ == "__main__":
    main()
