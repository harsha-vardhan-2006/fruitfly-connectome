"""E13-full: complete robustness battery (Gates 5 support).

13.1 Panel seeds at k=32: add seeds 2 and 3 on the 200 finalists
     (checkpointed, one file per (seed) -> ~6.5 min each); Spearman +
     4-way top-100 Jaccard.
13.2 Panel size: k=16 panel (seed 0) on finalists; screen(k=8) vs k=16 vs
     k=32 Spearman + Jaccard ladder.
13.3 Degree definition: which degree was used in E08 matching; recompute
     correlations of the alternatives (in/out/total) with CIS on tested set.
13.4 Metric sensitivity: reach_drop (k=32) vs CIS Spearman (already in
     e11_e14; recomputed here for the single E13 report).
13.5 GABA-definition sensitivity: redo E08 matching with GABA+GLUT as the
     'inhibitory-candidate' set; Wilcoxon on pairs + Cliff's delta.
13.6 Connection-table: DOCUMENTED ONLY - v783 Princeton no-threshold has
     5.6M rows => ~50M node-pairs after collapse; OOM risk at 8 GB RAM on
     this machine. Moved to a dedicated notebook on a >=32 GB machine; not
     a claim. Buhmann table: different reconstruction pipeline (not
     methodologically comparable per MASTER_PLAN 6.4) - excluded.

Run:  py -m src.experiments.run_e13_full
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from src.data.loaders import PROJECT_ROOT
from src.experiments.control_impact import PanelConfig, cis_bfs_panel
from src.experiments.run_e07_e09 import cliffs_delta

TABLES = PROJECT_ROOT / "results" / "tables"


def load_annotated() -> pd.DataFrame:
    return pd.read_parquet(TABLES / "e07_annotated.parquet")


def finalist_targets() -> list[int]:
    """The 200 E06 rerank targets = top150 by k=8 screen + 50 anchors."""
    fin = json.loads((TABLES / "e06_finalists.json").read_text())
    return [int(t) for t in (fin["top150"] + fin["anchors"])]


def run_seed(i: int) -> None:
    """Panel CIS (k=32, seed i) on the 200 finalists - checkpointed."""
    from src.experiments.run_e06 import build_graph

    ck = TABLES / f"e13_seed{i}_k32.parquet"
    if ck.exists():
        return
    A, _nodes, _idx = build_graph()
    targets = finalist_targets()
    res = cis_bfs_panel(A, targets=targets, cfg=PanelConfig(n_sources=32, seed=i))
    res["seed"] = i
    res.to_parquet(ck, index=False)
    print(f"[E13.1] seed {i} done: {len(res)} targets", flush=True)


def run_k16() -> None:
    """Panel CIS (k=16, seed 0) on finalists."""
    from src.experiments.run_e06 import build_graph

    ck = TABLES / "e13_k16_seed0.parquet"
    if ck.exists():
        return
    A, _nodes, _idx = build_graph()
    targets = finalist_targets()
    res = cis_bfs_panel(A, targets=targets, cfg=PanelConfig(n_sources=16, seed=0))
    res.to_parquet(ck, index=False)
    print(f"[E13.2] k=16 done: {len(res)} targets", flush=True)


def stability_report(df: pd.DataFrame) -> dict:
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    s0 = pd.read_parquet(TABLES / "e06_rerank_k32_seed0.parquet").rename(
        columns={"cis": "cis_s0"})
    s1 = pd.read_parquet(TABLES / "e06_rerank_k32_seed1.parquet").rename(
        columns={"cis": "cis_s1"})
    s2 = pd.read_parquet(TABLES / "e13_seed2_k32.parquet").rename(
        columns={"cis": "cis_s2"})
    s3 = pd.read_parquet(TABLES / "e13_seed3_k32.parquet").rename(
        columns={"cis": "cis_s3"})
    k16 = pd.read_parquet(TABLES / "e13_k16_seed0.parquet").rename(
        columns={"cis": "cis_k16"})

    seed_dfs = [s0, s1, s2, s3]
    m = rr[["target", "cis_mean"]].rename(columns={"cis_mean": "cis_k32main"})
    for sd, nm in zip(seed_dfs, ["s0", "s1", "s2", "s3"]):
        m = m.merge(sd[["target", f"cis_{nm}"]], on="target")
    m = m.merge(k16[["target", "cis_k16"]], on="target")
    m = m.merge(df[["target", "cis"]].rename(columns={"cis": "cis_k8"}),
                on="target")

    # k=32 variants: main run (mean of seeds 0+1) plus 4 independent seeds;
    # 4-seed Jaccard uses ONLY the independent per-seed files.
    seed_cols = ["cis_s0", "cis_s1", "cis_s2", "cis_s3"]
    k_cols = ["cis_k8", "cis_k16", "cis_k32main"]
    seed_rhos = {c: float(m["cis_k32main"].corr(m[c], method="spearman"))
                 for c in seed_cols}
    k_ladder = {f"{a}_vs_{b}": float(m[a].corr(m[b], method="spearman"))
                for ai, a in enumerate(k_cols) for b in k_cols[ai + 1:]}

    def jaccard(cols: list[str], n_top: int = 100) -> float:
        tops = [set(m.nlargest(n_top, c)["target"]) for c in cols]
        u = set().union(*tops)
        return float(len(set.intersection(*tops)) / len(u))

    return {
        "spearman_vs_main_k32": seed_rhos,
        "k_ladder_spearman": k_ladder,
        "top100_jaccard_4seeds": jaccard(seed_cols),
        "top100_jaccard_k_ladder": jaccard(k_cols),
        "top50_jaccard_4seeds": jaccard(seed_cols, 50),
        "top50_jaccard_k_ladder": jaccard(k_cols, 50),
    }


def degree_definition_sensitivity(df: pd.DataFrame) -> dict:
    """Correlate in/out/total degree with CIS on the tested population,
    and report degree composition of the top-50 (which definition drives
    high CIS: in- or out-degree?)."""
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    top50 = set(rr.nlargest(50, "cis_mean")["root_id"])
    sub = df[df["root_id"].isin(top50)]
    tested = df[df["cis"].notna()]
    out = {
        "spearman_cis_vs_total_degree": float(
            tested["cis"].corr(tested["total_degree"], method="spearman")),
        "spearman_cis_vs_in_degree": float(
            tested["cis"].corr(tested["in_degree"], method="spearman")),
        "spearman_cis_vs_out_degree": float(
            tested["cis"].corr(tested["out_degree"], method="spearman")),
        "top50_median_in_degree": float(sub["in_degree"].median()),
        "top50_median_out_degree": float(sub["out_degree"].median()),
        "top50_median_total_degree": float(sub["total_degree"].median()),
        "tested_median_total_degree": float(tested["total_degree"].median()),
    }
    return out


def _greedy_match(df: pd.DataFrame, case_col: str, case_val: str,
                  ctrl_col: str, ctrl_val: str, window: float = 0.10,
                  seed: int = 0) -> pd.DataFrame:
    """1:1 greedy degree matching, same algorithm as E08 degree_match
    (larger-degree cases first, nearest-degree control, without replacement,
    rng tiebreak) but with configurable class columns for sensitivity defs."""
    rng = np.random.default_rng(seed)
    case = df[df[case_col] == case_val].sort_values("total_degree",
                                                    ascending=False)
    pool = df[df[ctrl_col] == ctrl_val].copy()
    used: set[int] = set()
    rows = []
    for _, g in case.iterrows():
        d = g["total_degree"]
        lo, hi = d * (1 - window), d * (1 + window)
        cand = pool[(pool["total_degree"] >= lo)
                    & (pool["total_degree"] <= hi)
                    & (~pool["target"].isin(used))]
        if cand.empty:
            continue
        cand = cand.assign(_d=(cand["total_degree"] - d).abs()
                           + rng.random(len(cand)) * 1e-6)
        c = cand.nsmallest(1, "_d").iloc[0]
        used.add(int(c["target"]))
        rows.append({"case_target": int(g["target"]),
                     "case_cis": g["cis"], "case_degree": d,
                     "ctrl_target": int(c["target"]),
                     "ctrl_cis": c["cis"], "ctrl_degree": c["total_degree"]})
    return pd.DataFrame(rows)


def gaba_glut_sensitivity(df: pd.DataFrame) -> dict:
    """E08 redo with the inhibitory-candidate set = GABA+GLUT."""
    df2 = df.copy()
    df2["nt2"] = df2["nt_type"].where(
        ~df2["nt_type"].isin(["GABA", "GLUT"]), "INH_CAND")
    pairs = _greedy_match(df2, "nt2", "INH_CAND", "nt2", "ACH")
    g = pairs["case_cis"].to_numpy()
    c = pairs["ctrl_cis"].to_numpy()
    stat = wilcoxon(g, c)
    perm = permutation_p(g, c)
    return {
        "n_pairs_inh_cand_vs_ach": int(len(pairs)),
        "median_inh_cand_minus_ach": float(np.median(g) - np.median(c)),
        "wilcoxon_p": float(stat.pvalue),
        "cliffs_delta": cliffs_delta(g, c),
        "sign_flip_permutation_p": perm,
        "note": "sensitivity definition only - GLUT is ambiguous E/I; "
                "primary comparison remains GABA vs ACh",
    }


def permutation_p(g: np.ndarray, c: np.ndarray, n_perm: int = 10_000) -> float:
    """Sign-flip permutation on paired differences (exact labels within
    pairs are exchanged)."""
    d = g - c
    obs = np.median(d)
    rng = np.random.default_rng(123)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    null = np.median(signs * d[None, :], axis=1)
    return float((1 + int((np.abs(null) >= abs(obs)).sum())) / (n_perm + 1))


def main() -> None:
    t0 = time.perf_counter()
    df = load_annotated()

    print("[E13] running k=32 seeds 2,3 (~6.5 min each) ...", flush=True)
    run_seed(2)
    run_seed(3)
    print("[E13] running k=16 seed 0 ...", flush=True)
    run_k16()

    print("[E13] stability report ...", flush=True)
    stab = stability_report(df)

    print("[E13] degree-definition sensitivity ...", flush=True)
    dd = degree_definition_sensitivity(df)

    print("[E13] GABA+GLUT sensitivity ...", flush=True)
    gg = gaba_glut_sensitivity(df)

    out = {
        "seeds_k32": {"added": [2, 3], "total_seeds": 4},
        "stability": stab,
        "degree_definition": dd,
        "gaba_glut_sensitivity": gg,
        "connection_table": {
            "status": "documented_not_run",
            "reason": "no-threshold collapse ~50M node-pairs exceeds 8 GB RAM "
                      "on this machine; moved to dedicated high-RAM notebook; "
                      "Buhmann excluded as methodologically non-comparable",
        },
        "metric": {
            "status": "ok",
            "spearman_cis_vs_reach_drop": read_reach_corr(),
        },
        "runtime_s": round(time.perf_counter() - t0, 1),
    }
    (TABLES / "e13_full_results.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


def read_reach_corr() -> float:
    try:
        return float(pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
                     ["cis_mean"].corr(
                         pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
                         ["reach_drop_mean"], method="spearman"))
    except Exception:
        return float("nan")


if __name__ == "__main__":
    main()
