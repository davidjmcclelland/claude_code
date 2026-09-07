"""Exports review results as JSON and CSV for a dashboard to consume.

Two files are written:
  * dashboard_export.json — full detail, including every finding/suggested
    edit, for a dashboard that wants drill-down.
  * dashboard_export.csv  — one row per document x category, just the
    scores, for quick pivoting/charting.
"""

from __future__ import annotations

import csv
import json
import datetime


def build_export(review_results: list, rubric: dict) -> dict:
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    documents = []
    for entry in review_results:
        d = entry["doc"]
        categories = []
        for r in entry["results"]:
            categories.append({
                "category": r.category,
                "score": r.score,
                "max_score": 5,
                "rationale": r.rationale,
                "findings": [
                    {
                        "location": f.location,
                        "snippet": f.snippet,
                        "issue": f.issue,
                        "suggestion": f.suggestion,
                    }
                    for f in r.findings
                ],
            })
        documents.append({
            "name": d.name,
            "path": d.path,
            "format": d.format,
            "word_count": d.word_count,
            "is_freeform_layout": d.is_freeform_layout,
            "total_score": entry["total"],
            "max_total_score": 25,
            "compliance_level": entry["level"],
            "categories": categories,
        })

    return {
        "generated_at": generated_at,
        "rubric_title": rubric["title"],
        "rubric_bands": rubric["summary_bands"],
        "documents": documents,
    }


def write_json(export: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)


def write_csv(export: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "document", "format", "word_count", "category", "score", "max_score",
            "finding_count", "total_score", "compliance_level", "generated_at",
        ])
        for doc in export["documents"]:
            for cat in doc["categories"]:
                writer.writerow([
                    doc["name"], doc["format"], doc["word_count"], cat["category"],
                    cat["score"], cat["max_score"], len(cat["findings"]),
                    doc["total_score"], doc["compliance_level"], export["generated_at"],
                ])
