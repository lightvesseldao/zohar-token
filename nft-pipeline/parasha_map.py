#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 7
Group the 849,882 ordered words (words.json) into per-Parasha word lists.

Output: parasha_words/  — 54 JSON files
  51 section files (incl. hakdamah, idra_rabba, idra_zuta) + 3 Hakdamah-derived
  portions (reeh, nitzavim, ki_tavo).

NOTE: Hakdamah has only 34 chapters, so the spec's 1-40/41-80/81+ split is scaled
to three contiguous thirds of its actual chapter range. Adjust HAKDAMAH_SPLIT below.

Local stdlib only.  python parasha_map.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS = HERE / "words.json"
OUT = HERE / "parasha_words"

# exact (nikud-stripped) section string in words.json  ->  output slug
SLUG = {
    "הקדמה": "hakdamah",
    "בראשית": "beresheet", "נח": "noach", "לך לך": "lech_lecha", "וירא": "vayera",
    "חיי שרה": "chayei_sarah", "תולדות": "toldot", "ויצא": "vayetzei",
    "וישלח": "vayishlach", "וישב": "vayeshev", "מקץ": "miketz", "ויגש": "vayigash",
    "ויחי": "vayechi", "שמות": "shemot", "וארא": "vaera", "בא": "bo",
    "בשלח": "beshalach", "יתרו": "yitro", "משפטים": "mishpatim", "תרומה": "terumah",
    "ספרא דצניעותא": "sifra_ditzniuta", "תצוה": "tetzaveh", "כי תשא": "ki_tisa",
    "ויקהל": "vayakhel", "פקודי": "pekudei", "ויקרא": "vayikra", "צו": "tzav",
    "שמיני": "shemini", "תזריע": "tazria", "מצרע": "metzora", "אחרי מות": "acharei_mot",
    "קדשים": "kedoshim", "אמור": "emor", "בהר": "behar", "בחקתי": "bechukotai",
    "במדבר": "bamidbar", "נשא": "naso", "האדרא רבא": "idra_rabba",
    "בהעלתך": "behaalotecha", "שלח לך": "shelach_lecha", "קרח": "korach",
    "חקת": "chukat", "בלק": "balak", "פינחס": "pinchas", "מטות": "matot",
    "עקב": "ekev", "שופטים": "shoftim", "כי תצא": "ki_tetze", "וילך": "vayelech",
    "האזינו": "haazinu", "האדרא זוטא": "idra_zuta",
}

# Hakdamah-derived portions: (slug, chapter_lo_frac, chapter_hi_frac) of its real range
HAKDAMAH_SPLIT = [("reeh", 0.0, 1 / 3), ("nitzavim", 1 / 3, 2 / 3), ("ki_tavo", 2 / 3, 1.0)]


def write_list(slug, hebrew, words):
    rec = {
        "slug": slug,
        "hebrew": hebrew,
        "word_count": len(words),
        "chapter_range": [min((w["ch"] for w in words), default=0),
                          max((w["ch"] for w in words), default=0)],
        "words": [{"i": w["i"], "ch": w["ch"], "w": w["w"], "c": w["c"]} for w in words],
    }
    (OUT / f"{slug}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return len(words)


def main():
    if not WORDS.exists():
        sys.exit("words.json missing — run phase1_extract.py first.")
    words = json.loads(WORDS.read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)

    # group by section, preserving order + first-appearance order of sections
    groups, order = {}, []
    for w in words:
        s = w["sec"]
        if s not in groups:
            groups[s] = []
            order.append(s)
        groups[s].append(w)

    missing = [s for s in order if s not in SLUG]
    if missing:
        sys.exit(f"Unmapped sections: {missing!r}")

    counts, files = [], 0
    for s in order:
        files += 1
        counts.append((SLUG[s], write_list(SLUG[s], s, groups[s])))

    # Hakdamah-derived portions by contiguous chapter thirds
    hak = groups["הקדמה"]
    chs = sorted({w["ch"] for w in hak})
    lo, hi = chs[0], chs[-1]
    span = hi - lo + 1
    print(f"\nHakdamah real chapters: {lo}-{hi} ({span} chapters)")
    for slug, f0, f1 in HAKDAMAH_SPLIT:
        c0 = lo + int(round(f0 * span))
        c1 = lo + int(round(f1 * span)) - 1
        if slug == HAKDAMAH_SPLIT[-1][0]:
            c1 = hi
        portion = [w for w in hak if c0 <= w["ch"] <= c1]
        files += 1
        counts.append((f"{slug} (Hakdamah ch {c0}-{c1})", write_list(slug, "הקדמה", portion)))

    # report
    counts_sorted = sorted(counts, key=lambda x: -x[1])
    print(f"\n{files} files written to {OUT.name}/  "
          f"(total words grouped: {sum(len(v) for v in groups.values()):,})\n")
    print("Per-Parasha word counts (largest first):")
    for name, n in counts_sorted:
        print(f"  {n:>7,}  {name}")


if __name__ == "__main__":
    main()
