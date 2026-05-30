#!/usr/bin/env python3
"""
Visual theme: palette, fonts, and geometry for the e-ink tide ribbon.

Design intent (Tufte, for e-ink): white ground, one black data line, a tiny
restrained set of grays, direct labels, no boxes or gridlines. Mid-gray fills
and fine texture are deliberately avoided because they ghost and band on e-ink.
"""

import os
from PIL import ImageFont

# E-ink panel (Waveshare 7.8" / IT8951), landscape.
WIDTH = 1872
HEIGHT = 1404

# Grayscale palette (0 = black, 255 = white). Kept deliberately sparse.
INK = 0           # primary data + text
PAPER = 255       # background
INK_SOFT = 95     # secondary text / moon dark side
GRID = 205        # hairlines, ticks, past data
FAINT = 226       # night band fill
TWILIGHT = 246    # twilight band fill
NIGHT_WASH = 246  # barely-there night shading inside the plot

# Plot geometry. The canvas splits into a sky panel (celestial arcs, above the
# horizon) and the tide/sea panel (below it).
PLOT_LEFT = 124
PLOT_RIGHT = WIDTH - 70
SKY_TOP = 188             # top of the sky panel
HORIZON_Y = 436           # the horizon: arcs rise from here, sea sits below
ALT_SCALE = 72.0          # altitude (deg) mapped to the full sky-panel height
PLOT_TOP = 492            # top of the tide panel
PLOT_BOTTOM = 1112

BAND_TOP = 1130           # daylight band
BAND_H = 30
AXIS_LABEL_Y = 1176       # time-axis labels
FOOTER_Y = HEIGHT - 44

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
]

_FONT_FILES = {
    "serif": ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "Georgia.ttf"],
    "serif_bold": ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    "sans": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"],
    "sans_bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
}

_cache = {}


def font(style, size):
    """Load a themed font, cached. style in serif/serif_bold/sans/sans_bold."""
    key = (style, size)
    if key in _cache:
        return _cache[key]
    for name in _FONT_FILES.get(style, []):
        for d in _FONT_DIRS:
            path = os.path.join(d, name)
            if os.path.exists(path):
                f = ImageFont.truetype(path, size)
                _cache[key] = f
                return f
    f = ImageFont.load_default()
    _cache[key] = f
    return f


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]
