"""E14 v2: selection-bias-corrected chokepoint catalogue.

Correction vs v1 (documented in RESEARCH_LOG E14b): the old
cis_excess_over_degree_prediction residual was computed relative to an OLS
fit and used to label 'strong chokepoints' among nodes ALREADY selected for
top CIS - inflating residuals (selection on the outcome variable). v2
replaces it with an empirical, population-calibrated statistic:

  emp_p_degree_matched(node) = fraction of tested neurons within +/-10%
  total degree (nearest-50 fallback) whose CIS >= the node's CIS
  (2,000 Monte-Carlo draws per node, seed 14).

A top-50 node with emp_p < 0.01 has impact genuinely beyond degree peers
calibrated on the FULL tested population (no selection circularity).
Also reported per node: median CIS of its degree-peer pool
(cis_excess_ratio = node CIS / peer median).

Class labels:
  A_strong_chokepoint  top-50 & emp_p < 0.01
  B_degree_driven_hub  top-50 & emp_p >= 0.05
  B_intermediate       top-50 & 0.01 <= emp_p < 0.05
  + tags: D_visual_system (super_class in {visual_centrifugal, optic});
          C_gaba_exploratory (GABA & matched-ctrl delta > 0; Gate-4 pilot
          negative, so exploratory only)

Run:  py -m src.experiments.run_e14_v2
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
N_DRAWS = 2_000
RNG_SEED = 14


def emp_p_and_peer_median(deg: np.ndarray, cis: np.ndarray,
                          pos_of: dict, node_targets: np.ndarray,
                          ) -> tuple[np.ndarray, np.ndarray]:
    """Monte-Carlo degree-matched exceedance p + peer-pool median CIS."""
    log_deg = np.log10(deg + 1.0)
    order = np.argsort(log_deg)
    sorted_ld = log_deg[order]
    rng = np.random.default_rng(RNG_SEED)
    emp = np.empty(len(node_targets))
    peer_med = np.empty(len(node_targets))
    pool_n = np.empty(len(node_targets), dtype=int)
    for j, t in enumerate(node_targets):
        i = pos_of[t]
        ld = log_deg[i]
        lo, hi = ld - np.log10(1.1), ld + np.log10(1.1)
        a = np.searchsorted(sorted_ld, lo, side="left")
        b = np.searchsorted(sorted_ld, hi, side="right")
        if b > a:
            pool = order[a:b]
        else:  # fallback: nearest 50 by degree on each side
            p = np.searchsorted(sorted_ld, ld)
            pool = order[max(0, p - 50):p + 50]
        pool = pool[pool != i]  # EXCLUDE SELF (critical for tiny pools)
        pool_n[j] = len(pool)
        draws = pool[rng.integers(0, len(pool), size=N_DRAWS)]
        emp[j] = float((cis[draws] >= cis[i]).mean())
        peer_med[j] = float(np.median(cis[pool]))
    return emp, peer_med, pool_n


def main() -> None:
    df = pd.read_parquet(TABLES / "e07_annotated.parquet")
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    core = pd.read_parquet(
        PROJECT_ROOT / "data" / "processed" / "neuron_core.parquet")[
        ["root_id", "super_class", "side", "name", "primary_type"]]
    matched = pd.read_csv(TABLES / "e08_matched_pairs.csv")

    df = df.merge(core, on="root_id", how="left", suffixes=("", "_core"))
    tested = df.set_index("target")
    deg = tested["total_degree"].to_numpy(dtype=float)
    cis = tested["cis"].to_numpy(dtype=float)
    pos_of = {t: i for i, t in enumerate(tested.index.to_numpy())}

    top = rr.nlargest(50, "cis_mean")["target"].astype(int).to_numpy()
    emp, peer_med, pool_n = emp_p_and_peer_median(deg, cis, pos_of, top)

    sub = tested.loc[top].copy()
    sub["rank"] = range(1, 51)
    sub["emp_p_degree_matched"] = emp
    sub["peer_median_cis"] = peer_med
    sub["peer_pool_n"] = pool_n
    sub["cis_excess_ratio"] = sub["cis"] / peer_med

    # matched-control delta for GABA rows (exploratory context)
    mC = matched.set_index("gaba_root_id")["ctrl_cis_k8"]
    mG = matched.set_index("gaba_root_id")["gaba_cis_k8"]
    has_match = sub["root_id"].isin(mG.index)
    sub["gaba_vs_matched_ctrl"] = np.where(
        has_match, sub["root_id"].map(mG) - sub["root_id"].map(mC), np.nan)

    def classify(row) -> str:
        if row["emp_p_degree_matched"] < 0.01:
            base = "A_strong_chokepoint"
        elif row["emp_p_degree_matched"] >= 0.05:
            base = "B_degree_driven_hub"
        else:
            base = "B_intermediate"
        tags = []
        if row["super_class"] in ("visual_centrifugal", "optic"):
            tags.append("D_visual_system")
        if row["nt_type"] == "GABA" and row["gaba_vs_matched_ctrl"] > 0:
            tags.append("C_gaba_exploratory")
        return base + ("|" + "+".join(tags) if tags else "")

    sub["class_label"] = sub.apply(classify, axis=1)
    cols = ["rank", "root_id", "cis", "total_degree", "in_degree",
            "out_degree", "nt_type", "nt_sign", "super_class", "side",
            "primary_type", "name", "emp_p_degree_matched",
            "peer_pool_n", "peer_median_cis", "cis_excess_ratio",
            "gaba_vs_matched_ctrl", "class_label"]
    cat = sub[cols].sort_values("rank")
    cat.to_csv(TABLES / "e14_chokepoint_catalogue_v2.csv", index=False)

    summary = {
        "n_top50": 50,
        "class_counts": cat["class_label"].value_counts().to_dict(),
        "median_emp_p": float(cat["emp_p_degree_matched"].median()),
        "n_emp_p_below_0.01": int((cat["emp_p_degree_matched"] < 0.01).sum()),
        "n_emp_p_below_0.05": int((cat["emp_p_degree_matched"] < 0.05).sum()),
        "n_tiny_pools_lt10": int((cat["peer_pool_n"] < 10).sum()),
        "visual_system_fraction_top50": float(
            cat["super_class"].isin(["visual_centrifugal", "optic"]).mean()),
        "median_cis_excess_ratio": float(cat["cis_excess_ratio"].median()),
        "note": "emp_p calibrated on full tested population, self excluded "
                "from pools; tiny peer pools (<10) flagged via peer_pool_n; "
                "Gate-4 closed by E10B 100-null ensemble (p_delta = 0.109, "
                "p_median_diff = 0.782; results/final/e10b_final.json)",
    }
    (TABLES / "e14_v2_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(cat[["rank", "root_id", "cis", "total_degree", "nt_type",
               "super_class", "emp_p_degree_matched", "cis_excess_ratio",
               "class_label"]].head(12).to_string(index=False))


if __name__ == "__main__":
    main()
