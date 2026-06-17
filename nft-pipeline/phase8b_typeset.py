"""
Phase 8b - Typeset real Zohar opening text onto the two manuscript pages
of base_ner.png via perspective transform + sepia multiply blend.

Source text : words.json, sec == "הקדמה" (Hakdamah / Shoshana petichta), in order.
Form        : consonantal (`c`)  [set USE_POINTED=True for vowel-pointed `w`]
Font        : Frank Ruhl (C:\\Windows\\Fonts\\frank.ttf)
Blend       : multiply @ OPACITY onto existing parchment.
Output      : base_ner_zohar.png  (+ phase8b_crop.png approval crop)
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PIPE = r'C:\Users\Usuario\LIghtVessel\Zohar Edition\temple_pipeline'
BASE = os.path.join(PIPE, 'base_ner.png')
OUT  = os.path.join(PIPE, 'base_ner_zohar.png')
CROP = os.path.join(PIPE, 'phase8b_crop.png')
WORDS = os.path.join(PIPE, 'words.json')
FONT_PATH = r'C:\Windows\Fonts\frank.ttf'

USE_POINTED = False          # False -> consonantal `c`; True -> pointed `w`
OPACITY = 0.70               # multiply blend strength
INK = (38, 24, 12)           # dark sepia ink
SS = 3                       # supersample factor for flat page render (crispness)

# Perspective destination quads in base-image coords (TL, TR, BR, BL)
LEFT_QUAD  = [(326, 765), (520, 765), (436, 1045), (121, 1045)]
RIGHT_QUAD = [(520, 765), (714, 765), (752, 1045), (436, 1045)]

# Flat page render size (portrait page); warped onto quads
PAGE_W, PAGE_H = 600, 860
MARGIN = 46
FONT_SIZE = 24
LINE_GAP = 1.34


def load_opening_words(limit=900):
    with open(WORDS, encoding='utf-8') as f:
        data = json.load(f)
    key = 'w' if USE_POINTED else 'c'
    out = [d[key] for d in data if d.get('sec') == 'הקדמה']
    return out[:limit]


def render_flat_page(words, font):
    """Render Hebrew RTL onto a transparent flat page. Returns (RGBA, used_count)."""
    W, H = PAGE_W * SS, PAGE_H * SS
    m = MARGIN * SS
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * LINE_GAP)
    space = d.textlength(' ', font=f)
    right = W - m
    left = m
    x = right
    y = m
    used = 0
    for w in words:
        wl = d.textlength(w, font=f)
        if x - wl < left:                     # wrap to next line
            y += lh
            x = right
            if y + lh > H - m:                # page full
                break
        d.text((x - wl, y), w, font=f, fill=(*INK, 255))
        x -= wl + space
        used += 1
    return img.resize((PAGE_W, PAGE_H), Image.LANCZOS), used


def find_coeffs(dst, src):
    """Coeffs for PIL PERSPECTIVE mapping output->input. dst/src are 4 (x,y)."""
    A = []
    for (xd, yd), (xs, ys) in zip(dst, src):
        A.append([xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd])
        A.append([0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd])
    A = np.array(A, dtype=float)
    b = np.array(src, dtype=float).reshape(8)
    res = np.linalg.solve(A, b)
    return res.tolist()


def warp_to_quad(flat, quad, canvas_size):
    """Warp flat page (RGBA) into canvas at quad (TL,TR,BR,BL)."""
    W, H = canvas_size
    src_corners = [(0, 0), (PAGE_W, 0), (PAGE_W, PAGE_H), (0, PAGE_H)]
    coeffs = find_coeffs(quad, src_corners)
    return flat.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def multiply_composite(base_rgb, ink_layer, opacity):
    """Multiply ink_layer (RGBA) onto base_rgb where alpha>0, mixed by opacity."""
    base = np.asarray(base_rgb, dtype=float) / 255.0
    lay = np.asarray(ink_layer, dtype=float) / 255.0
    rgb = lay[..., :3]
    a = (lay[..., 3:4]) * opacity
    multiplied = base * rgb
    out = base * (1 - a) + multiplied * a
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype('uint8'), 'RGB')


def main():
    words = load_opening_words()
    print(f"Loaded {len(words)} Hakdamah words (pointed={USE_POINTED})")
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE * SS)

    base = Image.open(BASE).convert('RGB')
    W, H = base.size

    left_flat, n1 = render_flat_page(words, font)
    right_flat, n2 = render_flat_page(words[n1:], font)
    print(f"Left page used {n1} words, right page used {n2} words")

    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(warp_to_quad(left_flat, LEFT_QUAD, (W, H)))
    canvas.alpha_composite(warp_to_quad(right_flat, RIGHT_QUAD, (W, H)))

    result = multiply_composite(base, canvas, OPACITY)
    result.save(OUT)
    print(f"Saved {OUT}")

    # approval crop: right page region, upscaled 2x
    cx0, cy0, cx1, cy1 = 430, 740, 770, 1070
    crop = result.crop((cx0, cy0, cx1, cy1))
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save(CROP)
    print(f"Saved {CROP}")


if __name__ == '__main__':
    main()
