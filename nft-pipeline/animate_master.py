"""
Master Edition — animated holographic shimmer.
Builds a 3s seamless loop from zohar_token_master_clean.png:

  MP4 : 1080x1920, 30fps, 90 frames   -> zohar_token_master_animated.mp4
  GIF :  540x960,  15fps, 45 frames   -> zohar_token_master_animated.gif

Shimmer = soft gold/white light band travelling the anti-diagonal (TL->BR),
NOT a rainbow. Divine-beam pulses +10% at peak. Gold corners flare as the
band sweeps past. Seamless: state at phase 1.0 == phase 0.0.

Pure local: Pillow + numpy + imageio (bundled ffmpeg). No API.
"""
import os
import argparse
import numpy as np
from PIL import Image
import imageio.v2 as imageio

PIPE = r'C:\Users\Usuario\LIghtVessel\Zohar Edition\temple_pipeline'

# --- shimmer parameters ---
BAND_SIGMA = 0.07                       # diagonal band width (s-space)
BAND_STRENGTH = 0.42                    # gold/white intensity at band center
GOLD_WHITE = np.array([1.00, 0.94, 0.78], np.float32)
PULSE_AMP = 0.05                        # *(1-cos) -> +0.10 peak (= +10%)
FLARE_STRENGTH = 0.55
FLARE_SPACE_SIGMA = 0.10
FLARE_TIME_SIGMA = 0.045
GOLD = np.array([1.00, 0.82, 0.18], np.float32)
CORNERS = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]  # TL TR BL BR (xn,yn)

# --- protected divine-beam / Holy of Holies region ---
# The shimmer must NOT cross the central light beam (it would paint a cross over
# the bright Holy-of-Holies roof). Inside this region: no band, no flare, no
# pulse amplification -> the beam stays exactly as the clean base image.
BEAM_X_HALF = 0.10        # plateau half-width: protects x in [0.40, 0.60]
BEAM_X_FEATHER = 0.08     # shimmer eases AROUND the beam over this x margin
BEAM_Y_KEEP = 0.52        # fully protect from the top down to here (beam shaft + roof)
BEAM_Y_RELEASE = 0.68     # shimmer fully returns below here (lower courtyard / gate)


def wrapdist(a, b):
    """Signed wrap-around distance on the unit circle -> seamless loop."""
    return (a - b + 0.5) % 1.0 - 0.5


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def protection_mask(X, Y):
    """1.0 over the central beam / Holy of Holies, fading to 0 outside.
    A central x-plateau (full strength across 40%-60%) feathered at the edges,
    capped vertically so shimmer resumes on the lower courtyard."""
    dx = np.abs(X - 0.5)
    px = 1.0 - smoothstep((dx - BEAM_X_HALF) / BEAM_X_FEATHER)
    py = 1.0 - smoothstep((Y - BEAM_Y_KEEP) / (BEAM_Y_RELEASE - BEAM_Y_KEEP))
    return (px * py).astype(np.float32)


def build_grids(W, H):
    xn = (np.arange(W, dtype=np.float32) + 0.5) / W
    yn = (np.arange(H, dtype=np.float32) + 0.5) / H
    X, Y = np.meshgrid(xn, yn)
    s = (X + Y) * 0.5                    # anti-diagonal coordinate, TL=0 -> BR=1
    return X, Y, s


def screen(a, b):
    return 1.0 - (1.0 - a) * (1.0 - b)


def render_frame(base, X, Y, s, phase, keep):
    # keep = 1 - protection_mask: 1 where shimmer is allowed, ~0 over the beam
    out = base.copy()
    # diagonal light band (transverse Gaussian -> fades to invisible at edges),
    # suppressed over the protected beam so it passes AROUND, never across it
    d = wrapdist(s, phase)
    band = np.exp(-(d * d) / (2 * BAND_SIGMA * BAND_SIGMA)) * keep
    add = (band[..., None] * BAND_STRENGTH) * GOLD_WHITE[None, None, :]
    out = screen(out, add)
    # gold corner flares timed to the band sweep
    for cx, cy in CORNERS:
        sc = (cx + cy) * 0.5
        tflare = np.exp(-(wrapdist(sc, phase) ** 2) / (2 * FLARE_TIME_SIGMA ** 2))
        if tflare < 0.02:
            continue
        sp = np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / (2 * FLARE_SPACE_SIGMA ** 2)))
        fa = (sp * tflare * FLARE_STRENGTH * keep)[..., None] * GOLD[None, None, :]
        out = screen(out, fa)
    # global pulse (+10% at mid-loop, seamless) — gated out of the beam zone so
    # the divine light beam is never amplified beyond the base image
    pulse = 1.0 + PULSE_AMP * (1.0 - np.cos(2 * np.pi * phase)) * keep
    out = out * pulse[..., None]
    return np.clip(out, 0.0, 1.0)


def make(src, W, H, total, fps, out_path, kind):
    img = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)
    base = np.asarray(img, dtype=np.float32) / 255.0
    X, Y, s = build_grids(W, H)
    keep = 1.0 - protection_mask(X, Y)        # 1 = shimmer allowed, 0 = protected beam
    print(f"[{kind}] {W}x{H} {total}f @ {fps}fps -> {out_path}", flush=True)
    if kind == 'mp4':
        writer = imageio.get_writer(out_path, fps=fps, codec='libx264',
                                    quality=8, macro_block_size=8,
                                    pixelformat='yuv420p')
    else:
        writer = imageio.get_writer(out_path, mode='I', duration=1.0 / fps, loop=0)
    for f in range(total):
        fr = render_frame(base, X, Y, s, f / total, keep)
        writer.append_data((fr * 255).astype(np.uint8))
        if f % 15 == 0:
            print(f"  {kind} frame {f}/{total}", flush=True)
    writer.close()
    print(f"[{kind}] done -> {out_path}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='zohar_token_master_clean.png')
    ap.add_argument('--mp4', default='zohar_token_master_animated.mp4')
    ap.add_argument('--gif', default='zohar_token_master_animated.gif')
    a = ap.parse_args()
    src = os.path.join(PIPE, a.src)
    mp4 = os.path.join(PIPE, a.mp4)
    gif = os.path.join(PIPE, a.gif)
    if not os.path.exists(src):
        raise SystemExit(f"missing {src} — run the clean recomposite first")
    make(src, 1080, 1920, 90, 30, mp4, 'mp4')
    make(src, 540, 960, 45, 15, gif, 'gif')
    print("ANIMATION COMPLETE", flush=True)


if __name__ == '__main__':
    main()
