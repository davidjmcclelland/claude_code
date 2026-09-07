# Document Compliance Reviewer

A dependency-free Python tool that scores documents against the rubric in
[`../marketing_rubric.pdf`](../marketing_rubric.pdf), writes a single
`report.docx` covering everything it reviewed, and exports the results as
JSON/CSV for a dashboard.

Built and validated against the real files in [`../../marketing/`](../../marketing/)
(3 `.docx`, 1 `.pptx`, 1 `.pdf`) — not synthetic samples.

## Quick start

```bash
cd finance/document_review
python3 review_documents.py
```

With no arguments it reviews every supported file directly inside
`marketing/`. Point it anywhere else instead:

```bash
python3 review_documents.py "/path/to/some/file.docx"
python3 review_documents.py "/path/to/a/folder/"
```

Supported formats: `.docx`, `.pptx`, `.pdf`, `.md`, `.txt`.

Output, written to `output/`:

| File | Purpose |
|---|---|
| `report.docx` | One Word document covering every reviewed document: score breakdown against the rubric's own wording, plus suggested edits |
| `dashboard_export.json` | Full detail per document/category, including every finding, for a dashboard with drill-down |
| `dashboard_export.csv` | One row per document × category (just the scores) for quick pivoting/charting |

`report.docx` is a real Word (OOXML) file, hand-built without python-docx —
see "Why hand-built OOXML" below. It opens natively in Word, LibreOffice,
and Google Docs.

## How scoring works

There is no dependency on an LLM or any external service — every score is
produced by deterministic, rule-based text analysis: readability formulas,
regex pattern matching, and structural checks (headings, lists, paragraph
length). This makes runs fast, free, and 100% reproducible, but it is **not
editorial judgment**. Treat every score and finding as a fast, consistent
first pass that tells a reviewer where to look — not a final verdict. A
document can score well here and still read poorly, and vice versa.

The five categories, and what each one actually checks:

1. **Tone and Professional Voice** — density of hype/marketing words
   ("amazing", "game-changing", …), slang, contractions, ALL-CAPS words, and
   exclamation-mark overuse, per 100 words.
2. **Clarity and Readability** — Flesch Reading Ease (via a syllable-count
   heuristic), percentage of sentences over 28 words, and passive-voice
   density. Sentences are split **per paragraph**, not across the whole
   document — a paragraph with no terminal punctuation (a bullet, a slide
   line) would otherwise run on into the next paragraph and badly distort
   the words-per-sentence ratio.
3. **Formatting and Structure** — presence and hierarchy of headings, list
   usage, and unbroken very-long paragraphs.
4. **Data and Evidence Usage** — every numeric claim (percentages, currency,
   plain numbers) is checked for a nearby comparison/source/unit cue
   ("compared to", "according to", "%", a year range, …); a document with no
   numeric claims at all is scored neutrally rather than penalized, since
   not every piece of writing needs statistics.
5. **Compliance With Style Guide** — checked against [`style_guide.json`](style_guide.json),
   a small **example** rule set (banned/discouraged terms and their
   preferred replacements, plus mechanical checks like double spaces and
   mixed quote styles). No real Red30 Tech style guide exists in this repo —
   edit that file to match yours.

Each category returns a 0–5 score plus a `rationale` (the numbers behind the
score) and a list of findings; every finding pairs a concrete `issue` with a
concrete `suggestion` — never just "this could be better." The overall
score out of 25 and its compliance band (Excellent / Good / Moderate /
Significant / Major) both come from **parsing `marketing_rubric.pdf` itself**
at run time (see `rubric_parser.py`), not a hand-copied version of it — if
the rubric PDF changes, the tool picks that up automatically.

### Documents that aren't prose

A slide deck (`.pptx`) or a visual one-sheet/infographic (`.pdf` with very
short, layout-driven text) doesn't have "sentences" or "headings" in the
prose sense. Rather than force sentence-level metrics onto bullet fragments
or callout-box labels — which produces nonsense (a slide deck's Flesch score
came out at **-19** before this was handled) — `readers.py` flags such
documents (`is_freeform_layout`), and `scoring.py` holds Clarity, Formatting,
and Data Usage at a neutral score of 4 for them, with a note to review those
sections manually instead.

## The PDF engine (`pdf_extract.py`)

There's no `pip` in this environment, so there's no PyPDF2/pdfplumber/etc.
available. `pdf_extract.py` is a small, dependency-free PDF reader built for
this project: it scans indirect objects by byte offset (not a `.*?endobj`
regex, so it stays fast even on huge files — the 111 MB persona PDF in
`marketing/` parses in under 2 seconds because the multi-hundred-MB parts are
embedded images it never touches), walks the real `/Catalog → /Pages → /Kids`
tree for correct page order, decompresses `/FlateDecode` (+ optional
`/ASCII85Decode`) content streams, and interprets just enough of the content
stream language (`q`/`Q`/`cm`/`BT`/`Tm`/`Td`/`Tj`/`TJ`) to recover positioned
text.

It is **not** a general PDF library. Known limitations:

- CTM transforms are treated as pure translations (rotation/scale/skew are
  ignored) — fine for the simple, axis-aligned layouts this was built
  against; a rotated-text PDF would extract with drifted positions.
- Only simple (non-CID/Type0) fonts are supported — an embedded-subset PDF
  using CID fonts with custom encodings (common from some Word→PDF exporters)
  isn't decoded correctly.
- Text is decoded as cp1252, which matches WinAnsiEncoding closely enough for
  ordinary Latin text but isn't a real per-font glyph mapping. One symbol-font
  hyphen glyph in the rubric PDF itself is patched by name in
  `rubric_parser.py` rather than solved generally, for exactly this reason.
- "Reading order" is reconstructed by grouping text into lines (same page,
  similar y) and ordering lines top-to-bottom — this reads correctly for
  single-column prose, but a multi-column poster (like the persona one-sheet
  in `marketing/`) interleaves columns row-by-row rather than reading one
  column fully before the next. `readers.py`'s `is_freeform_layout` flag
  exists partly because of this.

## Why hand-built OOXML

This environment has no `python-docx`, no Microsoft Word, and no
LibreOffice. A `.docx` file is just a zip archive of a handful of XML parts
(`word/document.xml`, `word/styles.xml`, a couple of relationship files and
some metadata), so `report_writer.py` builds those parts directly —
headings, paragraphs, bulleted findings, and bordered tables as
WordprocessingML — and zips them up with the stdlib's `zipfile` module. It's
the same approach this project already uses to *read* `.docx`/`.pptx` files
(`readers.py`) and to *write* the `.pptx` deck built earlier in this
project — OOXML in both directions, no third-party dependency either way.
`Heading1`/`Heading2`/`Heading3` styles are defined in `word/styles.xml`
rather than left to Word's built-in defaults, so the report's appearance
doesn't depend on which styles a given install happens to ship.

## Files

| File | Role |
|---|---|
| `review_documents.py` | CLI entry point — wires everything below together |
| `readers.py` | Loads `.docx`/`.pptx`/`.pdf`/`.md`/`.txt` into a common `DocumentContent` |
| `pdf_extract.py` | The stdlib-only PDF engine readers.py and rubric_parser.py both use |
| `rubric_parser.py` | Extracts the 5 categories + scoring bands from `marketing_rubric.pdf` |
| `scoring.py` | The five heuristic scorers + shared text-analysis helpers |
| `style_guide.json` | Example style-guide rules for category 5 — customize this |
| `report_writer.py` | Builds `report.docx` (hand-built OOXML) |
| `dashboard_export.py` | Builds `dashboard_export.json` / `.csv` |

## Extending it

- **Real style guide**: replace the contents of `style_guide.json` with your
  organization's actual banned terms / preferred phrasing.
- **New document formats**: add a reader function to `readers.py` and
  register its extension in `_READERS`; it only needs to produce a
  `DocumentContent` (paragraphs + optional headings/list-item indices).
- **Tuning thresholds**: every scoring cutoff (hype-word density bands,
  Flesch bands, etc.) is a plain constant near the top of its function in
  `scoring.py` — there's no hidden configuration layer.
- **Wiring up an actual dashboard**: `dashboard_export.json`/`.csv` are the
  data layer; there's no UI here yet (the sibling `dashboard/` folder is
  currently empty) — point a Streamlit/Dash app or a BI tool at those files.
