#!/usr/bin/env python
"""Minimal Markdown -> HTML converter for the manuscript (no external deps).

Handles the constructs actually used in paper/manuscript.md: ATX headers,
horizontal rules, bullet/numbered lists, bold/italic/code spans, paragraphs.
Output: paper/manuscript.html (for Edge headless print-to-PDF).
Run:  py scripts/md_to_html.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paper" / "manuscript.md"
OUT = ROOT / "paper" / "manuscript.html"


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
    return s


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    list_open: str | None = None  # "ul" | "ol"

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append(f"</{list_open}>")
            list_open = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        if line.startswith("### "):
            close_list(); out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list(); out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list(); out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.strip() == "---":
            close_list(); out.append("<hr>")
        elif line.startswith("- "):
            if list_open != "ul":
                close_list(); out.append("<ul>"); list_open = "ul"
            out.append(f"<li>{inline(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            if list_open != "ol":
                close_list(); out.append("<ol>"); list_open = "ol"
            out.append(f"<li>{inline(re.sub(r'^\\d+\\. ', '', line))}</li>")
        else:
            close_list(); out.append(f"<p>{inline(line)}</p>")
    close_list()

    body = "\n".join(out)
    doc = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>Manuscript</title><style>"
        "body{font-family:'Cambria','Georgia',serif;font-size:11pt;"
        "line-height:1.45;max-width:52em;margin:2em auto;color:#111}"
        "h1{font-size:1.5em}h2{font-size:1.2em;border-bottom:1px solid #999;"
        "padding-bottom:2px}h3{font-size:1.05em}"
        "code{font-family:Consolas,monospace;font-size:0.9em}"
        "li{margin:2px 0}hr{border:none;border-top:1px solid #bbb;margin:1.2em 0}"
        "</style></head><body>\n" + body +
        "\n<hr><p><em>HTML rendering generated from manuscript.md "
        "(scripts/md_to_html.py); formatting is approximate — the Markdown "
        "source is authoritative.</em></p></body></html>"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(f"OK {OUT.relative_to(ROOT)} ({len(body)} chars body)")


if __name__ == "__main__":
    main()
