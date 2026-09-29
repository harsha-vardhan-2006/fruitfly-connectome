# MASTER PLAN — Inhibitory Chokepoints in the Drosophila Brain
### The definitive project document: requirements → verified novelty → frozen hypothesis → experiments → status

**Version:** 2.2 (2026-09-19, release preparation — historical roadmap clearly marked; v2.1 2026-09-18 post-finalization; v2.0 2026-09-15 post-audit)
**Supersedes:** research_plan.md Parts 4–8 (lit survey + hypotheses) — those remain valid for dataset audit (Parts 1–3) but the novelty verdict below is the authoritative one.
**Inputs:** `review.md` (raw-data audit), `research_plan.md` (strategy), `literature/literature_review.csv` (19 verified papers), `RESEARCH_LOG.md` (executed experiments).

---

## 1. Project definition

**Working title:** *Inhibitory Chokepoints in the Drosophila Brain: A Neurotransmitter-Resolved Network Analysis of Information Flow*

**Research question:**
> Does inhibitory (GABAergic) identity predict per-neuron control impact on whole-brain information flow **beyond** what degree, strength, and centrality already explain — tested by structural neuron-removal perturbation with degree-matched controls and degree-preserving nulls on the adult FAFB connectome?

**The one rule:** never call anything novel because we haven't personally seen it; never call anything a discovery before statistical testing; never modify a raw file.

---

## 2. Exact requirements extracted (data, files, environments)

### 2.1 Data requirements (verified locally)

| Tier | Files | Status |
|---|---|---|
| T1 core | `neurons`, `classification`, `names`, `consolidated_cell_types` (+`visual_neuron_types` for OL subsets) | ✅ loaded, validated, merged (139,255 neurons; 100% ID-valid; edges 100% in-metadata) |
| T1 edges | `connections_princeton.csv.gz` (5,342,446 rows → 3,732,460 pairs) | ✅ processed to `data/processed/graph_pairs.parquet` |
| T2 robustness | `connections_princeton_no_threshold`, `connections_buhmann_no_threshold` | present, unused until E07 |
| T3 spatial | `synapse_coordinates`, master synapse table (mangled IDs — reconstruct `720575940` + 9-digit suffix) | present, unused in this project's core claims |
| T4 morphology | `sk_lod1_783_healed.zip` (139,273 SWCs, 18 orphans) | present, unused (no morphology claim) |

### 2.2 Software requirements (verified working)

- Python 3.13.2 via `py`; pandas 2.3.3, numpy 2.4.2, scipy 1.18.0, pyarrow 23.0.1, tqdm 4.67.3 — **all installed, all exercised by E01/E02 runs**
- Graph engine: **scipy.sparse CSR + numpy** (NetworkX deliberately excluded; plan §27)
- Optional: matplotlib/seaborn (figures, not yet needed), igraph (only if sampled betweenness proves too slow)

### 2.3 Citation requirements (license condition)

CC BY-NC 4.0 — non-commercial; cite Dorkenwald 2024, Schlegel 2024, Matsliah 2024; pin "FAFB v783" in methods. Details: `LICENSE_NOTES.md`.

---

## 3. Novelty verdict — audit-corrected, primary-source-verified

### 3.1 What the audit changed

The pre-audit matrix claimed "Lin 2024: no node removal." **Primary-source reading (PMC11446825, full text) falsified that:** Lin et al. DID degree-ordered neuron-removal survival curves (Fig 1f,g; ED Fig 2a–d). The corrected gap therefore rests on the four-way combination below, and on two additional verified facts that *shrink* the claim space further:

- **Lin used v630** (127,978 neurons / 2,613,129 connections), not v783 — our baseline numbers (139,255 / 3,732,460) differ for that reason, not error.
- **Lin already showed "high-total-degree neurons are mostly GABAergic"** (ED Fig 3d) — so our E02 GABA-strength signal is a **replication** of Lin, not a finding. (It remains useful as a pipeline-correctness check: our independent pipeline reproduced their qualitative result.)

### 3.2 The verified gap (what survives the audit)

No published work combines, on the adult FAFB connectome:
1. **per-neuron** control-impact perturbation (remove neuron → measure communication loss → rank); Lin's removal is degree-ordered aggregate survival, not per-neuron ranking;
2. **neurotransmitter-conditioned** comparison (inhibitory vs excitatory vs glut vs modulatory); Lin's NT use is descriptive composition of motifs/reciprocity;
3. **degree-matched controls** (compare GABA vs ACh neurons at matched degree); absent from every verified paper;
4. **degree-preserving null validation of the impact ranking** (Maslov–Sneppen z-scores).

Also verified: Shiu 2024 = simulated activity manipulation of neuron sets (not structural removal ranking); Uzel 2022 = C. elegans hub-removal without NT controls; Winding 2023 = larval descriptive centrality (the purported larval "removal companion" paper does not exist and was removed from the matrix); brainwide_visual_2026 = pathway-level flow, no per-neuron validation.

**Verdict:** novelty is **"probable and precisely bounded"** — defensible for starting E03, not yet publication-grade proof. Publication-grade proof additionally requires (a) a dedicated search of 2025–2026 preprint servers (bioRxiv/arXiv q-bio) with the exact phrase set in §5, (b) a CODEX/FlyWire community check for in-preparation work, and (c) re-verification of all 19 matrix rows' bibliographic details (DOI-level) at submission time. These are tracked as pre-submission gates, not blockers for the experiment.

---

## 4. Frozen hypothesis (v2, post-audit)

> **H1 (frozen 2026-09-15, v2):** Inhibitory neurons have disproportionately large per-neuron control impact on network information flow relative to their degree, **beyond the degree-GABA association already documented by Lin et al. (2024)** — i.e., after degree-matching and degree-preserving nulls, inhibitory identity still predicts control impact.

H1 v1 (pre-audit) is superseded: it failed to account for Lin's GABA-degree finding. The v2 wording bakes the replication duty in: **any claim must be residual-to-degree, not raw.**

**NT policy (unchanged, safer than binary):** GABA → inhibitory; ACh → excitatory; GLUT → separate (sign context-dependent; Lin note: in fly brain glutamate has largely been observed inhibitory — sensitivity analysis will test GLUT-as-inhibitory); DA/SER/OCT → modulatory; unknown → retained, excluded from E/I comparisons.

---

## 5. Experiments (E01–E08) — exact data, methods, statistics

**E01 — Pipeline (DONE, log E01).** Loaders with verified quirks handling (CRLF, per-neuropil rows, mangled-ID reconstruction for T3, orphan-SWC exclusion); validation (18-digit ID regex, duplicate keys, in-metadata fractions); pair-collapse (sum syn_count; majority NT by synapse-weighted count). Outputs: `data/processed/{neuron_core,graph_pairs}.parquet`, `build_report.json`.

**E02 — Baseline (DONE, log E02).** Global: n, mean degree 26.8, density 1.92e-4, reciprocity 0.083, 875 WCCs (largest 98.4%). By-NT table (key row: GABA n=16,017, mean in-strength 754 vs ACh 318 — the Lin-replication signal). Outputs in `results/tables/`.

**E03 — Chokepoint perturbation (EXECUTED as the E06–E10 chain; see RESEARCH_LOG).**
- *Data:* `graph_pairs.parquet` + `neuron_core.parquet`.
- *Graph:* binary digraph on the 137,679-node thresholded connectome; per-neuropil variant for regional analyses.
- *Performance metric:* global efficiency on sampled source set (n≈1,000 sources; exact on ≤5,000-node subgraphs). CIS(i) = (Eff(G) − Eff(G−i)) / Eff(G).
- *Targets:* union of top-1% by degree, in/out-strength, PageRank, sampled betweenness (k≈512 sources); plus random-degree control sample; plus all GABA neurons with degree in the top decile of GABA degrees.
- *Controls:* (a) degree-matched ACh partners (±10% window) for every high-impact GABA hit; (b) strength-matched variants; (c) superclass-stratified matching as sensitivity.
- *Statistics:* Wilcoxon signed-rank on matched pairs; linear model CIS ~ degree + strength + nt_sign (+ superclass FE); permutation p-values; BH-FDR.
- *Success criteria:* Outcome A = inhibitory excess in CIS persists after matching (median ΔCIS > 0, q < 0.05); Outcome B = regional/class-specific excess only; Outcome C = no excess after matching (report "topology explains control; NT identity adds nothing" — publishable null).

**E04 — Null models (EXECUTED: E10 pilot 5 nulls, then E10B 100/100 with per-null degree verification; Gate 4 closed 2026-09-17, Scenario B).** Maslov–Sneppen degree-preserving rewires on the binary graph; recompute matched-pair statistic per replicate. Implementations in `src/experiments/null_models.py` + `run_e10b.py`, regression-tested in `tests/test_null_models.py`.

**E05 — Robustness.** Repeat E03–E04 on: (a) no-threshold Princeton edges; (b) Buhmann edges; (c) threshold ∈ {2, 5, 10}; (d) GLUT-as-inhibitory sensitivity; (e) QC weighting by `synapse_attachment_rates.proof_ratio`. Report concordance of top-100 chokepoint sets (Jaccard) and sign stability of the matched-pair effect.

**E06 — Signed motifs around chokepoints.** 3-node signed motif census (FFI, disinhibition, reciprocal E–I) in the 1-hop and 2-hop neighborhoods of top chokepoints vs degree-matched non-chokepoints; enrichment z-scores vs Maslov–Sneppen ensemble. Extends (not repeats) Lin's whole-brain descriptive motif counts by conditioning on chokepoint membership.

**E07 — Biological interpretation.** Map chokepoints to `consolidated_cell_types`, `classification.super_class`, neuropils (via edge tables), `coordinates` (soma position), `connectivity_tags` (rich-club/reciprocal overlap); FBbt cross-refs via `processed_labels`. Deliverable: chokepoint atlas table with anatomical identity and literature cross-refs.

**E08 — AI prediction layer (gated).** Only after E03–E07 pass review: features (degree, strength, PageRank, betweenness, NT, class, neuropil, local motif counts) → predict CIS; XGBoost/RF with SHAP-style importance; question: "can expensive perturbation be predicted from cheap features?" Explicitly decorative-free: included only if E03–E07 produce a stable target.

---

## 6. Execution status (honest)

| Component | Status |
|---|---|
| Raw dataset protection | ✅ untouched; all outputs to data/processed, results/ |
| Dataset audit | ✅ review.md + verified quirks in loaders |
| Literature review | ✅ 19 papers, 100% verification-statused, structure-validated CSV |
| Novelty | 🟢 probable + precisely bounded; pre-submission gates EXECUTED 2026-09-18 (2025–26 sweep + FlyWire/CODEX community check; no competing four-way-combination work) |
| H1 | 🔒 frozen **v2**, TESTED — REJECTED under the pre-registered framework (E10B 100-null ensemble, Scenario B, p = 0.109 / 0.782) |
| Project structure | ✅ src/ data/ results/ literature/ + docs |
| Data pipeline | ✅ E01 executed (38s, all validations green) |
| Baseline | ✅ E02 executed (20s); GABA-strength signal = Lin replication (documented) |
| Chokepoint experiment | ✅ E06–E08 executed (3,518 pre-registered targets; CIS ranking; 12/12 tests) |
| Degree-matched analysis | ✅ E08/E09 executed (848 pairs; δ = 0.111; OLS β₁ = −0.025) |
| Null models | ✅ E10 pilot + E10B 100/100 degree-verified (p = 0.109 / 0.782; Gate 4 CLOSED, Scenario B) |
| Statistical validation | ✅ E09 tests + E13-full robustness battery (seeds ρ 0.88–0.96; GABA+GLUT δ = 0.107) |
| Biological interpretation | ✅ E11 neighborhoods, E12-strong VC enrichment (2.6×, z = 5.3), E14-v2 catalogue (13/50), region mapping |
| Paper | ✅ manuscript + 6 figures + PDF; number audit 43/43; references 12/12 DOI-verified |

**Final state (2026-09-18):** H1 was tested and **rejected** under the pre-registered framework — the matched GABA effect is compatible with degree-preserving structure (E10B, Scenario B). The positive contribution is the visual-centrifugal chokepoint architecture (2.6× enrichment after degree matching; 13/50 individuals beating degree-matched peers). Pipeline, statistics, interpretation, paper, QC, package, and git history are complete; submission tasks remain (venue, cover letter, bioRxiv).

**Release state (2026-09-19):** E10B complete (100/100 nulls, degree-verified), E14 complete (v2 catalogue + region mapping), final manuscript complete (md/tex/PDF), final QC complete (12/12 tests; 43/43 number audit; 19/19 SHA256), repository freeze complete — scientific freeze commit `fdfafe5`; public release prepared with documentation/provenance updates only (see `results/final/FINAL_REPORT.md` §Release state).

---

## 7. Corrected roadmap (HISTORICAL)

*(Historical schedule as planned 2026-09-15 — PRESERVED FOR RECORD ONLY; every item below was executed per RESEARCH_LOG, finalization completed 2026-09-18, repository frozen. This table does NOT describe remaining work.)*

- **Now (Week 4):** run E03 as specified in §5; pre-register exact target lists in RESEARCH_LOG before unblinding results.
- **Week 5:** E04 nulls; freeze chokepoint definition (no post-hoc changes after nulls run).
- **Week 6:** E05 robustness; E06 motifs.
- **Week 7:** E07 biological interpretation; figures.
- **Week 8:** pre-submission novelty gates (dedicated 2025–26 preprint sweep; CODEX community check; DOI-level re-verification of matrix); write-up.
- **Week 9+:** E08 AI layer if warranted; preprint.

---

## 8. Provenance & reproducibility

- Raw files: never modified (verified by the fact that all scripts write only to data/processed and results/).
- Environment: `requirements.txt` pins verified versions.
- Log: `RESEARCH_LOG.md` E00–E03 (append-only discipline).
- Data version: FAFB v783 (Princeton exports); Lin comparisons noted against their v630.
