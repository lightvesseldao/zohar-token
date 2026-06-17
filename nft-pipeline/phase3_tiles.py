#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 3
Render one illuminated micro word-image per unique Zohar word.

Pure local Python + Pillow only (stdlib + PIL). NO API calls, NO other deps.

Design: tiles are base-image-INDEPENDENT (gold calligraphy on a midnight vignette,
transparent edges). Per-zone color + opacity + rotation are applied later at
composite time (Phase 4) using ZONE_PALETTES below — so this can run *now*,
before the Temple PNG exists.

Correct Hebrew without libraqm: Pillow draws left-to-right, which visually reverses
Hebrew. We cluster-reverse (each base letter keeps its trailing nikud) so the word
reads right-to-left correctly.

Usage:
    python phase3_tiles.py                 # render all unique vocalized words
    python phase3_tiles.py --size 128 --key vocalized
    python phase3_tiles.py --key consonantal   # 49,878 tiles, no nikud
    python phase3_tiles.py --limit 200         # quick sample for review
Resume-safe: existing tiles are skipped. Re-run any time.
"""
import argparse, hashlib, json, sys, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
WORDS = HERE / "words.json"
OUT_DIR = HERE / "word_images"
INDEX = HERE / "tile_index.json"

# Canonical zone palettes (gold/light per architectural zone).
# Phase 4 multiplies these over the neutral gold glyph + backing.
ZONE_PALETTES = {
    "wall":      {"glyph": (255, 200, 90),  "bg": (40, 26, 8)},    # warm gold / amber
    "pillar":    {"glyph": (255, 244, 210), "bg": (46, 40, 26)},   # white gold / ivory
    "gate":      {"glyph": (235, 170, 60),  "bg": (38, 22, 6)},    # deep gold / bronze
    "dome":      {"glyph": (180, 210, 255), "bg": (10, 18, 46)},   # celestial blue / gold
    "courtyard": {"glyph": (255, 226, 170), "bg": (40, 32, 18)},   # warm stone / light
    "sky":       {"glyph": (200, 180, 255), "bg": (12, 10, 38)},   # deep indigo / violet
    "shadow":    {"glyph": (140, 170, 220), "bg": (6, 10, 28)},    # deep blue / charcoal
}

# Font fallback chain (Frank Ruhl first, per spec).
FONT_CANDIDATES = ["frank.ttf", "david.ttf", "davidbd.ttf", "times.ttf", "arial.ttf"]

# Hebrew base-letter range (alef..tav incl. finals)
HE_BASE = range(0x05D0, 0x05EB)


# --------------------------------------------------------------------------
def find_font_path() -> str:
    import os, glob
    fdir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name in FONT_CANDIDATES:
        p = fdir / name
        if p.exists():
            return str(p)
    # last resort: any ttf
    any_ttf = glob.glob(str(fdir / "*.ttf"))
    if any_ttf:
        return any_ttf[0]
    sys.exit("No TrueType font found.")


def visual_rtl(word: str) -> str:
    """Reorder logical Hebrew to visual order for LTR drawing.
    Each base char keeps its following combining marks (nikud/te'amim)."""
    clusters, cur = [], ""
    for ch in word:
        if unicodedata.combining(ch):
            cur += ch                      # mark sticks to current base
        else:
            if cur:
                clusters.append(cur)
            cur = ch
    if cur:
        clusters.append(cur)
    return "".join(reversed(clusters))


def fit_font(font_path: str, text: str, box: int, pad: int):
    """Pick the largest font size fitting `text` in a box-sized square."""
    probe = ImageFont.truetype(font_path, 100)
    l, t, r, b = probe.getbbox(text)
    w, h = max(1, r - l), max(1, b - t)
    avail = box - 2 * pad
    scale = min(avail / w, avail / h)
    size = max(8, min(int(100 * scale), box * 2))
    return ImageFont.truetype(font_path, size)


def make_backing(size: int) -> Image.Image:
    """Reusable midnight-blue radial vignette, transparent at the edges."""
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = bg.load()
    cx = cy = (size - 1) / 2
    maxd = (cx ** 2 + cy ** 2) ** 0.5
    for y in range(size):
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / maxd
            a = int(max(0, 1 - d ** 1.4) * 235)         # fade to transparent
            px[x, y] = (10, 14, 40, a)
    return bg


def gold_gradient(size: int) -> Image.Image:
    """Reusable vertical gold gradient (bright top -> deep bottom)."""
    top, bot = (255, 233, 168), (200, 150, 30)
    grad = Image.new("RGB", (1, size))
    gp = grad.load()
    for y in range(size):
        f = y / max(1, size - 1)
        gp[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * f) for i in range(3))
    return grad.resize((size, size))


def render_tile(text_visual: str, font: ImageFont.FreeTypeFont,
                size: int, backing: Image.Image, grad: Image.Image) -> Image.Image:
    # glyph alpha mask, centered
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    l, t, r, b = d.textbbox((0, 0), text_visual, font=font)
    x = (size - (r - l)) // 2 - l
    y = (size - (b - t)) // 2 - t
    d.text((x, y), text_visual, fill=255, font=font)

    # soft glow halo behind the gold letters
    glow = mask.filter(ImageFilter.GaussianBlur(size / 22))

    tile = backing.copy()
    # halo: warm gold, low alpha
    halo = Image.new("RGBA", (size, size), (255, 210, 120, 0))
    halo.putalpha(glow.point(lambda v: int(v * 0.6)))
    tile = Image.alpha_composite(tile, halo)
    # gold gradient letters
    letters = grad.convert("RGBA")
    letters.putalpha(mask)
    tile = Image.alpha_composite(tile, letters)
    return tile


def fname(word: str) -> str:
    return hashlib.sha1(word.encode("utf-8")).hexdigest()[:16] + ".png"


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=128, help="tile px (square)")
    ap.add_argument("--key", choices=["vocalized", "consonantal"], default="vocalized")
    ap.add_argument("--limit", type=int, default=0, help="render only first N (sampling)")
    ap.add_argument("--outdir", default=str(OUT_DIR))
    a = ap.parse_args()

    if not WORDS.exists():
        sys.exit("words.json missing — run phase1_extract.py first.")

    words = json.loads(WORDS.read_text(encoding="utf-8"))
    field = "w" if a.key == "vocalized" else "c"

    # unique words in first-appearance order
    seen, uniq = set(), []
    for item in words:
        v = item[field]
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    if a.limit:
        uniq = uniq[:a.limit]

    out = Path(a.outdir)
    out.mkdir(exist_ok=True)
    font_path = find_font_path()
    pad = max(4, a.size // 12)
    backing = make_backing(a.size)
    grad = gold_gradient(a.size)

    print(f"Font: {font_path}")
    print(f"Rendering {len(uniq):,} unique {a.key} tiles @ {a.size}px -> {out}")

    index = {"_meta": {"key": a.key, "size": a.size, "count": len(uniq),
                       "font": Path(font_path).name}}
    rendered = skipped = 0
    for n, word in enumerate(uniq, 1):
        fn = fname(word)
        index[word] = fn
        fp = out / fn
        if fp.exists():
            skipped += 1
        else:
            font = fit_font(font_path, visual_rtl(word) or word, a.size, pad)
            tile = render_tile(visual_rtl(word) or word, font, a.size, backing, grad)
            tile.save(fp)
            rendered += 1
        if n % 2000 == 0:
            INDEX.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
            print(f"  {n:,}/{len(uniq):,}  (rendered {rendered:,}, skipped {skipped:,})")

    INDEX.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"Done. rendered={rendered:,} skipped={skipped:,} index={INDEX.name}")


if __name__ == "__main__":
    main()
