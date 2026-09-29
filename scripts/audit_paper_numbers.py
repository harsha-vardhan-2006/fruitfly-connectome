#!/usr/bin/env python
"""Citation-resolution + scientific-language audit for the paper package.

Checks:
1. every \\cite{...} key resolves to paper/references.bib; every bib entry
   has a DOI and is cited at least once;
2. prohibited overclaim terms are absent (unless in the allowed
   "unsupported interpretation" framing files/lines, reported for review);
3. canonical numbers appear in the rendered production HTML.

Run:  py scripts/audit_paper_numbers.py
"""
from __future__ import annotations

import re
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "paper"

BANNED = [
    r"\bproves\b", r"\bproved\b", r"\bcauses\b", r"\bcaused\b",
    r"functionally essential", r"functional bottleneck", r"causal bottleneck",
    r"controls behavior", r"controls the brain", r"functionally indispensable",
    r"first study", r"worldwide first", r"groundbreaking",
]
ALLOWED_CONTEXT = ("not", "cannot", "does not", "no claim", "unsupported")


def main() -> None:
    bib = (P / "references.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"@\w+\{(\w+),", bib))
    entries = re.findall(r"@\w+\{(\w+),(.*?)(?=@\w+\{|\Z)", bib, re.S)
    bad_doi = [k for k, body in entries
               if not re.search(r"doi\s*=\s*\{10\.", body)]
    doi_ok = not bad_doi
    if bad_doi:
        print("entries missing DOI:", bad_doi)
    print("bib entries:", len(bib_keys))
    print("all entries DOI-bearing:", doi_ok)

    cited: set[str] = set()
    for f in sorted((P / "sections").glob("*.tex")) + [P / "manuscript.tex"]:
        for group in re.findall(r"\\cite\{([^}]*)\}", f.read_text(encoding="utf-8")):
            cited |= {k.strip() for k in group.split(",")}
    print("cited keys:", len(cited))
    print("undefined citations:", sorted(cited - bib_keys) or "NONE")
    print("uncited bib entries:", sorted(bib_keys - cited) or "NONE")

    # language audit (paragraph-based to tolerate line wrapping)
    hits = []
    for f in sorted((P / "sections").glob("*.tex")) + [P / "manuscript.md"]:
        text = f.read_text(encoding="utf-8")
        paras = re.split(r"\n\s*\n", text)
        for j, para in enumerate(paras, 1):
            low = " ".join(para.lower().split())
            for pat in BANNED:
                m = re.search(pat, low)
                if m:
                    framed = any(c in low for c in ALLOWED_CONTEXT)
                    hits.append((f.name, j, pat,
                                 "framed-negative" if framed else "REVIEW"))
    print("\nlanguage audit hits:", len(hits))
    for h in hits:
        print("  ", h)

    # canonical numbers in the production HTML rendering
    prod = (P / "manuscript_production.html").read_text(encoding="utf-8")
    canonical = ["138,584", "3,732,460", "139,255", "26.8", "0.083", "848",
                 "0.111", "0.0011", "0.098", "0.0979", "0.071", "0.022",
                 "0.109", "0.782", "1.21", "2.63", "5.3", "2.47", "2.15",
                 "0.27", "13/50", "156", "2.40", "0.107", "0.63", "0.40",
                 "0.86", "3,518"]
    missing = [c for c in canonical if c not in prod]
    print("\ncanonical numbers missing from production PDF HTML:", missing or "NONE")

    ok = (not (cited - bib_keys)) and doi_ok and not missing
    print("\nAUDIT RESULT:", "PASS" if ok else "REVIEW NEEDED")


if __name__ == "__main__":
    main()
