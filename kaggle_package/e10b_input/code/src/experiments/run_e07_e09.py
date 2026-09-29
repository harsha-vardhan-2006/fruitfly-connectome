"""E07-E09: GABA annotation, degree matching, statistics.

E07: join E06 CIS tables with neuron metadata; annotation-quality counts.
E08: degree-matched GABA-vs-ACh comparison (PRE-REGISTERED in E08 spec:
     primary match = total degree within +/-10%, control class = ACh;
     1:1 greedy matching without replacement).
E09: descriptives per group, Cliff's delta, Wilcoxon signed-rank on pairs,
     label-permutation test on median difference, OLS
     log10(CIS+eps) ~ GABA + log10(degree) with permutation p for beta1.

Run:  py -m src.experiments.run_e07_e09
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.stats import wilcoxon

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
PROCESSED = PROJECT_ROOT / "data" / "processed"
EPS = 1e-7


# ------------------------------------------------------------------ E07

def annotate() -> pd.DataFrame:
    screen = pd.read_parquet(TABLES / "e06_screen_k8.parquet")
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    core = pd.read_parquet(PROCESSED / "neuron_core.parquet")

    pairs = pd.read_parquet(PROCESSED / "graph_pairs.parquet")
    deg = (pairs.groupby("pre_root_id").size().rename("out_degree")
           .to_frame().join(pairs.groupby("post_root_id").size()
                            .rename("in_degree"), how="outer").fillna(0))
    deg["total_degree"] = deg["out_degree"] + deg["in_degree"]
    deg.index.name = "root_id"

    df = (screen.merge(core, on="root_id", how="left")
                .merge(deg.reset_index(), on="root_id", how="left"))
    # attach reranked (k=32, 2-seed mean) CIS where available
    df = df.merge(rr.rename(columns={"cis_mean": "cis_k32",
                                     "target": "rr_target"}),
                  on="root_id", how="left")
    df["is_finalist"] = df["cis_k32"].notna()
    df.to_parquet(TABLES / "e07_annotated.parquet", index=False)

    counts = {
        "total_tested": int(len(df)),
        "by_nt": df["nt_type"].value_counts(dropna=False).to_dict(),
        "by_nt_sign": df["nt_sign"].value_counts(dropna=False).to_dict(),
        "pct_annotated_nt": float(df["nt_type"].notna().mean() * 100),
    }
    (TABLES / "e07_annotation_quality.json").write_text(json.dumps(counts, indent=2, default=str))
    return df


# ------------------------------------------------------------------ E08

def degree_match(df: pd.DataFrame, window: float = 0.10,
                 seed: int = 0) -> pd.DataFrame:
    """1:1 greedy matching, GABA (tested) vs ACh (tested), total degree +/-window.

    Pre-registered: match on total degree; control class = ACh; without
    replacement (each control used once); larger-degree GABA matched first.
    """
    rng = np.random.default_rng(seed)
    gaba = df[df["nt_type"] == "GABA"].sort_values("total_degree", ascending=False)
    ach_pool = df[df["nt_type"] == "ACH"].copy()

    used: set[int] = set()
    rows = []
    for _, g in gaba.iterrows():
        d = g["total_degree"]
        lo, hi = d * (1 - window), d * (1 + window)
        cand = ach_pool[(ach_pool["total_degree"] >= lo)
                        & (ach_pool["total_degree"] <= hi)
                        & (~ach_pool["target"].isin(used))]
        if cand.empty:
            continue
        # nearest-degree control; rng tiebreak
        cand = cand.assign(_d=(cand["total_degree"] - d).abs()
                           + rng.random(len(cand)) * 1e-6)
        c = cand.nsmallest(1, "_d").iloc[0]
        used.add(int(c["target"]))
        rows.append({
            "gaba_target": int(g["target"]), "gaba_root_id": g["root_id"],
            "gaba_cis_k8": g["cis"],
            "gaba_cis_k32": g.get("cis_k32", np.nan),
            "gaba_degree": d, "gaba_in_degree": g["in_degree"],
            "gaba_out_degree": g["out_degree"],
            "ctrl_target": int(c["target"]), "ctrl_root_id": c["root_id"],
            "ctrl_cis_k8": c["cis"], "ctrl_cis_k32": c.get("cis_k32", np.nan),
            "ctrl_degree": c["total_degree"],
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ E09

def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Cliff's delta via Mann-Whitney U (rank-based, no pairwise loops)."""
    from scipy.stats import mannwhitneyu
    n1, n2 = len(x), len(y)
    u = mannwhitneyu(x, y, alternative="two-sided").statistic
    return float(2.0 * u / (n1 * n2) - 1.0)


def permutation_median_diff(x: np.ndarray, y: np.ndarray,
                            n_perm: int = 10_000, seed: int = 0) -> tuple[float, float]:
    """Observed median(x)-median(y) and two-sided permutation p."""
    rng = np.random.default_rng(seed)
    obs = float(np.median(x) - np.median(y))
    pooled = np.concatenate([x, y])
    nx = len(x)
    count = 0
    for _ in range(n_perm):
        p = rng.permutation(pooled)
        d = np.median(p[:nx]) - np.median(p[nx:])
        if abs(d) >= abs(obs):
            count += 1
    return obs, (count + 1) / (n_perm + 1)


def ols_permutation(df: pd.DataFrame, n_perm: int = 5_000,
                    seed: int = 0) -> dict:
    """log10(CIS+eps) ~ 1 + GABA + log10(total_degree); beta1 permutation p."""
    rng = np.random.default_rng(seed)
    y = np.log10(df["cis"].to_numpy() + EPS)
    gaba = (df["nt_type"] == "GABA").to_numpy(dtype=float)
    X = np.column_stack([
        np.ones(len(df)), gaba,
        np.log10(df["total_degree"].to_numpy() + 1.0),
    ])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    def _beta1(yy: np.ndarray, gg: np.ndarray) -> float:
        Xi = np.column_stack([np.ones(len(yy)), gg,
                              np.log10(df["total_degree"].to_numpy() + 1.0)])
        b, *_ = np.linalg.lstsq(Xi, yy, rcond=None)
        return float(b[1])

    obs = _beta1(y, gaba)
    count = 0
    for _ in range(n_perm):
        if _beta1(rng.permutation(y), gaba) >= obs:
            count += 1
    return {"beta0": float(beta[0]), "beta1_gaba": float(beta[1]),
            "beta2_logdegree": float(beta[2]),
            "beta1_perm_p_one_sided": (count + 1) / (n_perm + 1)}


def main() -> None:
    print("[E07] annotating ...")
    df = annotate()
    print(json.loads((TABLES / "e07_annotation_quality.json").read_text()))

    print("[E08] degree matching (pre-registered: total degree +/-10%, GABA vs ACh) ...")
    matched = degree_match(df)
    matched.to_csv(TABLES / "e08_matched_pairs.csv", index=False)
    print(f"  matched pairs: {len(matched)} "
          f"(GABA tested: {(df['nt_type']=='GABA').sum()})")

    print("[E09] statistics ...")
    use_k32 = matched["gaba_cis_k32"].notna().all() and len(matched) >= 30
    col = "gaba_cis_k32" if use_k32 else "gaba_cis_k8"
    ccol = "ctrl_cis_k32" if use_k32 else "ctrl_cis_k8"
    x = matched[col].to_numpy()
    y = matched[ccol].to_numpy()

    desc = pd.DataFrame({
        "group": ["GABA_matched", "ACh_control"],
        "n": [len(x), len(y)],
        "mean_cis": [x.mean(), y.mean()],
        "median_cis": [np.median(x), np.median(y)],
        "sd_cis": [x.std(ddof=1), y.std(ddof=1)],
        "iqr_cis": [np.subtract(*np.percentile(x, [75, 25])),
                    np.subtract(*np.percentile(y, [75, 25]))],
    })
    desc.to_csv(TABLES / "e09_descriptives.csv", index=False)

    delta = cliffs_delta(x, y)
    w_stat, w_p = wilcoxon(x, y)
    obs_diff, perm_p = permutation_median_diff(x, y)
    reg = ols_permutation(df[df["nt_type"].isin(["GABA", "ACH"])])

    # group-level comparison on ALL tested GABA vs ALL tested ACh (unmatched,
    # degree-confounded by design - reported for transparency only)
    g_all = df.loc[df["nt_type"] == "GABA", "cis"].to_numpy()
    a_all = df.loc[df["nt_type"] == "ACH", "cis"].to_numpy()

    results = {
        "cis_column_used": col,
        "matched_pairs": int(len(matched)),
        "cliffs_delta_matched": delta,
        "wilcoxon_signed_rank_p": float(w_p),
        "median_diff_matched": obs_diff,
        "permutation_p_median_diff": perm_p,
        "ols_log_cis": reg,
        "unmatched_median_gaba": float(np.median(g_all)),
        "unmatched_median_ach": float(np.median(a_all)),
        "unmatched_cliffs_delta": cliffs_delta(g_all, a_all),
        "background_median_cis_random500": float(
            df[df["in_background"] == True]["cis"].median())
        if "in_background" in df.columns else None,
    }
    (TABLES / "e09_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
