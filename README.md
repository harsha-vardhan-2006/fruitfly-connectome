# Single-Neuron Structural Perturbation Reveals Visual-Centrifugal Chokepoints in the Adult Drosophila Connectome

Publication repository for the frozen FAFB v783 connectome control-impact study.

**Repository status: FINAL SCIENTIFIC STATE — analysis frozen 2026-09-18.**
E10B degree-preserving null analysis: COMPLETE (100/100 null networks).
E14 visual-centrifugal chokepoint analysis: COMPLETE. Final manuscript:
COMPLETE. Final scientific QC: COMPLETE. All experiments E01–E14B are
executed; nothing is staged or pending.

**Current release: v1.1.0 (2026-09-29)** — connection-table sensitivity
completed (QC 46/46); see `RELEASE_NOTES.md`.

The frozen manuscript is *Neuron-Level Structural Control Impact Reveals
Visual-Centrifugal Chokepoints in the Drosophila Connectome*
(`paper/manuscript.md`, `paper/manuscript.tex`, production PDF in `dist/`).
Historical working title (superseded, context only): *Inhibitory Chokepoints
in the Drosophila Brain* — retained in historical planning documents
(`MASTER_PLAN.md`, `RESEARCH_LOG.md`) as a record of the project's origin.

## Overview

This repository contains the complete, finalized study: analysis code,
frozen processed results, validation scripts, figures, the manuscript, the
verified literature matrix, and provenance/QC documentation.

The study asks whether neuron-level structural control points in the adult
*Drosophila* brain connectome are explained by neurotransmitter identity or
by broader network architecture. It combines neuron-removal perturbation,
degree-controlled neurotransmitter comparison, and 100 degree-preserving
null networks.

**The primary GABAergic hypothesis was not supported after degree control
and degree-preserving null testing. Instead, high-control-impact neurons
were strongly enriched in visual-centrifugal architecture.** The negative
result is reported as the primary outcome; the visual-centrifugal finding
is the positive contribution.

## Research Question

> To identify structurally important neuron-level control points in the
> adult *Drosophila* connectome and determine whether their impact reflects
> neurotransmitter identity or broader network architecture.

**Primary hypothesis (pre-registered, v2):** GABAergic neurons have
disproportionately high structural network-control impact after accounting
for degree.

## Dataset

- **FlyWire FAFB v783** (Princeton exports), adult *Drosophila melanogaster*
  whole-brain connectome, CC BY-NC 4.0.
- 19 raw gzipped CSV exports + SWC morphology archive were used; **raw files
  are never modified and are not redistributed here** (licensing: see
  `LICENSE_NOTES.md`). SHA256 checksums of all 19 raw files are recorded in
  `results/tables/e18_manifest.json` (19/19 recomputed MATCH).
- Required citations: Dorkenwald et al. 2024; Schlegel et al. 2024;
  Matsliah et al. 2024 (details in `LICENSE_NOTES.md`).
- Analysis graph: **138,584 nodes / 3,732,460 directed edges** (pair-collapsed
  thresholded connectivity, binary digraph) from a metadata universe of
  **139,255 annotated neurons**; mean degree 26.8; density 1.92 × 10⁻⁴;
  reciprocity 0.083; largest weak component 98.4% of nodes (875 components).

## Methods

- **Control Impact Score (CIS).** Structural metric: remove neuron *i*, measure
  the loss of directed global efficiency under the freeze-N convention —
  CIS(i) = 1 − S(G−i)/S(G), S = Σ 1/d over unweighted directed shortest
  paths. Estimated with a fixed-source-panel BFS (panel(k=N) ≡ exact at
  1 × 10⁻⁹). Screening at k=8, finalist rerank at k=32–64, null comparison
  at k=4.
- **Targets:** 3,518 pre-registered neurons (top-1% union of degree /
  in/out-strength / PageRank / sampled betweenness, plus high-degree GABA
  and a random background). Median CIS ≈ 9.7 × 10⁻⁶; 99th percentile ≈
  3.9 × 10⁻⁴; maximum CIS = 2.40% of whole-brain efficiency.
- **Degree-matched comparison:** 848 GABA–ACh pairs (±10% total degree,
  1:1 greedy, no replacement; pre-registered).
- **Null networks:** 100 directed degree-preserving configuration-model
  networks with exact in-/out-degree preservation verified per null
  (seeds 100+i).
- Statistics: Wilcoxon signed-rank, permutation tests, Cliff's δ, OLS with
  log-degree control, empirical p-values against the 100-null ensemble.

## Final Results

### GABAergic hypothesis — NOT supported

- Matched-pair screening result: GABA median CIS higher than matched ACh
  controls (Cliff's δ = 0.111; Wilcoxon p = 0.0011; permutation p ≈ 1e-4).
- **E10B 100-null ensemble (the decisive arbiter):** observed δ = 0.0979 vs
  null mean ≈ 0.0713 (SD ≈ 0.0220); empirical p(δ) = 0.109;
  median-difference p = 0.782; z = 1.21. The observed effect lies inside the
  degree-preserving null distribution (pre-locked verdict: Scenario B).
- Degree-controlled regression: OLS log10(CIS) ~ GABA + log10(degree):
  β ≈ −0.025, p ≈ 0.95.
- **Conclusion:** GABAergic identity did not independently predict
  structural control impact after accounting for degree and
  degree-preserving network structure.

### Visual-centrifugal enrichment — the positive finding

- **21/50** top CIS neurons are visual centrifugal — ≈ **2.63-fold
  enrichment after per-slot degree matching** (z = 5.30, p = 1e-4);
  K=25 ≈ 2.47×; K=100 ≈ 2.15×; central-brain neurons under-represented
  (0.27×).
- **E14-v2 catalogue:** 13/50 top chokepoints individually exceed their
  degree-matched peer distributions; 10/13 of those are visual-system
  neurons.
- Individual example: **ME.131** (visual centrifugal; degree ≈ 858;
  CIS ≈ 0.324%; ≈ 155.9× its peer-median impact). This is a single-neuron
  example under the CIS metric — not evidence of functional necessity.

### Robustness

- Seed stability (k=32): Spearman ρ 0.88–0.96 across 4 panels; k16↔k32 0.86.
- GABA+GLUT sensitivity: 967 pairs, δ = 0.107 ≈ 0.111 (GABA-only).
- Metric sensitivity: reachability-drop ρ = 0.39 (reported, not hidden).
- Connection-table sensitivity (E13.6b, 2026-09-29): no-threshold graph
  rebuilt on the frozen node universe (19,765,143 pairs; chunked, < 1 GB
  RAM) with the identical k=4 panel estimator — the raw matched-pair
  effect flips sign (δ = −0.117 vs +0.098 thresholded, outside the
  thresholded null range 0.008–0.121). The raw GABA effect is therefore
  not robust to the edge-inclusion rule; the frozen verdict (no
  GABA-specific effect beyond degree/structure) is reinforced. Buhmann
  table remains methodologically non-comparable.

## Reproducibility

The repository ships analysis code, frozen processed/final results, unit and
regression tests, figure/table generators, the manuscript, the 22-paper
verified literature matrix, and provenance/QC documentation.

```bash
py -m pytest -q                    # 12/12 tests (metric + null-model)
py scripts/verify_e10b_final.py    # independent recomputation of the E10B statistics
py scripts/make_paper_figures.py   # regenerate figures from frozen artifacts
py scripts/make_paper_tables.py    # regenerate tables from frozen artifacts
```

Environment: Python 3.13.2; pandas 2.3.3; numpy 2.4.2; scipy 1.18.0;
pyarrow 23.0.1; matplotlib 3.11.2 (pinned in `requirements.txt`). Invoke
scripts as `py -3.13` (a bare `py` may resolve to another interpreter
without pandas). scipy
sparse CSR + numpy throughout (NetworkX intentionally not used at this
graph size). End-to-end re-execution from raw data additionally requires
obtaining FAFB v783 (see Data Availability); all frozen result artifacts
are included here.

## Repository Structure

```
├── paper/                  manuscript (md/tex/html), sections, Figures 1–7,
│                           Tables 1–5, supplementary, graphical abstract,
│                           references.bib, production report
├── results/
│   ├── final/              canonical final artifacts (e10b_final.json,
│   │                       FINAL_REPORT.md, NUMBER_AUDIT.md, finalize stamp)
│   ├── tables/             all experiment outputs (e01–e18)
│   ├── figures/            analysis figures (fig2–fig7)
│   ├── e10b/               E10B archive + null CSV
│   └── superseded/         quarantined interim artifacts (preserved, labeled)
├── src/                    loaders (data), graph build/baseline (graph),
│                           CIS + all experiment runners (experiments)
├── scripts/                verification, figures, tables, packaging
├── tests/                  pytest suite (12 tests)
├── configs/                frozen YAML configs (primary/null/robustness)
├── data/processed/         pipeline outputs (graph pairs, neuron core)
├── literature/             22-paper verified literature matrix (CSV)
├── reproducibility/        environment + pipeline reproduction manifest
├── dist/                   final deliverable ZIP + SHA256SUMS.txt + PDF
├── MASTER_PLAN.md          definitive plan: novelty verdict, hypothesis, status
├── RESEARCH_LOG.md         append-only experiment log (E00–E16B + closes)
├── QC_STATUS.md            final QC checklist with artifact evidence
├── LICENSE_NOTES.md        CC BY-NC 4.0 conditions + required citations
└── CITATION.cff            citation metadata
```

## Data Availability

Raw FAFB v783 data are available from the canonical FlyWire sources
(flywire.ai, codex.flywire.ai; Zenodo connectivity record 10676866) under
CC BY-NC 4.0. They are **not** redistributed in this repository; integrity is
documented via the SHA256 manifest (`results/tables/e18_manifest.json`).
All processed and final result files are included here.

## Code Availability

All analysis code is in this repository (`src/`, `scripts/`, `tests/`) and
is frozen at the release tag **v1.1.0** (v1.0.0 = initial public
research package; v1.1.0 adds the completed E13.6b connection-table
sensitivity, QC 46/46). A permanent archival DOI will be
added upon release through an archival repository.

## License

CC BY-NC 4.0 — see `LICENSE_NOTES.md` for the dataset license conditions
and the three required citations before any publication or redistribution.

## Citation

Cite this repository via `CITATION.cff`. A permanent archival DOI will be
added upon release through an archival repository.

## Scientific Limitations

- CIS is a **computational structural** network metric (removal-based
  global-efficiency impact). It does not establish physiological causality,
  behavioral necessity, or synaptic causal influence.
- Shortest-path / global-efficiency model of information flow (reachability
  correlates only moderately, ρ = 0.39).
- Neurotransmitter annotations are predictions (Schlegel 2024), not measured
  sign; GLUT handled separately; 227 tested neurons have unknown NT.
- Single adult female brain, one reconstruction (v783); no cross-dataset
  replication yet (FANC/MANC/MaleCNS/BANC left to future work).
- 3,518 targeted neurons were tested rather than the full graph;
  high-degree candidates were enriched by design.
- 100-null ensemble limits tail resolution (≈ 0.01); the null comparison
  uses the k=4 panel (both statistics agree on the verdict).
- E14-v2 per-node peer comparisons involve multiple tests; peer pools < 10
  are flagged (9 of top 50).

## Final Research Status

**FINAL SCIENTIFIC STATE — Analysis frozen 2026-09-18.** Subsequent changes
are restricted to documentation, formatting, archival, reproducibility, or
correction of demonstrated errors.

Completion status:

- ✅ E10B degree-preserving null analysis — COMPLETE (100 directed
  configuration-model null networks, exact degree preservation verified
  per null)
- ✅ E14 visual-centrifugal chokepoint analysis — COMPLETE (v2 catalogue
  + region mapping)
- ✅ Final manuscript — COMPLETE (md/tex/HTML + production PDF)
- ✅ Final scientific QC — COMPLETE (12/12 tests; 43/43 number audit;
  19/19 raw-file SHA256)
- ✅ Scientific freeze — 2026-09-18 (freeze commit `fdfafe5`;
  release-preparation documentation follows it)

See `results/final/FINAL_REPORT.md` and
`results/final/FINALIZE_DONE.stamp`.
