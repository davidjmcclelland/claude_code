#!/usr/bin/env python3
"""CLI: review documents against marketing_rubric.pdf and write report.docx
plus a dashboard export.

Usage:
    python3 review_documents.py [FOLDER_OR_FILE ...]

With no arguments, reviews every supported file directly inside
../../marketing/ (the sample set this tool was built against). Supported
formats: .docx, .pptx, .pdf, .md, .txt.

Outputs (written to ./output/):
    report.docx             — one Word document covering all reviewed documents
    dashboard_export.json  — full per-document, per-category detail
    dashboard_export.csv   — one row per document x category, for pivoting
"""

from __future__ import annotations

import os
import sys

import readers
import scoring
import rubric_parser
import report_writer
import dashboard_export

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RUBRIC = os.path.join(HERE, "..", "marketing_rubric.pdf")
DEFAULT_STYLE_GUIDE = os.path.join(HERE, "style_guide.json")
DEFAULT_TARGET = os.path.join(HERE, "..", "..", "marketing")
OUTPUT_DIR = os.path.join(HERE, "output")


def resolve_targets(args: list) -> list:
    if not args:
        return readers.discover_documents(DEFAULT_TARGET)
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths.extend(readers.discover_documents(a))
        else:
            paths.append(a)
    return paths


def main(argv: list) -> int:
    targets = resolve_targets(argv)
    if not targets:
        print("No reviewable documents found (.docx, .pptx, .pdf, .md, .txt).", file=sys.stderr)
        return 1

    print(f"Rubric:       {os.path.abspath(DEFAULT_RUBRIC)}")
    print(f"Style guide:  {os.path.abspath(DEFAULT_STYLE_GUIDE)}")
    print(f"Documents:    {len(targets)} found")
    print()

    rubric = rubric_parser.parse_rubric(DEFAULT_RUBRIC)
    style_guide = scoring.load_style_guide(DEFAULT_STYLE_GUIDE)

    review_results = []
    for path in targets:
        name = os.path.basename(path)
        try:
            doc = readers.load_document(path)
        except Exception as e:
            print(f"  [skip] {name}: could not read ({e})")
            continue

        results = scoring.score_document(doc, style_guide)
        total = sum(r.score for r in results)
        level = rubric_parser.compliance_level(rubric, total)
        review_results.append({"doc": doc, "results": results, "total": total, "level": level})
        print(f"  {name:50s} {total:2d}/25  {level}")

    if not review_results:
        print("Nothing could be scored.", file=sys.stderr)
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    docx_bytes = report_writer.build_report(review_results, rubric, os.path.relpath(DEFAULT_STYLE_GUIDE, OUTPUT_DIR))
    report_path = os.path.join(OUTPUT_DIR, "report.docx")
    with open(report_path, "wb") as f:
        f.write(docx_bytes)

    export = dashboard_export.build_export(review_results, rubric)
    json_path = os.path.join(OUTPUT_DIR, "dashboard_export.json")
    csv_path = os.path.join(OUTPUT_DIR, "dashboard_export.csv")
    dashboard_export.write_json(export, json_path)
    dashboard_export.write_csv(export, csv_path)

    print()
    print(f"Wrote {report_path}")
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
