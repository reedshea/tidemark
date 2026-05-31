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

# Day/night gradient block (the "sky" strip below the title). Each column's gray
# tracks the sun's altitude: PAPER at/above the horizon, darkening to NIGHT_SKY
# once the sun is TWILIGHT_SPAN degrees below it (~ astronomical night).
NIGHT_SKY = 188
TWILIGHT_SPAN = 18.0

# Plot geometry. Time axis runs along the TOP (minimal); the tide is the hero
# below it; the moon rides in a thin strip near the top; day/night band and the
# optional temperature line sit at the bottom.
PLOT_LEFT = 124
PLOT_RIGHT = WIDTH - 60

TOP_RULE_Y = 112          # rule under the title
TIME_LABEL_Y = 140        # baseline of the top time-axis labels
TICK_Y = 152              # short downward ticks under the time labels

MOON_TOP = 178            # thin strip the moon glyph rides in
MOON_BOT = 246
ALT_SCALE = 72.0          # moon altitude (deg) mapped across the moon strip

PLOT_TOP = 270            # top of the tide panel
PLOT_BOTTOM = 1118

BAND_TOP = 1136           # day/night band
BAND_H = 28

TEMP_TOP = 1182           # optional temperature line (bottom)
TEMP_BOT = 1256

FOOTER_Y = HEIGHT - 60

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
]

_FONT_FILES = {
    "serif": ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "Georgia.ttf"],
    "serif_bold": ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf",
                   "Georgia Bold.ttf"],
    "sans": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"],
    "sans_bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                  "Arial Bold.ttf"],
}

_cache = {}

# Smallest type we ever render. Anything requested below this is bumped up so
# every label stays legible at panel viewing distance. Tune this one knob to
# raise/lower the floor for all secondary text.
FONT_MIN = 44


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
