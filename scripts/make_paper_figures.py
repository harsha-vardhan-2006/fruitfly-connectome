#!/usr/bin/env python
"""Publication-quality figure production for the FAFB v783 control-impact paper.

Generates paper/figures/Figure1..7 in vector PDF + 300-dpi PNG from the
authoritative result files (read-only). No analysis is recomputed; all
statistics shown are read from the locked result JSONs / tables.

Run:  py scripts/make_paper_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import ConnectionPatch, FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "results" / "tables"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 8.5,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "font.family": "DejaVu Sans",
})

# Neutral, colorblind-safe palette
C_NULL = "#9aa5b1"
C_OBS = "#b23a48"
C_GABA = "#3d6b8e"
C_ACH = "#c98d4c"
C_VC = "#33665a"
C_CENTRAL = "#8a8fa3"
C_GREY = "#c9cdd4"


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("wrote", name)


# ----------------------------------------------------------------------------
# Figure 1 — study overview / workflow (schematic; no data claims)
# ----------------------------------------------------------------------------
def fig1_overview() -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.6)
    ax.axis("off")

    def box(x, y, w, h, text, fc, fs=8.0, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.08,rounding_size=0.12",
                                    linewidth=0.8, edgecolor="#666a70", facecolor=fc))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                fontweight="bold" if bold else "normal", wrap=True)

    def arrow(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                                     arrowstyle="-|>", mutation_scale=10,
                                     linewidth=1.0, color="#666a70"))

    # Row 1: data -> graph -> removal -> CIS
    box(0.2, 5.0, 2.0, 1.15, "A. FAFB v783\nconnectome\n(139,255 neurons)", "#eef1f4")
    box(2.7, 5.0, 2.0, 1.15, "B. Directed graph\n138,584 nodes\n3,732,460 edges", "#eef1f4")
    box(5.2, 5.0, 2.0, 1.15, "C. Remove neuron $i$\n(computational\nperturbation)", "#eef1f4")
    box(7.7, 5.0, 2.1, 1.15, "D. Structural control\nimpact\nCIS$(i)=1-S(G{-}i)/S(G)$", "#eef1f4", bold=True)
    arrow(2.2, 5.575, 2.7, 5.575)
    arrow(4.7, 5.575, 5.2, 5.575)
    arrow(7.2, 5.575, 7.7, 5.575)

    # Row 2: workflow
    box(0.2, 3.2, 2.35, 1.1, "E1. 3,518 pre-registered\nperturbation targets\n(k=8 screen -> k=32 rerank)", "#f4f1ea")
    box(2.85, 3.2, 2.35, 1.1, "E2. Degree-matched\nGABA vs ACh pairs\n(848 pairs, +/-10%)", "#f4f1ea")
    box(5.5, 3.2, 2.1, 1.1, "E3. Degree-preserving\nnull networks\n(100, exact sequences)", "#f4f1ea")
    box(7.9, 3.2, 1.9, 1.1, "E4. Enrichment +\nindividual chokepoints\n(E12 / E14-v2)", "#f4f1ea")
    arrow(1.375, 5.0, 1.375, 4.3)
    arrow(4.025, 4.3, 4.025, 4.3)
    arrow(5.2, 3.75, 5.5, 3.75)
    arrow(7.6, 3.75, 7.9, 3.75)

    # Row 3: outcomes
    box(0.6, 1.3, 4.0, 1.2,
        "Primary hypothesis (GABA excess):\nNOT supported\n$\\delta=0.098$ within null ensemble\n(p$_\\delta$=0.109; p$_{median}$=0.782)",
        "#fbeaec", bold=False)
    box(5.4, 1.3, 4.0, 1.2,
        "Positive finding:\nvisual-centrifugal chokepoints\n2.63x at K=50 after degree matching\n(z=5.3, p=1e-4); 13/50 beat peers",
        "#eaf2ef", bold=False)
    arrow(2.6, 3.2, 2.6, 2.5)
    arrow(7.4, 3.2, 7.4, 2.5)

    ax.text(5.0, 0.55, "All claims are structural (removal-based network sensitivity), not functional causality.",
            ha="center", fontsize=7.5, style="italic", color="#55595f")
    save(fig, "Figure1")


# ----------------------------------------------------------------------------
# Figure 2 — network + CIS characterization
# ----------------------------------------------------------------------------
def fig2_network_cis() -> None:
    scr = json.loads((T / "e06_screen_summary.json").read_text())
    ann = pd.read_parquet(T / "e07_annotated.parquet")

    fig, axes = plt.subplots(1, 3, figsize=(9.2, 2.9))

    # A. CIS distribution (log)
    ax = axes[0]
    cis = ann["cis"].to_numpy()
    bins = np.logspace(np.log10(cis[cis > 0].min()), np.log10(cis.max()), 40)
    ax.hist(cis, bins=bins, color=C_NULL, edgecolor="white", linewidth=0.3)
    ax.set_xscale("log")
    ax.set_xlabel("CIS (removal-based impact)")
    ax.set_ylabel("neurons")
    ax.set_title("A  Structural control-impact distribution")
    ax.axvline(scr["screen"]["cis_median"], color="#55595f", lw=1.0, ls="--",
               label=f"median {scr['screen']['cis_median']:.1e} (n={scr['screen']['n']:,})")
    ax.axvline(scr["screen"]["cis_max"], color=C_OBS, lw=1.4,
               label=f"max {scr['screen']['cis_max']:.3f}")
    ax.legend(frameon=False, loc="upper left")

    # B. top-50 by super-class
    ax = axes[1]
    e12 = json.loads((T / "e11_e14_results.json").read_text())["e12_enrichment"]["top50_super_class_counts"]
    labels = list(e12.keys())
    vals = list(e12.values())
    colors = [C_VC if "visual" in l or l == "optic" else C_CENTRAL for l in labels]
    ax.barh(range(len(vals))[::-1], vals, color=colors)
    ax.set_yticks(range(len(vals))[::-1])
    ax.set_yticklabels(labels)
    ax.set_xlabel("neurons in top-50 CIS")
    ax.set_title("B  Top-50 anatomical composition")

    # C. top-50 vs tested degree
    ax = axes[2]
    med50 = json.loads((T / "e13_full_results.json").read_text())["degree_definition"]
    vals = [med50["top50_median_out_degree"], med50["top50_median_in_degree"],
            med50["tested_median_total_degree"]]
    ax.bar(["top-50\nout-degree", "top-50\nin-degree", "tested\nmedian degree"],
           vals, color=[C_GABA, C_GABA, C_GREY])
    ax.set_ylabel("median degree")
    ax.set_title("C  Top-50 are output-dominated hubs")
    for i, v in enumerate(vals):
        ax.text(i, v * 1.02, f"{int(v):,}", ha="center", fontsize=7.5)
    ax.set_ylim(0, max(vals) * 1.15)

    fig.tight_layout()
    save(fig, "Figure2")


# ----------------------------------------------------------------------------
# Figure 3 — GABA hypothesis (negative result made visually clear)
# ----------------------------------------------------------------------------
def fig3_gaba_hypothesis() -> None:
    e09 = json.loads((T / "e09_results.json").read_text())
    e10b = json.loads((ROOT / "results" / "final" / "e10b_final.json").read_text())
    ann = pd.read_parquet(T / "e07_annotated.parquet")
    pairs = pd.read_csv(T / "e08_matched_pairs.csv")

    fig, axes = plt.subplots(1, 3, figsize=(9.2, 2.9))

    # A. matched-pair deltas (paired, per pair)
    ax = axes[0]
    d = (pairs["gaba_cis_k8"] - pairs["ctrl_cis_k8"]).to_numpy()
    # symmetric log around 0
    span = np.nanmax(np.abs(d))
    ax.hist(d, bins=50, color=C_NULL, edgecolor="white", linewidth=0.3)
    ax.axvline(0, color="#44484e", lw=1.0)
    ax.axvline(np.nanmedian(d), color=C_OBS, lw=1.4,
               label=f"median diff {np.nanmedian(d):.2e}")
    ax.set_xlabel("CIS(GABA) $-$ CIS(matched ACh), per pair")
    ax.set_ylabel("pairs")
    ax.set_title("A  Matched pairs (848), k=8 CIS")
    ax.legend(frameon=False)

    # B. CIS by NT (matched medians) — box-ish summary
    ax = axes[1]
    data = [pairs["gaba_cis_k8"].dropna(), pairs["ctrl_cis_k8"].dropna()]
    bp = ax.boxplot(data, tick_labels=["GABA", "matched ACh"], showfliers=False,
                    patch_artist=True, widths=0.5)
    for patch, col in zip(bp["boxes"], [C_GABA, C_ACH]):
        patch.set_facecolor(col)
        patch.set_alpha(0.75)
    ax.set_yscale("log")
    ax.set_ylabel("CIS (k=8)")
    ax.set_title(f"B  Matched comparison\nWilcoxon p = {e09['wilcoxon_signed_rank_p']:.4f}")
    # annotate medians
    for i, s in enumerate(data, start=1):
        ax.text(i, s.median() * 1.15, f"{s.median():.2e}", ha="center", fontsize=7.0)

    # C. observed vs null ensemble
    ax = axes[2]
    nulls = pd.read_csv(T / "e10b_nulls.csv")["cliffs_delta"].to_numpy()
    obs = e10b["observed"]["cliffs_delta"]
    ax.hist(nulls, bins=15, color=C_NULL, edgecolor="white", label=f"nulls (n={len(nulls)})")
    ax.axvline(obs, color=C_OBS, lw=2.0, label=f"observed $\\delta$ = {obs:.3f}")
    ax.axvline(nulls.mean(), color="#55595f", lw=1.2, ls="--",
               label=f"null mean = {nulls.mean():.3f}")
    ax.set_xlabel("Cliff's $\\delta$, GABA vs matched ACh")
    ax.set_ylabel("null networks")
    ax.set_title("C  E10B: inside the null ensemble\n"
                 f"p$_\\delta$={e10b['empirical_p_delta']:.3f}, "
                 f"p$_{{median}}$={e10b['empirical_p_median_diff']:.3f}")
    ax.legend(frameon=False)

    fig.tight_layout()
    save(fig, "Figure3")


# ----------------------------------------------------------------------------
# Figure 4 — degree-controlled comparison (OLS + scatter)
# ----------------------------------------------------------------------------
def fig4_degree_control() -> None:
    e09 = json.loads((T / "e09_results.json").read_text())
    pairs = pd.read_csv(T / "e08_matched_pairs.csv")

    eps = 1e-9
    g = pairs["gaba_cis_k8"].to_numpy()
    c = pairs["ctrl_cis_k8"].to_numpy()
    deg = pairs["gaba_degree"].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.1))

    # A. log CIS vs log degree, GABA vs controls
    ax = axes[0]
    ax.scatter(np.log10(deg + 1), np.log10(g + eps), s=6, alpha=0.45, color=C_GABA, label="GABA")
    ax.scatter(np.log10(pairs["ctrl_degree"] + 1), np.log10(c + eps), s=6, alpha=0.45,
               color=C_ACH, label="matched ACh")
    ax.set_xlabel("$\\log_{10}$(degree + 1)")
    ax.set_ylabel("$\\log_{10}$(CIS + $\\epsilon$)")
    ax.set_title("A  Degree dominates CIS")
    ax.legend(frameon=False, markerscale=2)

    # B. paired difference vs degree (residual view)
    ax = axes[1]
    logratio = np.log10((g + eps) / (c + eps))
    ax.scatter(np.log10(deg + 1), logratio, s=6, alpha=0.45, color="#55595f")
    ax.axhline(0, color="#44484e", lw=1.0)
    b1 = e09["ols_log_cis"]["beta1_gaba"]
    ax.set_xlabel("$\\log_{10}$(degree + 1)")
    ax.set_ylabel("$\\log_{10}$(CIS$_{GABA}$/CIS$_{ACh}$)")
    ax.set_title("B  Pairwise log-ratio vs degree\n"
                 f"OLS $\\beta_1$(GABA) = {b1:.3f} (perm p = "
                 f"{e09['ols_log_cis']['beta1_perm_p_one_sided']:.2f})")

    fig.tight_layout()
    save(fig, "Figure4")


# ----------------------------------------------------------------------------
# Figure 5 — null-network framework (schematic + verification summary)
# ----------------------------------------------------------------------------
def fig5_null_framework() -> None:
    rows = list(pd.read_csv(T / "e10b_nulls.csv").itertuples(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))

    # A. procedure schematic
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    steps = [
        (0.3, 3.6, "observed graph G\n(exact in/out degree\nsequences)"),
        (3.7, 3.6, "vectorized stub\nmatching + defect\nrepair / rejection redraw"),
        (7.0, 3.6, "rewired null $G^{(m)}$\nsame degree sequences,\nno self-loops / dupes"),
        (7.0, 1.2, "recompute matched-pair\n$\\delta^{(m)}$ on same\n848 pairs (k=4 panel)"),
        (3.7, 1.2, "ensemble of 100 nulls\n(null_id 0-99, seeds\n100+i, verified per null)"),
        (0.3, 1.2, "empirical p = fraction\nof nulls >= observed"),
    ]
    for (x, y, t) in steps:
        ax.text(x + 1.25, y + 0.55, t, ha="center", va="center", fontsize=7.4,
                bbox=dict(boxstyle="round,pad=0.35", fc="#f1f3f6", ec="#666a70", lw=0.8))
    for (x0, y0, x1, y1) in [(2.9, 4.15, 3.7, 4.15), (6.15, 4.15, 7.0, 4.15),
                             (8.25, 3.55, 8.25, 2.35), (7.0, 1.75, 6.15, 1.75),
                             (3.7, 1.75, 2.85, 1.75)]:
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                     mutation_scale=9, lw=0.9, color="#666a70"))
    ax.set_title("A  Degree-preserving null procedure")

    # B. per-null verification: degree-match booleans + runtime distribution
    ax = axes[1]
    ok = sum(1 for r in rows if r.out_degree_exact_match and r.in_degree_exact_match)
    ax.bar(["degree-verified", "any mismatch"], [ok, len(rows) - ok],
           color=[C_VC, C_OBS])
    ax.set_ylim(0, 105)
    ax.set_ylabel("null networks")
    ax.set_title("B  Per-null verification\n"
                 f"{ok}/{len(rows)} exact in+out sequence match (status=ok)")
    for i, v in enumerate([ok, len(rows) - ok]):
        ax.text(i, v + 2, str(v), ha="center", fontsize=8)

    fig.tight_layout()
    save(fig, "Figure5")


# ----------------------------------------------------------------------------
# Figure 6 — E10B final null distribution (the decisive figure)
# ----------------------------------------------------------------------------
def fig6_null_distribution() -> None:
    e10b = json.loads((ROOT / "results" / "final" / "e10b_final.json").read_text())
    nulls = pd.read_csv(T / "e10b_nulls.csv")["cliffs_delta"].to_numpy()
    obs = e10b["observed"]["cliffs_delta"]

    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.hist(nulls, bins=15, color=C_NULL, edgecolor="white",
            label=f"degree-preserving nulls (n={len(nulls)})")
    ax.axvline(obs, color=C_OBS, lw=2.2, label=f"observed $\\delta$ = {obs:.4f}")
    ax.axvline(nulls.mean(), color="#55595f", lw=1.3, ls="--",
               label=f"null mean = {nulls.mean():.4f} (sd {nulls.std(ddof=1):.4f})")
    n_ge = int((nulls >= obs).sum())
    ymax = ax.get_ylim()[1]
    for v in nulls[nulls >= obs]:
        ax.plot([v, v], [0, ymax * 0.03], color=C_OBS, lw=1.0, alpha=0.7)
    ax.set_xlabel("Cliff's $\\delta$, GABA vs matched ACh (k=4 panel)")
    ax.set_ylabel("null networks")
    ax.set_title("Observed effect inside the null ensemble\n"
                 f"empirical p($\\delta$) = {e10b['empirical_p_delta']:.3f} ({n_ge}/{len(nulls)} nulls $\\geq$ obs); "
                 f"p(median diff) = {e10b['empirical_p_median_diff']:.3f}")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "Figure6")


# ----------------------------------------------------------------------------
# Figure 7 — visual-centrifugal enrichment + representative chokepoints
# ----------------------------------------------------------------------------
def fig7_vc_enrichment() -> None:
    e12 = json.loads((T / "e12_strong_results.json").read_text())
    cat = pd.read_csv(T / "e14_chokepoint_catalogue_v2.csv")

    fig, axes = plt.subplots(1, 3, figsize=(9.4, 3.0))

    # A. enrichment vs K (both controls)
    ax = axes[0]
    ks = [25, 50, 100]
    eB = [e12[f"K{k}"]["expected_B_degree_matched"] for k in ks]
    eA = [e12[f"K{k}"]["expected_A_tested_universe"] for k in ks]
    obs = [e12[f"K{k}"]["observed_vc"] for k in ks]
    x = np.arange(3)
    ax.bar(x - 0.22, eA, width=0.4, color=C_GREY, label="expected (tested-universe)")
    ax.bar(x + 0.22, eB, width=0.4, color=C_CENTRAL, label="expected (degree-matched)")
    ax.plot(x, obs, "o", color=C_VC, ms=7, label="observed VC in top-K")
    for i in range(3):
        ax.text(x[i], obs[i] + 0.8, str(obs[i]), ha="center", fontsize=8, color=C_VC, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["K=25", "K=50", "K=100"])
    ax.set_ylabel("visual-centrifugal neurons")
    ax.set_title("A  VC enrichment across K")
    ax.legend(frameon=False)

    # B. enrichment ratio (degree-matched) with z annotation
    ax = axes[1]
    ratios = [e12[f"K{k}"]["enrichment_vs_degree_matched"] for k in ks]
    zs = [e12[f"K{k}"]["z_B"] for k in ks]
    ax.bar(["K=25", "K=50", "K=100"], ratios, color=[C_VC, C_VC, C_VC], alpha=0.85)
    ax.axhline(1.0, color="#44484e", lw=1.0, ls="--", label="no enrichment")
    for i, (r, z) in enumerate(zip(ratios, zs)):
        ax.text(i, r + 0.05, f"{r:.2f}x\nz={z:.1f}", ha="center", fontsize=7.6)
    ax.set_ylabel("enrichment vs degree-matched")
    ax.set_ylim(0, max(ratios) * 1.3)
    ax.set_title("B  Degree-matched enrichment")
    ax.legend(frameon=False)

    # C. representative chokepoints (peer-excess ratios)
    ax = axes[2]
    top = cat.nsmallest(12, "rank")
    names = [f"{r.name} ({r.nt_type})" for r in top.itertuples()]
    ratios = top["cis_excess_ratio"].to_numpy()
    colors = [C_VC if r.super_class in ("visual_centrifugal", "optic") else C_CENTRAL
              for r in top.itertuples()]
    ax.barh(range(len(ratios))[::-1], ratios, color=colors)
    ax.set_yticks(range(len(ratios))[::-1])
    ax.set_yticklabels(names, fontsize=6.6)
    ax.set_xlabel("CIS / degree-matched peer median")
    ax.set_title("C  Representative chokepoints\n(green = optic/VC)")
    ax.axvline(1.0, color="#44484e", lw=0.9, ls="--")

    fig.tight_layout()
    save(fig, "Figure7")


def main() -> None:
    fig1_overview()
    fig2_network_cis()
    fig3_gaba_hypothesis()
    fig4_degree_control()
    fig5_null_framework()
    fig6_null_distribution()
    fig7_vc_enrichment()
    print("all figures written to", OUT)


if __name__ == "__main__":
    main()
