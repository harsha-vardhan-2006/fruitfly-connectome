# FAFB v783 Research Plan
## From dataset verification → literature landscape → research gaps → hypotheses → one designed experiment

**Date:** September 15, 2026
**Companion file:** `review.md` (technical audit of the raw files — file integrity, formats, quirks)
**Status of this document:** Steps 1–3 report on the *local* copy; Steps 4–8 are desk research + design. **No dataset file was modified.**

---

# Part 1 — Verification: exactly what every file contains

## 1.1 Verified facts (run against the local bytes, not assumed)

**Core per-neuron tables — clean and internally consistent:**
- `neurons`, `names`, `classification` each have **exactly 139,255 data rows**. `root_id` is unique in all five per-neuron tables (0 duplicates found in `neurons`, `names`, `classification`, `consolidated_cell_types`, `visual_neuron_types`).
- `root_id`s are 18-digit, sorted ascending in every per-neuron table; max ID observed `720575940661339777`.
- `classification.side` is fully populated: **69,959 left, 69,093 right, 173 center, 30 blank** (sums to 139,255).
- `neurons.nt_type` empty for untyped neurons; `nt_type_score` present for typed ones.

**Edge tables — clean on ID structure:**
- `connections_princeton` (5,342,446 rows) and `connections_buhmann_no_threshold`: both endpoints of sampled edges conform exactly to the 18-digit ID pattern `720575940` + 9 digits. **0 malformed IDs** in a 200k-line sample of each.
- Edge list is **pre-thresholded by neuropil** (same pair can appear once per neuropil).

**⚠ Master synapse table — one real artifact found:**
- `fafb_v783_princeton_synapse_table.csv.gz`: headers are `pre_root_id_720575940` / `post_root_id_720575940` and values carry only the 9-digit suffix (e.g. `610757204`). **The full ID must be reconstructed as `720575940` + suffix.** Anyone naive-loading this file and joining on it will silently produce garbage joins. This is the single most dangerous gotcha in the folder.
- `neuropil` column is sometimes empty for a synapse (unassigned neuropil).

**Morphology archive:**
- `sk_lod1_783_healed.zip` = 139,273 SWC files, generated 2023-11-11 with `navis`, units nanometers, standard 8-column SWC. Sample file verified readable (`720575940596125868.swc`).
- **18 SWCs are orphans**: IDs like `720575940590515268` and `720575940591418150` appear in the zip but in **none** of the metadata tables (probably fragments superseded by later segment merges). Conversely the tables cover ~139,255 neurons vs 139,273 skeletons — the overlap is ~99.99% but not exact; joins must be inner joins.

**Encoding quirks (carried over from review.md, all confirmed):** CRLF line endings, forward-filled `pre/post_root_id` in `synapse_coordinates.csv.gz` (pandas `ffill()` required), Python-literal list strings in `processed_labels.csv.gz` (`ast.literal_eval`), stringified numpy vectors in `coordinates.csv.gz` (`[x y z]` format).

## 1.2 What each file contains (one-line, verified)

| File | Grain | Key columns | Verified role |
|---|---|---|---|
| `neurons.csv.gz` | 1 row/neuron | root_id, group, nt_type, nt_type_score, da/ser/gaba/glut/ach/oct averages | Neurotransmitter + group per neuron |
| `names.csv.gz` | 1 row/neuron | root_id, name, group | Auto-name (ME.2982) or curated name |
| `classification.csv.gz` | 1 row/neuron | root_id, flow, super_class, class, sub_class, hemilineage, side, nerve | Hierarchical class + side |
| `consolidated_cell_types.csv.gz` | 1 row/typed neuron | root_id, primary_type, additional_type(s) | Best-known type per neuron |
| `visual_neuron_types.csv.gz` | 1 row/OL neuron | root_id, type, family, subsystem, category, side | Optic-lobe typing (Motion/Color/OFF/Object) |
| `cell_stats.csv.gz` | 1 row/neuron | root_id, length_nm, area_nm, size_nm | Morphometrics |
| `coordinates.csv.gz` | 1 row/cell body | root_id, position "[x y z]", supervoxel_id | Soma location |
| `column_assignment.csv.gz` | 1 row/columnar neuron | root_id, hemisphere, type, column_id, x, y, p, q | Optic-lobe columnar coordinates |
| `connectivity_tags.csv.gz` | 1 row/neuron | root_id, connectivity_tag (CSV-in-cell) | rich_club / reciprocal / loop participation |
| `connections_princeton.csv.gz` | 1 row/pair×neuropil | pre_root_id, post_root_id, neuropil, syn_count, nt_type | **Thresholded connectome (primary analysis table)** |
| `connections_princeton_no_threshold.csv.gz` | 1 row/pair×neuropil | same | ≥1-synapse edges |
| `connections_buhmann_no_threshold.csv.gz` | 1 row/pair×neuropil | same | Buhmann cross-check set |
| `neuropil_synapse_table.csv.gz` | 1 row/neuron | root_id + ~100 neuropil count columns | Precomputed in/out synapse totals per neuropil |
| `synapse_attachment_rates.csv.gz` | 1 row/neuropil×side | neuropil, count_total, count_proof, proof_ratio, side | Proofread quality QC |
| `synapse_coordinates.csv.gz` | 1 row/synapse | pre/post_root_id (ffilled), x, y, z | Individual synapse locations |
| `fafb_v783_princeton_synapse_table.csv.gz` | 1 row/synapse | pre/ctr/post xyz, size, mangled root IDs, neuropil | Master synapse table (2.5 GB) |
| `labels.csv.gz` | 1 row/annotation | root_id, label, user_id, position, supervoxel_id, date, user_name, user_affiliation | Human annotations (curator-level) |
| `processed_labels.csv.gz` | 1 row/neuron | root_id, processed_labels (list) | Curated labels + FBbt ontology IDs |
| `sk_lod1_783_healed.zip` | 1 SWC/neuron | — | Skeletons, LOD1, healed |

---

# Part 2 — Relationship map (join graph via `root_id`)

```
                        ┌───────────────────────────── CORE ENTITY: root_id (139,255 neurons) ─────────────────────────────┐
                        │                                                                                                   │
  ATTRIBUTE TABLES      │                     CONNECTIVITY TABLES                       SUPPORTING SPATIAL  │
  neurons ──────────────┤   connections_princeton (pre→post, thresholded)  ◄── primary    coordinates (soma xyz)  │
  names ────────────────┤   connections_princeton_no_threshold                            cell_stats            │
  classification ───────┤   connections_buhmann_no_threshold                              column_assignment     │
  consolidated_cell_types┤        │ all join on pre_root_id / post_root_id = root_id       synapse_coordinates   │
  visual_neuron_types ──┤        ▼                                                                              │
  connectivity_tags ────┘   fafb_v783_princeton_synapse_table  ⚠ mangled IDs (prefix 720575940)                 │
                            neuropil_synapse_table (per-neuron wide)                                             │
                            synapse_attachment_rates (QC, join on neuropil only)                                 │
                                                                                                                                 │
  ANNOTATION: labels ──────────── processed_labels ──────────── SWC zip (sk_lod1_783_healed.zip, 18 orphans) ────┘
```

**Join rules (write these into your loader once):**
1. `root_id` inner-joins all per-neuron attribute tables; inner-join semantics matter (typed tables cover only subsets: 138,327 and 95,079).
2. Edge tables: aggregate by (pre, post) summing `syn_count` across neuropils to get a brain-wide pair weight.
3. Master synapse table: reconstruct IDs `str(720575940) + suffix.zfill(9)` before any join; verify against `connections_princeton` counts per pair as a sanity check.
4. SWC zip: extract selectively by root_id; 18 zip-only IDs must be excluded (or investigated) rather than assumed present.
5. `synapse_attachment_rates` joins on `neuropil` — the only non-root_id key — used to weight confidence per region.

---

# Part 3 — Essential vs optional files

**Tier 1 — Essential for essentially any network-level study (~70 MB):**
`neurons`, `classification`, `names`, `consolidated_cell_types`, `connections_princeton`, `connectivity_tags`, `synapse_attachment_rates`.

**Tier 2 — Essential for visual-system / optic-lobe studies (+6 MB):**
`visual_neuron_types`, `column_assignment`, `cell_stats`, `coordinates`.

**Tier 3 — Situational (large):**
- `fafb_v783_princeton_synapse_table.csv.gz` (2.5 GB): only needed for synapse-precision spatial questions (column-level receptive fields, synaptic microcircuits at synapse resolution). Reconstructable aggregates exist in Tier 1.
- `synapse_coordinates.csv.gz` (302 MB): synapse spatial stats, layered depth profiles.
- `connections_princeton_no_threshold.csv.gz` (263 MB) + `connections_buhmann_no_threshold.csv.gz` (202 MB): only for sensitivity analyses on threshold choices or cross-validation of the Buhmann vs Princeton pipelines.
- `sk_lod1_783_healed.zip` (12.9 GB): morphology-driven questions (cable length in compartments, dendritic vs axonal segregation, bio-realistic compartment models). Extract selectively, never all at once.

**Tier 4 — Reference/metadata (tiny, keep):** `labels`, `processed_labels`, `neuropil_synapse_table`, `Microsoft.Services.Store.winmd` (**delete — unrelated Windows binary**).

**Bottom line:** a full connectome-network paper needs **only ~70 MB** of this folder; the 17 GB is dominated by files you should treat as on-demand reference material.

---

# Part 4 — FlyWire licensing & citation requirements

- **License:** FlyWire public data products are released under **CC BY-NC 4.0** (attribution + non-commercial). The Zenodo connectivity archive is additionally listed cc-by-4.0 for the connectivity subset; treat the umbrella rule as CC BY-NC 4.0 and check the exact record you redistribute from. Commercial use is not permitted without separate permission.
- **Required citations (all three — license condition, not courtesy):**
  1. Dorkenwald, S. et al. *Neuronal wiring diagram of an adult brain.* **Nature 634, 124–144 (2024)** — the connectome itself.
  2. Schlegel, P. et al. *Whole-brain annotation and multi-connectome cell typing quantifies circuit stereotypy in Drosophila.* **Nature 634, 153–170 (2024)** — the cell-typing/annotation product.
  3. Matsliah, A. et al. *Neuronal parts list and wiring diagram for a visual system.* **Nature (2024)** — if any optic-lobe data (i.e. `visual_neuron_types`, `column_assignment`) is used.
- **Version pinning:** state "FAFB v783, Princeton pyCROU-style exports" in methods; the version number is mandatory for reproducibility because FlyWire re-releases (v630, v783, …) change root IDs via ongoing merges.
- **Redistribution:** derived aggregate results are fine; wholesale redistribution of raw products should point to the canonical FlyWire/Zenodo sources rather than re-hosting.

---

# Part 5 — What has already been done with these exact products (the "occupied territory")

All of the following have already been published using FAFB v783 (or its immediate predecessors):

1. **The connectome + parts list** (Dorkenwald 2024; Schlegel 2024; Matsliah 2024) — circuit motifs, cell typing (8,557 types), stereotypy quantification, optic-lobe wiring rules and metabrain-wide visual partition.
2. **Whole-brain network statistics** — Lin et al. 2024 (PMC11446825): rich-club, ~30% highly connected core, recurrence, degree distributions, hubs. **Generic network statistics of the whole brain are taken.**
3. **Central-complex circuit analysis** — Hulse et al. 2021 (plus v783-era updates): ring attractors, navigation motifs.
4. **Optic-lobe visual circuits** — Matsliah 2024; T4/T5 motion circuit literature (Takemura 2017 + FAFB-era work); orientation maps via spiking simulation (NeurIPS 2025); optic-flow large-neuron survey (Zhao 2024, eLife).
5. **Brain-wide visual projection analysis** — bioRxiv Feb 2026 "Connectome analysis reveals brainwide visual processing…" — long-range OL→central-brain visual routing.
6. **Whole-brain dynamical simulation** — LeLE/Fly-connectomic Graph Model (arXiv 2026, whole-body locomotion control); several simulation-first frameworks (NeurIPS 2025 orientation maps).
7. **Synapse detection improvements** — bioRxiv Jul 2025 "New Synapse Detection in the Whole-Brain Connectome of Drosophila" — the synapse table itself is being superseded by a newer detection round.

**Corollary:** any project whose pitch is "train a model on 17 GB and see what it finds" or "compute the connectome's network statistics" is already scooped. Novelty must come from *questions the original teams did not ask*, not from the data's existence.

---

# Part 6 — Research gaps (what remains genuinely unclaimed)

**G1 — Left–right asymmetry at cell-type resolution.** Lin 2024 characterized global topology; Schlegel 2024 quantified stereotypy *across* animals via the Buhmann FlyEM hemisphere. Nobody has published a systematic, per-cell-type **within-animal L–R asymmetry atlas** on the full FAFB (69,959 L vs 69,093 R neurons, with the 173 midline cells as a built-in control). Asymmetry exists in biology (e.g. asymmetric learning-side usage, lateralized visual behaviors), but a full-brain quantitative asymmetry atlas does not exist.

**G2 — Connectivity-tag semantics as a null model.** `connectivity_tags.csv.gz` labels every neuron (rich_club, reciprocal, feedforward_loop_participant, 3_cycle_participant). These are published phenomena (Lin 2024), but **no one has derived the degree-preserving null expectations for *every* tag jointly** — e.g. how much of rich-club reciprocity is just degree + class-mixing? A single rigorous "tags vs null" paper (motif-level, per superclass) is absent.

**G3 — Neurotransmitter-scored bipartite interaction structure.** `neurons.nt_type` + per-edge `nt_type` in `connections_princeton` gives an NT-labeled directed graph — excitation/inhibition per edge with confidence scores. Published analyses treat NT types mostly descriptively; **systematic E/I network structure** (in-degree/out-degree per class, E→I vs I→I motif enrichment, inhibition hotspots per neuropil, NT switch points along pathways) is not a published whole-brain paper.

**G4 — Hemilineage as an organizing principle.** `classification.hemilineage` exists but hemilineage-level connectivity organization (do hemilineage siblings preferentially interconnect? is hemilineage a better predictor of connectivity than class?) is unexplored at whole-brain scale.

**G5 — Columnar vs non-columnar connectivity in the optic lobe.** `column_assignment` gives precise column IDs (x, y, p, q) for 45,528 neurons. Matsliah 2024 did wiring rules; a **column-to-column effective connectivity map** (synapse-weighted, per layer/type) feeding a directional-motion simulation is partially occupied (NeurIPS 2025 orientation maps) — the *unclaimed* slice is column-level variability statistics, which overlaps G1.

**G6 — Provenance-aware sub-connectome reliability.** `synapse_attachment_rates` + `labels` (curator identity, dates) allow per-region, per-annotator reliability modeling. Nobody has published an uncertainty-calibrated connectome analysis (which claims survive proofread-quality weighting?). Niche but citable, and a genuinely useful community tool.

**G7 — The Buhmann↔Princeton disagreement map.** Two independent reconstruction/curation pipelines shipped edge lists. Their **systematic disagreement** (which cell types, neuropils, and connection strengths diverge) is unpublished and directly actionable for anyone using v783.

---

# Part 7 — Five hypotheses (novel, testable with *these local files*)

**H1 (from G1):** *Within-animal L–R asymmetry in the fly brain is concentrated in a small set of cell types and concentrated in neuropils serving lateralized behaviors; for most types, asymmetry is statistically indistinguishable from sampling noise.* — Quantitative, atlas-producing, controllable (midline cells, degree-matched nulls).

**H2 (from G2):** *Rich-club reciprocity is largely a degree artifact: after degree- and class-preserving randomization, the excess reciprocity of rich-club members shrinks by >50%, and the residual is concentrated in specific sensory neuropils.* — Tests the interpretation of an already-published headline finding; results either way are publishable.

**H3 (from G3):** *Inhibition is not uniformly distributed but organized into a small number of "inhibitory chokepoints" — specific cell classes through which a disproportionate share of all inhibitory synapses flow — and these chokepoints sit at pathway branch points between sensory and central neuropils.* — Whole-brain E/I cartography; directly ties NT labels to topology.

**H4 (from G4):** *Hemilineage siblings show above-chance connection probability with each other, and hemilineage identity predicts connectivity profiles better than cell class for untyped neurons.* — Uses `classification.hemilineage` + the untyped-neuron majority; touches the "cell type" definition debate in Schlegel 2024.

**H5 (from G7):** *Pipeline disagreement (Buhmann vs Princeton) is not random: it concentrates on specific synapse-size classes and neuropils, and disagreement rate predicts downstream conclusions' robustness.* — Meta-scientific, methodological impact.

---

# Part 8 — Chosen hypothesis and experimental design

**Selected: H3 — "Inhibitory chokepoints: whole-brain cartography of neurotransmitter-resolved control flow in the fly brain."**

**Why this one:**
- **Data fit:** needs exactly Tier-1 files (~70 MB): `connections_princeton` (has per-edge `nt_type`), `neurons` (per-neuron NT + scores), `classification` (cell classes), `synapse_attachment_rates` (QC weighting). No 2.5 GB file required.
- **Gap clarity:** Lin 2024 owns topology; Schlegel 2024 owns types; nobody owns **NT-resolved whole-brain flow structure**.
- **Realistic single-author compute:** 5.3M edges → networkx/graph-tool on a laptop; hours, not GPU-weeks.
- **Falsifiable and two-sided:** chokepoints either exist (positive result with a map) or don't (equally publishable null with a null-model contribution).

**Experimental design:**

**Step 0 — Build the analysis graph.**
- Collapse `connections_princeton` to pair level: `W(pre, post) = Σ syn_count`, keep NT = mode/consistent-majority of per-neuropil nt_type; attach `nt_type_score` and drop edges from neurons with NT score < 0.5 (sensitivity analysis at 0.3/0.7).

**Step 1 — Define E/I.** Map nt_type ∈ {ACH → excitatory; GABA, GLUT (with ionotropic ambiguity flagged), others → per conventions} following Schlegel 2024 conventions; report GLUT separately since its sign is context-dependent.

**Step 2 — Inhibitory load metrics.** For each neuron *i*: inhibitory in-fraction, inhibitory out-fraction, and **inhibitory betweenness** (share of all shortest paths whose intermediary edges are inhibitory). Define chokepoint score `C(i) = betweenness_Δ when inhibitory edges touching i are removed`, computed on the thresholded graph.

**Step 3 — Null models (the credibility core).**
- Degree-preserving edge swaps (Maslov–Sneppen), 1,000 replicates.
- Class- and neuropil-preserving configuration model (rewire within superclass × neuropil blocks).
- Report z-scores and FDR-corrected q-values per neuron/class; chokepoint = q < 0.01 AND effect size > threshold.

**Step 4 — Robustness.**
- Recompute on `connections_princeton_no_threshold`; cross-check on `connections_buhmann_no_threshold` (this also pre-answers H5 for the chokepoint set).
- Weight edges by `synapse_attachment_rates.proof_ratio` of the edge's neuropil; verify chokepoint stability under QC weighting.
- Split-half by neuropil-L vs neuropil-R hemispheres.

**Step 5 — Biological grounding.**
- Annotate chokepoints with `classification`, `consolidated_cell_types`, `visual_neuron_types` (are they known modality hubs — e.g. lateral accessory lobe, mushroom body input circuits?), `connectivity_tags` (do they overlap rich_club?), and test positional enrichment via `coordinates`.
- Deliverables: (a) ranked chokepoint table with FBbt ontology cross-refs from `processed_labels`; (b) per-neuropil E/I flow map; (c) null-model toolkit released as a package.

**Timeline & feasibility:** Week 1: loaders + graph build + QC joins. Week 2: metrics + nulls. Week 3: robustness + buhmann cross-check. Week 4: figures + methods writeup. All on CPU; disk never exceeds ~400 MB of working data.

**Anticipated reviewer objections (pre-empted):** NT sign of GLUT → handled by separate reporting; syn_count ≠ strength → report binary-edge sensitivity; incomplete proofreading → QC weighting + hemisphere split; threshold sensitivity → both edge lists.

**Expected outcomes:** Either (a) a small (n ≈ 50–200 neuron classes) set of statistically robust inhibitory chokepoints with clear anatomical identity — a new whole-brain organizing principle — or (b) demonstration that inhibitory control is distributed, contradicting the chokepoint framing and constraining models of E/I balance. Both outcomes are novel relative to Part 5's occupied territory.

---

# Appendix — Reproducibility checklist

- Pin: FAFB v783 (Princeton exports), file SHA256s to be recorded before first analysis run (see review.md recommendation).
- Cite: Dorkenwald 2024; Schlegel 2024; Matsliah 2024 (license condition).
- Handle: master synapse table ID reconstruction (`720575940` + 9-digit suffix); CRLF; ffilled synapse_coordinates; 18 orphan SWCs excluded from joins; inner joins on typed tables.
- Do not modify raw files; all outputs go to a separate `analysis/` directory.
