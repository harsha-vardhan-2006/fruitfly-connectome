# Folder Review — FlyConnectome Dataset (FAFB v783)

**Review date:** September 15, 2026
**Folder contents:** 20 files, ~17 GB total on disk
**Dataset identity:** This is the complete public release of the FlyWire **FAFB (Full Adult Fly Brain) connectome, version 783**, as processed by the Princeton University group (Dorkenwald et al., "Whole-brain synaptic connectome of the adult fruit fly", Nature 2024). Note: no `total/` subfolder exists — the folder is flat, so this review covers the entire directory.

---

## 1. File Inventory & Classification

### Core neuron tables (one row per neuron, ~139,255 neurons)

| File | Size (disk) | Rows | Description |
|---|---|---|---|
| `neurons.csv.gz` | 1.6 MB | 139,255 | Per-neuron summary: `root_id, group, nt_type (neurotransmitter), nt_type_score, da/ser/gaba/glut/ach/oct averages` |
| `names.csv.gz` | 1.1 MB | 139,255 | Neuron names (`root_id, name, group`) — auto-assigned names like `ME.LOP.4824` for unannotated cells |
| `classification.csv.gz` | 0.9 MB | 139,255 | Cell classification: `flow` (intrinsic/afferent/efferent), `super_class, class, sub_class, hemilineage, side, nerve` |
| `consolidated_cell_types.csv.gz` | 0.9 MB | 138,327 | Consolidated cell typing: `root_id, primary_type, additional_type(s)` |
| `visual_neuron_types.csv.gz` | 0.6 MB | 95,079 | Optic-lobe neuron typing: `type, family, subsystem (Motion/Color/OFF/Object…), category, side` |
| `cell_stats.csv.gz` | 2.4 MB | 139,246 | Morphology metrics: `length_nm, area_nm, size_nm` (membrane volume) |
| `coordinates.csv.gz` | 5.1 MB | 238,909 | soma/cell-body positions: `root_id, position ("[x y z]"), supervoxel_id` |
| `column_assignment.csv.gz` | 0.4 MB | 45,528 | Optic-lobe columnar assignment: `hemisphere, type (T4b/Tm1/T5c…), column_id, x, y, p, q` |
| `connectivity_tags.csv.gz` | 0.6 MB | 134,437 | Graph-derived tags: `reciprocal, rich_club, feedforward_loop_participant, 3_cycle_participant` |

### Connectivity (synapse) tables — the heavyweight files

| File | Size (disk) | Rows | Description |
|---|---|---|---|
| `connections_princeton.csv.gz` | 65 MB | 5,342,446 | Thresholded connectome edges: `pre_root_id, post_root_id, neuropil, syn_count, nt_type` |
| `connections_princeton_no_threshold.csv.gz` | 263 MB | (~22 M) | Unthresholded edges (every 1+ synapse connection kept) |
| `connections_buhmann.csv.gz` | 202 MB | (~13 M) | Buhmann et al. synaptic-resolution connections, unthresholded |
| `neuropil_synapse_table.csv.gz` | 4.5 MB | 134,181 | Per-neuron per-neuropil synapse counts (wide format, ~100 columns) |
| `synapse_attachment_rates.csv.gz` | 3 KB | 162 | Per-neuropil proofreading/attachment quality ratios, split by `pre`/`post` side |
| `synapse_coordinates.csv.gz` | 302 MB | (~millions) | Individual synapse xyz coordinates, forward-filled `pre_root_id, post_root_id` |
| `fafb_v783_princeton_synapse_table.csv.gz` | **2.5 GB** | (~hundreds of millions) | **The master synapse table**: pre/center/post xyz, size, root IDs, neuropil. Largest file in the folder |

### Annotation & proofreading metadata

| File | Size (disk) | Rows | Description |
|---|---|---|---|
| `labels.csv.gz` | 4.5 MB | 160,728 | Human annotations: `label, user_id, position, supervoxel_id, date_created, user_name, user_affiliation` (Mala Murthy Lab, Barry Dickson Lab, etc.) |
| `processed_labels.csv.gz` | 1.0 MB | 100,091 | Cell-type labels with VFB ontology IDs (FBbt, e.g. `T4b; FBbt_00003733`), Python-list format |

### Morphology archive

| File | Size | Contents |
|---|---|---|
| `sk_lod1_783_healed.zip` | **12.9 GB** | **139,273 SWC files** (one per neuron, named `{root_id}.swc`), level-of-detail 1, "healed" (proofread & reconnected) skeleton reconstructions, zipped 2023-11-11 |

### Unrelated / stray file

| File | Size | Notes |
|---|---|---|
| `Microsoft.Services.Store.winmd` | 5 KB | **Does not belong to this dataset.** It is a PE32 .NET/DLL executable — a Windows Store metadata binary that is typically installed system-wide (e.g. in `C:\Windows\System32` or WinSxS). It looks like it was accidentally copied into this folder. Safe to delete from here; not needed for the dataset. |

---

## 2. Data Integrity Observations

1. **Row-count consistency:** The core per-neuron tables (`neurons`, `names`, `classification`) all have exactly **139,255** rows — consistent and keyed on `root_id`. `consolidated_cell_types` has 138,327 (~927 fewer) and `visual_neuron_types` 95,079 (optic-lobe neurons only, ~44k fewer), which is expected since typing is not available for every neuron.
2. **Key linkage:** `root_id` is the universal primary key across all per-neuron files, and `pre_root_id`/`post_root_id` foreign keys tie the connectome tables back to it. This is a clean, relational star schema.
3. **CRLF line endings:** Files use Windows `\r\n` line endings (visible in raw dumps) — harmless for pandas/Python, but shell tools like `cut`/`awk` may need `tr -d '\r'` handling.
4. **Forward-filled IDs:** `synapse_coordinates.csv.gz` uses blank cells to repeat the previous `pre_root_id`/`post_root_id` — a compact but fragile format (a single dropped row corrupts all subsequent groupings). Handle with `ffill()` in pandas, not naive CSV parsing.
5. **Quoted lists:** `processed_labels.csv.gz` stores Python-list-like strings (`['T4b; FBbt_00003733']`) with embedded commas — requires `ast.literal_eval` after standard CSV parsing.
6. **Bracketed vectors:** `coordinates.csv.gz` stores positions as stringified numpy arrays (`"[352484 175164 229040]"`), needing string parsing before numeric use.

---

## 3. Analysis-Ready Notes

- **Fast path for most analyses:** use `connections_princeton.csv.gz` (5.3 M edges, thresholded) + the per-neuron tables — this fits easily in memory.
- **Heavy files** (`fafb_v783_princeton_synapse_table.csv.gz` at 2.5 GB compressed, `synapse_coordinates.csv.gz` at 302 MB) should be streamed in chunks (`pd.read_csv(..., chunksize=...)`) or loaded with Polars/DuckDB rather than pandas `read_csv` in one go.
- **Morphology:** the 139,273 SWC skeletons in the zip pair 1:1 with `root_id`s in the tables. Extract selectively (`unzip -o sk_lod1_783_healed.zip '720575940596125868.swc'`) rather than extracting all 33 GB at once.
- **`synapse_attachment_rates.csv.gz` is a quality-control table** — consult `proof_ratio` per neuropil before trusting synapse counts in low-proofread regions.
- **Neurotransmitter confidence:** `nt_type_score` in `neurons.csv.gz` should be filtered (e.g. > 0.5) before drawing NT-specific conclusions.

## 4. Recommended Actions

1. **Remove the stray `Microsoft.Services.Store.winmd`** — it is unrelated to the dataset (it's a Windows system binary).
2. Add a `README.md` or `manifest.csv` with sha256 checksums so the 17 GB of data can be verified after transfers.
3. Consider whether both `connections_princeton.csv.gz` and `connections_princeton_no_threshold.csv.gz` (and the Buhmann variant) are all needed — the unthresholded variants are 470 MB combined and derivable/available separately.
4. If the 2.5 GB synapse table is queried often, convert to Parquet for ~5-10x faster columnar access.
5. Add `labels.csv.gz` provenance: it contains personal names/affiliations of annotators — fine for research use, but note it if the folder will be redistributed.

---

## 5. Summary

This is a complete, well-organized copy of the **FlyWire FAFB v783 Princeton connectome release**: ~139k neurons, ~5.3M thresholded connections, ~hundreds of millions of synapses, and 139k SWC skeleton files, totaling ~17 GB. The tables form a clean relational schema keyed on `root_id`. The only anomaly is a stray Windows Store binary (`Microsoft.Services.Store.winmd`) that should be removed. Data formats are standard CSV+gzip with a few parsing quirks (CRLF, forward-filled IDs, quoted lists) worth handling in downstream code.
