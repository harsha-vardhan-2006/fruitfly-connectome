# Neuron-Level Structural Control Impact Reveals Visual-Centrifugal Chokepoints in the Drosophila Connectome

*Working manuscript — E06–E14 results frozen 2026-09-15; E10B 100-null confirmation protocol completed 2026-09-17 (`results/final/e10b_final.json`). All cited references DOI-level verified 2026-09-17 (see References). Title aligned with the headline finding 2026-09-18; primary H1 rejected under the pre-registered framework (Scenario B). Pre-submission tracker at the end of this document.*

---

## Abstract

**Background.** The FlyWire FAFB v783 connectome provides the complete wiring diagram of the adult female *Drosophila* brain (139,255 neurons; ~3.7M thresholded connections at the pair level). High-degree neurons are known to be disproportionately GABAergic, but degree alone does not establish network control.

**Question.** Do GABAergic neurons exert per-neuron control over whole-brain information flow that is disproportionate to their degree?

**Methods.** We define the Control Impact Score, CIS(i) = 1 − S(G−i)/S(G), where S is the sum of inverse directed shortest-path lengths (freeze-N convention) and G−i is the network with neuron i removed. We pre-registered 3,518 perturbation targets (top-1% union of degree/strength/PageRank; all high-degree GABAergic neurons; 500 random background), computed CIS via a fixed-source-panel BFS estimator (validated to 1e-9 against exact computation), performed pre-registered degree matching (GABA vs ACh, total degree ±10%, 848 pairs), and compared the observed effect against degree-preserving configuration-model null networks.

**Results.** Control impact is highly skewed: the median tested neuron accounts for ~1e-5 of whole-brain efficiency, while the top neuron accounts for 2.4% (three orders of magnitude higher). Top chokepoints are enriched for **visual centrifugal neurons: 21/50 of the top-50 (11.7× raw; 2.6× after degree matching, z = 5.3, p = 1e-4)**, and 13/50 beat degree-matched peers individually (E14 v2). GABAergic neurons show a small raw advantage over degree-matched ACh controls (Cliff's δ = 0.111, Wilcoxon p = 0.0011), but (i) this effect is within the range produced by degree-preserving random rewiring (100 null networks with exactly preserved in/out degree sequences: null δ = 0.071 ± 0.022, max 0.121, vs observed 0.098 at matched panel size; empirical p = 0.109; median-difference p = 0.78), and (ii) a regression of log-CIS on log-degree and GABA identity finds no GABA association (β₁ = −0.025, p = 0.95). GABA fraction among top-50 chokepoints (54%) matches the tested population (52%), and chokepoint neighborhoods are ACh-dominated regardless of chokepoint identity.

**Conclusion.** Structural topology, not neurotransmitter identity, is the dominant determinant of per-neuron network control in the adult fly brain. The chokepoint population is anatomically structured — dominated by visual centrifugal and optic-lobe neurons bridging the eye to the central brain — providing a concrete, testable anatomical target list. The data argue against a specialized "GABA traffic-controller" role at whole-brain scale, while not excluding neurotransmitter-specific effects on circuit function that a structural, shortest-path analysis cannot detect.

---

## 1. Introduction

1. Whole-brain connectomes now exist for adult *Drosophila* (FAFB; Dorkenwald et al. 2024), enabling network-level analysis of an entire animal brain at synaptic resolution.
2. Network analyses identified rich-club organization and showed that high-degree neurons are mostly GABAergic (Lin et al. 2024), but degree-ordered removal analyses do not isolate per-neuron control or its neurotransmitter dependence.
3. A neuron's importance as a control point cannot be read from its degree: bridging positions can make sparse neurons disproportionately influential, and hub-degree can be redundant.
4. Whether neurotransmitter identity — specifically inhibitory (GABAergic) identity — predicts per-neuron control impact beyond degree has not been tested.
5. We therefore pre-registered a perturbation pipeline: per-neuron removal, efficiency-based impact scoring, degree-matched NT comparison, and degree-preserving null validation.

## 2. Related Work

- **Connectome resources:** Dorkenwald 2024 (v783), Schlegel 2024 (cell typing + NT annotation), Matsliah 2024 (optic lobe).
- **Network analyses:** Lin 2024 (rich club, motifs, degree-ordered removal survival; v630); Kunin 2023 (modules); Shih 2015 (early flow analysis).
- **Perturbation-style analyses:** Shiu 2024 (whole-brain LIF simulation with set-wise manipulation); Uzel 2022 (C. elegans hub removal, no NT controls); Szilagyi 2026 (signed motifs in C. elegans).
- **Gap:** per-neuron control-impact ranking + NT-conditioned + degree-matched + null-validated analysis on the adult connectome (see `literature/literature_review.csv`, 22 papers with per-entry verification status; core citations DOI-level re-verified — References).

## 3. Materials and Methods

### 3.1 Dataset
FlyWire FAFB v783 (Princeton exports), CC BY-NC 4.0. Raw files unmodified; all processing scripted (see E18 manifest). Version pinned; master synapse table IDs reconstructed as `720575940` + 9-digit suffix (not used in the core analysis).

### 3.2 Connectome construction
Nodes = neurons from the union of metadata (139,255) and edge tables; edges = collapsed (pre, post) pairs from `connections_princeton` (≥5-synapse threshold), summing synapse counts across neuropils; per-pair NT = synapse-weighted majority. Validation: all root_ids 18-digit FAFB pattern; 0 self-loops; 100% of edge endpoints present in metadata.

### 3.3 Network representation
Binary directed adjacency (CSR); 138,584 nodes / 3,732,460 edges after edge-table universe restriction. Mean degree 26.8; density 1.92e-4; reciprocity 0.083; largest weak component 98.4%.

### 3.4 Global efficiency (frozen metric)
Eff(G) = (1/(N_F(N_F−1))) Σ_{i≠j} 1/d(i,j), d = unweighted directed shortest path, N_F = freeze-time node count. The freeze-N convention bounds CIS ∈ [0,1]; free-N renormalization reported as diagnostic only (can be negative for tail removals).

### 3.5 CIS
CIS(i) = (Eff(G) − Eff(G−i))/Eff(G) = 1 − S(G−i)/S(G). Exact for validation; at scale, fixed-source-panel BFS (k sources drawn once; per-target edge masking via COO arrays; CIS = 1 − S_panel(G−i)/S_panel(G)). Estimator validated: panel(k=N) ≡ exact (atol 1e-9); two-panel stability ρ>0.9 on structured fixtures; random-graph instability documented as expected (true CIS ≈ 0 there).

### 3.6 Node perturbation
Pre-registered targets (n=3,518): top-1% union of total degree / in+out strength / PageRank; all GABA neurons with degree ≥ 90th percentile of GABA degrees (n=937); 500 random background. Screening k=8; rerank of top-150 + 50 anchors at k=32 (two seeds).

### 3.7 GABA annotation
Per-neuron NT predictions from Schlegel 2024 via `neurons.csv.gz`; classes preserved (GABA/ACH/GLUT/DA/SER/OCT/unknown); primary comparison GABA vs ACh only; GLUT analyzed separately (sign context-dependent); modulatory (DA/SER/OCT) excluded from E/I claims.

### 3.8 Degree matching
1:1 greedy, without replacement, GABA→ACh on total degree within ±10%, larger-degree GABA matched first (pre-registered before unblinding). Result: 848/1,707 GABA neurons matched.

### 3.9 Statistical tests
Wilcoxon signed-rank on matched pairs; label-permutation test on median difference (10,000 permutations); Cliff's delta; OLS log10(CIS+ε) ~ GABA + log10(degree+1) with permutation inference on β₁.

### 3.10 Null models
Directed configuration model preserving both degree sequences exactly (vectorized stub matching with self-loop/duplicate repair). Two correctness guarantees, both locked by regression tests (`tests/test_null_models.py`, adversarial fixtures): (i) repair swaps use partner sets that are distinct *and* disjoint from the defect set (repeated or overlapping partners corrupt the in-degree multiset); (ii) non-converging repair rounds trigger rejection redraw — every accepted draw has exact degree sequences, verified per null inside the run. Per-null recomputation of the matched-pair statistic on the same 848 pairs, k=4 panel. **Pilot: 5 nulls** (feasibility; artifacts superseded and quarantined). **Full protocol (E10B, completed 2026-09-17): 100 nulls, seeds 100+i, 3 parallel workers, per-null degree-preservation verification — 100/100 completed, all degree-verified** (per-null rows `e10b_nulls.csv`; final statistics `results/final/e10b_results.json` = `results/final/e10b_final.json`).

### 3.11 Robustness
Screen↔rerank rank correlation; two-seed k=32 stability; top-100 3-way Jaccard; CIS vs reachability-drop rank agreement.

### 3.12 Software
Python 3.13.2; pandas 2.3.3; numpy 2.4.2; scipy 1.18.0; pyarrow 23.0.1; matplotlib 3.11.2 (figures only). NetworkX deliberately not used. Local CPU (Windows); runtimes in `results/tables/e04_benchmark.json` and RESEARCH_LOG.

## 4. Results

### 4.1 Baseline network
138,584 nodes, 3,732,460 edges, mean degree 26.8, reciprocity 0.083, giant WCC 98.4% (Fig 2; `baseline_global.csv`). Edge NT composition: ACh 60.3%, GABA 22.4%, GLUT 15.3%.

### 4.2 Control-impact distribution
Median tested CIS ≈ 9.7e-6; p99 = 3.9e-4; max = 2.40e-2 (Fig 3). The distribution is extremely right-skewed: chokepoints are rare, and impact spans three orders of magnitude.

### 4.3 High-impact neurons
Top-50 (k=32 rerank) median degree 1,925 vs 317 (all tested) — top chokepoints are high-degree, as expected. **Anatomical identity is the striking result: 21/50 visual centrifugal (11.7× raw enrichment over the tested population), 19/50 optic lobe, 6 central** (Fig 7). These are neurons feeding the eye's output back toward the central brain.

**Rigorous enrichment statistics (E12-strong, pre-registered controls).** Because CIS grows with degree, the raw ratio overstates enrichment. Two null controls (10,000 replicates each): (A) random draws from the 3,518 tested neurons; (B) per-slot degree-matched draws (±10% log-degree, nearest-50 fallback). At K=50: observed 21 VC neurons vs E(A)=1.8 (z=14.5, p=1e-4) and **E(B)=8.0 (z=5.3, p=1e-4; 2.6× after degree matching)**. K=25: 9 vs 3.6, z=3.3. K=100: 30 vs 14.0, z=4.9 (2.1×). Central-brain neurons are significantly *under*-represented (6 observed vs 22.3 expected, 0.27×). Degree explains most, but not all, of the VC concentration.

### 4.4 GABA vs non-GABA
Unmatched: GABA median CIS 1.01e-5 vs ACh 9.26e-6 (the Lin-replication direction). Matched (848 pairs): GABA > ACh with median difference 8.7e-7, Wilcoxon p = 0.0011, permutation p ≈ 1e-4, Cliff's δ = 0.111 (Fig 5). GABA fraction among top-50 chokepoints: 54% vs 52% base (no enrichment). GABA+GLUT sensitivity definition (E13): consistent with the primary analysis (see 4.6).

### 4.4b Individual chokepoints beyond degree (E14 v2, selection-bias-corrected)
Each top-50 node was tested against degree-matched peers (±10% total degree, self excluded, pools calibrated on the full tested population): **13/50 beat their degree peers (empirical p < 0.0005–0.01), 10 of the 13 are visual-system neurons**. The single most damaging neuron (rank 1: GABAergic optic-system, degree 12,444, CIS = 2.40%) shows 2.35× its peer-median CIS (p < 0.0005). Rank 3 is an octopaminergic visual centrifugal neuron of modest degree (858) with **156× its peer-median CIS** — a genuine low-degree bridge chokepoint. 22/50 are degree-driven hubs (their impact is what degree predicts). Catalogue: `e14_chokepoint_catalogue_v2.csv`; peer-pool sizes recorded (9 nodes have pools < 10 and are flagged).

### 4.5 Degree-matched analysis and null models — the decisive tests
- OLS: β₁(GABA) = −0.025 (permutation p = 0.95): after log-degree control, GABA identity carries **no** positive association with CIS.
- Degree-preserving nulls (E10B, 100 networks, exact in/out degree preservation verified per null; seeds 100+i): null δ = 0.071 ± 0.022 (range 0.042–0.121; 95th percentile 0.107) vs observed 0.098 at matched panel size (k=4); **10/100 nulls meet or exceed the observed δ → empirical p = 0.109**; median-difference statistic p = 0.78 (Fig 6). Degree-preserving rewiring reproduces the matched-pair "GABA effect." *(Reconciliation: the primary matched-pair analysis in §4.4 reads δ = 0.111 from the k=8 screening CIS; the null comparison uses the k=4 panel for observed and nulls alike, because the null statistic is computed at k=4. Both figures describe the same 848 pairs; the k=4 observed value (0.098) is the correct comparator for the null ensemble — Methods §3.10.)*
- Neighborhood composition: GABA fraction around top-50 chokepoints (16.7%) ≈ background neurons (16.9%); both ACh-dominated (~60–64%).

### 4.6 Robustness (E13-full battery)
- **Panel seeds (k=32, 4 independent source panels):** Spearman ρ vs main run = 0.96 / 0.95 / 0.91 / 0.88; top-100 four-way Jaccard = 0.63; top-50 = 0.40 (top-50 membership is panel-sensitive; top-100-level conclusions are stable).
- **Panel size:** k=8 vs k=16 ρ = 0.66, k=8 vs k=32 ρ = 0.67, **k=16 vs k=32 ρ = 0.86** — screening (k=8) is deliberately coarse; finalists agree at k≥16, validating the two-stage design.
- **Degree definition:** CIS correlates with total degree (ρ=0.58), out-degree (0.54), in-degree (0.49). Top-50 chokepoints are output-dominated (median out-degree 1,050 vs in-degree 566).
- **GABA-definition sensitivity:** GABA+GLUT as inhibitory-candidate set (967 matched pairs): δ = 0.107, Wilcoxon p = 1.1e-5 — statistically identical to the GABA-only result; conclusion unchanged under the broader definition.
- **Metric:** CIS vs reachability-drop ρ = 0.39 (related but not identical; both reported).
- **Connection tables:** no-threshold table re-analysed post-freeze (2026-09-29, E13.6b) via a chunked, memory-safe rebuild on the frozen node universe (19,765,143 pairs; peak RSS < 1 GB) with the identical k=4 panel estimator (equivalence-gated at max|ΔCIS| = 0.0 vs the frozen per-node output): the raw matched-pair effect flips sign (δ = −0.117 vs +0.098 thresholded) and lies outside the thresholded 100-null range (0.008–0.121) — the raw positive effect is not robust to the edge-inclusion rule, reinforcing the Scenario-B verdict (the null comparison is indicative only, as the nulls were built on the thresholded graph). Buhmann excluded as methodologically non-comparable (MASTER_PLAN §6.4).

### 4.7 Interpretation (Scenario B — pre-locked verdict)
Per the interpretation rule frozen in `results/final/FINAL_REPORT.md` before unblinding (Scenario B: observed statistic inside the null ensemble → effect compatible with degree-driven structure → H1 rejected; "a legitimate, publishable outcome"), the 100-null result closes Gate 4: **the matched-pair "GABA effect" is not separable from the structural null (empirical p = 0.109; median-difference p = 0.78; both statistics agree on the verdict, so Scenario C does not apply)**. What the analysis *does* establish is a novel, concrete anatomical result: whole-brain control concentrates in visual centrifugal circuitry.

## 5. Discussion

- **Main finding.** The per-neuron control hierarchy is anatomical (visual centrifugal dominance), not neurochemical: the small matched-pair GABA-vs-ACh effect lies within the range generated by degree-preserving rewiring alone (empirical p = 0.109 against 100 exact-degree-preserving nulls), and NT identity carries no residual association after log-degree control (β₁ ≈ 0). This is evidence that degree/topology suffices to account for the effect at this resolution — not proof of absence of neurotransmitter-specific control effects, which a structural, shortest-path analysis cannot detect.
- **Relation to prior work.** Replicates Lin 2024's GABA-degree association as a byproduct (our pipeline independently reproduces it); extends their degree-ordered survival curves to per-neuron, NT-conditioned impact. Concurrent work: Bates et al. 2026 (Nature; brain-and-cord connectome) analyze control circuits at whole-CNS scale on the BANC dataset — different dataset and scope, no per-neuron NT-conditioned degree-matched control-impact ranking on FAFB. Hoeller et al. 2026 (Cell) classify VIN/VPN/VCN visual-pathway groups anatomically but perform no perturbation analysis. The TiNS review (Mickels & Turner 2026) provides functional context for centrifugal feedback. **The visual-centrifugal chokepoint concentration is, to our knowledge, not previously reported as a whole-brain control phenomenon**, and the enrichment here is quantified against degree-matched nulls rather than raw base rates.
- **Mechanistic reading.** Visual centrifugal neurons (optic-lobe → central brain feedback) occupy bridging positions between the massive optic-lobe periphery and the central brain; their removal disproportionately severs eye-brain communication paths. This is a structural bottleneneck phenomenon, not an inhibitory one.
- **Structural vs functional.** All claims concern structural network control (shortest-path communication), not physiological causality.

## 6. Limitations

1. Structural connectome ≠ functional dynamics (no firing rates, delays, or state dependence).
2. NT annotation is a prediction, not a measured sign; GLUT handled separately for this reason.
3. Node removal is an abstraction of silencing.
4. Efficiency is one metric; reachability correlates only moderately (ρ=0.39), so metric choice matters (both reported).
5. FAFB v783 is one female brain, one reconstruction; v630 vs v783 and pipeline differences (Princeton vs Buhmann) not fully swept here.
6. Null comparison resolution and estimator matching: the null ensemble is computed at the k=4 panel, so the observed effect enters that comparison at k=4 as well (δ = 0.098) while the primary matched-pair statistic reads δ = 0.111 from the k=8 screening CIS (§4.5); with 100 nulls the empirical p has ~0.01 resolution near the tail, and the conclusion rests on 10/100 nulls meeting or exceeding the observed δ plus the null spread (sd 0.022) bracketing it. The OLS result (β₁ ≈ 0) independently points the same way.
7. Connection-table sensitivity was completed post-freeze (2026-09-29, E13.6b): the no-threshold graph (19,765,143 pairs) was rebuilt on the frozen node universe with a chunked loader and analysed with the identical k=4 estimator; the raw matched-pair effect reverses sign (δ = −0.117), so the primary GABA-versus-ACh contrast is not robust to the edge-inclusion rule — consistent with the pre-registered null verdict of no GABA-specific effect. The Buhmann table remains methodologically non-comparable (different reconstruction pipeline). GABA-definition sensitivity is resolved (GABA+GLUT: δ = 0.107 ≈ 0.111 primary; §4.6).

## 7. Conclusion

The 100-null degree-preserving ensemble (E10B, exact in/out degree sequences verified per null) places the matched-pair GABA-vs-ACh effect within the range of pure structural rewiring (empirical p = 0.109; median-difference p = 0.78): structural topology, not neurotransmitter identity, accounts for per-neuron control in the adult *Drosophila* brain. This is a Scenario-B rejection of the frozen hypothesis under the pre-registered pipeline — evidence that degree/topology suffices to explain the effect at this resolution, not proof that neurotransmitters play no role in circuit function beyond it. Control concentrates instead in visual centrifugal architecture — a positive anatomical discovery to pursue next.

## Data / code availability

- Data: FlyWire FAFB v783 (Princeton exports), CC BY-NC 4.0 — see `LICENSE_NOTES.md` for required citations (Dorkenwald 2024; Schlegel 2024; Matsliah 2024).
- Code: this repository (`src/`, `tests/`), pipeline reproducible via the commands in `README.md`; full manifest in `results/tables/e18_manifest.json`.

## References

*All 12 references below were re-verified at the DOI level on 2026-09-17 against Crossref/publisher records (titles, first authors, journals, volumes/pages, DOIs). The full 22-paper novelty matrix with per-entry verification status is `literature/literature_review.csv`. Corrections applied during verification: Dorkenwald pages (124–138), Schlegel exact title, Shih journal (Current Biology, not Cell Reports), Uzel pages (3443–3459.e8), Hoeller DOI, and the TiNS review identity (Mickels & Turner 2026, not 2025).*

1. Dorkenwald, S., Matsliah, A., Sterling, A.R., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature* **634**, 124–138. doi:10.1038/s41586-024-07558-y
2. Schlegel, P., Yin, Y., Bates, A.S., et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature* **634**, 139–152. doi:10.1038/s41586-024-07686-5
3. Matsliah, A., Yu, S.-c., Kruk, K., et al. (2024). Neuronal parts list and wiring diagram for a visual system. *Nature* **634**, 166–180. doi:10.1038/s41586-024-07981-1
4. Lin, A., Yang, R., Dorkenwald, S., et al. (2024). Network statistics of the whole-brain connectome of *Drosophila*. *Nature* **634**, 153–165. doi:10.1038/s41586-024-07968-y
5. Shiu, P.K., Sterne, G.R., Spiller, N., et al. (2024). A *Drosophila* computational brain model reveals sensorimotor processing. *Nature* **634**, 210–219. doi:10.1038/s41586-024-07763-9
6. Bates, A.S., Phelps, J.S., Kim, M., et al. (2026). Distributed control circuits across a brain-and-cord connectome. *Nature*. doi:10.1038/s41586-026-10735-w
7. Hoeller, J., Zhao, A., Nern, A., et al. (2026). The organization of visual pathways in the *Drosophila* brain. *Cell*. doi:10.1016/j.cell.2026.08.014
8. Mickels, C.A. & Turner, M.H. (2026). How neural feedback enables flexible visual processing in *Drosophila*. *Trends in Neurosciences* **49**(1), 63–75. doi:10.1016/j.tins.2025.10.012
9. Kunin, A.B., Guo, J., Bassler, K.E., Pitkow, X. & Josić, K. (2023). Hierarchical modular structure of the *Drosophila* connectome. *Journal of Neuroscience* **43**(37), 6384–6400. doi:10.1523/JNEUROSCI.0134-23.2023
10. Shih, C.-T., Sporns, O., Yuan, S.-L., et al. (2015). Connectomics-based analysis of information flow in the *Drosophila* brain. *Current Biology* **25**, 1249–1258. doi:10.1016/j.cub.2015.03.021
11. Uzel, K., Kato, S. & Zimmer, M. (2022). A set of hub neurons and non-local connectivity features support global brain dynamics in *C. elegans*. *Current Biology* **32**, 3443–3459.e8. doi:10.1016/j.cub.2022.06.039
12. Szilagyi, G.S., Gulyas, A., Vassy, Z., Csermely, P. & Fenyves, B.G. (2026). Signed motif analysis of the *Caenorhabditis elegans* neuronal network reveals positive feedforward and negative feedback loops. *BMC Biology* **24**. doi:10.1186/s12915-026-02641-4

## Pre-submission status (updated 2026-09-17)

1. ✅ **Full null protocol:** 100 nulls at k=4, seeds 100+i — COMPLETE; every null degree-verified; empirical p(δ) = 0.109, p(median diff) = 0.782; **Scenario B** verdict per the pre-locked rule (`results/final/e10b_final.json`; independently recomputed by `scripts/verify_e10b_final.py`).
2. ✅ **Robustness sweep:** GABA+GLUT sensitivity done (δ = 0.107 ≈ 0.111 primary); no-threshold dataset completed post-freeze (E13.6b, 2026-09-29: raw effect flips sign, δ = −0.117, reinforcing the null verdict); Buhmann table excluded as non-comparable.
3. ✅ **Novelty sweep + DOI re-verification:** 12/12 cited references verified against Crossref/publisher records on 2026-09-17 (6 corrections applied — see References); 22-paper matrix with per-entry verification status in `literature/literature_review.csv`.
4. ✅ **Region mapping + localization figure:** `e14_top50_region_mapping.csv` (top-3 input/output neuropils per top-50 chokepoint); Fig 7.
5. ☐ **Signed-motif layer** around the visual-centrifugal chokepoint set — not executed; not claim-blocking (no manuscript claim depends on motif composition; the anatomical claims rest on E12 enrichment, E14-v2 per-node tests, and E11 neighborhoods). Recorded as future work.
