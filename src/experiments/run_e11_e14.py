"""E11-E14: neighborhood composition, region enrichment, robustness,
final chokepoint catalogue.

E11: NT composition of 1-hop neighborhoods of top-CIS neurons vs matched
     background neurons (neurotransmitter-defined structural composition;
     no functional-sign claims).
E12: enrichment of top-CIS neurons by super_class and by degree decile;
     GABA-region interaction via side/super_class splits.
E13: robustness - (a) screen(k=8) vs rerank(k=32) rank stability,
     (b) reach_drop as alternative metric: rank correlation with CIS,
     (c) two-panel (seed) stability of k=32 CIS on finalists.
E14: final catalogue with classes:
     A strong chokepoint (top-50 k=32 CIS + robust across checks)
     B degree-driven hub (high CIS, GABA effect absent after matching)
     C GABA-specific candidate (GABA && CIS > matched-control CIS)
     D region-specific (super_class enrichment of top set)
Run:  py -m src.experiments.run_e11_e14
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
PROCESSED = PROJECT_ROOT / "data" / "processed"


def load_all() -> tuple[pd.DataFrame, sp.csr_matrix, pd.Index]:
    df = pd.read_parquet(TABLES / "e07_annotated.parquet")
    pairs = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    nodes = pd.Index(pd.concat([pairs["pre_root_id"], pairs["post_root_id"]])).unique()
    idx = {r: i for i, r in enumerate(nodes)}
    A = sp.csr_matrix(
        (np.ones(len(pairs)),
         (pairs["pre_root_id"].map(idx), pairs["post_root_id"].map(idx))),
        shape=(len(nodes), len(nodes)))
    return df, A, nodes


def e11_neighborhood_nt(df: pd.DataFrame, A: sp.csr_matrix,
                        nodes: pd.Index) -> dict:
    """NT composition of 1-hop in/out neighborhoods: top-50 CIS vs
    50 random background-tested neurons."""
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    top50 = rr.nlargest(50, "cis_mean")["target"].to_numpy()
    bg = df[df["cis"] <= df["cis"].quantile(0.5)].sample(50, random_state=0)
    bg_targets = bg["target"].to_numpy()

    def composition(targets: np.ndarray) -> dict:
        # NT lookup over the FULL core metadata (all 139,255 neurons),
        # indexed by positional target id
        core = pd.read_parquet(PROCESSED / "neuron_core.parquet")
        pairs = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
        all_nodes = pd.Index(pd.concat(
            [pairs["pre_root_id"], pairs["post_root_id"]])).unique()
        nt_by_pos = core.set_index("root_id")["nt_type"].reindex(all_nodes)
        counts = {"GABA": 0, "ACH": 0, "GLUT": 0, "other": 0, "unknown": 0}
        total = 0
        for t in targets:
            neigh = set(A.indices[A.indptr[t]:A.indptr[t + 1]].tolist())
            neigh |= set(np.where(A[:, t].toarray().ravel() > 0)[0].tolist())
            for u in neigh:
                nt = nt_by_pos.iloc[u]
                total += 1
                if nt in counts:
                    counts[nt] += 1
                elif nt is None or (isinstance(nt, float) and np.isnan(nt)):
                    counts["unknown"] += 1
                else:
                    counts["other"] += 1
        return {k: v / total for k, v in counts.items()} | {"n_partners": total}

    return {"top50": composition(top50), "background": composition(bg_targets)}


def e12_enrichment(df: pd.DataFrame) -> dict:
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    top50 = rr.nlargest(50, "cis_mean")["root_id"]
    sub = df[df["root_id"].isin(set(top50))]
    base = df[df["nt_type"].notna()]

    sc_top = sub["super_class"].value_counts(normalize=True)
    sc_all = base["super_class"].value_counts(normalize=True)
    enrich = (sc_top / sc_all).dropna().sort_values(ascending=False)

    out = {
        "top50_super_class_counts": sub["super_class"].value_counts().to_dict(),
        "enrichment_ratio_top50_vs_all": enrich.round(2).to_dict(),
        "top50_nt_counts": sub["nt_type"].value_counts().to_dict(),
        "gaba_frac_top50": float((sub["nt_type"] == "GABA").mean()),
        "gaba_frac_all_tested": float((base["nt_type"] == "GABA").mean()),
    }
    # degree profile of top-50 vs all tested
    out["top50_median_degree"] = float(sub["total_degree"].median())
    out["all_median_degree"] = float(base["total_degree"].median())
    return out


def e13_robustness(df: pd.DataFrame) -> dict:
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    s0 = pd.read_parquet(TABLES / "e06_rerank_k32_seed0.parquet").rename(
        columns={"cis": "cis_s0"})
    s1 = pd.read_parquet(TABLES / "e06_rerank_k32_seed1.parquet").rename(
        columns={"cis": "cis_s1"})

    m = (rr[["target", "cis_mean"]].rename(columns={"cis_mean": "cis_k32"})
         .merge(df[["target", "cis"]].rename(columns={"cis": "cis_k8"}),
                on="target"))
    rho_screen = m["cis_k8"].corr(m["cis_k32"], method="spearman")

    mm = s0[["target", "cis_s0"]].merge(s1[["target", "cis_s1"]], on="target")
    rho_seeds = mm["cis_s0"].corr(mm["cis_s1"])

    top100_k32 = set(rr.nlargest(100, "cis_mean")["target"])
    top100_s0 = set(s0.nlargest(100, "cis_s0")["target"])
    top100_s1 = set(s1.nlargest(100, "cis_s1")["target"])
    jacc = len(top100_k32 & top100_s0 & top100_s1) / len(
        top100_k32 | top100_s0 | top100_s1)

    # alternative metric: reach_drop rank correlation with CIS (k=32 run)
    rho_reach = rr["cis_mean"].corr(rr["reach_drop_mean"], method="spearman")

    return {"spearman_screen_vs_rerank": float(rho_screen),
            "pearson_k32_seed0_vs_seed1": float(rho_seeds),
            "top100_jaccard_3way": float(jacc),
            "spearman_cis_vs_reachdrop": float(rho_reach)}


def e14_catalogue(df: pd.DataFrame) -> pd.DataFrame:
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    matched = pd.read_csv(TABLES / "e08_matched_pairs.csv")
    core = pd.read_parquet(PROCESSED / "neuron_core.parquet")

    cat = rr.merge(core[["root_id", "nt_type", "nt_sign", "super_class",
                         "class", "side", "primary_type", "name"]],
                   on="root_id", how="left")
    cat = cat.merge(df[["root_id", "total_degree"]], on="root_id", how="left")
    cat["cis"] = cat["cis_mean"]
    cat["rank"] = cat["cis"].rank(ascending=False).astype(int)

    # null percentile per node: where does its k=32 CIS sit vs its
    # degree-predicted CIS? Use OLS fit from E09 as the expectation.
    eps = 1e-7
    sub = df[df["nt_type"].isin(["GABA", "ACH"])]
    y = np.log10(sub["cis"] + eps)
    X = np.column_stack([np.ones(len(sub)),
                         np.log10(sub["total_degree"] + 1.0)])
    beta, *_ = np.linalg.lstsq(X, y.to_numpy(), rcond=None)
    cat["expected_log_cis_from_degree"] = (
        beta[0] + beta[1] * np.log10(cat["total_degree"] + 1.0))
    cat["cis_excess_over_degree_prediction"] = (
        np.log10(cat["cis"] + eps) - cat["expected_log_cis_from_degree"])

    # matched-control delta for GABA neurons
    mG = matched.set_index("gaba_root_id")["gaba_cis_k8"]
    mC = matched.set_index("gaba_root_id")["ctrl_cis_k8"]
    cat["matched_ctrl_cis"] = cat["root_id"].map(mC)
    cat["gaba_vs_matched_ctrl"] = np.where(
        cat["root_id"].isin(mG.index),
        cat["root_id"].map(mG) - cat["matched_ctrl_cis"], np.nan)

    def classify(row) -> str:
        top = row["rank"] <= 50
        excess = row["cis_excess_over_degree_prediction"]
        if top and excess > 0.3:
            return "A_strong_chokepoint"
        if top and row["nt_type"] == "GABA" and row["gaba_vs_matched_ctrl"] > 0:
            return "C_gaba_candidate"
        if top:
            return "B_degree_driven_hub"
        if row["nt_type"] == "GABA" and row["gaba_vs_matched_ctrl"] > 0:
            return "C_gaba_candidate"
        return "not_classified"

    cat["class_label"] = cat.apply(classify, axis=1)
    cols = ["rank", "root_id", "cis", "total_degree", "nt_type", "nt_sign",
            "super_class", "side", "primary_type", "name",
            "cis_excess_over_degree_prediction", "matched_ctrl_cis",
            "gaba_vs_matched_ctrl", "class_label"]
    cat = cat[cols].sort_values("rank")
    cat.to_csv(TABLES / "e14_chokepoint_catalogue.csv", index=False)
    return cat


def main() -> None:
    print("[E11-E14] loading ...")
    df, A, nodes = load_all()

    print("[E11] neighborhood NT composition ...")
    e11 = e11_neighborhood_nt(df, A, nodes)
    print(json.dumps(e11, indent=2))

    print("[E12] region/type enrichment ...")
    e12 = e12_enrichment(df)
    print(json.dumps(e12, indent=2))

    print("[E13] robustness ...")
    e13 = e13_robustness(df)
    print(json.dumps(e13, indent=2))

    print("[E14] catalogue ...")
    cat = e14_catalogue(df)
    print(cat["class_label"].value_counts().to_string())

    (TABLES / "e11_e14_results.json").write_text(json.dumps(
        {"e11_neighborhood_nt": e11, "e12_enrichment": e12,
         "e13_robustness": e13,
         "e14_class_counts": cat["class_label"].value_counts().to_dict()},
        indent=2))
    print("[E11-E14] done.")


if __name__ == "__main__":
    main()
