#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLACEHOLDER base image generator — validation only.
Creates a synthetic Temple-like luminance field (bright central structure, sky band,
courtyard foreground, side shadows) so phase2 'map' can be exercised before the real
Ideogram Temple exists. Replace base_temple.png with the real render for production.
"""
import numpy as np
from PIL import Image
from pathlib import Path

W, H = 1500, 2100                      # 5:7 portrait, downscaled-friendly
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
xn, yn = x / W, y / H

sky = np.clip(0.55 - yn * 0.6, 0, 1) * (yn < 0.30)          # bright top sky
# central temple block: bright vertical mass, columns texture
cx = np.abs(xn - 0.5)
temple = np.clip(0.9 - cx * 2.2, 0, 1) * (yn > 0.28) * (yn < 0.82)
columns = (np.sin(x / 22.0) * 0.12 + 0.88) * temple
courtyard = np.clip(0.5 - (yn - 0.82) * 1.5, 0, 1) * (yn > 0.82)
shadow = (cx > 0.42) * 0.05
lum = np.clip(sky + columns + courtyard + shadow, 0, 1)
# central divine glow
glow = np.exp(-(((xn - 0.5) ** 2) / 0.02 + ((yn - 0.45) ** 2) / 0.05))
lum = np.clip(lum + glow * 0.5, 0, 1)

Image.fromarray((lum * 255).astype(np.uint8), "L").save(Path(__file__).parent / "base_temple.png")
print("wrote placeholder base_temple.png", W, "x", H)
