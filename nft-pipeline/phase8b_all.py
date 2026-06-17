#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 8b (ALL) — one unique typeset manuscript base per Parasha.

For each of the 53 Parashiot:
  - take the clean manuscript base (base_ner.png, no real text)
  - extract the first WORDS_PER_TOKEN words from parasha_words/<slug>.json
  - typeset them in Frank Ruhl onto the two pages via perspective transform:
        RIGHT page = lines 1-18 (first words)   [Hebrew book reads right first]
        LEFT  page = lines 19-36 (continuation)
  - multiply-blend the sepia ink onto the parchment
  - save ner_bases/base_ner_<slug>.png

Resume-safe: existing bases are skipped.
Local only (Pillow + numpy).

  python phase8b_all.py                      # all 53
  python phase8b_all.py --only beresheet,noach   # just these (for sampling)
"""
import sys, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BASE = HERE / "base_ner.png"               # clean manuscript, no real text
PDIR = HERE / "parasha_words"
OUTDIR = HERE / "ner_bases"
FONT_PATH = r"C:\Windows\Fonts\frank.ttf"

USE_POINTED = False           # False -> consonantal `c` (manuscript-authentic)
OPACITY = 0.70                # multiply-blend strength
INK = (38, 24, 12)            # dark sepia ink
SS = 3                        # supersample for crisp text
WORDS_PER_TOKEN = 250
LINES_PER_PAGE = 18

# perspective destination quads in base_ner.png coords (TL, TR, BR, BL)
LEFT_QUAD = [(326, 765), (520, 765), (436, 1045), (121, 1045)]
RIGHT_QUAD = [(520, 765), (714, 765), (752, 1045), (436, 1045)]
PAGE_W, PAGE_H = 600, 860
MARGIN = 46

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_words(slug):
    d = json.loads((PDIR / f"{slug}.json").read_text(encoding="utf-8"))
    key = "w" if USE_POINTED else "c"
    return [w[key] for w in d["words"][:WORDS_PER_TOKEN]], d["hebrew"]


def render_page(words, font, line_h_ss):
    """Render Hebrew RTL onto a transparent flat page, up to LINES_PER_PAGE
    lines. Returns (downscaled RGBA, words_used)."""
    W, H = PAGE_W * SS, PAGE_H * SS
    m = MARGIN * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    space = d.textlength(" ", font=font)
    right, left = W - m, m
    x, y, line, used = right, m, 1, 0
    for w in words:
        wl = d.textlength(w, font=font)
        if x - wl < left:                      # wrap
            line += 1
            if line > LINES_PER_PAGE:
                break
            y += line_h_ss
            x = right
        d.text((x - wl, y), w, font=font, fill=(*INK, 255))
        x -= wl + space
        used += 1
    return img.resize((PAGE_W, PAGE_H), Image.LANCZOS), used


def find_coeffs(dst, src):
    A = []
    for (xd, yd), (xs, ys) in zip(dst, src):
        A.append([xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd])
        A.append([0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd])
    A = np.array(A, float)
    b = np.array(src, float).reshape(8)
    return np.linalg.solve(A, b).tolist()


def warp(flat, quad, size):
    src = [(0, 0), (PAGE_W, 0), (PAGE_W, PAGE_H), (0, PAGE_H)]
    return flat.transform(size, Image.PERSPECTIVE, find_coeffs(quad, src), Image.BICUBIC)


def multiply_blend(base_rgb, ink_layer, opacity):
    base = np.asarray(base_rgb, float) / 255.0
    lay = np.asarray(ink_layer, float) / 255.0
    a = lay[..., 3:4] * opacity
    out = base * (1 - a) + (base * lay[..., :3]) * a
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype("uint8"), "RGB")


def build_base(slug, base):
    words, _ = load_words(slug)
    W, H = base.size
    line_h_ss = ((PAGE_H - 2 * MARGIN) / LINES_PER_PAGE) * SS
    font = ImageFont.truetype(FONT_PATH, int(line_h_ss / 1.34))

    right_flat, n_r = render_page(words, font, line_h_ss)        # lines 1-18
    left_flat, n_l = render_page(words[n_r:], font, line_h_ss)   # lines 19-36

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(warp(right_flat, RIGHT_QUAD, (W, H)))
    canvas.alpha_composite(warp(left_flat, LEFT_QUAD, (W, H)))
    out = multiply_blend(base, canvas, OPACITY)

    OUTDIR.mkdir(exist_ok=True)
    op = OUTDIR / f"base_ner_{slug}.png"
    out.save(op)
    return op, n_r, n_l


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated slugs (default: all 53)")
    a = ap.parse_args()
    if not BASE.exists():
        sys.exit(f"missing {BASE}")
    base = Image.open(BASE).convert("RGB")

    all_slugs = sorted(p.stem for p in PDIR.glob("*.json"))
    slugs = [s.strip() for s in a.only.split(",") if s.strip()] or all_slugs
    OUTDIR.mkdir(exist_ok=True)
    print(f"phase8b_all: {len(slugs)} base(s) -> {OUTDIR}")
    done = 0
    for i, slug in enumerate(slugs, 1):
        op = OUTDIR / f"base_ner_{slug}.png"
        if op.exists():
            print(f"[{i:>2}/{len(slugs)}] skip (exists)  {slug}")
            done += 1
            continue
        op, n_r, n_l = build_base(slug, base)
        print(f"[{i:>2}/{len(slugs)}] {slug:<16} right={n_r} left={n_l} -> {op.name} "
              f"({op.stat().st_size // 1024} KB)")
        done += 1
    print(f"DONE. {done}/{len(slugs)} bases present.")


if __name__ == "__main__":
    main()
