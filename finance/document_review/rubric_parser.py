"""Extracts the structured rubric (categories, per-score descriptions, and
the overall Scoring Summary bands) out of marketing_rubric.pdf itself, so
the tool always reflects whatever the PDF currently says rather than a
hand-copied snapshot of it.

Works off pdf_extract's linearized text rather than raw positioned runs:
this specific PDF lays each table row out as "<score> <description>" on its
own line once reading order is reconstructed, so a small line-pattern state
machine is enough to recover the table structure.
"""

from __future__ import annotations

import re

import pdf_extract

_CATEGORY_HEADER_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_ROW_RE = re.compile(r"^([0-5])\s+(.+)$")
_RANGE_RE = re.compile(r"^(\d+)[–\-](\d+)\s+(.+)$")
_SKIP_LINES = {"Score Description", "Total Score Compliance Level"}


def parse_rubric(pdf_path: str) -> dict:
    text = pdf_extract.extract_text(pdf_path)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise ValueError(f"No extractable text in {pdf_path}")

    title = lines[0]
    categories = []
    summary_bands = []
    mode = None
    current = None

    for line in lines[1:]:
        if line == "Scoring Summary":
            mode = "summary"
            continue
        if line in _SKIP_LINES:
            continue

        if mode != "summary":
            m = _CATEGORY_HEADER_RE.match(line)
            if m:
                current = {"number": int(m.group(1)), "name": m.group(2).strip(), "criteria": {}}
                categories.append(current)
                mode = "category"
                continue
            if mode == "category" and current is not None:
                m2 = _ROW_RE.match(line)
                if m2:
                    current["criteria"][int(m2.group(1))] = m2.group(2).strip()
                    continue
        else:
            m3 = _RANGE_RE.match(line)
            if m3:
                summary_bands.append({
                    "min": int(m3.group(1)),
                    "max": int(m3.group(2)),
                    "level": m3.group(3).strip(),
                })

    if not categories:
        raise ValueError(f"Could not find any rubric categories in {pdf_path} — has its layout changed?")

    _fix_known_glyph_artifacts(categories)
    return {"title": title, "categories": categories, "summary_bands": summary_bands}


def _fix_known_glyph_artifacts(categories: list) -> None:
    """The source PDF renders one hyphen via a symbol font (ZapfDingbats),
    which this tool's generic WinAnsi-only text decoding can't map — it
    reads as a bare "n". Patch that one known case rather than building a
    general per-font glyph table for a single character."""
    for cat in categories:
        for score, desc in list(cat["criteria"].items()):
            cat["criteria"][score] = desc.replace("non n compliant", "noncompliant")


def compliance_level(rubric: dict, total_score: int) -> str:
    for band in rubric["summary_bands"]:
        if band["min"] <= total_score <= band["max"]:
            return band["level"]
    return "Unrated"


def criterion_text(rubric: dict, category_name: str, score: int) -> str:
    for cat in rubric["categories"]:
        if cat["name"] == category_name:
            return cat["criteria"].get(score, "")
    return ""


if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "../marketing_rubric.pdf"
    rubric = parse_rubric(path)
    print(json.dumps(rubric, indent=2))
    print()
    print("Max score 25 ->", compliance_level(rubric, 25))
    print("Score 14 ->", compliance_level(rubric, 14))
    print("Score 3 ->", compliance_level(rubric, 3))
