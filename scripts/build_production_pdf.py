#!/usr/bin/env python
"""Build paper/manuscript_production.pdf — an inspection rendering of the
LaTeX manuscript for environments without a TeX toolchain.

Assembles title, abstract, all section .tex files, figures, table .tex
files, and references into one HTML page (small LaTeX-to-HTML subset
converter), then prints to PDF via Edge headless. The submission-grade
source remains paper/manuscript.tex.

Run:  py scripts/build_production_pdf.py
"""
from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"

SECTIONS = ["abstract", "introduction", "related_work", "methods",
            "results", "discussion", "limitations", "conclusion"]
SEC_TITLES = {
    "abstract": "", "introduction": "1. Introduction",
    "related_work": "2. Related Work", "methods": "3. Materials and Methods",
    "results": "4. Results", "discussion": "5. Discussion",
    "limitations": "6. Limitations", "conclusion": "7. Conclusion",
}
FIG_META = {  # number -> (file, label used in text)
    1: ("Figure1", "fig:overview"), 2: ("Figure2", "fig:network"),
    3: ("Figure3", "fig:gaba"), 4: ("Figure4", "fig:degctrl"),
    5: ("Figure5", "fig:nullproc"), 6: ("Figure6", "fig:nulls"),
    7: ("Figure7", "fig:vc"),
}
TITLE = ("Neuron-Level Structural Control Impact Reveals Visual-Centrifugal "
         "Chokepoints in the <i>Drosophila</i> Connectome")


def tex_inline(s: str) -> str:
    """Convert the LaTeX subset used in this manuscript to HTML text."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\\emph\{([^{}]*)\}", r"<i>\1</i>", s)
    s = re.sub(r"\\textit\{([^{}]*)\}", r"<i>\1</i>", s)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"<b>\1</b>", s)
    s = re.sub(r"\\texttt\{([^{}]*)\}", r"<code>\1</code>", s)
    s = re.sub(r"\$\\sim\$", "~", s)
    s = s.replace("$\\rightarrow$", " -> ").replace("\\rightarrow", " -> ")
    s = s.replace("$\\pm$", "+/-").replace("\\pm", "+/-")
    s = s.replace("$\\times$", "x").replace("\\times", "x")
    s = s.replace("$\\delta$", "delta").replace("\\delta", "delta")
    s = s.replace("$\\beta_1$", "beta1").replace("\\beta_1", "beta1")
    s = s.replace("$\\rho$", "rho").replace("\\rho", "rho")
    s = s.replace("$\\ll$", " << ")
    s = s.replace("$\\geq$", ">=").replace("\\geq", ">=")
    s = s.replace("$\\leq$", "<=").replace("\\leq", "<=")
    s = s.replace("$\\approx$", "~=").replace("\\approx", "~=")
    s = s.replace("\\%", "%").replace("~$", "")
    s = s.replace("$10^{-4}$", "1e-4").replace("$^{-1}$", "^-1")
    s = re.sub(r"\$10\^\{-?(\d+)\}\$", r"1e-\1", s)
    # strip remaining $...$ math markers, keep content readable
    s = s.replace("$", "")
    s = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\log_\{?10\}?", "log10", s)
    s = re.sub(r"\\cite\{([^}]*)\}", lambda m: "[" + ",".join(
        w.strip() for w in m.group(1).split(",")) + "]", s)
    s = re.sub(r"\\ref\{([^}]*)\}", r"(\1)", s)
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\paragraph\{([^}]*)\}", r"<b>\1</b>", s)
    s = re.sub(r"\\noindent", "", s)
    s = re.sub(r"\\item", "&bull;", s)
    s = re.sub(r"\\S", "S", s)
    return s


def tex_to_html(raw: str) -> str:
    out, in_list = [], None  # enumerate | itemize
    for line in raw.splitlines():
        st = line.strip()
        if st.startswith("\\section{"):
            continue  # headings added by caller
        if st.startswith("\\begin{abstract}") or st.startswith("\\end{abstract}"):
            continue
        if st.startswith("\\begin{enumerate}"):
            out.append("<ol>"); in_list = "ol"; continue
        if st.startswith("\\end{enumerate}"):
            out.append("</ol>"); in_list = None; continue
        if st.startswith("\\begin{itemize}"):
            out.append("<ul>"); in_list = "ul"; continue
        if st.startswith("\\end{itemize}"):
            out.append("</ul>"); in_list = None; continue
        if st.startswith("\\subsection{"):
            m = re.match(r"\\subsection\{(.+)\}", st)
            out.append(f"<h3>{tex_inline(m.group(1))}</h3>"); continue
        if not st:
            out.append("</p><p>" if out and out[-1] == "@P@" else "")
            out.append("@P@")
            continue
        out.append(tex_inline(st))
    body = " ".join(x for x in out if x != "@P@")
    body = re.sub(r"&bull;", "<li style='margin-left:1.2em'>", body)
    body = re.sub(r"</p><p>", "</p>\n<p>", body)
    return f"<p>{body}</p>"


def extract_captions() -> dict[int, str]:
    tex = (P / "manuscript.tex").read_text(encoding="utf-8")
    caps = {}
    for m in re.finditer(r"\\caption\{(.*?)\}\s*\\label", tex, re.S):
        block = m.group(1)
        # figure number from the following includegraphics
        tail = tex[m.end():m.end() + 400]
        fm = re.search(r"Figure(\d)", tail)
        if fm:
            caps[int(fm.group(1))] = tex_inline(re.sub(r"\s+", " ", block))
    return caps


def tex_table_to_html(path: Path) -> str:
    t = path.read_text(encoding="utf-8")
    cap = re.search(r"\\caption\{(.*?)\}\\label", t, re.S)
    cap_html = tex_inline(re.sub(r"\s+", " ", cap.group(1))) if cap else ""
    rows_html = []
    for line in t.splitlines():
        st = line.strip()
        if st.endswith("\\\\") and "&" in st:
            cells = [tex_inline(c.strip()) for c in st[:-2].split("&")]
            rows_html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return (f"<table>{''.join(rows_html)}</table>"
            f"<p class='cap'><b>Table.</b> {cap_html}</p>")


def build_html() -> str:
    caps = extract_captions()
    parts = [f"<html><head><meta charset='utf-8'><style>"
             "body{font-family:Georgia,'Times New Roman',serif;font-size:11pt;"
             "margin:2.2cm;line-height:1.45;color:#111}"
             "h1{font-size:17pt;text-align:center}"
             "h2{font-size:13pt;border-bottom:1px solid #999;padding-bottom:2px;margin-top:22px}"
             "h3{font-size:11.5pt;margin:14px 0 4px}"
             "table{border-collapse:collapse;margin:10px auto;font-size:9.5pt}"
             "td{border:1px solid #999;padding:3px 8px}"
             "tr:first-child td{background:#eee;font-weight:bold}"
             "img{max-width:100%;display:block;margin:12px auto}"
             ".cap{font-size:9.5pt;color:#333;margin:4px 24px 18px}"
             ".meta{text-align:center;color:#444;font-size:10pt}"
             "</style></head><body>"]
    parts.append(f"<h1>{TITLE}</h1>")
    parts.append("<p class='meta'>FAFB v783 Connectome Control-Impact Study — "
                 "frozen results: E06-E14 (2026-09-15), E10B 100-null "
                 "confirmation (2026-09-17) — production rendering 2026-09-18</p>")
    for s in SECTIONS:
        raw = (P / "sections" / f"{s}.tex").read_text(encoding="utf-8")
        if SEC_TITLES[s]:
            parts.append(f"<h2>{SEC_TITLES[s]}</h2>")
        parts.append(tex_to_html(raw))
    parts.append("<h2>Figures</h2>")
    for n in range(1, 8):
        f, lab = FIG_META[n]
        parts.append(f"<h4>Figure {n}</h4>")
        parts.append(f"<img src='figures/{f}.png'>")
        parts.append(f"<p class='cap'><b>Figure {n}.</b> {caps.get(n, '')}</p>")
    parts.append("<h2>Tables</h2>")
    for i in range(1, 6):
        parts.append(tex_table_to_html(P / "tables" / f"Table{i}.tex"))
    parts.append("<h2>References</h2><ol>")
    bib = (P / "references.bib").read_text(encoding="utf-8")
    for m in re.finditer(r"@\w+\{(\w+),\s*(.*?)\n\}", bib, re.S):
        key, body = m.group(1), m.group(2)
        auth = re.search(r"author\s*=\s*\{(.+)\}", body)
        titl = re.search(r"title\s*=\s*\{(.+)\}", body)
        jour = re.search(r"journal\s*=\s*\{(.+)\}", body)
        year = re.search(r"year\s*=\s*\{(.+)\}", body)
        doi = re.search(r"doi\s*=\s*\{(.+)\}", body)
        parts.append("<li style='margin-bottom:6px'>"
                     + tex_inline(auth.group(1) if auth else "")
                     + " " + tex_inline(titl.group(1) if titl else "")
                     + ". <i>" + tex_inline(jour.group(1) if jour else "") + "</i> "
                     + (year.group(1) if year else "")
                     + (". doi:" + doi.group(1) if doi else "") + "</li>")
    parts.append("</ol><p class='cap'>NOTE: this PDF is an inspection "
                 "rendering of the submission-grade LaTeX source "
                 "(paper/manuscript.tex) for machines without a TeX "
                 "toolchain; it contains identical text, figures, tables, "
                 "and references.</p></body></html>")
    return "\n".join(parts)


def main() -> None:
    out_html = P / "manuscript_production.html"
    out_html.write_text(build_html(), encoding="utf-8")
    print("wrote", out_html)
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.exists():
        edge = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
    target = ROOT / "paper" / "manuscript_production.pdf"
    subprocess.run([str(edge), "--headless", "--disable-gpu",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={target}",
                    out_html.as_uri()], check=False, timeout=90,
                   capture_output=True)
    import time; time.sleep(2)
    size = target.stat().st_size if target.exists() else 0
    pages = "?"
    if size:
        data = target.read_bytes()
        pages = len(re.findall(rb"/Type\s*/Page[^s]", data)) or "?"
    print(f"wrote {target} ({size:,} bytes, pages~{pages})")


if __name__ == "__main__":
    main()
