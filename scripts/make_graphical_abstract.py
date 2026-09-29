#!/usr/bin/env python
"""Graphical abstract for the FAFB v783 control-impact paper.

Text-only, data-honest flow diagram built with matplotlib (no decorative
imagery, no unsupported claims). Run:  py scripts/make_graphical_abstract.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "graphical_abstract"
OUT.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(7.4, 4.2))
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis("off")

stages = [
    (0.3, 5.6, 2.2, 1.0, "FAFB v783\nconnectome\n139,255 neurons", "#eef1f4"),
    (3.0, 5.6, 2.2, 1.0, "single-neuron\nremoval", "#eef1f4"),
    (5.7, 5.6, 2.6, 1.0, "global efficiency\nchange = CIS", "#eef1f4"),
    (8.9, 5.6, 2.6, 1.0, "3,518 targets\nk=8 $\\rightarrow$ k=32", "#eef1f4"),
    (0.3, 3.6, 3.2, 1.0, "degree-matched\nGABA vs ACh (848 pairs)", "#f4f1ea"),
    (4.0, 3.6, 3.2, 1.0, "100 degree-preserving\nnull networks", "#f4f1ea"),
    (7.7, 3.6, 3.8, 1.0, "$\\delta$ = 0.098 inside null ensemble\n$p_\\delta$ = 0.109;  $p_{median}$ = 0.782", "#fbeaec"),
    (0.3, 1.4, 5.2, 1.1, "GABA hypothesis:\nNOT supported", "#fbeaec"),
    (6.2, 1.4, 5.3, 1.1, "Visual-centrifugal chokepoints enriched\n2.63$\\times$ after degree matching ($z$=5.3, $p$=1e-4)\n13/50 beat degree-matched peers", "#eaf2ef"),
]
for (x, y, w, h, t, fc) in stages:
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.08,rounding_size=0.12",
                                lw=0.8, ec="#666a70", fc=fc))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7.6)

def arrow(x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=10, lw=1.0, color="#666a70"))

arrow(2.5, 6.1, 3.0, 6.1)
arrow(5.2, 6.1, 5.7, 6.1)
arrow(8.3, 6.1, 8.9, 6.1)
arrow(10.2, 5.6, 10.2, 4.9)
arrow(3.5, 3.6, 3.5, 2.5)
arrow(5.6, 4.1, 7.7, 4.1)
arrow(7.7, 4.1, 5.6, 4.1)
arrow(10.1, 3.6, 10.1, 2.55)
arrow(9.6, 5.6, 9.6, 4.65)
ax.text(6.0, 0.45, "Structural control impact (removal-based), not functional causality",
        ha="center", fontsize=8, style="italic", color="#55595f")

fig.savefig(OUT / "graphical_abstract.pdf", bbox_inches="tight")
fig.savefig(OUT / "graphical_abstract.png", bbox_inches="tight", dpi=300)
print("wrote graphical_abstract to", OUT)
