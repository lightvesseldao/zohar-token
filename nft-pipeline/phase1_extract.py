#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 1
Extract every Aramaic word of the Zohar corpus, in order.

Input : zohar_lightvessel_v1_2026.txt  (Sefaria-merged vocalized Zohar)
Output: words.json   — ordered stream, every word with section/chapter/position
        vocab.json   — unique consonantal forms + frequency
        phase1_stats.json — summary counts

Pure stdlib (no deps). Run:  python phase1_extract.py
"""
import json, re, sys, unicodedata
from pathlib import Path
from collections import Counter, OrderedDict

HERE = Path(__file__).resolve().parent
SRC  = HERE.parent / "zohar_lightvessel_v1_2026.txt"

# --- Unicode ranges -------------------------------------------------------
HE_LETTERS = r"א-ת"          # alef..tav incl. final forms
NIKUD      = r"֑-ׇ"          # cantillation + vowel points
GERESH     = r"׳״"           # ׳ ״  (also ASCII " ' appear inline)
MAQAF      = "־"                  # ־ word-joining hyphen

# a "word chunk" = run of Hebrew letters / nikud / geresh / inline quotes
WORD_RE = re.compile(rf"[{HE_LETTERS}{NIKUD}{GERESH}\"']+")
NIKUD_RE = re.compile(rf"[{NIKUD}]")
EDGE_QUOTES = re.compile(r"^[\"']+|[\"']+$")

# structural markers in the body
CHAP_RE = re.compile(r"(Chapter\s+\d+|Cap[ií]tulo\s+\d+|פֶּרֶק)")
SEP_RE  = re.compile(r"^[═━]{5,}\s*$")
TOC_RE  = re.compile(rf"^\s*\d+\s+[{HE_LETTERS}]")        # "2   בְּרֵאשִׁית  Bereshit ..."
BEGIN_MARK  = "BEGIN SACRED TEXT"   # end of front-matter
FIRST_TITLE = "הקדמה"               # first parsha (consonantal); body starts at its separator

# editorial apparatus to strip for the "clean" stream
PARENS = re.compile(r"\([^()]*\)")
BRACKS = re.compile(r"\[[^\[\]]*\]")


def strip_nikud(s: str) -> str:
    return NIKUD_RE.sub("", s)


def clean_token(tok: str):
    """Return (vocalized, consonantal) or None if not a real word."""
    tok = EDGE_QUOTES.sub("", tok)
    if not tok:
        return None
    cons = strip_nikud(tok)
    # must contain at least one Hebrew letter after stripping quotes/nikud
    if not re.search(rf"[{HE_LETTERS}]", cons):
        return None
    return tok, cons


def tokenize(text: str):
    """Yield (vocalized, consonantal) words. Splits maqaf-joined words."""
    for chunk in WORD_RE.findall(text):
        for piece in chunk.split(MAQAF):
            res = clean_token(piece)
            if res:
                yield res


def main():
    if not SRC.exists():
        sys.exit(f"Corpus not found: {SRC}")

    raw_lines = SRC.read_text(encoding="utf-8").splitlines()

    # locate body start: the separator line just before the first parsha title,
    # so the title-capture logic tags the opening section (Hakdamah) correctly.
    begin = next((i for i, ln in enumerate(raw_lines) if BEGIN_MARK in ln), -1)
    title_idx = next((i for i, ln in enumerate(raw_lines)
                      if i > begin and strip_nikud(ln.strip()) == FIRST_TITLE), None)
    if title_idx is None:
        sys.exit("Could not locate first parsha title — check corpus format.")
    start = title_idx - 1   # the '════' separator preceding the title

    # walk the body, tracking current section (parsha) and chapter
    section = "(prologue)"
    chapter = 0
    pending_section = None       # set when we pass a separator, captured on next He-only line

    stream = []                  # clean ordered words (apparatus removed)
    raw_token_count = 0          # including parenthetical/bracketed apparatus
    apparatus_tokens = 0

    i = start
    n = len(raw_lines)
    while i < n:
        line = raw_lines[i]
        i += 1
        stripped = line.strip()

        if SEP_RE.match(stripped):
            pending_section = "expect"
            continue

        # capture a parsha title: short Hebrew-led line right after a separator
        if pending_section == "expect":
            if stripped and re.match(rf"^[{HE_LETTERS}֑-ׇ\s׳״']+$", stripped) \
               and len(stripped) < 60:
                section = strip_nikud(stripped)
                chapter = 0
                pending_section = None
                continue
            pending_section = None  # not a title; fall through to normal handling

        if CHAP_RE.search(line):
            m = re.search(r"(\d+)", line)
            chapter = int(m.group(1)) if m else chapter + 1
            continue

        if TOC_RE.match(line):       # stray TOC-style line — skip
            continue

        if not re.search(rf"[{HE_LETTERS}]", line):
            continue                 # no Hebrew on this line

        # count raw tokens (with apparatus) for the "inclusive" total
        raw_here = list(tokenize(line))
        raw_token_count += len(raw_here)

        # clean line: drop parenthetical citations + bracketed editorial notes
        cleaned = BRACKS.sub(" ", PARENS.sub(" ", line))
        clean_here = list(tokenize(cleaned))
        apparatus_tokens += len(raw_here) - len(clean_here)

        for voc, cons in clean_here:
            stream.append({
                "i": len(stream),
                "sec": section,
                "ch": chapter,
                "w": voc,
                "c": cons,
            })

    # vocab (unique consonantal forms, by frequency)
    freq = Counter(item["c"] for item in stream)
    vocab = OrderedDict((w, c) for w, c in freq.most_common())

    stats = {
        "source_file": SRC.name,
        "total_words_clean": len(stream),
        "total_words_with_apparatus": raw_token_count,
        "apparatus_tokens_removed": apparatus_tokens,
        "unique_consonantal": len(freq),
        "unique_vocalized": len({item["w"] for item in stream}),
        "sections_seen": len({item["sec"] for item in stream}),
        "max_chapter": max((item["ch"] for item in stream), default=0),
    }

    (HERE / "words.json").write_text(
        json.dumps(stream, ensure_ascii=False), encoding="utf-8")
    (HERE / "vocab.json").write_text(
        json.dumps(vocab, ensure_ascii=False, indent=0), encoding="utf-8")
    (HERE / "phase1_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print("\nFirst 12 words:",
          " ".join(item["w"] for item in stream[:12]))


if __name__ == "__main__":
    main()
