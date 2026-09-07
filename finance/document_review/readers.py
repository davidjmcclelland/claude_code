"""Loads .docx, .pptx, .pdf, .md, and .txt files into a common
DocumentContent structure the scorers in scoring.py can work with,
regardless of source format.
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

import pdf_extract

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


@dataclass
class Heading:
    level: int          # 1 = top-level heading/title/slide title, 2 = sub, ...
    text: str
    para_index: int


@dataclass
class DocumentContent:
    path: str
    name: str
    format: str                     # "docx" | "pptx" | "pdf" | "md" | "txt"
    paragraphs: list = field(default_factory=list)   # plain-text paragraphs, in order
    headings: list = field(default_factory=list)     # list[Heading]
    list_items: list = field(default_factory=list)   # indices into paragraphs that are bullet/numbered items
    font_sizes: list = field(default_factory=list)    # observed font sizes (pdf only; used as a heading proxy)
    is_freeform_layout: bool = False   # True for poster/infographic-style PDFs: sentence-level
                                        # metrics (readability, sentence length) are unreliable

    @property
    def text(self) -> str:
        return "\n\n".join(p for p in self.paragraphs if p.strip())

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\S+", self.text))


# ------------------------------------------------------------------ docx --

def _read_docx(path: str) -> DocumentContent:
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    doc = DocumentContent(path=path, name=os.path.basename(path), format="docx")

    heading_re = re.compile(r"^Heading(\d+)$|^Title$")
    for p_index, p in enumerate(root.iter(f"{W_NS}p")):
        runs_text = "".join(t.text or "" for t in p.iter(f"{W_NS}t"))
        if not runs_text.strip():
            continue
        doc.paragraphs.append(runs_text)
        this_index = len(doc.paragraphs) - 1

        pstyle_el = p.find(f"{W_NS}pPr/{W_NS}pStyle")
        style_val = pstyle_el.get(f"{W_NS}val") if pstyle_el is not None else None
        if style_val:
            m = heading_re.match(style_val)
            if m:
                level = int(m.group(1)) if m.group(1) else 1
                doc.headings.append(Heading(level, runs_text, this_index))

        num_pr = p.find(f"{W_NS}pPr/{W_NS}numPr")
        if num_pr is not None:
            doc.list_items.append(this_index)

    return doc


# ------------------------------------------------------------------ pptx --

def _read_pptx(path: str) -> DocumentContent:
    z = zipfile.ZipFile(path)
    slide_files = sorted(
        (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
        key=lambda n: int(re.search(r"slide(\d+)\.xml$", n).group(1)),
    )
    doc = DocumentContent(path=path, name=os.path.basename(path), format="pptx")

    for slide_file in slide_files:
        root = ET.fromstring(z.read(slide_file))
        slide_title_added = False

        # Each <p:sp> shape has an optional placeholder type (title/body) and
        # one or more <a:p> paragraphs of text.
        ns_p = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        for sp in root.iter(f"{ns_p}sp"):
            ph = sp.find(f".//{ns_p}nvSpPr/{ns_p}nvPr/{ns_p}ph")
            is_title = ph is not None and ph.get("type") in ("title", "ctrTitle")
            for a_p in sp.iter(f"{A_NS}p"):
                text = "".join(t.text or "" for t in a_p.iter(f"{A_NS}t"))
                if not text.strip():
                    continue
                doc.paragraphs.append(text)
                this_index = len(doc.paragraphs) - 1
                if is_title and not slide_title_added:
                    doc.headings.append(Heading(1, text, this_index))
                    slide_title_added = True
                bu = a_p.find(f"{A_NS}pPr")
                if bu is not None and (bu.find(f"{A_NS}buChar") is not None or bu.find(f"{A_NS}buAutoNum") is not None):
                    doc.list_items.append(this_index)
    return doc


# -------------------------------------------------------------------- pdf --

def _read_pdf(path: str) -> DocumentContent:
    runs = pdf_extract.extract_positioned_runs(path)
    doc = DocumentContent(path=path, name=os.path.basename(path), format="pdf")

    if not runs:
        doc.is_freeform_layout = True
        return doc

    doc.font_sizes = [r.size for r in runs if r.size]

    # Group into lines the same way pdf_extract.extract_text does, but keep
    # per-line max font size so headings can be inferred from a size jump.
    by_page = {}
    for r in runs:
        by_page.setdefault(r.page, []).append(r)

    sizes_sorted = sorted(doc.font_sizes)
    body_size = sizes_sorted[len(sizes_sorted) // 2] if sizes_sorted else 0  # median as a proxy for body text
    heading_threshold = body_size * 1.35

    for page in sorted(by_page):
        page_runs = sorted(by_page[page], key=lambda r: -r.y)
        lines = []
        for r in page_runs:
            placed = False
            for line in lines:
                if abs(line[0] - r.y) <= 2.0:
                    line[1].append(r)
                    placed = True
                    break
            if not placed:
                lines.append([r.y, [r]])
        for _, line_runs in lines:
            line_runs.sort(key=lambda r: r.x)
            text = " ".join(r.text for r in line_runs if r.text.strip())
            text = re.sub(r"\s{2,}", " ", text).strip()
            if not text:
                continue
            doc.paragraphs.append(text)
            this_index = len(doc.paragraphs) - 1
            max_size = max((r.size for r in line_runs), default=0)
            if body_size and max_size >= heading_threshold and len(text) < 80:
                doc.headings.append(Heading(1, text, this_index))
            if text.lstrip()[:1] in ("•", "-", "*") or re.match(r"^\d+[.)]\s", text.strip()):
                doc.list_items.append(this_index)

    # Heuristic: a single-page design with many short lines and heavy
    # repetition of header words (a poster/infographic) rather than prose —
    # sentence-level metrics won't mean much on it.
    avg_line_len = sum(len(p) for p in doc.paragraphs) / max(1, len(doc.paragraphs))
    if len(by_page) == 1 and avg_line_len < 60 and len(doc.paragraphs) > 15:
        doc.is_freeform_layout = True

    return doc


# --------------------------------------------------------------- txt/md ---

def _read_text_like(path: str, fmt: str) -> DocumentContent:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    doc = DocumentContent(path=path, name=os.path.basename(path), format=fmt)

    blocks = re.split(r"\n\s*\n", raw)
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        doc.paragraphs.append(block)
        this_index = len(doc.paragraphs) - 1

        if fmt == "md":
            m = re.match(r"^(#{1,6})\s+(.*)", block.strip())
            if m:
                doc.headings.append(Heading(len(m.group(1)), m.group(2), this_index))
                continue
        else:
            # Plain text: an ALL-CAPS short line, or a Title Case short line
            # ending without a period, reads as a heading.
            stripped = block.strip()
            if len(stripped) < 70 and "\n" not in stripped and not stripped.endswith((".", "!", "?")):
                if stripped.isupper() or stripped.istitle():
                    doc.headings.append(Heading(1, stripped, this_index))
                    continue

        if re.match(r"^\s*([-*•]|\d+[.)])\s", block):
            doc.list_items.append(this_index)

    return doc


# ------------------------------------------------------------------- api --

_READERS = {
    ".docx": _read_docx,
    ".pptx": _read_pptx,
    ".pdf": _read_pdf,
    ".md": lambda p: _read_text_like(p, "md"),
    ".txt": lambda p: _read_text_like(p, "txt"),
}


def load_document(path: str) -> DocumentContent:
    ext = os.path.splitext(path)[1].lower()
    reader = _READERS.get(ext)
    if reader is None:
        raise ValueError(f"Unsupported file type: {ext} ({path})")
    return reader(path)


def load_documents(paths) -> list:
    return [load_document(p) for p in paths]


def discover_documents(folder: str) -> list:
    """All reviewable files directly inside a folder, sorted by name."""
    out = []
    for name in sorted(os.listdir(folder)):
        ext = os.path.splitext(name)[1].lower()
        if ext in _READERS:
            out.append(os.path.join(folder, name))
    return out
