#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Ner Edition  ·  PHASE 9  (Option A manuscript re-skin)
Zone structure for the candlelit-manuscript Ner base (base_ner_zohar.png).
Resolution-independent template: per-Parasha grid + word assignment happen in
Phase 10 (each Parasha has a different word count -> different grid size).
Here we define the 7 manuscript zones, validate them against the base, and
emit ner_map_template.json + ner_zones_preview.png.

Zones (bright/sacred -> empty):
  flame · page_bright · page_text · parchment · table_edge · near_dark · deep_dark

Luminance bands are data-driven from base_ner_zohar.png's histogram; the flame
is spatially gated to the candle region (it is the only place such brightness
means "flame" rather than lit parchment).

Local (Pillow + numpy).  python phase9_ner_map.py
"""
import json, sys, math
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
NER = HERE / "base_ner_zohar.png"          # approved Phase 8b typeset base

# flame spatial gate (normalized) — candle region, upper-left
FLAME_X_MAX = 0.24
FLAME_Y_MIN = 0.30
FLAME_Y_MAX = 0.48
FLAME_LUM_MIN = 200

# Ordered most-sacred -> emptiest. lum band [incl, excl) + role + palette.
NER_ZONES = [
    {"zone": "flame",       "role": "most sacred words, Divine Names",
     "lum": [FLAME_LUM_MIN, 256], "glyph": [255, 245, 220], "bg": [60, 42, 16]},
    {"zone": "page_bright", "role": "opening & closing words of each Parasha",
     "lum": [90, 256],  "glyph": [240, 210, 150], "bg": [44, 34, 18]},
    {"zone": "page_text",   "role": "body of the Zohar text",
     "lum": [45, 90],   "glyph": [210, 170, 110], "bg": [34, 26, 14]},
    {"zone": "parchment",   "role": "supporting passages",
     "lum": [22, 45],   "glyph": [170, 135, 85],  "bg": [26, 20, 11]},
    {"zone": "table_edge",  "role": "connective / repetitive words",
     "lum": [9, 22],    "glyph": [120, 90, 55],   "bg": [20, 15, 9]},
    {"zone": "near_dark",   "role": "sparse words",
     "lum": [2, 9],     "glyph": [80, 62, 40],    "bg": [12, 9, 6]},
    {"zone": "deep_dark",   "role": "empty / minimal",
     "lum": [0, 2],     "glyph": [55, 48, 42],    "bg": [4, 4, 6]},
]


def ner_zone(lum: int, x_frac: float, y_frac: float) -> str:
    """Classify a cell by luminance, with the flame spatially gated to the
    candle region (high brightness elsewhere is lit parchment, not flame)."""
    if (lum >= FLAME_LUM_MIN and x_frac <= FLAME_X_MAX
            and FLAME_Y_MIN <= y_frac <= FLAME_Y_MAX):
        return "flame"
    if lum >= 90:
        return "page_bright"
    if lum >= 45:
        return "page_text"
    if lum >= 22:
        return "parchment"
    if lum >= 9:
        return "table_edge"
    if lum >= 2:
        return "near_dark"
    return "deep_dark"


def classify_grid(lum_arr):
    rows, cols = lum_arr.shape
    counts = {z["zone"]: 0 for z in NER_ZONES}
    grid = np.empty((rows, cols), dtype=object)
    for r in range(rows):
        yf = r / max(1, rows - 1)
        for c in range(cols):
            xf = c / max(1, cols - 1)
            z = ner_zone(int(lum_arr[r, c]), xf, yf)
            grid[r, c] = z
            counts[z] += 1
    return grid, counts


def save_preview(grid, path):
    pal = {z["zone"]: tuple(z["glyph"]) for z in NER_ZONES}
    rows, cols = grid.shape
    arr = np.zeros((rows, cols, 3), np.uint8)
    for r in range(rows):
        for c in range(cols):
            arr[r, c] = pal[grid[r, c]]
    Image.fromarray(arr, "RGB").resize((cols * 3, rows * 3), Image.NEAREST).save(path)


def main():
    if not NER.exists():
        sys.exit(f"{NER.name} missing — run Phase 8b first.")
    src = Image.open(NER)
    base_w, base_h = src.size
    aspect = base_w / base_h

    # reference grid (~mid-size Parasha, 20k cells) purely to validate zone shape
    REF_N = 20000
    cols = max(1, round(math.sqrt(REF_N * aspect)))
    rows = max(1, round(cols / aspect))
    lum = np.asarray(src.convert("L").resize((cols, rows), Image.LANCZOS), np.float32)
    grid, counts = classify_grid(lum)
    save_preview(grid, HERE / "ner_zones_preview.png")

    total = cols * rows
    template = {
        "base_image": NER.name,
        "base_w": base_w, "base_h": base_h, "aspect": round(aspect, 4),
        "method": "per-cell luminance band + flame spatial gate; grid is per-Parasha (Phase 10)",
        "flame_gate": {"x_max": FLAME_X_MAX, "y_min": FLAME_Y_MIN,
                       "y_max": FLAME_Y_MAX, "lum_min": FLAME_LUM_MIN},
        "zones": NER_ZONES,
        "reference_grid": {"cols": cols, "rows": rows, "cells": total},
        "reference_distribution": {z: counts[z] for z in counts},
        "reference_distribution_pct": {z: round(100 * counts[z] / total, 2) for z in counts},
    }
    (HERE / "ner_map_template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Ner base {NER.name} {base_w}x{base_h} (aspect {aspect:.3f})")
    print(f"Reference grid {cols}x{rows} = {total:,} cells")
    print("Zone distribution (most sacred -> emptiest):")
    for z in NER_ZONES:
        n = counts[z["zone"]]
        print(f"  {n:>6,}  {100*n/total:5.2f}%  {z['zone']:<12} {z['role']}")
    print("\nWrote ner_map_template.json + ner_zones_preview.png")


if __name__ == "__main__":
    main()
