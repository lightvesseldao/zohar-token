#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Ner Edition  ·  PHASE 10
Generate all 53 Parasha composites: each Parasha's words become illuminated
micro-tiles placed onto the candlelit manuscript base (base_ner_zohar.png),
colored by the Phase 9 manuscript zone map, then framed as a Ner card.

Per token:
  - load parasha_words/<slug>.json
  - fit a grid to that Parasha's word count (each token differs)
  - assign words sequentially to cells; zone per cell from the Phase 9 map
  - composite zone-tinted word tiles onto base_ner_zohar.png (opacity by luminance)
  - add the delicate Ner gold frame: Hebrew name (Frank Ruhl gold) + ✦ + footer
  - save ner_output/ner_<slug>.png

Resume-safe: existing outputs are skipped. Progress saved every 5 tokens.
Local only (Pillow + numpy).  python phase10_ner_composite.py
"""
import sys, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from phase3_tiles import find_font_path, visual_rtl
from phase9_ner_map import NER_ZONES, ner_zone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE / "ner_bases"            # one unique typeset base per Parasha (phase8b_all)
INDEX = HERE / "tile_index.json"
TILES = HERE / "word_images"
PDIR = HERE / "parasha_words"
OUT = HERE / "ner_output"
PROGRESS = OUT / "_progress.json"

GLYPH = {z["zone"]: tuple(z["glyph"]) for z in NER_ZONES}
GOLD = (214, 176, 82)
GOLD_DEEP = (150, 120, 40)
CARD_BG = (10, 8, 6, 255)
FOOTER = "NER EDITION · LIGHTVESSEL DAO · 2026"


def lum_factor(lum: int) -> float:
    """Opacity by luminance. Steep curve: words blaze on the lit pages and fade
    into shadow so the dark zones stay 'empty/minimal' per the Phase 9 roles."""
    return 0.05 + 0.95 * (lum / 255.0) ** 1.25


def fit_grid(n: int, aspect: float):
    cols = max(1, round(math.sqrt(n * aspect)))
    rows = max(1, math.ceil(n / cols))
    return cols, rows


def build_get(index, cwi, chi):
    cache = {}
    solids = {z: Image.new("RGB", (cwi, chi), GLYPH[z]) for z in GLYPH}

    def get(word, zone):
        key = (word, zone)
        hit = cache.get(key, 0)
        if hit != 0:
            return hit
        fn = index.get(word)
        if not fn or not (TILES / fn).exists():
            cache[key] = None
            return None
        t = Image.open(TILES / fn).convert("RGBA").resize((cwi, chi), Image.LANCZOS)
        rgb = Image.blend(t.convert("RGB"), solids[zone], 0.35)
        cache[key] = (rgb, t.getchannel("A"))
        return cache[key]

    return get


def star4(d, cx, cy, R, fill):
    pts = []
    for k in range(8):
        ang = -math.pi / 2 + k * math.pi / 4
        rad = R if k % 2 == 0 else R * 0.40
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def draw_frame(card, art_box, hebrew, font_path, mtop, mbot):
    d = ImageDraw.Draw(card)
    W, _ = card.size
    x0, y0, x1, y1 = art_box

    # delicate twin gold border (thinner than Master Edition)
    d.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], outline=GOLD, width=1)
    d.rectangle([x0 - 9, y0 - 9, x1 + 9, y1 + 9], outline=GOLD_DEEP, width=1)

    # Hebrew Parasha name (top, Frank Ruhl gold), RTL-corrected
    name = visual_rtl(hebrew) or hebrew
    fname = ImageFont.truetype(font_path, int(mtop * 0.42))
    l, t, r, b = d.textbbox((0, 0), name, font=fname)
    d.text(((W - (r - l)) / 2 - l, mtop * 0.16), name, font=fname, fill=GOLD)

    # ✦ ornament between the name and the artwork
    star4(d, W / 2, mtop * 0.78, max(7, mtop * 0.085), GOLD)

    # footer
    ff = ImageFont.truetype(font_path, max(14, int(mbot * 0.27)))
    l, t, r, b = d.textbbox((0, 0), FOOTER, font=ff)
    d.text(((W - (r - l)) / 2 - l, y1 + mbot * 0.30), FOOTER, font=ff, fill=GOLD)


def compose_one(slug, index, font_path):
    data = json.loads((PDIR / f"{slug}.json").read_text(encoding="utf-8"))
    words = data["words"]
    hebrew = data["hebrew"]
    n = len(words)

    base = Image.open(BASE_DIR / f"base_ner_{slug}.png").convert("RGB")
    bw, bh = base.size
    aspect = bw / bh
    cols, rows = fit_grid(n, aspect)
    cwi = max(2, round(bw / cols))
    chi = max(2, round(bh / rows))

    lum = np.asarray(base.convert("L").resize((cols, rows), Image.LANCZOS), np.float32)
    get = build_get(index, cwi, chi)

    art = base.copy()
    placed = 0
    for idx in range(n):
        c = idx % cols
        r = idx // cols
        if r >= rows:
            break
        xf = c / max(1, cols - 1)
        yf = r / max(1, rows - 1)
        L = int(lum[r, c])
        zone = ner_zone(L, xf, yf)
        tile = get(words[idx]["w"], zone)
        if tile is None:
            continue
        rgb, alpha = tile
        f = lum_factor(L)
        mask = alpha.point(lambda v: int(v * f))
        art.paste(rgb, (round(c * bw / cols), round(r * bh / rows)), mask)
        placed += 1

    # frame
    mx = max(36, bw // 22)
    mtop = max(96, bh // 12)
    mbot = max(60, bh // 20)
    card = Image.new("RGBA", (bw + 2 * mx, bh + mtop + mbot), CARD_BG)
    card.alpha_composite(art.convert("RGBA"), (mx, mtop))
    draw_frame(card, (mx, mtop, mx + bw, mtop + bh), hebrew, font_path, mtop, mbot)

    OUT.mkdir(exist_ok=True)
    out_path = OUT / f"ner_{slug}.png"
    card.convert("RGB").save(out_path, "PNG")
    return out_path, placed, n, cols, rows


def main():
    for p in (BASE_DIR, INDEX, TILES, PDIR):
        if not p.exists():
            sys.exit(f"missing {p} (run phase8b_all.py first for the per-Parasha bases)")
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    font_path = find_font_path()

    slugs = sorted(p.stem for p in PDIR.glob("*.json"))
    OUT.mkdir(exist_ok=True)
    completed = []
    print(f"Phase 10: {len(slugs)} Ner composites -> {OUT}")
    for i, slug in enumerate(slugs, 1):
        out_path = OUT / f"ner_{slug}.png"
        if out_path.exists():
            print(f"[{i:>2}/53] skip (exists)  {slug}")
            completed.append(slug)
            continue
        if not (BASE_DIR / f"base_ner_{slug}.png").exists():
            print(f"[{i:>2}/53] MISSING BASE  {slug} (run phase8b_all.py)")
            continue
        op, placed, n, cols, rows = compose_one(slug, index, font_path)
        kb = op.stat().st_size // 1024
        print(f"[{i:>2}/53] {slug:<16} words={n:<6} grid={cols}x{rows} "
              f"placed={placed:<6} {kb} KB")
        completed.append(slug)
        if i % 5 == 0:
            PROGRESS.write_text(json.dumps({"completed": completed}, ensure_ascii=False),
                                encoding="utf-8")
            print(f"   ...progress saved ({len(completed)}/53)")

    PROGRESS.write_text(json.dumps({"completed": completed}, ensure_ascii=False),
                        encoding="utf-8")
    print(f"DONE. {len(completed)}/53 complete.")


if __name__ == "__main__":
    main()
