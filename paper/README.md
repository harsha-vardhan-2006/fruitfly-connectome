# paper/ — Publication package

Manuscript source, publication figures/tables, supplementary material, and
the graphical abstract for **"Neuron-Level Structural Control Impact
Reveals Visual-Centrifugal Chokepoints in the *Drosophila* Connectome"**
(FAFB v783 structural control-impact study; frozen results).

## Layout

```
paper/
├── manuscript.tex          submission-grade LaTeX source (article class)
├── manuscript.md / .html   markdown source + rendered HTML (legacy pipeline)
├── references.bib          12 DOI-verified references (no unverified entries)
├── sections/               abstract, introduction, related_work, methods,
│                           results, discussion, limitations, conclusion (.tex)
├── figures/                Figure1..7 (.pdf vector + .png 300 dpi)
├── tables/                 Table1..5.tex (generated; numbers read from
│                           authoritative result files at build time)
├── supplementary/          S1 top-50 chokepoints (E14-v2), S2 matched pairs,
│                           S3 E10B null statistics, S4 literature verification
│                           matrix, NUMBER_AUDIT.md copy, figS1 baseline
├── graphical_abstract/     graphical_abstract.pdf/.png
└── PAPER_PRODUCTION_REPORT.md
```

## How to compile (LaTeX)

```bash
cd paper
pdflatex manuscript && bibtex manuscript && pdflatex manuscript && pdflatex manuscript
```

Requires a standard TeX Live / MiKTeX installation (packages: graphicx,
amsmath, booktabs, geometry, hyperref, microtype). The final PDF for
inspection is `manuscript_production.pdf` (see below).

## How figures are produced

```bash
py scripts/make_paper_figures.py      # -> paper/figures/Figure1..7 (pdf+png)
py scripts/make_graphical_abstract.py # -> paper/graphical_abstract/
py scripts/make_paper_tables.py       # -> paper/tables/Table1..5.tex
```

All three generators read **only** the frozen result artifacts:

| Figure/Table | Authoritative source |
|---|---|
| Fig 1, graphical abstract | schematic; statistics quoted from e10b_final.json / e12_strong_results.json |
| Fig 2 | e07_annotated.parquet, e06_screen_summary.json, e11_e14_results.json, e13_full_results.json |
| Fig 3 | e08_matched_pairs.csv, e09_results.json, e10b_nulls.csv, results/final/e10b_final.json |
| Fig 4 | e08_matched_pairs.csv, e09_results.json (OLS block) |
| Fig 5 | e10b_nulls.csv (verification columns) |
| Fig 6 | results/final/e10b_final.json, e10b_nulls.csv |
| Fig 7 | e12_strong_results.json, e14_chokepoint_catalogue_v2.csv |
| Tables 1–5 | same sources as above (read at build time; no hand-typed numbers) |

No analysis is recomputed by the generators; no result file is modified.

## Data provenance

- Connectome: FlyWire FAFB v783 (Princeton exports), CC BY-NC 4.0.
  Cite Dorkenwald et al. 2024 (doi:10.1038/s41586-024-07558-y),
  Schlegel et al. 2024 (doi:10.1038/s41586-024-07686-5), and
  Matsliah et al. 2024 (doi:10.1038/s41586-024-07981-1). See
  `../LICENSE_NOTES.md` before redistribution.
- Raw data are **not** included in this package; processed/final result
  files live in `../results/` and are checksummed in
  `../results/tables/e18_manifest.json` (19 raw-file SHA256, verified
  2026-09-18).

## Reproducibility quick start

```bash
py -m pytest -q                       # 12/12 unit/regression tests
py scripts/verify_e10b_final.py       # independent E10B recomputation
py scripts/make_paper_figures.py      # regenerate all figures
py scripts/make_paper_tables.py       # regenerate all tables
py scripts/make_graphical_abstract.py # regenerate graphical abstract
```

Environment: Python 3.13.2, pandas 2.3.3, numpy 2.4.2, scipy 1.18.0,
pyarrow 23.0.1, matplotlib 3.11.2 (see `../requirements.txt`).

## Scientific freeze notice

The scientific content (hypothesis, metrics, statistics, conclusions) is
frozen as of 2026-09-18 (see `../results/final/FINAL_REPORT.md`,
§Scientific Freeze). This package improves presentation only. If a
demonstrated numeric error is ever found: fix the generator/source,
re-run the audits, regenerate the PDF, and record the change in
`../RESEARCH_LOG.md`.
