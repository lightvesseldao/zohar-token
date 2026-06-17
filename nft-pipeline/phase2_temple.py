#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 2
(a) generate  : create the base Third-Temple image via Ideogram   [needs API key + $]
(b) map       : build temple_map.json from a base image + words.json  [no API, free]

Usage:
    python phase2_temple.py generate                 # 1 paid Ideogram call -> base_temple.png
    python phase2_temple.py map --base base_temple.png [--cells fit|N]

Deps: pillow, numpy, httpx  (pip install -r requirements.txt)
"""
import argparse, json, os, sys, math
from pathlib import Path

HERE = Path(__file__).resolve().parent

TEMPLE_PROMPT = (
    "Photorealistic Third Temple Beit HaMikdash HaShlishi, Jerusalem stone, golden "
    "divine light, Shekhinah descending from above, heavenly clouds, the Temple Mount, "
    "architectural masterpiece, every surface glowing with inner light, cinematic "
    "dramatic lighting, 8K ultra sharp, front elevation view, symmetrical composition, "
    "portrait orientation, no people, no text, pure architecture, sacred and "
    "transcendent, golden hour light, detailed stone texture, ornate gates, grand "
    "courtyard, Holy of Holies visible, rays of divine light, volumetric light beams"
)

CARD_W, CARD_H = 5, 7          # trading-card aspect 2.5 x 3.5


# --------------------------------------------------------------------------
def load_env():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# --------------------------------------------------------------------------
def generate():
    """One Ideogram call -> base_temple.png. EXTERNAL + PAID."""
    import httpx
    load_env()
    key = os.environ.get("IDEOGRAM_API_KEY")
    if not key:
        sys.exit("IDEOGRAM_API_KEY missing. Copy .env.template -> .env and fill it in.")

    endpoint = os.environ.get("IDEOGRAM_ENDPOINT", "https://api.ideogram.ai/generate")
    payload = {"image_request": {
        "prompt": TEMPLE_PROMPT,
        "model": os.environ.get("IDEOGRAM_MODEL", "V_2"),
        "aspect_ratio": os.environ.get("IDEOGRAM_ASPECT", "ASPECT_3_4"),
        "magic_prompt_option": "OFF",
    }}
    print("Calling Ideogram (this spends credits)...")
    r = httpx.post(endpoint, headers={"Api-Key": key}, json=payload, timeout=180)
    r.raise_for_status()
    url = r.json()["data"][0]["url"]
    img = httpx.get(url, timeout=180).content
    out = HERE / "base_temple.png"
    out.write_bytes(img)
    print(f"Saved {out} ({len(img)} bytes)")


# --------------------------------------------------------------------------
def fit_grid(n_words: int, target, aspect: float):
    """Return (cols, rows) at the given w/h aspect covering `target` cells."""
    n = n_words if target == "fit" else int(target)
    cols = max(1, round(math.sqrt(n * aspect)))
    rows = max(1, math.ceil(n / cols))
    return cols, rows


def zone_for(lum: float, y_frac: float) -> str:
    """Heuristic zone from luminance (0-1) + vertical position (0=top).
    Refine once the real base image is inspected."""
    if lum < 0.12:
        return "shadow"
    if y_frac < 0.22:
        return "sky"
    if y_frac < 0.38:
        return "dome" if lum > 0.45 else "sky"
    if y_frac > 0.80:
        return "courtyard"
    if lum > 0.70:
        return "pillar"
    if lum > 0.45:
        return "gate"
    return "wall"


def build_map(base_path: Path, target):
    import numpy as np
    from PIL import Image

    words = json.loads((HERE / "words.json").read_text(encoding="utf-8"))

    src = Image.open(base_path)
    base_w, base_h = src.size
    aspect = base_w / base_h                                # follow image, no distortion
    cols, rows = fit_grid(len(words), target, aspect)
    n_cells = cols * rows
    print(f"Base {base_w}x{base_h} (aspect {aspect:.3f}) -> "
          f"Grid {cols} x {rows} = {n_cells:,} cells for {len(words):,} words")

    img = src.convert("L").resize((cols, rows), Image.LANCZOS)   # one pixel per cell
    lum = np.asarray(img, dtype=np.float32) / 255.0        # rows x cols, 0..1

    cells = []
    for r in range(rows):
        y_frac = r / max(1, rows - 1)
        for c in range(cols):
            idx = r * cols + c
            L = float(lum[r, c])
            w = words[idx] if idx < len(words) else None
            cells.append({
                "x": c, "y": r,
                "lum": round(L * 255),
                "zone": zone_for(L, y_frac),
                "wi": w["i"] if w else None,      # word index into words.json
                "w": w["w"] if w else None,       # vocalized
                "c": w["c"] if w else None,       # consonantal (tile-image key)
            })

    zone_counts = {}
    for cell in cells:
        zone_counts[cell["zone"]] = zone_counts.get(cell["zone"], 0) + 1

    meta = {
        "base_image": base_path.name,
        "base_w": base_w, "base_h": base_h, "aspect": round(aspect, 4),
        "grid_cols": cols, "grid_rows": rows, "cell_count": n_cells,
        "words_placed": min(len(words), n_cells),
        "unique_tile_images_needed": len({c["c"] for c in cells if c["c"]}),
        "zone_counts": zone_counts,
    }
    (HERE / "temple_map.json").write_text(
        json.dumps({"meta": meta, "cells": cells}, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("generate")
    m = sub.add_parser("map")
    m.add_argument("--base", required=True)
    m.add_argument("--cells", default="fit", help="'fit' (one cell per word) or an integer")
    a = ap.parse_args()

    if a.cmd == "generate":
        generate()
    else:
        build_map(Path(a.base), a.cells)
