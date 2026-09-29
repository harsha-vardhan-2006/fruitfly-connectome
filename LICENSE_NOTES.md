# LICENSE NOTES — FlyWire FAFB v783

| Field | Value |
|---|---|
| Dataset | FlyWire FAFB v783 (Princeton exports) |
| Source | flywire.ai / codex.flywire.ai; Zenodo connectivity record 10676866 |
| Version | v783 |
| License | **CC BY-NC 4.0** (attribution + non-commercial). Zenodo connectivity subset additionally listed cc-by-4.0 — treat CC BY-NC 4.0 as the umbrella rule and verify the exact record before any redistribution. |
| Commercial use | Not permitted without separate permission. |
| Local copy verified | 2026-09-15 (see `review.md`, `research_plan.md`) |

## Required citations (license condition — all three)

1. Dorkenwald, S. et al. *Neuronal wiring diagram of an adult brain.*
   **Nature 634, 124–144 (2024).** — the connectome.
2. Schlegel, P. et al. *Whole-brain annotation and multi-connectome cell
   typing quantifies circuit stereotypy in Drosophila.*
   **Nature 634, 153–170 (2024).** — cell types / NT annotations.
3. Matsliah, A. et al. *Neuronal parts list and wiring diagram for a visual
   system.* **Nature (2024).** — required when optic-lobe files
   (`visual_neuron_types`, `column_assignment`) are used.

## Methods sentence (template)

> Connectivity and cell annotation were obtained from FlyWire's FAFB v783
> whole-brain connectome (Princeton exports), used under CC BY-NC 4.0
> (Dorkenwald et al. 2024; Schlegel et al. 2024; Matsliah et al. 2024).
> Raw files were not modified; all processing is scripted and reproducible.

## Redistribution policy

- Derived aggregates and figures: permitted with attribution.
- Wholesale re-hosting of raw products: avoid; link to canonical
  FlyWire/Zenodo sources instead.
- `labels.csv.gz` contains annotator names/affiliations — do not
  redistribute the raw annotation table without checking terms.

## Before submission

- Re-verify license text at flywire.ai (citation guidelines page) — terms
  may have been updated since this copy was made.
- Record SHA256 checksums of all raw files used — DONE: 19/19 recorded in
  `results/tables/e18_manifest.json` (`dataset.raw_file_sha256`).
