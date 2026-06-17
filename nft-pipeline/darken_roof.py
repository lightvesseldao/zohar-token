"""
Darken the blinding Holy-of-Holies roof in base_temple.png so the bright roof
mass no longer forms a cross with the vertical Shekhinah beam.

- Soft feathered mask over the roof zone (x 42-58%, y 30-42%).
- Luminance-weighted: bright roof pixels darken ~35%, dark architectural
  detail is preserved (not crushed), so it blends naturally.
- The beam ABOVE the temple (y < ~30%) is left bright.

Output: base_temple_adjusted.png  (original untouched)  +  _roof_compare.png
"""
import os
import numpy as np
from PIL import Image

PIPE = r'C:\Users\Usuario\LIghtVessel\Zohar Edition\temple_pipeline'
SRC = os.path.join(PIPE, 'base_temple.png')
OUT = os.path.join(PIPE, 'base_temple_adjusted.png')
CMP = os.path.join(PIPE, '_roof_compare.png')

STRENGTH = 0.37                 # peak brightness reduction (~37%)
# roof zone (normalized) — plateau region + feather margins
CX, HALF_X, FEATHER_X = 0.50, 0.08, 0.045    # x plateau 0.42..0.58
CY, HALF_Y, FEATHER_Y = 0.36, 0.06, 0.040    # y plateau 0.30..0.42
LUM_LO, LUM_HI = 60.0, 185.0    # protect shadows (<LO), full effect on bright (>HI)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def plateau(coord, center, half, feather):
    d = np.abs(coord - center)
    return 1.0 - smoothstep((d - half) / feather)


def main():
    im = Image.open(SRC).convert('RGB')
    W, H = im.size
    rgb = np.asarray(im, np.float32)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)

    xn = (np.arange(W, dtype=np.float32) + 0.5) / W
    yn = (np.arange(H, dtype=np.float32) + 0.5) / H
    X, Y = np.meshgrid(xn, yn)

    spatial = plateau(X, CX, HALF_X, FEATHER_X) * plateau(Y, CY, HALF_Y, FEATHER_Y)
    lum_w = np.clip((lum - LUM_LO) / (LUM_HI - LUM_LO), 0.0, 1.0)
    mask = spatial * lum_w                          # (H,W) in 0..1

    factor = 1.0 - STRENGTH * mask
    out = np.clip(rgb * factor[..., None], 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGB').save(OUT)

    # before/after crop of the roof zone (with a little context)
    cx0, cy0, cx1, cy1 = int(0.30 * W), int(0.22 * H), int(0.70 * W), int(0.50 * H)
    before = im.crop((cx0, cy0, cx1, cy1))
    after = Image.fromarray(out, 'RGB').crop((cx0, cy0, cx1, cy1))
    cw, ch = before.size
    cmp = Image.new('RGB', (cw * 2 + 12, ch), (0, 0, 0))
    cmp.paste(before, (0, 0)); cmp.paste(after, (cw + 12, 0))
    cmp.save(CMP)

    peak = STRENGTH * mask.max()
    print(f"base_temple.png {W}x{H}")
    print(f"mask plateau x[{CX-HALF_X:.2f}-{CX+HALF_X:.2f}] y[{CY-HALF_Y:.2f}-{CY+HALF_Y:.2f}]")
    print(f"peak reduction applied: {peak*100:.0f}%")
    print(f"saved {OUT}\nsaved {CMP} (before | after)")


if __name__ == '__main__':
    main()
