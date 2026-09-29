# Reproducibility manifest — flybrain-research FINAL

Generated: 2026-09-17 (updated at E10B freeze).

## Dataset
- **FAFB v783 (Princeton exports)**, CC BY-NC 4.0
- Required citations: Dorkenwald et al. *Nature* 634:124–144 (2024);
  Schlegel et al. *Nature* 634:153–170 (2024); Matsliah et al. *Nature* (2024)
- Raw files unmodified; SHA256 of all 19 raw files:
  `results/tables/e18_manifest.json` → `dataset.raw_file_sha256`
- Raw data is **never** included in the submission archive
  (`dist/flybrain_connectome_control_FINAL.zip` ships code + results only).

## Environment (recorded by E18 manifest + runtime probes)
- Python 3.13.2 (Windows 11, AMD64, local CPU)
- pandas 2.3.3 · numpy 2.4.2 · scipy 1.18.0 · pyarrow 23.0.1 · matplotlib 3.11.2
- NetworkX deliberately not used (plan §27); scipy sparse CSR + numpy throughout
- Test command: `py -m pytest -q` (12 tests) + `py -m compileall src tests`

## Frozen analysis parameters
- Graph: binary directed CSR; 138,584 nodes / 3,732,460 edges
  (pair-collapsed `connections_princeton`, ≥5-synapse threshold)
- CIS(i) = 1 − S(G−i)/S(G); freeze-N convention; unweighted directed
  shortest paths; fixed-source-panel estimator (validated: panel(k=N) ≡
  exact at atol 1e-9)
- Screening k=8 (3,518 pre-registered targets); rerank k=32 (seeds 0, 1;
  E13 adds seeds 2, 3)
- Degree matching: 1:1 greedy, GABA→ACh, total degree ±10%, no
  replacement, larger-degree GABA first — 848 pairs (pre-registered)
- E10B: 100 nulls, directed configuration model with EXACT in+out degree
  sequences (verified per null, abort on mismatch), seeds 100+i (i=0..99),
  panel k=4, 3 workers, resumable checkpoints

## Pipeline (exact reproduction order)
```bash
py -m src.graph.build_graph            # E01
py -m src.graph.baseline               # E02
py -m src.experiments.run_e06          # E06 screen+rerank
py -m src.experiments.run_e07_e09      # E07-E09 annotation/matching/stats
py -m src.experiments.run_e10b         # E10B 100-null protocol (long)
py -m src.experiments.run_e10b stats   # E10B final statistics
py -m src.experiments.run_e11_e14      # E11-E14 biology + catalogue
py -m src.experiments.run_e12_strong   # E12-strong enrichment controls
py -m src.experiments.run_e13_full     # E13 robustness battery
py -m src.experiments.run_e14_v2       # E14-v2 catalogue (bias-corrected)
py -m src.experiments.run_e15_figures  # Figures 2-7
```

## Provenance & honesty notes
- **Git state:** the repository is public at
  `https://github.com/harsha-vardhan-2006/fruitfly_paper` (branch `main`).
  Scientific freeze commit: `fdfafe5` (2026-09-18); release tag `v1.0.0`
  (initial public package); superseded by release tag `v1.1.0`
  (2026-09-29, adds E13.6b connection-table sensitivity; QC 46/46).
  The E10B code version hash `f1d00d078f7f3ad7` (recorded inside
  `e10b_final_report.txt` / worker config) remains the analysis-time
  code-identity anchor, and the archive ships the exact code itself.
- Interim/superseded artifacts are preserved under `results/superseded/`
  (E10 pilot 5-null run; 16-null interim report) — audit trail intact,
  never deleted, never mixed into final numbers.
- Connection-table sensitivity: completed post-freeze 2026-09-29 (E13.6b):
  chunked no-threshold collapse on the frozen node universe (19,765,143
  pairs; peak RSS < 1 GB) — `scripts/run_e13b_nothreshold_sensitivity.py`;
  equivalence-gated vs the frozen estimator (max|ΔCIS| = 0.0);
  results in `results/tables/e13b_nothr_results.json`. The Buhmann table
  remains methodologically non-comparable.
- 2025–26 novelty sweep: 22-paper verified matrix
  (`literature/literature_review.csv`); live web re-verification was
  unavailable in the finalization session — re-run before submission;
  no references added from memory.

## Figures ↔ claims
- fig2 baseline · fig3 CIS distribution · fig4 degree vs CIS ·
  fig5 matched pairs · **fig6 = observed vs 100 degree-preserving nulls** ·
  fig7 top-50 super-class + E14v2 classes
