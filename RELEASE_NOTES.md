# Release v1.1.0 — Connection-Table Sensitivity Completed (QC 46/46)

**Date:** 2026-09-29
**Status:** FINAL — all pre-registered experiments, robustness checks, and QC
items executed with artifact evidence (46/46).

## Highlights

- **Robustness battery now complete.** The single open QC item —
  connection-table sensitivity (E13.6b) — was executed post-freeze:
  - No-threshold graph rebuilt on the **frozen node universe** via a
    chunked, memory-safe loader (peak RSS < 1 GB on an 8 GB machine;
    prior naive attempt OOM'd at ~50M collapsed pairs).
  - Graph: **19,765,143 pairs** = 3,732,460 thresholded + 16,032,683 added
    low-synapse edges (4.30×; synapse totals 76.93M vs 50.67M).
  - Identical frozen estimator (k=4 panel, seed 0, 848 pre-registered
    GABA–ACh pairs); **equivalence gate max|ΔCIS| = 0.0** against the
    frozen per-node output before any new number was trusted.
- **New result:** the raw matched-pair GABA effect **flips sign** under the
  no-threshold edge definition (δ = **−0.117** vs **+0.098** thresholded;
  outside the thresholded 100-null range 0.008–0.121, z = −8.5). The raw
  positive effect is an artifact of the thresholded edge-inclusion rule.
  This **reinforces** the frozen Scenario-B verdict (no GABA-specific
  structural control effect): both edge definitions agree on the
  substantive conclusion. Honest caveat: the null ensemble was built on
  the thresholded graph, so the no-threshold comparison is indicative,
  not a formal test.
- Stray Windows system binary (`Microsoft.Services.Store.winmd`) removed
  from the repository root (flagged in the original dataset review).
- Deliverables regenerated: production PDF, `dist/manuscript.pdf`, final
  ZIP (156 files, 8.2 MB, raw-dataset leak check CLEAN), SHA256SUMS.

## Headline findings (unchanged from v1.0.0, now stronger)

1. **Negative (primary, pre-registered):** GABAergic identity does not
   predict per-neuron structural control impact beyond degree/structure
   (100-null ensemble: p = 0.109 / 0.782; OLS β₁ = −0.025, p = 0.95).
2. **Positive:** high-impact neurons are strongly enriched in
   visual-centrifugal architecture — 21/50 top chokepoints, 2.63×
   enrichment after per-slot degree matching (z = 5.30, p = 1e-4);
   13/50 individually exceed degree-matched peers (10/13 visual-system).

## Verification

- Tests: **12/12 pass** (`py -3.13 -m pytest -q`)
- Independent E10B recomputation: all checks green
  (`py -3.13 scripts/verify_e10b_final.py`)
- Number audit: 44/44 (43 frozen rows + 1 new E13.6b row)
- Raw-data integrity: 19/19 SHA256 recomputed MATCH (raw data not
  redistributed; see `results/tables/e18_manifest.json`)

## Environment

Python 3.13.2; pandas 2.3.3; numpy 2.4.2; scipy 1.18.0; pyarrow 23.0.1
(pinned in `requirements.txt`). Invoke scripts as `py -3.13` on Windows
(a bare `py` may resolve to an interpreter without pandas).

## Data & License

FlyWire FAFB v783 (Princeton exports), CC BY-NC 4.0. Raw files are NOT
redistributed; required citations and redistribution policy in
`LICENSE_NOTES.md` (Dorkenwald 2024; Schlegel 2024; Matsliah 2024).

## Upgrade notes (v1.0.0 → v1.1.0)

- No changes to any frozen scientific artifact; all v1.0.0 numbers remain
  valid. v1.1.0 adds the E13.6b artifacts (`results/tables/e13b_*`,
  `data/processed/e13b_nothr_pairs.parquet`), the runner script, and
  synced documentation.
- `CITATION.cff` version bumped to 1.1.0 (2026-09-29).
