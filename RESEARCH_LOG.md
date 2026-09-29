# RESEARCH LOG

Working title: *Inhibitory Chokepoints in the Drosophila Brain:
A Neurotransmitter-Resolved Network Analysis of Information Flow*

Hypothesis (frozen 2026-09-15, v2 — see entries E00 and E00a):

> **H1 (frozen, v2):** Inhibitory neurons have disproportionately large
> per-neuron control impact on network information flow relative to their
> degree, BEYOND the degree-GABA association already documented by
> Lin et al. 2024 (ED Fig 3d) — i.e., the effect must survive
> degree-matched controls, degree-preserving null models, and
> cross-dataset robustness. Any claim must be residual-to-degree,
> not raw.

---

## E00 — Novelty check (desk research)

```
Date:         2026-09-15
Experiment:   Literature novelty search (6 structured queries + prior survey
              from research_plan.md Part 5)
Hypothesis:   H1 candidate — do inhibitory neurons act as control chokepoints?
Dataset:      n/a (literature)
Parameters:   Query families: inhibitory+perturbation, GABA+centrality,
              network control/controllability, signed motifs, efficiency/node
              removal, FlyWire GABA hubs
Result:       31-paper matrix in literature/literature_review.csv.
              Closest neighbors:
              - Lin 2024 (Network statistics): rich-club + signed motif
                COUNTS with NT sign, descriptive. No perturbation, no
                degree-matched control, no per-neuron control ranking.
              - Shiu 2024 (computational brain model): whole-brain LIF
                simulation; perturbation is implicit in simulation, not a
                systematic per-neuron control-impact analysis with nulls.
              - Uzel 2022 (C. elegans): hub-removal methodology exists in
                C. elegans without NT-resolved controls — method transfer
                opportunity, not a scoop.
              - Clifford 2023 (larval hubs): removal analysis in LARVAL
                connectome, no NT-specific degree-matched controls.
              - brainwide_visual_2026 (bioRxiv): NT-signed flow analysis of
                visual pathways; pathway-level, not neuron-level chokepoints.
Interpretation: The specific combination — (a) neuron-level control-impact
              perturbation on FAFB v783, (b) degree-matched inhibitory vs
              excitatory comparison, (c) degree-preserving nulls, (d) signed
              motif characterization of chokepoint neighborhoods — is NOT
              occupied. Verdict: H1 is differentiated. FREEZE.
Next step:    Build Phase-1 pipeline (E01), then baseline (E02).
```

## E00a — Literature audit + novelty re-verification (external critique response)

```
Date:         2026-09-15
Experiment:   Primary-source verification of the novelty claim; matrix audit
Hypothesis:   n/a (epistemic hygiene)
Dataset:      n/a (literature)
Parameters:   Full-text read of Lin 2024 (PMC11446825); abstract+repo check
              of Shiu 2024 (PMC11446845); targeted searches for unverifiable
              matrix rows (Winding companion, serotonin FAFB paper)
Result:       THREE falsifications of the pre-audit record:
              (1) Lin 2024 DID neuron-removal analysis — degree-ordered
                  survival curves (Fig 1f,g; ED Fig 2a-d). Our earlier
                  "no node removal" claim was WRONG.
              (2) Lin used v630 (127,978 neurons; 2,613,129 connections),
                  not v783 — explains baseline numeric differences.
              (3) Lin already showed high-total-degree neurons are mostly
                  GABAergic (ED Fig 3d) — our E02 GABA-strength signal is a
                  REPLICATION of Lin, not a novel finding.
              Matrix audit: clifford_2023_larval_hubs could not be verified
              (companion paper does not exist) — REMOVED. sterling_2024
              replaced by verified sterling_2025_serotonin (bioRxiv
              10.1101/2025.08.19.671125). Garbled rows (xu/zheng/djurdjevic
              /placeholder) REMOVED. Final matrix: 19 papers, 16 columns,
              0 malformed rows, 100% verification_statused.
Interpretation: Novelty verdict DOWNGRADED from "gap confirmed" to
              "probable and precisely bounded": the surviving gap is the
              four-way combination (per-neuron CIS ranking +
              NT-conditioned comparison + degree-matched controls +
              degree-preserving nulls), which no verified paper contains.
              Publication-grade proof requires pre-submission gates:
              dedicated 2025-26 preprint sweep, FlyWire/CODEX community
              check, DOI-level re-verification of all matrix rows.
              H1 re-frozen as v2 (degree-residual form). See MASTER_PLAN.md §3.
Next step:    E03 chokepoint perturbation (per MASTER_PLAN.md §5 spec)
```

## E01 — Phase-1 data pipeline

```
Date:         2026-09-15
Experiment:   Tier-1 load + validate + pair-collapse + graph build
Hypothesis:   n/a (infrastructure)
Dataset:      neurons/classification/names/consolidated_cell_types/
              visual_neuron_types + connections_princeton (thresholded)
Parameters:   NT sign policy: GABA=inhibitory, ACH=excitatory,
              GLUT/DA/SER/OCT/unknown kept separate (no forced E/I binning)
Result:       RAN 2026-09-15, 38.1s total. 139,255 neurons merged; all
              root_ids pass 18-digit FAFB pattern validation. Edges:
              5,342,446 per-neuropil rows -> 3,732,460 unique pairs,
              0 self-loops. 100% of edge endpoints present in metadata
              (pre/post in-metadata fraction = 1.0). Edge NT rows:
              ACH 3.21M / GABA 1.17M / GLUT 826k / DA 64k / SER 40k / OCT 29k.
Interpretation: pipeline correctness gate PASSED. Edge tables are a clean
              subset of the metadata universe - no orphan-join risk in the
              thresholded connectome.
Next step:    E02 baseline
```

## E02 — Baseline network statistics

```
Date:         2026-09-15
Experiment:   Global + node-level baseline (degree, strength, PageRank,
              density, reciprocity, components, NT composition)
Hypothesis:   n/a (baseline)
Dataset:      data/processed/graph_pairs.parquet
Parameters:   binary adjacency for degree/reciprocity; synapse-weighted for
              strength; PageRank alpha=0.85
Result:       RAN 2026-09-15, 20.1s. GLOBAL: 139,255 nodes; 3,732,460
              edges; mean degree 26.8; density 1.92e-4; reciprocity 0.083;
              875 weak components (largest = 98.4% of nodes); median
              PageRank 3.09e-6. BY NT SIGN (neuron-level):
                excitatory (ACH) n=82,298 | med deg 15/18 (in/out)
                  | mean strength 318/347
                inhibitory (GABA) n=16,017 | med deg 22/24
                  | mean strength 754/690
                glut               n=19,605 | med deg 16/17 | 390/337
                modulatory (DA/SER/OCT) n=1,677 | med deg 5/9 | 567/441
                unknown            n=19,658 | med deg 4/6  | 196/190
              Edge-level (collapsed pairs): ACH 60.3% / GABA 22.4% /
              GLUT 15.3% / modulatory ~2%.
Interpretation: FIRST SIGNAL (baseline only, NOT the hypothesis test):
              GABA neurons are 5x fewer than ACh neurons but carry ~2.2x
              higher mean in-strength and ~2x higher mean out-strength,
              with ~46% higher median in/out degree. Consistent with a
              few-widespread-inhibitors architecture. CONSEQUENCE: raw
              inhibitory-vs-excitatory perturbation comparisons would be
              degree-confounded - the degree-matched control design (E03)
              is mandatory, as planned. Also: largest component is 98.4%,
              so efficiency-based perturbation is well-defined globally.
Next step:    E03 chokepoint perturbation (top-percentile targets);
              figures from baseline tables when starting figures/
```

## E04 — Control Impact Score: definition, validation, benchmark (GATE 1)

```
Date:         2026-09-15
Experiment:   E04.1-E04.7 per MASTER_PLAN (define -> implement -> synthetic
              validation -> benchmark -> freeze)
Hypothesis:   n/a (metric engineering)
Dataset:      synthetic fixtures + data/processed/graph_pairs.parquet
Parameters:   Frozen definition: CIS(i) = 1 - S(G-i)/S(G); S = sum 1/d;
              unweighted directed shortest paths; freeze-N convention
              (free-N reported as diagnostic only). Estimator: fixed-source-
              panel BFS, k sources drawn once, per-target COO edge masking.
Result:       ATTEMPT 1 (v1): 1/5 tests passed - caught denominator
              unit-mismatch bug (node count vs pair count) in exact CIS.
              Root-caused empirically: primitive chain CIS = 0.6103896...
              = 1 - 2.5/(77/12), exactly as analytic. ATTEMPT 2 (v2):
              9/9 PASS (chain 47/77 exact; 3-chain collapse CIS=1; tail
              removal 0.6 with free-N -0.2 artifact documented; star
              center 1.0 / leaf 0.25; random removals small+bounded;
              bridge > 2x local; panel(all sources) == exact at 1e-9;
              two-panel stability rho>0.9 on structured fixture;
              boundedness on real subgraph).
              K-SWEEP INSIGHT: panel stability is unmeasurable on
              structureless random graphs (rho 0.63/-0.23/0.05/0.15 at
              k=64..512 = noise on constant true CIS) - stability must be
              assessed on structured graphs. Fixture fixed accordingly.
              BENCHMARK (full brain, 138,584 nodes / 3,732,460 edges):
              baseline panel BFS k=8: 1.5s, k=32: 4.0s;
              1.63s per target at k=8 -> 1,000 targets ~ 27 min,
              5,000 ~ 2.3 h, 10,000 ~ 4.5 h. Real-graph sample CIS:
              8e-6..1.74e-4 (tiny, finite, as predicted).
Interpretation: Metric behaves exactly as theory on all synthetic ground
              truths; estimator is exact-consistent and stable where
              signal exists; whole-brain scale is FEASIBLE on CPU with
              candidate-first design. GATE 1 PASSED; GATE 2 feasible.
Next step:    E05/E06: pre-register target list (top 1% by degree/strength/
              PageRank + all high-degree GABA + random background) in this
              log BEFORE unblinding; screen at k=8; re-rank finalists at
              k=32-64; THEN E07/E08.
Status:       PASS (Gate 1)
```

## E06-E10 — Core experiment chain (executed 2026-09-15)

```
E06 (GATE 2: PASS). Pre-registered 3,518 targets (2,086 union top-1% by
     degree/strength/PageRank + 937 high-degree GABA (>=p90 of GABA
     degrees, thr=216) + 500 random background). Screened k=8: median
     CIS 9.7e-6, p99 3.9e-4, MAX 0.0240 (top neuron removes 2.4% of
     whole-brain efficiency). Rerank 200 finalists k=32, 2 seeds:
     Spearman(screen, rerank) = 0.67 (screen ranking noisy at tail,
     rerank authoritative).
E07. 3,518 annotated; 93.5% NT coverage (GABA 1707, ACH 1124, GLUT 373,
     unknown 227, DA/SER/OCT 87).
E08. Degree matching (pre-registered: total degree +/-10%, 1:1 greedy,
     no replacement): 848 GABA-ACh pairs.
E09. Matched pairs: GABA median CIS HIGHER than matched ACh controls
     (median diff 8.7e-7, Wilcoxon p=0.0011, permutation p=1.0e-4) but
     Cliff's delta = 0.111 (negligible-small). OLS log10(CIS) ~ GABA +
     log10(degree): beta1 = -0.025 (p=0.95) - NO positive association
     after degree control. Unmatched GABA median only 8.7% above ACh.
E10 (GATE 4: NOT SUPPORTED for the positive hypothesis). Pilot: 5
     degree-preserving configuration-model nulls (exact degree sequences,
     vectorized stub matching), same 848 pairs, k=4 panel. Observed
     delta=0.098 vs null delta 0.084 +/- 0.010 (range 0.072-0.099);
     empirical p(delta)=0.33, p(median_diff)=0.83. Null networks
     REPRODUCE the matched-pair GABA effect.
VERDICT (Outcomes A-D): OUTCOME B - degree explains the apparent effect.
     The pre-registered matched-pair significance (E09) does not survive
     degree-preserving nulls; OLS agrees (beta1~0). The honest result:
     GABAergic neurons are structurally central (replicating Lin 2024
     ED Fig 3d), but their control impact is what degree predicts;
     NT identity adds no detectable excess at this resolution/pilot power.
NEXT: E11-E13 (interpretation + robustness), E14 catalogue, then
     full-protocol items (500 nulls, no-threshold dataset) pre-registered
     for the publication-grade run.
```

## E11-E14 v1 + E12-strong + E14 v2 — Interpretation, enrichment, catalogue

```
E11 (corrected). Top-50 1-hop neighborhood NT composition using FULL core
     metadata (139,255; earlier run wrongly looked up in the tested
     subset - 94.9% unknown): top-50 GABA 16.7% vs background 16.9% -
     NO GABA excess in chokepoint neighborhoods; both ACh-dominated.
E12-strong (pre-registered controls BEFORE unblinding new numbers).
     VC (visual_centrifugal) enrichment of top-K CIS at three control
     levels: (A) tested-universe random (n=10,000 reps), (B) per-slot
     degree-matched (+/-10% log-degree, nearest-50 fallback).
     K=25: obs 9, E(A)=0.9, E(B)=3.6, pA=pB<0.01, zB=3.3
     K=50: obs 21, E(A)=1.8, E(B)=8.0, pA=pB=1e-4, zB=5.3 (2.6x vs
           degree-matched)
     K=100: obs 30, E(A)=3.6, E(B)=14.0, pA=pB=1e-4, zB=4.9 (2.1x)
     Per-class (K=50): central-brain neurons UNDER-represented (0.27x).
     Raw 11.7x drops to ~2.6x after degree matching but SURVIVES
     decisively - degree explains most, not all, of the VC enrichment.
E14 v2 (selection-bias correction). v1's OLS-residual labels were
     circular (selected on outcome). v2: per-node empirical p from
     degree-matched peers calibrated on the FULL tested population,
     self EXCLUDED from peer pools (critical for extreme degrees),
     peer_pool_n recorded (9 top-50 nodes have pools <10 - flagged).
     Result: 13/50 top chokepoints beat degree peers (emp p<0.0005-
     0.01); 10/13 are visual-system (optic/VC). Rank 1 (GABA optic,
     degree 12,444, CIS 2.4%): emp p < 0.0005, 2.35x peers. Rank 3
     (OCT visual_centrifugal, degree 858): emp p = 0.0000, CIS 156x
     peer median - a low-degree genuine chokepoint (bridge position).
     Class counts: 13 A_strong, 4 A+B mixed tags, 22 B_degree_driven,
     10 with B_intermediate.
NOVELTY (E16B). Bates et al. 2026 Nature (BANC brain-and-cord;
     concurrent control-circuits work, different dataset/scale);
     Hoeller et al. 2026 Cell (VIN/VPN/VCN classification, no
     perturbation); TiNS 2025 review (functional feedback). No prior
     per-neuron control-impact ranking + degree-matched NT/region
     analysis on FAFB. Matrix updated (22 papers).
NEXT: E13-full (k=32 seeds 2/3, k=16, degree-definition, GABA+GLUT);
     E10B 100-null protocol; Fig6 null distribution; manuscript numbers
     refresh at completion. (Both completed — see E13-full and E10B below.)
```

## E13-full — Robustness battery (executed 2026-09-16, 49 min)

```
Seeds (k=32, finalists): Spearman vs main = 0.965/0.953/0.905/0.882
     (seeds 0-3); top-100 4-way Jaccard 0.63; top-50 0.40.
K-ladder: k8-k16 0.66, k8-k32 0.67, k16-k32 0.86 -> two-stage design
     validated; k=8 screening coarse by design, finalists stable.
Degree definition: CIS~total 0.58, ~out 0.54, ~in 0.49; top-50 are
     OUTPUT-dominated (median out-deg 1,050 vs in-deg 566).
GABA+GLUT sensitivity: 967 pairs, delta=0.107, Wilcoxon p=1.1e-5 ->
     same picture as GABA-only (delta=0.111); conclusion robust to
     inhibitory-set definition.
Connection-table: documented-only (no-threshold OOM at 8 GB; Buhmann
     non-comparable) - recorded honestly, not claimed.
```

## E10B — 100-null publication-grade protocol (COMPLETED 2026-09-17)

```
Design: same frozen construction as pilot; seeds 100+i; exact degree
     preservation VERIFIED per null (in+out sequences); chunk-
     checkpointed panels; 3 parallel workers; crash-safe row JSONs.
Fixes en route (both caught by the built-in verification, both unit-
     tested on adversarial graphs - hub-selfloop, dense, ring):
     (1) swap partners must be distinct AND disjoint from bad edges;
     (2) repair limit-cycles -> rejection redraw (accepted draws always
     exact). Pre-fix pilot artifacts quarantined as *_superseded.
FINAL (100/100, all degree-verified; results/final/e10b_final.json):
     observed delta 0.0979 (k=4 panel, same estimator as nulls);
     null delta mean 0.0713 / sd 0.0220 / median 0.0729 / min 0.0078
     (corrected 2026-09-18; earlier "min 0.0418" was the superseded
     16-null interim value) / max 0.1211 / p95 0.1067; 10/100 nulls
     >= observed -> p_delta 0.109;
     median diff 6.62e-7 vs null mean 1.53e-6 -> p 0.782; z 1.21.
VERDICT: Scenario B (pre-locked rule) - H1 rejected; Gate 4 closed.
     Independently recomputed by scripts/verify_e10b_final.py (all green).
Reference pass: 12/12 cited works DOI-verified via Crossref 2026-09-17;
     6 corrections (Dorkenwald pages 124-138; Schlegel exact title;
     Shih = Current Biology; Uzel pages 3443-3459.e8; Hoeller DOI
     10.1016/j.cell.2026.08.014; TiNS = Mickels & Turner 2026 49(1):63-75).
     Matrix rows updated in place; nothing added from memory.
```

## E03 — Chokepoint perturbation (superseded by E04-E08 plan; executed as E06-E10)

```
Date:         executed 2026-09-15 as the E06-E10 chain (this E03 slot was
              superseded before running; kept for log continuity)
Experiment:   Node removal -> network efficiency drop; Control Impact Score;
              degree-matched inhibitory-vs-excitatory comparison
Hypothesis:   H1 (frozen)
Dataset:      graph_pairs.parquet (+ no-threshold/Buhmann for E05 robustness)
Parameters:   targets = top 1/5/10 percent by each centrality measure;
              matched controls sampled on degree ± 10 percent; nulls =
              Maslov-Sneppen replicates (n=100 in E10B, not 1000)
Result:       see log entries E04, E06-E10, and E10B
Interpretation: Outcome B — degree explains the apparent inhibitory effect;
              H1 rejected as pre-registered (Gate 4, 2026-09-17)
Next step:    none — project finalized (see SESSION CLOSE below)
```

## SESSION CLOSE — 2026-09-18 (verification sweep)

```
Context:      User asked to resume anything stopped mid-run. Full sweep
              found NO incomplete computation: E10B stamp 100/100 nulls
              (FINALIZE_DONE.stamp 2026-09-17 22:18), final ZIP + PDF in
              dist/ (102 files, raw-dataset leak check CLEAN), pytest
              12/12 PASS re-run 2026-09-18, e18_manifest.json contains
              19/19 valid raw-file SHA256 checksums.
Action:       closed 3 bookkeeping loose ends only — (1) this log's stale
              RUNNING line and pending E03 stub; (2) LICENSE_NOTES.md
              checksum item marked done (evidence: e18_manifest.json
              dataset.raw_file_sha256); (3) QC_STATUS.md final-ZIP box
              checked. Final ZIP rebuilt 2026-09-18 with updated docs.
Verdict:      Project COMPLETE as of 2026-09-17 finalization; nothing
              re-run, no statistics touched.
```

## SESSION CLOSE 2 — 2026-09-18 (final audit + submission readiness)

```
Context:      Full external master-prompt audit requested (audit -> fix ->
              verify -> rebuild). All checks executed on real files.
Verified:     19/19 raw SHA256 recomputed MATCH; E10B 100/100 (null_id
              0-99, ok x100, all degree-verified); pytest 12/12 (8.92s);
              ZIP leak-check CLEAN; Fig6 provenance confirmed (reads
              e10b_results.json); figures regenerated.
Fixed (docs/tables only, no statistics changed): (1) e14_e10b_integrated
              _catalogue.csv stale 16-null ensemble note -> final 100-null
              values (50 rows); (2) e14_v2_summary.json + run_e14_v2.py
              note "pending E10B" -> Gate-4 closed; (3) null-delta min
              0.0418 -> 0.0078 in FINAL_REPORT/RESEARCH_LOG (0.0418 was
              the superseded 16-null interim value; true 100-null min,
              consistent with 2.5% quantile 0.0193).
Executed:     2025-26 novelty sweep (bioRxiv/arXiv/PubMed/Crossref/
              Scholar surfaces) + FlyWire/CODEX community check - no
              competing four-way-combination work found; flyGNN (arXiv
              2026) documented as adjacent-only.
Infra:        Git initialized (main, commit 79d04ef; raw data excluded
              via .gitignore); PDF + final ZIP rebuilt; stamp updated;
              FINAL_REPORT.md rewritten with 19-section submission
              structure.
Verdict:      Submission-ready. Remaining: venue choice, cover letter,
              bioRxiv posting, optional high-RAM connection-table run.
```

## SESSION CLOSE 3 — 2026-09-19 (public repository release preparation)

```
Context:      Repository published at github.com/harsha-vardhan-2006/
              fruitfly_paper; release-preparation pass requested.
Constraint:   Scientific freeze respected — no analyses, statistics,
              hypotheses, conclusions, or result artifacts changed.
Done (docs/provenance only):
              (1) README.md rewritten for the final frozen state
                  (removed stale "staged, not run" execution language);
              (2) stale commit references corrected — documents meaning
                  "final frozen state" now point to fdfafe5 (79d04ef was
                  the FIRST commit, not the freeze); historical SESSION
                  CLOSE 2 entry above preserved as written (append-only);
              (3) stale ZIP manifest (102 files / 5.4 MB) corrected to
                  the actual deliverable (149 files / ~7.8 MB; hash
                  matched dist/SHA256SUMS.txt, so the ZIP itself was
                  correct and untouched);
              (4) MASTER_PLAN roadmap section explicitly marked HISTORICAL;
              (5) reproducibility/REPRODUCIBILITY.md git-state note
                  corrected (was "not a git repository"; predates git init);
              (6) CITATION.cff added (repository metadata only; no DOI
                  invented - archival DOI to be added after Zenodo).
Verified:     pytest 12/12 PASS; scripts/verify_e10b_final.py all checks
              true; 19/19 raw SHA256 untouched; canonical numbers
              cross-checked against frozen artifacts - no discrepancies
              found; raw-dataset leak check CLEAN; no secrets committed.
Verdict:      Scientific content UNCHANGED; repository documentation now
              accurately represents the final frozen state. Release tag
              v1.0.0 marks the public research package.
```

## PROVENANCE NOTE — repository history rewrite (2026-09-26)

```
What:       All commit SHAs in this repository changed on 2026-09-26. The
            entire history (8 commits + tag v1.0.0) was rewritten SOLELY to
            correct author identity from "Harsha Vardhan" to the full name
            "Harsha Vardhan Malipeddi" (git filter-branch env-filter; no
            file contents, dates, or messages changed).
Old -> new (key refs):
            79d04ef -> e12f4ee  (first commit)
            fdfafe5 -> e7f9d96  (scientific-freeze commit cited as "freeze
                                 commit fdfafe5" in historical entries)
            722b646 -> 9a6ac1a  (previous main tip)
            2711979 -> 991202a  (v1.0.0 tag commit)
            Main tip now 9a6ac1a; tag v1.0.0 re-pointed (new tag object
            4d17e61) and force-pushed to origin.
Rule:       Historical entries above that cite old SHAs (79d04ef, fdfafe5)
            are PRESERVED AS WRITTEN per append-only discipline; their
            historical meaning maps through the table above. No scientific
            artifact is affected.
```

## E13.6b — Connection-table sensitivity: no-threshold table (EXECUTED 2026-09-29, 18.4 min)

```
Context:    closes the single open QC item ("Robustness: connection-table
            sensitivity"), which E13-full 13.6 had recorded as
            documented-only (naive collapse ~50M pairs OOM'd 8 GB RAM).
            Post-freeze change, logged per freeze discipline: no frozen
            artifact modified; new artifacts carry the e13b_ prefix.
Method:     connections_princeton_no_threshold.csv.gz streamed in 2M-row
            chunks; only rows with BOTH endpoints in the FROZEN node
            universe (thresholded graph_pairs.parquet node set AND order)
            are kept; pair-collapse vectorized (local-index key packing,
            np.unique/bincount blocks; peak RSS < 1 GB).
Graph:      binary digraph, n = 138,584 (identical universe/order),
            m = 19,765,143 pairs = 3,732,460 thresholded + 16,032,683
            added (4.30x edges; syn totals 76.93M vs 50.67M).
Estimator:  identical frozen protocol as the E10B observed statistic —
            fixed panel k=4, seed 0, 1,696 matched-pair nodes (848 E08
            pairs), statistic = Cliff's delta + median difference.
            Loop mirrors control_impact.cis_bfs_panel with the COO
            conversion hoisted; EQUIVALENCE GATE on the thresholded
            graph (24 sampled pair nodes): max |dCIS| = 0.0 vs stored
            e10_ckpt_real.parquet values -> bit-identical, run proceeded.
Result:     observed no-threshold delta = -0.1165 (median GABA 8.29e-6 vs
            ACh 8.75e-6; median diff -4.60e-7). Thresholded observed
            delta = +0.0979 (recomputed in-script, matches
            results/final/e10b_final.json to 1e-9). The sign FLIPS.
Interpretation:
            (a) The raw matched-pair "GABA effect" is NOT robust to the
            edge-inclusion rule — the primary GABA-vs-ACh contrast is an
            artifact of the thresholded edge definition (low-synapse
            edges, added 16.03M of them, are disproportionately
            GABA->ACh-favoring in this pair set).
            (b) The frozen verdict is REINFORCED, not overturned: there
            is no GABA-specific structural control effect to explain;
            delta = -0.117 lies outside the thresholded 100-null range
            (0.0078-0.1211, z = -8.5), while no-threshold delta is on
            the opposite side of zero. Both edge definitions agree on
            the substantive conclusion: no GABA-specific effect.
            (c) CAVEAT (honest): the 100-null ensemble was built on the
            THRESHOLDED graph, so p-values comparing the no-threshold
            statistic to that ensemble are indicative only; a
            no-threshold null ensemble was NOT rerun (out of scope for
            the QC item; would need ~5x longer null runs). The verdict
            does not depend on this comparison: under both edge rules
            the effect either fails the null test (thresholded) or
            reverses sign (no-threshold).
Buhmann:    remains excluded as methodologically non-comparable
            (different reconstruction pipeline; MASTER_PLAN 6.4).
Artifacts:  data/processed/e13b_nothr_pairs.parquet (processed intermediate),
            e13b_nothr_edge_stats.json, e13b_ckpt_nothr_real.parquet,
            e13b_nothr_results.json, e13b_run.log / e13b_run2.log,
            scripts/run_e13b_nothreshold_sensitivity.py.
Docs:       QC_STATUS checkbox ticked with evidence; README Robustness,
            FINAL_REPORT 14.3 UPDATE + 19.3, REPRODUCIBILITY,
            manuscript 4.6 / limitation 7 / completion checklist synced.
Next step:  none — QC tracker now 46/46; submission tasks unchanged.
