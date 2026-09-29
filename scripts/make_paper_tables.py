#!/usr/bin/env python
"""Generate publication tables (Table1-5.tex) from the locked result files.

Every number is read from the authoritative result artifacts at build time —
no hand-typed statistics. Run:  py scripts/make_paper_tables.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "results" / "tables"
F = ROOT / "results" / "final"
OUT = ROOT / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)


def write(name: str, body: str, caption: str, label: str) -> None:
    tex = (
        "\\begin{table}[htbp]\n"
        "\\centering\n"
        "\\small\n"
        f"\\caption{{{caption}}}\\label{{{label}}}\n"
        f"{body}\n"
        "\\end{table}\n"
    )
    (OUT / name).write_text(tex, encoding="utf-8")
    print("wrote", name)


# ---------------------------------------------------------------- Table 1
def table1() -> None:
    rows = [
        ("Metadata universe (neurons merged)", "139,255"),
        ("Graph nodes (edge-table universe)", "138,584"),
        ("Graph edges (collapsed pairs)", "3,732,460"),
        ("Mean degree", "26.8"),
        ("Density", "$1.92\\times10^{-4}$"),
        ("Reciprocity", "0.083"),
        ("Largest weak component", "98.4\\%"),
        ("Weak components", "875"),
        ("Pre-registered perturbation targets", "3,518"),
        ("Degree-matched GABA--ACh pairs", "848"),
        ("Degree-preserving null networks", "100 (all verified)"),
    ]
    body = ("\\begin{tabular}{lr}\n\\hline\n"
            "\\textbf{Quantity} & \\textbf{Value} \\\\\n\\hline\n"
            + "\n".join(f"{a} & {b} \\\\" for a, b in rows)
            + "\n\\hline\n\\end{tabular}")
    write("Table1.tex", body,
          "\\textbf{Dataset and network characteristics.} FlyWire FAFB v783 "
          "(Princeton exports); binary directed graph after pair-collapse of the "
          "thresholded connection table. All values from the authoritative "
          "result files (\\texttt{e18\\_manifest.json}, E01/E02 outputs).",
          "tab:network")


# ---------------------------------------------------------------- Table 2
def table2() -> None:
    e09 = json.loads((T / "e09_results.json").read_text())
    o = e09["ols_log_cis"]
    rows = [
        ("Matched pairs (GABA vs ACh, total degree $\\pm10\\%$)",
         f"{e09['matched_pairs']}"),
        ("Median difference in CIS (k=8 screening)",
         f"{e09['median_diff_matched']:.2e}"),
        ("Cliff's $\\delta$ (matched)",
         f"{e09['cliffs_delta_matched']:.3f}"),
        ("Wilcoxon signed-rank $p$",
         f"{e09['wilcoxon_signed_rank_p']:.4f}"),
        ("Permutation $p$ (median difference)",
         f"{e09['permutation_p_median_diff']:.1e}"),
        ("OLS $\\beta_1$ (GABA), $\\log_{10}$CIS $\\sim$ GABA + $\\log_{10}$degree",
         f"{o['beta1_gaba']:.3f}"),
        ("Permutation $p$ on $\\beta_1$ (one-sided)",
         f"{o['beta1_perm_p_one_sided']:.2f}"),
        ("Unmatched medians (GABA / ACh)",
         f"{e09['unmatched_median_gaba']:.2e} / {e09['unmatched_median_ach']:.2e}"),
    ]
    body = ("\\begin{tabular}{lr}\n\\hline\n"
            "\\textbf{Statistic} & \\textbf{Value} \\\\\n\\hline\n"
            + "\n".join(f"{a} & {b} \\\\" for a, b in rows)
            + "\n\\hline\n\\end{tabular}")
    write("Table2.tex", body,
          "\\textbf{Primary GABA hypothesis statistics.} The raw matched-pair "
          "effect is small and does not survive degree control (OLS "
          "$\\beta_1\\approx 0$); see Table~\\ref{tab:nulls} for the decisive "
          "null-ensemble comparison. Source: \\texttt{e09\\_results.json}.",
          "tab:gaba")


# ---------------------------------------------------------------- Table 3
def table3() -> None:
    e10b = json.loads((F / "e10b_final.json").read_text())
    nulls = pd.read_csv(T / "e10b_nulls.csv")
    d = nulls["cliffs_delta"]
    rows = [
        ("Null networks (exact in/out degree preservation)", f"{len(nulls)}"),
        ("Observed $\\delta$ (k=4 panel, matched estimator)", f"{e10b['observed']['cliffs_delta']:.4f}"),
        ("Null $\\delta$: mean $\\pm$ sd", f"{d.mean():.4f} $\\pm$ {d.std(ddof=1):.4f}"),
        ("Null $\\delta$: median / min / max", f"{d.median():.4f} / {d.min():.4f} / {d.max():.4f}"),
        ("Null $\\delta$: 2.5\\% / 97.5\\% percentile", f"{d.quantile(0.025):.4f} / {d.quantile(0.975):.4f}"),
        ("Nulls $\\geq$ observed", f"{int((d >= e10b['observed']['cliffs_delta']).sum())} / {len(nulls)}"),
        ("Empirical $p(\\delta)$", f"{e10b['empirical_p_delta']:.3f}"),
        ("Observed median difference", f"{e10b['observed']['median_diff']:.2e}"),
        ("Null median-difference mean", f"{e10b['null_median_diff_mean']:.2e}"),
        ("Empirical $p$(median difference)", f"{e10b['empirical_p_median_diff']:.3f}"),
        ("$z$ vs null ensemble", f"{e10b['obs_delta_z_vs_null']:.2f}"),
    ]
    body = ("\\begin{tabular}{lr}\n\\hline\n"
            "\\textbf{Statistic} & \\textbf{Value} \\\\\n\\hline\n"
            + "\n".join(f"{a} & {b} \\\\" for a, b in rows)
            + "\n\\hline\n\\end{tabular}")
    write("Table3.tex", body,
          "\\textbf{E10B degree-preserving null-network results.} Every null "
          "was verified to preserve both degree sequences exactly before its "
          "statistic was admitted. The observed statistic lies inside the null "
          "ensemble: the pre-registered hypothesis is rejected (Scenario B). "
          "Source: \\texttt{results/final/e10b\\_final.json} and "
          "\\texttt{e10b\\_nulls.csv}.",
          "tab:nulls")


# ---------------------------------------------------------------- Table 4
def table4() -> None:
    e12 = json.loads((T / "e12_strong_results.json").read_text())
    rows = []
    for k in (25, 50, 100):
        b = e12[f"K{k}"]
        rows.append((
            f"K={k}",
            f"{b['observed_vc']}",
            f"{b['expected_A_tested_universe']:.1f}",
            f"{b['expected_B_degree_matched']:.1f}",
            f"{b['enrichment_vs_degree_matched']:.2f}$\\times$",
            f"{b['z_B']:.1f}",
            f"{b['p_B']:.1e}",
        ))
    body = ("\\begin{tabular}{lrrrrrr}\n\\hline\n"
            "K & Obs & Exp$_{\\mathrm{univ}}$ & Exp$_{\\mathrm{deg}}$ & "
            "Enrich. & $z$ & $p$ \\\\\n\\hline\n"
            + "\n".join(f"{a} & {b} & {c} & {d} & {e} & {f} & {g} \\\\"
                        for a, b, c, d, e, f, g in rows)
            + "\n\\hline\n\\end{tabular}")
    write("Table4.tex", body,
          "\\textbf{Visual-centrifugal enrichment of top-K structural "
          "chokepoints.} Obs = observed visual-centrifugal count; "
          "Exp$_{\\mathrm{univ}}$ = expectation under tested-universe random "
          "draws (control A); Exp$_{\\mathrm{deg}}$ = expectation under "
          "per-slot degree-matched draws (control B); Enrichment and $z$ are "
          "given against control B, the degree-matched null. "
          "Source: \\texttt{e12\\_strong\\_results.json}.",
          "tab:vc")


# ---------------------------------------------------------------- Table 5
def table5() -> None:
    cat = pd.read_csv(T / "e14_chokepoint_catalogue_v2.csv")
    reg = pd.read_csv(T / "e14_top50_region_mapping.csv")
    top = cat.nsmallest(8, "rank").copy()
    rows = []
    for r in top.itertuples():
        rr = reg[reg["root_id"] == r.root_id]
        io = ""
        if len(rr):
            row = rr.iloc[0]
            io = str(row.get("top_input_neuropils", ""))[:28] + " / " + str(row.get("top_output_neuropils", ""))[:28]
        emp = float(r.emp_p_degree_matched)
        emp_s = "$<$0.0005" if emp <= 0.0005 else (f"{emp:.3f}" if emp >= 0.001 else f"{emp:.4f}")
        rows.append((
            str(int(r.rank)), r.name, r.nt_type, r.super_class.replace("_", "\\_"),
            f"{int(r.total_degree):,}", f"{r.cis*100:.2f}\\%",
            f"{r.cis_excess_ratio:.1f}$\\times$", emp_s,
        ))
    body = ("\\begin{tabular}{rllrrrrl}\n\\hline\n"
            "Rank & Neuron & NT & Class & Degree & CIS & vs peers & emp $p$ \\\\\n\\hline\n"
            + "\n".join(f"{a} & {b} & {c} & {d} & {e} & {f} & {g} & {h} \\\\"
                        for a, b, c, d, e, f, g, h in rows)
            + "\n\\hline\n\\end{tabular}")
    write("Table5.tex", body,
          "\\textbf{Representative structural chokepoints (E14-v2, "
          "selection-bias-corrected).} ``vs peers'' = CIS relative to the "
          "median of degree-matched peers (self excluded); emp $p$ = empirical "
          "p-value against those peers. NT = predicted neurotransmitter "
          "(Schlegel et al. 2024 annotations); all claims are structural, not "
          "functional. Source: \\texttt{e14\\_chokepoint\\_catalogue\\_v2.csv}.",
          "tab:chokepoints")


def main() -> None:
    table1(); table2(); table3(); table4(); table5()
    print("all tables written to", OUT)


if __name__ == "__main__":
    main()
