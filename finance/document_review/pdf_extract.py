"""A small, dependency-free PDF reader.

This is not a general-purpose PDF library. It supports exactly the subset of
the PDF spec produced by common simple generators (ReportLab, Adobe
Illustrator "print to PDF", Word's PDF export without embedded CID fonts):

  * classic (non-compressed) indirect objects — "N G obj ... endobj" —
    found directly in the file body, not packed into /ObjStm object streams
  * single content stream per page, or an array of them, referenced by
    /Contents, compressed with /FlateDecode (optionally /ASCII85Decode too)
  * simple (non-Type0/CID) fonts with WinAnsiEncoding, which is close enough
    to cp1252 for the text extraction done here
  * content-stream transforms that are pure translations (the "b" and "c"
    terms of the "a b c d e f cm"/"Tm" matrices are 0) — rotation/scale/skew
    is not modelled; the translation component is still applied, so output
    degrades gracefully (positions drift) rather than failing outright

Two entry points matter to the rest of this tool:

  * ``extract_text(path)``            -> best-effort linear text dump
  * ``extract_positioned_runs(path)`` -> the raw (page, x, y, size, text)
    tuples, which ``rubric_parser.py`` uses to reconstruct table structure
    that a plain text dump would lose.
"""

from __future__ import annotations

import re
import zlib
import base64
from dataclasses import dataclass


@dataclass
class TextRun:
    page: int
    x: float
    y: float
    size: float
    font: str
    text: str


# --------------------------------------------------------------- objects --

_OBJ_HEADER_RE = re.compile(rb"(?:^|[\r\n])\s*(\d+)\s+(\d+)\s+obj\b")


def _scan_objects(buf: bytes) -> dict:
    """Map object number -> raw bytes from that object's header to the next
    object's header (or EOF). A byte-offset slice rather than a DOTALL regex
    match against "endobj", so this stays fast even when some objects (image
    XObjects) are huge."""
    headers = list(_OBJ_HEADER_RE.finditer(buf))
    objects = {}
    for i, m in enumerate(headers):
        num = int(m.group(1))
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(buf)
        objects[num] = buf[start:end]
    return objects


def _find_ref(pattern: bytes, body: bytes):
    m = re.search(pattern, body)
    return int(m.group(1)) if m else None


def _find_refs_in_array(pattern: bytes, body: bytes):
    m = re.search(pattern, body, re.S)
    if not m:
        return []
    return [int(n) for n in re.findall(rb"(\d+)\s+\d+\s+R", m.group(1))]


def _decode_stream(obj_body: bytes) -> bytes:
    """Given an object's raw body (dict + 'stream'...'endstream'), return the
    decompressed stream bytes. Returns b'' if there is no stream."""
    idx = obj_body.find(b"stream")
    if idx == -1:
        return b""
    head = obj_body[:idx]
    start = idx + len(b"stream")
    if obj_body[start:start + 2] == b"\r\n":
        start += 2
    elif obj_body[start:start + 1] in (b"\r", b"\n"):
        start += 1
    end = obj_body.find(b"endstream", start)
    if end == -1:
        end = len(obj_body)
    raw = obj_body[start:end]

    if b"/ASCII85Decode" in head:
        trimmed = raw.strip()
        if trimmed.endswith(b"~>"):
            trimmed = trimmed[:-2]
        try:
            raw = base64.a85decode(trimmed, adobe=False)
        except Exception:
            pass
    if b"/FlateDecode" in head:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            # Some encoders omit the zlib header; try raw deflate.
            try:
                raw = zlib.decompress(raw, -15)
            except zlib.error:
                pass
    return raw


def _leaf_pages(objects: dict, pages_obj_num: int, seen=None) -> list:
    """Walk /Type/Pages -> /Kids recursively, returning object numbers of
    leaf /Type/Page nodes in document order."""
    if seen is None:
        seen = set()
    if pages_obj_num in seen or pages_obj_num not in objects:
        return []
    seen.add(pages_obj_num)
    body = objects[pages_obj_num]
    kids = _find_refs_in_array(rb"/Kids\s*\[(.*?)\]", body)
    leaves = []
    for kid in kids:
        kid_body = objects.get(kid, b"")
        head = kid_body[:2000]
        if re.search(rb"/Type\s*/Pages\b", head):
            leaves.extend(_leaf_pages(objects, kid, seen))
        else:
            leaves.append(kid)
    return leaves


def _page_content_bytes(objects: dict, page_body: bytes) -> bytes:
    head = page_body[:4000]
    single = _find_ref(rb"/Contents\s+(\d+)\s+0\s+R", head)
    if single is not None:
        return _decode_stream(objects.get(single, b""))
    refs = _find_refs_in_array(rb"/Contents\s*\[(.*?)\]", head)
    parts = [_decode_stream(objects.get(r, b"")) for r in refs]
    return b"\n".join(parts)


def get_pages(path: str) -> list:
    """Return a list of decompressed content-stream bytes, one per page, in
    document order (best effort via the Catalog -> Pages -> Kids tree; falls
    back to every object that looks like a /Type/Page if no Catalog is
    found)."""
    buf = open(path, "rb").read()
    objects = _scan_objects(buf)

    catalog_num = None
    for num, body in objects.items():
        if re.search(rb"/Type\s*/Catalog\b", body[:2000]):
            catalog_num = num
            break

    page_nums = []
    if catalog_num is not None:
        pages_ref = _find_ref(rb"/Pages\s+(\d+)\s+0\s+R", objects[catalog_num][:2000])
        if pages_ref is not None:
            page_nums = _leaf_pages(objects, pages_ref)

    if not page_nums:
        page_nums = [
            num for num, body in objects.items()
            if re.search(rb"/Type\s*/Page\b(?!s)", body[:2000])
        ]

    return [_page_content_bytes(objects, objects[num]) for num in page_nums]


# ------------------------------------------------------- content tokens ---

_TOKEN_RE = re.compile(rb"\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]*>|/[^\s/()<>\[\]]+|[^\s]+")
_NUM_RE = re.compile(rb"^[+-]?\d*\.?\d+$")


def _decode_literal_string(tok: bytes) -> str:
    inner = tok[1:-1]
    out = bytearray()
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == 0x5C and i + 1 < len(inner):  # backslash
            nxt = inner[i + 1]
            if nxt in b"nrtbf()\\":
                out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}.get(nxt, nxt))
                i += 2
                continue
            if nxt in b"\r\n":  # line continuation, drop it
                i += 2
                continue
            if 0x30 <= nxt <= 0x37:  # octal escape, up to 3 digits
                j = i + 1
                digits = b""
                while j < len(inner) and len(digits) < 3 and 0x30 <= inner[j] <= 0x37:
                    digits += inner[j:j + 1]
                    j += 1
                out.append(int(digits, 8) & 0xFF)
                i = j
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return bytes(out).decode("cp1252", errors="replace")


def _decode_hex_string(tok: bytes) -> str:
    hexdigits = re.sub(rb"\s+", b"", tok[1:-1])
    if len(hexdigits) % 2:
        hexdigits += b"0"
    try:
        return bytes.fromhex(hexdigits.decode("ascii")).decode("cp1252", errors="replace")
    except ValueError:
        return ""


def _run_positioned_text(stream: bytes, page_index: int) -> list:
    """Interpret a content stream, tracking CTM (translation only) and text
    position, yielding TextRun objects for every Tj/TJ show-text op."""
    tokens = _TOKEN_RE.findall(stream)
    runs = []
    ctm_stack = [(0.0, 0.0)]
    ctm = (0.0, 0.0)
    line_origin = (0.0, 0.0)
    font, size = "", 0.0
    pending_font_name = None
    nums = []
    i = 0
    n = len(tokens)

    def emit(text: str):
        if text.strip():
            runs.append(TextRun(page_index, ctm[0] + line_origin[0],
                                 ctm[1] + line_origin[1], size, font, text))

    while i < n:
        tok = tokens[i]

        if tok == b"[":
            # Collect a TJ array: mixture of strings and numbers until b"]"
            j = i + 1
            parts = []
            while j < n and tokens[j] != b"]":
                t = tokens[j]
                if t.startswith(b"(") and t.endswith(b")"):
                    parts.append(("s", _decode_literal_string(t)))
                elif t.startswith(b"<") and t.endswith(b">"):
                    parts.append(("s", _decode_hex_string(t)))
                elif _NUM_RE.match(t):
                    parts.append(("n", float(t)))
                j += 1
            # j now at "]"; the operator (TJ) follows at j+1.
            # Insert a space wherever a large negative kerning number sits
            # between strings (a heuristic word-gap, same one real PDF text
            # extractors use).
            rebuilt = []
            for kind, val in parts:
                if kind == "s":
                    rebuilt.append(val)
                elif kind == "n" and val < -100:
                    rebuilt.append(" ")
            text = "".join(rebuilt)
            if j + 1 < n and tokens[j + 1] == b"TJ":
                emit(text)
                i = j + 2
                continue
            i = j + 1
            continue

        if tok.startswith(b"(") and tok.endswith(b")"):
            text = _decode_literal_string(tok)
            if i + 1 < n and tokens[i + 1] == b"Tj":
                emit(text)
                i += 2
                continue
            i += 1
            continue

        if tok.startswith(b"<") and tok.endswith(b">") and not tok.startswith(b"<<"):
            text = _decode_hex_string(tok)
            if i + 1 < n and tokens[i + 1] == b"Tj":
                emit(text)
                i += 2
                continue
            i += 1
            continue

        if tok == b"q":
            ctm_stack.append(ctm)
        elif tok == b"Q":
            if len(ctm_stack) > 1:
                ctm_stack.pop()
            ctm = ctm_stack[-1]
        elif tok == b"BT":
            line_origin = (0.0, 0.0)
            nums = []
        elif tok == b"cm":
            if len(nums) >= 6:
                a, b_, c, d, e, f = nums[-6:]
                ctm = (ctm[0] + e, ctm[1] + f)
            nums = []
        elif tok == b"Tm":
            if len(nums) >= 6:
                a, b_, c, d, e, f = nums[-6:]
                line_origin = (e, f)
            nums = []
        elif tok in (b"Td", b"TD"):
            if len(nums) >= 2:
                dx, dy = nums[-2:]
                line_origin = (line_origin[0] + dx, line_origin[1] + dy)
            nums = []
        elif tok == b"Tf":
            if nums:
                size = nums[-1]
            font = pending_font_name or font
            nums = []
        elif tok.startswith(b"/"):
            pending_font_name = tok[1:].decode("latin1")
        elif _NUM_RE.match(tok):
            try:
                nums.append(float(tok))
            except ValueError:
                pass
        else:
            nums = []
        i += 1

    return runs


def extract_positioned_runs(path: str) -> list:
    """Every text-show operation across the document, as TextRun(page, x, y,
    size, font, text) — order is stream order, not reading order."""
    runs = []
    for page_index, stream in enumerate(get_pages(path)):
        runs.extend(_run_positioned_text(stream, page_index))
    return runs


def extract_text(path: str, y_tolerance: float = 2.0) -> str:
    """Best-effort linear text dump: group runs into lines by page + rounded
    y, sort each line left-to-right, then order lines top-to-bottom per
    page. Reading order is only approximate for multi-column layouts."""
    runs = extract_positioned_runs(path)
    if not runs:
        return ""

    by_page = {}
    for r in runs:
        by_page.setdefault(r.page, []).append(r)

    out_lines = []
    for page in sorted(by_page):
        page_runs = sorted(by_page[page], key=lambda r: -r.y)
        lines = []  # list of [y, [runs]]
        for r in page_runs:
            placed = False
            for line in lines:
                if abs(line[0] - r.y) <= y_tolerance:
                    line[1].append(r)
                    placed = True
                    break
            if not placed:
                lines.append([r.y, [r]])
        for _, line_runs in lines:
            line_runs.sort(key=lambda r: r.x)
            line = " ".join(r.text for r in line_runs if r.text.strip())
            out_lines.append(re.sub(r"\s{2,}", " ", line).strip())
    return "\n".join(out_lines)
