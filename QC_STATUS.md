# FINAL QC STATUS

Live document; ✅ only with artifact evidence. Final pass: 2026-09-18;
release-preparation re-check 2026-09-19 (documentation/provenance only,
no scientific changes).

## Data
- [x] Raw FAFB v783 untouched — all writes to `data/processed/`, `results/`; hashes in `results/tables/e18_manifest.json`
- [x] Dataset version documented — v783; `LICENSE_NOTES.md`; manuscript §3.1
- [x] Checksums recorded — `e18_manifest.json` (19 raw files, SHA256)

## Graph
- [x] Construction reproducible — `src/graph/build_graph.py`; `data/processed/build_report.json`
- [x] Root IDs validated — 100% 18-digit FAFB pattern (E01)
- [x] No duplicate edges — collapse to unique pairs; 0 self-loops (E01)
- [x] Degree statistics documented — `baseline_global.csv` (26.8 mean degree; audited ✅)

## CIS
- [x] Metric frozen — RESEARCH_LOG E04; `src/experiments/control_impact.py`
- [x] Synthetic tests — Gate 1, 9/9; full suite 12/12 PASS (re-run 2026-09-16)
- [x] Panel approximation validated — panel(k=N) ≡ exact at 1e-9
- [x] Seed stability — E13: ρ 0.88–0.96 across 4 seeds (k=32)

## GABA annotation
- [x] Source documented — Schlegel 2024 via `neurons.csv.gz` (§3.7)
- [x] Definition frozen — GABA-only primary; GABA+GLUT sensitivity (δ = 0.107 ≈ 0.111)
- [x] Other NTs retained — `e07_annotated.parquet`

## Matching
- [x] Rule pre-registered — ±10% total degree, 1:1 greedy, no replacement (§3.8)
- [x] 848 pairs — `e08_matched_pairs.csv`
- [x] No leakage — controls from ACh pool only, without replacement

## Statistics
- [x] Effect size — Cliff's δ 0.111 (primary) / 0.107 (GABA+GLUT)
- [x] Wilcoxon p = 0.0011; permutation p ≈ 1e-4 — `e09_results.json` (audited ✅)
- [x] OLS β₁(GABA) = −0.025, perm p = 0.95
- [x] Multiple-testing stance — single primary comparison; per-node emp_p descriptive + flagged

## Nulls (E10B)
- [x] Implementation correctness locked — adversarial regression tests (hub-selfloop, dense, ring)
- [x] Degree preservation verified per null — exact in+out sequences, abort on mismatch (**100/100 verified**)
- [x] Resumable run integrity — crash at 16/100 recovered; code/seeds/k unchanged
- [x] **100 nulls completed — 2026-09-17 (`results/tables/e10b_nulls.csv`, 100 rows, all status=ok)**
- [x] Empirical p-values at 100/100 — p(δ) = 0.109 (10/100 ≥ obs 0.098), p(median diff) = 0.782 → `results/final/e10b_final.json`; independently recomputed by `scripts/verify_e10b_final.py` (all checks green)
- [x] Gate 4 closure — **Scenario B** per the pre-locked rule: observed statistic inside the null ensemble (null δ = 0.071 ± 0.022, range 0.042–0.121); both statistics agree; H1 rejected as pre-registered

## Robustness
- [x] Seeds (4, ρ 0.88–0.96) / k-ladder (k16↔k32 0.86) / degree definition / metric (reach-drop 0.39) — E13-full
- [x] Connection-table sensitivity — **E13.6b EXECUTED 2026-09-29** (post-freeze, logged): chunked memory-safe no-threshold rebuild on the frozen node universe (19,765,143 pairs = thresholded + 16,032,683 added; peak RSS < 1 GB); identical k=4 panel estimator, equivalence gate max|ΔCIS| = 0.0 vs `e10_ckpt_real.parquet`. Result: δ = −0.117 (sign flip vs +0.098 thresholded; outside the 100-null range 0.008–0.121, z = −8.5) → the raw positive matched-pair effect is NOT robust to the edge-inclusion rule; the frozen Scenario-B verdict (no GABA-specific effect) is reinforced, not overturned. Evidence: `results/tables/e13b_nothr_results.json`, `e13b_ckpt_nothr_real.parquet`, `e13b_nothr_edge_stats.json`. Caveat: nulls were built on the thresholded graph, so the null-range comparison is indicative, not a formal test. Buhmann table remains excluded as methodologically non-comparable (MASTER_PLAN §6.4)

## Biology
- [x] VC enrichment quantified — E12-strong: 2.6× vs degree-matched, z = 5.3, p = 1e-4 (K=50); K=25/100 consistent
- [x] Enrichment-denominator & selection checks — E12-strong code audit (tested-universe + degree-matched controls; top-K fixed before testing; per-slot matching excludes self implicitly via pools from tested universe)
- [x] Duplicate/L/R handling — 1:1 collapse verified; side recorded per neuron; catalogue rows unique root_ids (50)
- [x] Region mapping — `e14_top50_region_mapping.csv` (top-3 input/output neuropils per top-50 chokepoint; NEW 2026-09-16)
- [x] E14-v2 catalogue — `e14_chokepoint_catalogue_v2.csv` (selection-bias-corrected; 9 tiny pools flagged)

## Paper
- [x] Figures fig2–fig7 (current results) — **regenerated 2026-09-17 from final data; Fig6 renders the 100-null distribution (p = 0.109 / 0.782)**
- [x] Number audit — `results/final/NUMBER_AUDIT.md` (**43/43 ✅**; rows 41–43 filled 2026-09-17)
- [x] Manuscript E10B sections — single-pass update from final JSON (abstract, §3.10, §4.5, §4.7, §6.6, §7); δ provenance note added; References section added; tracker updated
- [x] References DOI-level pass — **12/12 verified via Crossref/publisher records 2026-09-17; 6 corrections applied** (Dorkenwald pages, Schlegel title, Shih journal, Uzel pages, Hoeller DOI, TiNS identity); matrix rows updated in place
- [x] Limitations — §6 incl. null-resolution honesty (100-null tail resolution; k=4 vs k=8 estimator note)
- [x] Novelty wording — concurrent-work framing (Bates 2026, Hoeller 2026, Mickels & Turner 2026)

## Gates
- [x] Gate 1 metric (9/9) · Gate 2 scale (ρ 0.67) · Gate 3 matched test (δ = 0.111) · Gate 5 robustness (PASS w/ documented gaps)
- [x] **Gate 4 — 100-null confirmation: CLOSED 2026-09-17, Scenario B (effect compatible with degree-preserving structure; H1 rejected as pre-registered)**

## Reproducibility & archive
- [x] Environment manifest — `e18_manifest.json` (Python 3.13.2, pandas 2.3.3, numpy 2.4.2, scipy 1.18.0, Win11 AMD64)
- [x] Results reorganization — `results/final/` + `results/superseded/` (pilot + 16-null interim preserved, never deleted)
- [x] E10B archive — `results/e10b/E10B_FINAL_STATUS.md`
- [x] Final package ZIP (code+results+paper, excluding raw dataset) — `dist/flybrain_connectome_control_FINAL.zip` (149 files, ≈ 7.8 MB; leak-check CLEAN); rebuilt 2026-09-19 for release preparation with updated RESEARCH_LOG/README/CITATION.cff/provenance docs; SHA256 refreshed in `dist/SHA256SUMS.txt`. **Rebuilt 2026-09-29 (post-freeze E13.6b docs + artifacts): 156 files, 8.2 MB, leak-check CLEAN; SHA256SUMS.txt refreshed**
