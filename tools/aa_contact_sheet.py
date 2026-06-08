#!/usr/bin/env python3
"""
Render the tide ribbon under several antialiasing / e-ink settings and tile
zoomed crops side by side, so the techniques can be compared at a glance.

    python3 tools/aa_contact_sheet.py [--now ISO] [--panel] [--scale 3]
                                      [--out /tmp/aa_contact.png]

--panel applies the simulator's panel emulation (16 levels + reflective
ink..paper band) to each crop, so you compare what the display would actually
show, not crisp 8-bit on glass.

Pillow-only; shells out to src/python/main.py with the TIDE_* env knobs.
"""

import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.path.join(ROOT, "src", "python", "main.py")
PY = sys.executable

# (label, extra env) — the settings to compare.
VARIANTS = [
    ("baseline SS2 gamma-AA", {"TIDE_SS": "2", "TIDE_LINEAR": "0",
                               "TIDE_SNAP": "0"}),
    ("SS4 linear+snap", {}),
    ("+ text gamma 1.4", {"TIDE_TEXT_GAMMA": "1.4"}),
]

# Zoom crops (logical px on the 1872×1404 panel): a title-text patch and a
# stretch of the tide curve. Tweak if your layout differs.
CROPS = [("text", (150, 90, 600, 230)), ("curve", (650, 520, 1100, 760))]


def panel_map(img, ink=30, paper=225, levels=16):
    n = levels - 1
    return img.point(lambda v: ink + (round(v / 255 * n) * 255 // n)
                     * (paper - ink) // 255)


def render(env_extra, out):
    env = dict(os.environ)
    env.update(env_extra)
    subprocess.run([PY, MAIN, "--output", out] + ARGS_NOW, check=True,
                   env=env, stdout=subprocess.DEVNULL)


def main():
    global ARGS_NOW
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None)
    ap.add_argument("--panel", action="store_true")
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--out", default="/tmp/aa_contact.png")
    args = ap.parse_args()
    ARGS_NOW = ["--now", args.now] if args.now else []

    label_font = ImageFont.load_default()
    pad, sc = 12, args.scale
    cols = []
    with tempfile.TemporaryDirectory() as td:
        for label, env in VARIANTS:
            bmp = os.path.join(td, "v.bmp")
            render(env, bmp)
            full = Image.open(bmp).convert("L")
            tiles = []
            for _, (x0, y0, x1, y1) in CROPS:
                crop = full.crop((x0, y0, x1, y1))
                if args.panel:
                    crop = panel_map(crop)
                crop = crop.resize((crop.width * sc, crop.height * sc),
                                   Image.NEAREST)  # NEAREST: show real pixels
                tiles.append(crop)
            col_w = max(t.width for t in tiles)
            col_h = sum(t.height for t in tiles) + 24 + pad * (len(tiles) + 1)
            col = Image.new("L", (col_w + pad * 2, col_h), 255)
            d = ImageDraw.Draw(col)
            d.text((pad, 6), label, fill=0, font=label_font)
            y = 24 + pad
            for t in tiles:
                col.paste(t, (pad, y))
                y += t.height + pad
            cols.append(col)

    W = sum(c.width for c in cols) + pad * (len(cols) + 1)
    H = max(c.height for c in cols) + pad * 2
    sheet = Image.new("L", (W, H), 245)
    x = pad
    for c in cols:
        sheet.paste(c, (x, pad))
        x += c.width + pad
    sheet.save(args.out)
    print(f"Wrote {args.out} ({'panel-emulated' if args.panel else 'raw 8-bit'})")


if __name__ == "__main__":
    main()
