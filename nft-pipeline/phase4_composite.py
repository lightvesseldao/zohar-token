#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 4
Composite the Temple: every word-tile placed into its cell over the base Temple,
opacity driven by luminance, color by zone; then holographic foil + gold card frame.

Local only (Pillow + numpy). No API.

Usage:
    python phase4_composite.py                 # default cell=6  (~8K tall)
    python phase4_composite.py --cell 8        # larger / sharper / heavier
Output: zohar_token_master_final.png
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

from phase3_tiles import ZONE_PALETTES, find_font_path   # reuse palettes + font finder

HERE = Path(__file__).resolve().parent
MAP = HERE / "temple_map.json"
INDEX = HERE / "tile_index.json"
TILES = HERE / "word_images"


def lum_factor(lum: int) -> float:
    """0..255 luminance -> tile opacity. Shadow faint, light fully present."""
    return 0.20 + 0.80 * (lum / 255.0) ** 0.85


def build_tile_cache(cell: int):
    """Lazy cache of (word,zone) -> (small_rgb, small_alpha) at cell size, zone-tinted."""
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cache = {}
    solids = {z: Image.new("RGB", (cell, cell), p["glyph"]) for z, p in ZONE_PALETTES.items()}

    def get(word, zone):
        key = (word, zone)
        hit = cache.get(key)
        if hit is not None:
            return hit
        fn = index.get(word)
        if not fn:
            cache[key] = None
            return None
        try:
            t = Image.open(TILES / fn).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        except FileNotFoundError:
            cache[key] = None
            return None
        rgb = t.convert("RGB")
        rgb = Image.blend(rgb, solids.get(zone, rgb), 0.35)   # shift gold toward zone hue
        alpha = t.getchannel("A")
        cache[key] = (rgb, alpha)
        return cache[key]

    return get


def make_foil(w: int, h: int) -> Image.Image:
    """Iridescent diagonal rainbow, brighter toward the edges."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hue = ((xx / w + yy / h) * 0.5 + np.sin(xx / w * 6.28) * 0.05) % 1.0
    H = (hue * 255).astype(np.uint8)
    S = np.full((h, w), 115, np.uint8)
    V = np.full((h, w), 255, np.uint8)
    rgb = Image.merge("HSV", [Image.fromarray(H), Image.fromarray(S), Image.fromarray(V)]).convert("RGB")
    # edge-weighted alpha: ~0 in the center, shimmer only toward the borders
    cx, cy = (w - 1) / 2, (h - 1) / 2
    d = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    a = np.clip(d ** 3.0 * 60, 0, 55).astype(np.uint8)        # 0..55, edges only
    rgb.putalpha(Image.fromarray(a))
    return rgb


def draw_frame(card: Image.Image, art_box, font_path: str):
    """Gold filigree border + titles around the art."""
    d = ImageDraw.Draw(card)
    W, H = card.size
    x0, y0, x1, y1 = art_box
    gold, deep = (212, 175, 70), (150, 120, 30)

    for i, col in enumerate([deep, gold, gold, deep]):
        d.rectangle([x0 - 6 - i * 3, y0 - 6 - i * 3, x1 + 6 + i * 3, y1 + 6 + i * 3],
                    outline=col, width=2)
    # corner flourishes: gold diamond + short inward strokes
    m = max(14, (x1 - x0) // 48)
    off = 12
    for (cx, cy, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        ax, ay = cx - sx * off, cy - sy * off
        d.polygon([(ax, ay - m), (ax + m, ay), (ax, ay + m), (ax - m, ay)],
                  outline=gold, width=2)
        d.line([(ax, ay), (ax + sx * m * 2, ay)], fill=gold, width=2)
        d.line([(ax, ay), (ax, ay + sy * m * 2)], fill=gold, width=2)

    def centered(text, cy, size, fill):
        f = ImageFont.truetype(font_path, size)
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        d.text(((W - (r - l)) / 2 - l, cy), text, font=f, fill=fill)

    top_h = y0
    centered("ZOHAR TOKEN", top_h * 0.30, int(top_h * 0.40), gold)
    bot = (H - y1)
    centered("MASTER EDITION · LIGHTVESSEL DAO · 2026", y1 + bot * 0.30,
             max(14, int(bot * 0.16)), gold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", type=int, default=6, help="pixels per word cell")
    ap.add_argument("--out", default="zohar_token_master_final.png")
    ap.add_argument("--no-foil", dest="no_foil", action="store_true",
                    help="skip the holographic foil layer (clean recomposite)")
    a = ap.parse_args()

    for p in (MAP, INDEX, TILES):
        if not p.exists():
            sys.exit(f"missing {p} — run earlier phases first.")

    doc = json.loads(MAP.read_text(encoding="utf-8"))
    meta, cells = doc["meta"], doc["cells"]
    cols, rows = meta["grid_cols"], meta["grid_rows"]
    cell = a.cell
    art_w, art_h = cols * cell, rows * cell
    print(f"Composite art: {art_w} x {art_h}  ({cols}x{rows} cells @ {cell}px)")

    # base Temple as the underlayer
    base = Image.open(HERE / meta["base_image"]).convert("RGB").resize((art_w, art_h), Image.LANCZOS)
    art = base.convert("RGBA")

    get_tile = build_tile_cache(cell)
    placed = 0
    for c in cells:
        w = c.get("w")
        if not w:
            continue
        tile = get_tile(w, c["zone"])
        if tile is None:
            continue
        rgb, alpha = tile
        f = lum_factor(c["lum"])
        mask = alpha.point(lambda v: int(v * f))
        art.paste(rgb, (c["x"] * cell, c["y"] * cell), mask)
        placed += 1
        if placed % 100000 == 0:
            print(f"  placed {placed:,}/{len(cells):,}")
    print(f"placed {placed:,} word-tiles")

    # holographic foil
    if a.no_foil:
        print("--no-foil: skipping holographic foil layer")
    else:
        art = Image.alpha_composite(art, make_foil(art_w, art_h))

    # card frame
    font_path = find_font_path()
    margin_x = max(40, art_w // 14)
    margin_top = max(80, art_h // 22)
    margin_bot = max(70, art_h // 26)
    card = Image.new("RGBA", (art_w + 2 * margin_x, art_h + margin_top + margin_bot),
                     (8, 7, 16, 255))
    card.alpha_composite(art, (margin_x, margin_top))
    draw_frame(card, (margin_x, margin_top, margin_x + art_w, margin_top + art_h), font_path)

    out = HERE / a.out
    card.convert("RGB").save(out, "PNG")
    print(f"Saved {out}  ({card.size[0]}x{card.size[1]})")


if __name__ == "__main__":
    main()
