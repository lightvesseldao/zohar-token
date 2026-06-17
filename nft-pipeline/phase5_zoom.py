#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 5
Three preview crops:
  zoom_full.png  full card (downscaled)
  zoom_10.png    ~10% region, words emerging
  zoom_01.png    ~1% region, individual words legible (re-composited at full tile res)

Local only (Pillow + numpy). Run after phase4.
    python phase5_zoom.py
"""
import json, sys
from pathlib import Path
from PIL import Image
from phase3_tiles import ZONE_PALETTES
from phase4_composite import lum_factor

HERE = Path(__file__).resolve().parent
MAP = HERE / "temple_map.json"
INDEX = HERE / "tile_index.json"
TILES = HERE / "word_images"


def region_render(cells, cols, base, c0, r0, cw, rh, tile_px):
    """Re-composite a (cw x rh) cell window at tile_px resolution over the base crop."""
    out_w, out_h = cw * tile_px, rh * tile_px
    base_w, base_h = base.size
    # matching slice of the base, upscaled to the crop
    bx0 = int(c0 / cols * base_w)
    bx1 = int((c0 + cw) / cols * base_w)
    by0 = int(r0 / (len(cells) / cols) * base_h)
    by1 = int((r0 + rh) / (len(cells) / cols) * base_h)
    crop = base.crop((bx0, by0, bx1, by1)).resize((out_w, out_h), Image.LANCZOS).convert("RGBA")

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    solids = {z: Image.new("RGB", (tile_px, tile_px), p["glyph"]) for z, p in ZONE_PALETTES.items()}
    tcache = {}

    def tile(word, zone):
        key = (word, zone)
        if key in tcache:
            return tcache[key]
        fn = index.get(word)
        if not fn or not (TILES / fn).exists():
            tcache[key] = None
            return None
        t = Image.open(TILES / fn).convert("RGBA").resize((tile_px, tile_px), Image.LANCZOS)
        rgb = Image.blend(t.convert("RGB"), solids.get(zone, t.convert("RGB")), 0.35)
        tcache[key] = (rgb, t.getchannel("A"))
        return tcache[key]

    for r in range(r0, r0 + rh):
        for c in range(c0, c0 + cw):
            idx = r * cols + c
            if idx >= len(cells):
                continue
            cell = cells[idx]
            if not cell.get("w"):
                continue
            got = tile(cell["w"], cell["zone"])
            if not got:
                continue
            rgb, alpha = got
            mask = alpha.point(lambda v: int(v * lum_factor(cell["lum"])))
            crop.paste(rgb, ((c - c0) * tile_px, (r - r0) * tile_px), mask)
    return crop.convert("RGB")


def main():
    doc = json.loads(MAP.read_text(encoding="utf-8"))
    meta, cells = doc["meta"], doc["cells"]
    cols, rows = meta["grid_cols"], meta["grid_rows"]
    base = Image.open(HERE / meta["base_image"]).convert("RGB")

    # full card preview
    final = HERE / "zohar_token_master_final.png"
    if final.exists():
        f = Image.open(final)
        f.copy().resize((round(f.width * 1600 / f.height), 1600), Image.LANCZOS)\
            .save(HERE / "zoom_full.png")
        print("zoom_full.png")

    # center crops around the Temple's bright center
    ccx, ccy = cols // 2, int(rows * 0.42)

    # ~10% linear region, emerging words
    cw10, rh10 = max(8, cols // 10), max(8, rows // 10)
    region_render(cells, cols, base, ccx - cw10 // 2, ccy - rh10 // 2, cw10, rh10, 24)\
        .save(HERE / "zoom_10.png")
    print(f"zoom_10.png  ({cw10}x{rh10} cells @24px)")

    # ~1% linear region, fully legible words at native tile res
    cw1, rh1 = 16, 24
    region_render(cells, cols, base, ccx - cw1 // 2, ccy - rh1 // 2, cw1, rh1, 128)\
        .save(HERE / "zoom_01.png")
    print(f"zoom_01.png  ({cw1}x{rh1} cells @128px)")


if __name__ == "__main__":
    main()
