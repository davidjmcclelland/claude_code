"""Writes report.docx: one Word document covering every reviewed document.

This environment has no python-docx, no Microsoft Word, and no
LibreOffice, so this hand-builds the OOXML package directly — the same
approach used for the .pptx built earlier in this project. A .docx is a
zip archive of a handful of XML parts (document body, styles, metadata);
DocxDoc below builds the body content (headings, paragraphs, bullets,
tables, page breaks) as WordprocessingML, and build_report() packages the
whole thing into the zip bytes Word expects.
"""

from __future__ import annotations

import datetime
import io
import zipfile
from xml.sax.saxutils import escape as xml_escape

RED = "B4392B"
BLUE = "1F5C99"
GREEN = "1E7A46"
GREY = "6B6E68"
HAIRLINE = "C3C6BC"
PAGE_BG = "F3F4EF"


def _t(text: str) -> str:
    """A <w:t> run-text element, whitespace-preserving and XML-escaped."""
    return f'<w:t xml:space="preserve">{xml_escape(text)}</w:t>'


def _run(text: str, bold=False, italic=False, color=None, sz=None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if sz:
        props.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{rpr}{_t(text)}</w:r>"


class DocxDoc:
    """Minimal WordprocessingML builder: headings, paragraphs, bullets, a
    horizontal rule, page breaks, and simple bordered tables. Good enough
    for this one report layout — not a general docx writer."""

    def __init__(self):
        self.body = []

    def heading(self, text: str, level: int = 1):
        style = {1: "Heading1", 2: "Heading2", 3: "Heading3"}.get(level, "Heading3")
        self.body.append(
            f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>{_run(text)}</w:p>'
        )

    def paragraph(self, text: str, italic: bool = False, color: str = None, size: int = 20):
        run = _run(text, italic=italic, color=color or None, sz=size)
        self.body.append(
            f'<w:p><w:pPr><w:spacing w:after="180"/></w:pPr>{run}</w:p>'
        )

    def rule(self):
        self.body.append(
            '<w:p><w:pPr><w:pBdr>'
            f'<w:bottom w:val="single" w:sz="6" w:space="4" w:color="{HAIRLINE}"/>'
            '</w:pBdr><w:spacing w:after="200"/></w:pPr></w:p>'
        )

    def page_break(self):
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def bullet(self, lead: str, rest: str = "", color: str = None):
        parts = [_run("•  "), _run(lead, bold=True, color=color)]
        if rest:
            parts.append(_run(rest))
        self.body.append(
            '<w:p><w:pPr><w:ind w:left="480" w:hanging="300"/>'
            f'<w:spacing w:after="140"/></w:pPr>{"".join(parts)}</w:p>'
        )

    def table(self, headers: list, rows: list, col_widths: list):
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)

        def cell(text: str, width: int, bold=False, shade=None) -> str:
            shd = f'<w:shd w:val="clear" w:fill="{shade}"/>' if shade else ""
            return (
                f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shd}'
                '<w:tcMar><w:top w:w="60" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/>'
                '<w:left w:w="100" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>'
                f'</w:tcPr><w:p>{_run(text, bold=bold, sz=18)}</w:p></w:tc>'
            )

        def row(cells: list, bold=False, shade=None) -> str:
            tcs = "".join(cell(c, w, bold=bold, shade=shade) for c, w in zip(cells, col_widths))
            return f"<w:tr>{tcs}</w:tr>"

        borders = (
            f'<w:tblBorders>'
            f'<w:top w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'<w:left w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'<w:bottom w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'<w:right w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'<w:insideV w:val="single" w:sz="4" w:color="{HAIRLINE}"/>'
            f'</w:tblBorders>'
        )
        tbl = (
            f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>{borders}</w:tblPr>'
            f'<w:tblGrid>{grid}</w:tblGrid>'
            f'{row(headers, bold=True, shade="EDEEE8")}'
            f'{"".join(row(r) for r in rows)}'
            f'</w:tbl>'
            # A table can't be the last element before another block without
            # a following paragraph in some readers' rendering — add a
            # small spacer paragraph after every table.
            f'<w:p><w:pPr><w:spacing w:after="200"/></w:pPr></w:p>'
        )
        self.body.append(tbl)

    def render_document_xml(self) -> str:
        sect_pr = (
            '<w:sectPr>'
            '<w:pgSz w:w="12240" w:h="15840"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
            'w:header="720" w:footer="720" w:gutter="0"/>'
            '</w:sectPr>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body>{"".join(self.body)}{sect_pr}</w:body>'
            '</w:document>'
        )


_STYLES_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/></w:rPr></w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/><w:b/><w:color w:val="{RED}"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="280" w:after="140"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/><w:b/><w:color w:val="{RED}"/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
    <w:pPr><w:spacing w:before="220" w:after="120"/><w:outlineLvl w:val="2"/></w:pPr>
    <w:rPr><w:b/><w:color w:val="{GREY}"/><w:sz w:val="22"/></w:rPr>
  </w:style>
</w:styles>"""

_CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

_ROOT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

_DOCUMENT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _doc_props_xml(title: str, doc_count: int):
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_escape(title)}</dc:title>
  <dc:creator>Document Compliance Reviewer</dc:creator>
  <cp:lastModifiedBy>Document Compliance Reviewer</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>"""
    app = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Document Compliance Reviewer</Application>
  <Company></Company>
  <Paragraphs>{doc_count}</Paragraphs>
</Properties>"""
    return core, app


def _package_docx(document_xml: str, title: str, doc_count: int) -> bytes:
    core_xml, app_xml = _doc_props_xml(title, doc_count)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        z.writestr("_rels/.rels", _ROOT_RELS_XML)
        z.writestr("word/document.xml", document_xml)
        z.writestr("word/styles.xml", _STYLES_XML)
        z.writestr("word/_rels/document.xml.rels", _DOCUMENT_RELS_XML)
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)
    return buf.getvalue()


def build_report(review_results: list, rubric: dict, style_guide_path: str) -> bytes:
    """review_results: list of dicts, one per document:
        {"doc": DocumentContent, "results": list[CategoryResult], "total": int, "level": str}

    Returns the raw bytes of a .docx file.
    """
    doc = DocxDoc()
    generated = datetime.datetime.now().strftime("%B %d, %Y")

    doc.heading(rubric["title"], level=1)
    doc.paragraph(
        f"Automated compliance review · {len(review_results)} document(s) · generated {generated}",
        italic=True, color=GREY,
    )
    doc.paragraph(
        "Scores are produced by rule-based text analysis (readability formulas, "
        "pattern matching, and structural checks) calibrated against the rubric's "
        "own score descriptions below — not editorial judgment. Treat this as a "
        "fast, consistent first pass that tells you where to look, not a final verdict.",
        color=GREY,
    )
    doc.rule()

    # ---- overview table -----------------------------------------------
    doc.heading("Overview", level=2)
    cat_names = [c["name"] for c in rubric["categories"]]
    headers = ["Document"] + [n.split(" and ")[0].split(" With ")[0] for n in cat_names] + ["Total", "Level"]
    rows = []
    for entry in review_results:
        row = [entry["doc"].name]
        by_cat = {r.category: r.score for r in entry["results"]}
        for name in cat_names:
            row.append(str(by_cat.get(name, "–")))
        row.append(f"{entry['total']}/25")
        row.append(entry["level"])
        rows.append(row)
    widths = [2000, 700, 700, 700, 700, 700, 700, 1900]
    doc.table(headers, rows, widths)

    doc.paragraph("Compliance bands, from the rubric's Scoring Summary:", color=GREY)
    for band in rubric["summary_bands"]:
        doc.bullet(f"{band['min']}–{band['max']}: ", band["level"])

    doc.page_break()

    # ---- per-document sections ------------------------------------------
    for i, entry in enumerate(review_results):
        d = entry["doc"]
        results = entry["results"]
        doc.heading(d.name, level=1)
        doc.paragraph(
            f"Format: {d.format.upper()}   ·   Words: {d.word_count:,}   ·   "
            f"Total score: {entry['total']}/25   ·   {entry['level']}",
            color=GREY,
        )
        if d.is_freeform_layout:
            doc.paragraph(
                "This document is a visual one-sheet/slide-style layout rather than "
                "continuous prose. A few categories below are held at a neutral score "
                "instead of being judged by prose-oriented metrics — see each category's "
                "rationale.",
                italic=True, color=GREY,
            )

        doc.heading("Category breakdown", level=3)
        cat_headers = ["Category", "Score", "Rubric description at this score", "What was checked"]
        cat_rows = []
        for r in results:
            rubric_text = ""
            for cat in rubric["categories"]:
                if cat["name"] == r.category:
                    rubric_text = cat["criteria"].get(r.score, "")
            cat_rows.append([r.category, f"{r.score}/5", rubric_text, r.rationale])
        doc.table(cat_headers, cat_rows, [1700, 600, 3200, 3200])

        total_findings = sum(len(r.findings) for r in results)
        if total_findings:
            doc.heading("Suggested edits", level=3)
            for r in results:
                if not r.findings:
                    continue
                doc.paragraph(r.category, color=BLUE, size=20)
                shown = r.findings[:8]
                for f in shown:
                    lead = f.issue
                    rest = f'"{f.snippet}" → {f.suggestion}' if f.snippet else f"→ {f.suggestion}"
                    doc.bullet(lead + " ", rest)
                if len(r.findings) > len(shown):
                    doc.paragraph(
                        f"…and {len(r.findings) - len(shown)} more instance(s) of this "
                        f"type of issue (see dashboard export for the full list).",
                        italic=True, color=GREY, size=18,
                    )
        else:
            doc.paragraph("No issues flagged in this document.", color=GREEN)

        if i < len(review_results) - 1:
            doc.page_break()

    doc.rule()
    doc.paragraph(
        f"Rubric source: marketing_rubric.pdf. Style guide rules: {style_guide_path} "
        "(edit that file to match your organization's actual style guide). "
        "Generated by finance/document_review/review_documents.py.",
        italic=True, color=GREY, size=16,
    )

    document_xml = doc.render_document_xml()
    return _package_docx(document_xml, rubric["title"], len(review_results))
