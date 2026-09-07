"""Heuristic, deterministic scorers for the five categories in
marketing_rubric.pdf.

These are rule-based text-analysis checks, not editorial judgment — they
give a fast, consistent, explainable first pass and flag concrete places to
look, calibrated against the rubric's own score descriptions. They are not a
substitute for a human editor, and a document scoring well here can still
read poorly, and vice versa. See README.md for the specific thresholds used
in each category and how to tune them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from readers import DocumentContent

# --------------------------------------------------------------- shared ---

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")
_WORD_RE = re.compile(r"[A-Za-z']+")


def split_sentences(text: str) -> list:
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def count_syllables(word: str) -> int:
    word = word.lower()
    if not word:
        return 0
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and not word.endswith("le") and n > 1:
        n -= 1
    return max(1, n)


def truncate(s: str, n: int = 110) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def sentences_of(doc: DocumentContent) -> list:
    """Sentence-split each paragraph independently rather than the whole
    joined document. Splitting the joined text in one pass lets a paragraph
    with no terminal punctuation — a bullet, a slide line, a heading, a
    table cell — run on into the next paragraph's sentence, which silently
    wrecks words-per-sentence based metrics (Flesch) on anything bulleted."""
    out = []
    for p in doc.paragraphs:
        p = p.strip()
        if not p:
            continue
        found = split_sentences(p)
        out.extend(found if found else [p])
    return out


@dataclass
class Finding:
    category: str
    location: str
    snippet: str
    issue: str
    suggestion: str


@dataclass
class CategoryResult:
    category: str
    score: int
    rationale: str
    findings: list = field(default_factory=list)


# ------------------------------------------------------- 1. tone/voice ---

_HYPE_WORDS = {
    "amazing", "awesome", "incredible", "revolutionary", "game-changing",
    "game changer", "unbelievable", "mind-blowing", "insane", "crazy",
    "epic", "unstoppable", "world-class", "best-in-class", "cutting-edge",
    "supercharge", "turbocharge", "unleash", "unlock", "next-level",
    "rockstar", "ninja", "guru", "hacks",
}
_SLANG_PHRASES = {"gonna", "wanna", "gotta", "kinda", "sorta", "y'all", "you guys"}
_CONTRACTION_RE = re.compile(r"\b\w+'(?:t|re|ve|ll|d|s|m)\b", re.I)


def score_tone(doc: DocumentContent) -> CategoryResult:
    text = doc.text
    words = _WORD_RE.findall(text)
    word_count = max(1, len(words))
    findings = []

    lower = text.lower()
    hype_hits = 0
    for phrase in _HYPE_WORDS | _SLANG_PHRASES:
        c = lower.count(phrase)
        if c:
            hype_hits += c

    exclam_hits = text.count("!")
    caps_words = [w for w in words if len(w) >= 4 and w.isupper()]
    contraction_hits = len(_CONTRACTION_RE.findall(text))

    for sent in sentences_of(doc):
        s_lower = sent.lower()
        hit_terms = [t for t in (_HYPE_WORDS | _SLANG_PHRASES) if t in s_lower]
        if hit_terms:
            findings.append(Finding(
                "Tone and Professional Voice", "", truncate(sent),
                f"Informal/promotional language: {', '.join(sorted(hit_terms))}.",
                f"Replace with a concrete, specific claim (what exactly makes it {hit_terms[0]!r}?).",
            ))
        if sent.count("!") >= 2:
            findings.append(Finding(
                "Tone and Professional Voice", "", truncate(sent),
                "Multiple exclamation points in one sentence.",
                "Use at most one exclamation point, or none, for a professional tone.",
            ))

    # Violation density per 100 words drives the score, in line with the
    # rubric's wording ("minor" / "some" / "frequent" / "often").
    density = 100 * (hype_hits + contraction_hits + len(caps_words) + max(0, exclam_hits - 1)) / word_count
    if density < 0.5:
        score = 5
    elif density < 1.5:
        score = 4
    elif density < 3.0:
        score = 3
    elif density < 6.0:
        score = 2
    elif density < 10.0:
        score = 1
    else:
        score = 0

    rationale = (
        f"{hype_hits} promotional/slang term(s), {contraction_hits} contraction(s), "
        f"{len(caps_words)} ALL-CAPS word(s), {exclam_hits} exclamation mark(s) "
        f"across {word_count} words (density {density:.1f} per 100 words)."
    )
    return CategoryResult("Tone and Professional Voice", score, rationale, findings)


# --------------------------------------------------- 2. clarity/readability

_PASSIVE_RE = re.compile(
    r"\b(am|is|are|was|were|be|been|being)\s+(\w+ed|born|built|chosen|done|"
    r"driven|given|known|made|paid|seen|shown|sold|taken|written)\b", re.I,
)


def _flesch_reading_ease(sentences: list) -> float:
    words = [w for s in sentences for w in _WORD_RE.findall(s)]
    if not sentences or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syllables / len(words))


def score_clarity(doc: DocumentContent) -> CategoryResult:
    findings = []

    if doc.is_freeform_layout:
        return CategoryResult(
            "Clarity and Readability", 4,
            "This document is a visual one-sheet/infographic, not continuous prose — "
            "sentence-level readability metrics don't apply cleanly, so no automated "
            "score below 4 is asserted here. Review labels and captions manually for "
            "clarity instead.",
            findings,
        )

    sentences = sentences_of(doc)
    if not sentences:
        return CategoryResult("Clarity and Readability", 3, "No prose sentences found to analyze.", findings)

    fre = _flesch_reading_ease(sentences)
    long_sentences = [s for s in sentences if len(_WORD_RE.findall(s)) > 28]
    passive_sentences = [s for s in sentences if _PASSIVE_RE.search(s)]
    passive_ratio = len(passive_sentences) / len(sentences)

    for s in long_sentences[:8]:
        wc = len(_WORD_RE.findall(s))
        findings.append(Finding(
            "Clarity and Readability", "", truncate(s),
            f"Long sentence ({wc} words).",
            f"Split into two sentences (currently {wc} words; aim for under 25).",
        ))
    for s in passive_sentences[:8]:
        findings.append(Finding(
            "Clarity and Readability", "", truncate(s),
            "Passive voice.",
            "Rewrite in active voice — name who or what performs the action.",
        ))

    if fre >= 60:
        score = 5
    elif fre >= 50:
        score = 4
    elif fre >= 40:
        score = 3
    elif fre >= 30:
        score = 2
    elif fre >= 20:
        score = 1
    else:
        score = 0

    if passive_ratio > 0.35 or (len(sentences) and len(long_sentences) / len(sentences) > 0.35):
        score = max(0, score - 1)

    rationale = (
        f"Flesch Reading Ease {fre:.0f} (higher = easier); "
        f"{len(long_sentences)}/{len(sentences)} sentences over 28 words; "
        f"{len(passive_sentences)}/{len(sentences)} passive-voice ({passive_ratio:.0%})."
    )
    return CategoryResult("Clarity and Readability", score, rationale, findings)


# ------------------------------------------------- 3. formatting/structure

def score_formatting(doc: DocumentContent) -> CategoryResult:
    findings = []
    para_count = len(doc.paragraphs)

    if doc.is_freeform_layout:
        return CategoryResult(
            "Formatting and Structure", 4,
            "Visual one-sheet layout — structure is carried by graphic design "
            "(columns, callout boxes) rather than headings, so heading-based "
            "checks don't apply. Not automatically scored below 4.",
            findings,
        )

    if para_count == 0:
        return CategoryResult("Formatting and Structure", 0, "No content found.", findings)

    has_headings = len(doc.headings) > 0
    long_doc = doc.word_count > 400

    if long_doc and not has_headings:
        findings.append(Finding(
            "Formatting and Structure", "whole document", "",
            f"No headings found in a {doc.word_count}-word document.",
            "Break this into labeled sections so readers can scan it.",
        ))

    # Heading hierarchy: flag a level jump greater than 1 (e.g. H1 -> H3).
    levels = [h.level for h in doc.headings]
    for i in range(1, len(levels)):
        if levels[i] - levels[i - 1] > 1:
            h = doc.headings[i]
            findings.append(Finding(
                "Formatting and Structure", f"heading {i+1}", truncate(h.text, 70),
                f"Heading level jumps from H{levels[i-1]} to H{levels[i]}.",
                f"Insert an intermediate H{levels[i-1]+1} heading, or promote this to H{levels[i-1]+1}.",
            ))

    # Very long unbroken paragraphs (no lists, no sub-breaks) read as a wall
    # of text.
    very_long = [i for i, p in enumerate(doc.paragraphs) if len(_WORD_RE.findall(p)) > 180]
    for i in very_long[:5]:
        findings.append(Finding(
            "Formatting and Structure", f"paragraph {i+1}", truncate(doc.paragraphs[i]),
            f"Very long paragraph ({len(_WORD_RE.findall(doc.paragraphs[i]))} words) with no sub-breaks.",
            "Split into shorter paragraphs or convert part of it to a bullet list.",
        ))

    violation_count = len(findings)
    if violation_count == 0 and has_headings:
        score = 5
    elif violation_count <= 1:
        score = 4
    elif violation_count <= 3:
        score = 3
    elif violation_count <= 6:
        score = 2
    elif violation_count <= 10:
        score = 1
    else:
        score = 0
    if not has_headings and not long_doc:
        # A short document (blog post, single slide) isn't expected to have
        # headings — don't penalize structure heavily for that alone.
        score = max(score, 3)

    rationale = (
        f"{len(doc.headings)} heading(s), {len(doc.list_items)} list item(s) across "
        f"{para_count} paragraph(s); {len(very_long)} very long paragraph(s); "
        f"{violation_count} structural issue(s) flagged."
    )
    return CategoryResult("Formatting and Structure", score, rationale, findings)


# --------------------------------------------------- 4. data and evidence

_NUMBER_RE = re.compile(
    r"(?<![\w.])(\$?\d[\d,]*(?:\.\d+)?%?|\$\d[\d,]*(?:\.\d+)?[MBK]?)(?![\w])"
)
_CONTEXT_CUES = re.compile(
    r"\b(increase|decrease|compared to|of total|representing|growth|from .+ to|"
    r"year[- ]over[- ]year|source:|according to|versus|vs\.?|up from|down from|"
    r"percent|per year|annually|quarter|cumulative|respectively)\b", re.I,
)


def score_data_usage(doc: DocumentContent) -> CategoryResult:
    text = doc.text
    findings = []
    numbers = list(_NUMBER_RE.finditer(text))

    if not numbers:
        return CategoryResult(
            "Data and Evidence Usage", 4,
            "No quantitative claims found in this document — this category is "
            "not strongly applicable to purely narrative content.",
            findings,
        )

    contextualized = 0
    for m in numbers:
        window = text[max(0, m.start() - 50): m.end() + 50]
        if _CONTEXT_CUES.search(window):
            contextualized += 1
        else:
            findings.append(Finding(
                "Data and Evidence Usage", "", truncate(window),
                f"Figure '{m.group(0)}' has no visible source, comparison, or unit context nearby.",
                "Add a comparison, time frame, or source so the figure is interpretable on its own.",
            ))

    ratio = contextualized / len(numbers)
    if ratio >= 0.95:
        score = 5
    elif ratio >= 0.75:
        score = 4
    elif ratio >= 0.5:
        score = 3
    elif ratio >= 0.25:
        score = 2
    else:
        score = 1

    rationale = f"{contextualized}/{len(numbers)} numeric claims have nearby context ({ratio:.0%})."
    return CategoryResult("Data and Evidence Usage", score, rationale, findings[:10])


# --------------------------------------------- 5. compliance w/ style guide

def load_style_guide(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_style_guide(doc: DocumentContent, style_guide: dict) -> CategoryResult:
    text = doc.text
    findings = []
    banned = style_guide.get("banned_terms", {})
    mech = style_guide.get("mechanical_rules", {})
    heading_rules = style_guide.get("heading_style", {})

    term_hits = 0
    for term, replacement in banned.items():
        for m in re.finditer(re.escape(term), text, re.I):
            term_hits += 1
            window = text[max(0, m.start() - 40): m.end() + 40]
            findings.append(Finding(
                "Compliance With Style Guide", "", truncate(window),
                f"Uses banned/discouraged term '{term}'.",
                f"Replace with: {replacement}.",
            ))

    mech_hits = 0
    if mech.get("no_double_spaces") and "  " in text:
        mech_hits += text.count("  ")
        findings.append(Finding(
            "Compliance With Style Guide", "whole document", "",
            f"{text.count('  ')} instance(s) of double spaces.",
            "Run a find-and-replace for double spaces.",
        ))
    if mech.get("no_mixed_quote_styles"):
        has_straight = "\"" in text or "'" in text
        has_curly = any(c in text for c in "“”‘’")
        if has_straight and has_curly:
            mech_hits += 1
            findings.append(Finding(
                "Compliance With Style Guide", "whole document", "",
                "Mixes straight and curly quotation marks.",
                "Standardize on one quote style throughout (curly is typical for finished copy).",
            ))

    if heading_rules.get("no_terminal_period"):
        for h in doc.headings:
            if h.text.strip().endswith("."):
                mech_hits += 1
                findings.append(Finding(
                    "Compliance With Style Guide", "heading", truncate(h.text, 70),
                    "Heading ends with a period.",
                    "Remove the trailing period from headings.",
                ))

    word_count = max(1, doc.word_count)
    density = 100 * (term_hits + mech_hits) / word_count
    if density < 0.3:
        score = 5
    elif density < 1.0:
        score = 4
    elif density < 2.5:
        score = 3
    elif density < 5.0:
        score = 2
    elif density < 8.0:
        score = 1
    else:
        score = 0

    rationale = (
        f"{term_hits} banned-term hit(s), {mech_hits} mechanical style issue(s) "
        f"across {word_count} words (density {density:.1f} per 100 words)."
    )
    return CategoryResult("Compliance With Style Guide", score, rationale, findings[:10])


# --------------------------------------------------------------- runner ---

def score_document(doc: DocumentContent, style_guide: dict) -> list:
    return [
        score_tone(doc),
        score_clarity(doc),
        score_formatting(doc),
        score_data_usage(doc),
        score_style_guide(doc, style_guide),
    ]
