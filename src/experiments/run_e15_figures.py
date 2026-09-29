"""E15: final figures from actual results (Figures 2-7 of the paper).

Run:  py -m src.experiments.run_e15_figures
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.loaders import PROJECT_ROOT

TABLES = PROJECT_ROOT / "results" / "tables"
FIGS = PROJECT_ROOT / "results" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
EPS = 1e-7

plt.rcParams.update({"figure.dpi": 150, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})


def fig2_baseline() -> None:
    g = pd.read_csv(TABLES / "baseline_global.csv")
    nt = pd.read_csv(TABLES / "baseline_edges_by_nt.csv")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    vals = g.set_index("metric")["value"]
    axes[0].axis("off")
    axes[0].text(0, 0.9, f"FAFB v783 (Princeton)", fontsize=11, weight="bold")
    txt = (f"nodes: {vals['n_nodes']:,.0f}\n"
           f"edges (pairs): {vals['n_edges_pairs']:,.0f}\n"
           f"mean degree: {vals['mean_out_degree']:.1f}\n"
           f"density: {vals['density']:.2e}\n"
           f"reciprocity: {vals['reciprocity']:.3f}\n"
           f"weak components: {vals['n_weak_components']:.0f}\n"
           f"largest comp: {100*vals['largest_component_frac']:.1f}%")
    axes[0].text(0, 0.75, txt, fontsize=9, va="top", family="monospace")
    axes[1].bar(nt["nt_type_edge"], nt["n_edges"],
                color=["#6699cc", "#cc6666", "#99cc88", "#aa88cc", "#ddaa55", "#88bbbb"])
    axes[1].set_yscale("log")
    axes[1].set_title("Collapsed edges by neurotransmitter")
    axes[1].set_ylabel("edges (pairs, log)")
    fig.tight_layout()
    fig.savefig(FIGS / "fig2_baseline.png")
    plt.close(fig)


def fig3_cis_distribution() -> None:
    screen = pd.read_parquet(TABLES / "e06_screen_k8.parquet")
    rr = pd.read_parquet(TABLES / "e06_rerank_k32.parquet")
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.hist(np.log10(screen["cis"] + EPS), bins=60, color="#6688aa",
            label=f"screen k=8 (n={len(screen):,})")
    ax.hist(np.log10(rr["cis_mean"] + EPS), bins=40, color="#cc5544",
            alpha=0.8, label=f"rerank k=32 (n={len(rr)})")
    ax.set_xlabel(r"$\log_{10}(\mathrm{CIS} + 10^{-7})$")
    ax.set_ylabel("neurons")
    ax.set_title("Control Impact Score distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "fig3_cis_distribution.png")
    plt.close(fig)


def fig4_degree_vs_cis() -> None:
    df = pd.read_parquet(TABLES / "e07_annotated.parquet")
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    colors = {"GABA": "#cc4444", "ACH": "#4466aa", "GLUT": "#66aa66"}
    for nt, c in colors.items():
        s = df[df["nt_type"] == nt]
        ax.scatter(s["total_degree"], s["cis"] + EPS, s=4, alpha=0.35,
                   c=c, label=f"{nt} (n={len(s):,})", rasterized=True)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("total degree (partners)")
    ax.set_ylabel("CIS (k=8 screening)")
    ax.set_title("Degree vs control impact, by neurotransmitter")
    ax.legend(markerscale=2)
    fig.tight_layout()
    fig.savefig(FIGS / "fig4_degree_vs_cis.png")
    plt.close(fig)


def fig5_matched_pairs() -> None:
    m = pd.read_csv(TABLES / "e08_matched_pairs.csv")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4))
    axes[0].scatter(m["gaba_degree"], m["ctrl_degree"], s=6, alpha=0.4)
    lims = [m["gaba_degree"].min(), m["gaba_degree"].max()]
    axes[0].plot(lims, lims, "k--", lw=0.8)
    axes[0].set_xscale("log"); axes[0].set_yscale("log")
    axes[0].set_xlabel("GABA degree"); axes[0].set_ylabel("matched ACh degree")
    axes[0].set_title(f"degree matching (n={len(m)} pairs)")

    ratio = (m["gaba_cis_k8"] + EPS) / (m["ctrl_cis_k8"] + EPS)
    axes[1].hist(np.log10(ratio), bins=50, color="#8888bb")
    axes[1].axvline(0, color="k", lw=0.8)
    axes[1].set_xlabel(r"$\log_{10}$( (CIS$_{GABA}$+$\epsilon$) / (CIS$_{matched\ ACh}$+$\epsilon$) )")
    axes[1].set_ylabel("pairs")
    axes[1].set_title("matched-pair comparison")
    fig.tight_layout()
    fig.savefig(FIGS / "fig5_matched_pairs.png")
    plt.close(fig)


def fig6_null_comparison() -> None:
    """Fig 6: observed GABA-vs-matched-ACh effect against the null
    distribution. Uses e10b (100-null protocol) when available; falls
    back to the 5-null pilot file otherwise."""
    if (TABLES / "e10b_results.json").exists():
        nulls = pd.read_csv(TABLES / "e10b_nulls.csv")
        deltas = nulls["cliffs_delta"].to_numpy()
        res = json.loads((TABLES / "e10b_results.json").read_text())
        obs = res["observed"]["cliffs_delta"]
        p_delta = res["empirical_p_delta"]
        p_diff = res["empirical_p_median_diff"]
        src_lbl = (f"degree-preserving nulls (n={len(deltas)})\n"
                   f"empirical p(delta) = {p_delta:.3f};  "
                   f"p(median diff) = {p_diff:.3f}")
        title = ("Observed effect vs degree-preserving nulls "
                 f"(100-null protocol, n={len(deltas)})")
    else:
        res = json.loads(
            (TABLES / "e10_results_pilot_PREFIX_superseded.json").read_text())
        deltas = [n["cliffs_delta"] for n in res["nulls"]]
        obs = res["observed_k4"]["cliffs_delta"]
        src_lbl = f"degree-preserving nulls (n={len(deltas)}, PILOT)"
        title = "Observed effect vs degree-preserving nulls (pilot)"
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.hist(deltas, bins=20, color="#9999aa", label=src_lbl)
    ax.axvline(obs, color="#cc3333", lw=2,
               label=f"observed delta = {obs:.3f}")
    ax.set_xlabel("Cliff's delta, GABA vs matched ACh")
    ax.set_ylabel("null networks")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "fig6_null_comparison.png")
    plt.close(fig)


def fig7_region_localization() -> None:
    """Fig 7: top-50 chokepoints by super-class + E14 v2 classes."""
    cat = pd.read_csv(TABLES / "e14_chokepoint_catalogue_v2.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.4))
    cat["super_class"].value_counts().plot.barh(ax=ax1, color="#557799")
    ax1.set_xlabel("neurons in top-50 CIS")
    ax1.set_title("Top-50 chokepoints by super-class\n"
                  "(VC enriched 2.6x vs degree-matched, p=1e-4)")
    base = cat["class_label"].str.split("|").str[0].value_counts()
    base.plot.barh(ax=ax2, color=["#336655" if c.startswith("A_")
                                  else ("#88aacc" if "intermediate" in c
                                        else "#bbbbcc") for c in base.index])
    ax2.set_xlabel("neurons")
    ax2.set_title("E14 v2 classes\n(empirical degree-matched p)")
    fig.tight_layout()
    fig.savefig(FIGS / "fig7_region_localization.png")
    plt.close(fig)


def main() -> None:
    fig2_baseline(); print("fig2 done")
    fig3_cis_distribution(); print("fig3 done")
    fig4_degree_vs_cis(); print("fig4 done")
    fig5_matched_pairs(); print("fig5 done")
    fig6_null_comparison(); print("fig6 done")
    fig7_region_localization(); print("fig7 done")


if __name__ == "__main__":
    main()
