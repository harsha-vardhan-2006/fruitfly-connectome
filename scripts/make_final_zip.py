#!/usr/bin/env python
"""Build the final submission ZIP (code + results + paper; NO raw dataset).

Run:  py scripts/make_final_zip.py
Output: dist/flybrain_connectome_control_FINAL.zip
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "flybrain_connectome_control_FINAL.zip"

INCLUDE_DIRS = ["src", "tests", "scripts", "literature", "paper",
                "results", "reproducibility", "configs"]
INCLUDE_FILES = ["README.md", "MASTER_PLAN.md", "RESEARCH_LOG.md",
                 "QC_STATUS.md", "research_plan.md", "review.md",
                 "LICENSE_NOTES.md", "requirements.txt", "CITATION.cff"]
SKIP_PARTS = {"__pycache__", ".pytest_cache", "dist", ".ipynb_checkpoints"}
MAX_FILE_MB = 80  # safety valve; results tables are far below this


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    n_files = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for d in INCLUDE_DIRS:
            base = ROOT / d
            if not base.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [x for x in dirnames if x not in SKIP_PARTS]
                for fn in filenames:
                    p = Path(dirpath) / fn
                    if p.stat().st_size > MAX_FILE_MB * 1_000_000:
                        print(f"skip (> {MAX_FILE_MB} MB): {p.relative_to(ROOT)}")
                        continue
                    z.write(p, p.relative_to(ROOT))
                    n_files += 1
        for fn in INCLUDE_FILES:
            p = ROOT / fn
            if p.exists():
                z.write(p, fn)
                n_files += 1
    mb = OUT.stat().st_size / 1_000_000
    print(f"OK {OUT.relative_to(ROOT)}  files={n_files}  size={mb:.1f} MB")
    # hard guarantee: no raw dataset inside
    with zipfile.ZipFile(OUT) as z:
        bad = [n for n in z.namelist()
               if n.endswith(".csv.gz") and "/" not in n
               or n.endswith(".zip")
               or n.startswith(("connections_", "fafb_", "synapse_",
                                "neurons.csv.gz", "sk_lod1"))]
    print("raw-dataset leak check:", "CLEAN" if not bad else f"LEAK {bad}")


if __name__ == "__main__":
    main()
