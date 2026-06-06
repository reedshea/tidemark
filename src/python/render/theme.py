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
INK = 0           # primary data line + dark text
PAPER = 255       # background
INK_SOFT = 95     # secondary text / moon dark side
GRID = 205        # hairlines, ticks
SEA_LINE = 120    # engraved hairlines filling the sea below the curve (uniform)
NIGHT_SKY = 238   # hard-edged night band behind the chart (sky)
BORDER = 150      # the thin framing rectangle

# Framed composition: a hairline border inset from the panel edge, a sky region
# up top (day labels + moon, with hard-edged night bands), a horizon line, and
# the engraved sea filling from the tide curve down to the horizon baseline.
MARGIN = 70               # inset of the framing border from the panel edge
PAD = 54                  # breathing room from border to the drawing area

PLOT_LEFT = MARGIN + PAD
PLOT_RIGHT = WIDTH - MARGIN - PAD

# Top "chart furniture", three rows top-to-bottom: day+date, sun times,
# then the x-axis line (also the night-box ceiling) with its hour ticks.
TITLE_Y = MARGIN + 72             # baseline of the day + date title line
SUN_LABEL_Y = TITLE_Y + 70        # sunrise / noon / sunset times row
AXIS_TICK_Y = SUN_LABEL_Y + 30    # x-axis line + ticks; also the night-box top
AXIS_TICK_LONG = 18               # tick length for 6h / midnight marks
AXIS_TICK_SHORT = 10              # tick length for 3h marks

SKY_TOP = AXIS_TICK_Y             # night bands hang from the axis line down
MOON_SKY_TOP = AXIS_TICK_Y + 40   # moon rides just below the axis
HORIZON_Y = HEIGHT - MARGIN - PAD  # the sea's baseline; engraved fill sits above
PLOT_TOP = 380            # highest the tide curve can reach
PLOT_BOTTOM = HORIZON_Y   # curve's low-water floor == horizon

MOON_STRIP_TOP = MOON_SKY_TOP
MOON_STRIP_BOT = PLOT_TOP - 36
ALT_SCALE = 72.0          # moon altitude (deg) mapped across the moon strip

SEA_LINE_GAP = 13         # vertical spacing of engraved sea hairlines (logical)

FOOTER_Y = HEIGHT - MARGIN - 8

_FONT_DIRS = [
    # ET Book (Tufte's Bembo), bundled with the repo so it works offline on the
    # Pi; searched first so the serif styles resolve to it.
    os.path.join(os.path.dirname(__file__), "..", "..", "..",
                 "assets", "fonts"),
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
]

_FONT_FILES = {
    # Everything is set in Tufte's ET Book for a unified, framed-print voice;
    # the sans styles are aliased to ET Book too. DejaVu/Liberation are kept
    # only as fallbacks should the bundled fonts be missing.
    "serif": ["roman.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"],
    "serif_bold": ["semibold.ttf", "bold.ttf", "DejaVuSerif-Bold.ttf",
                   "LiberationSerif-Bold.ttf"],
    "serif_italic": ["italic.ttf", "DejaVuSerif-Italic.ttf"],
    "sans": ["roman.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    "sans_bold": ["bold.ttf", "semibold.ttf", "DejaVuSans-Bold.ttf",
                  "LiberationSans-Bold.ttf"],
}

_cache = {}

# Smallest type we ever render (a safety floor below the intentional sizes).
FONT_MIN = 35

# Type scale (logical pt). Dates are the largest; times match the old date size.
FONT_DATE = 64            # weekday + date titles
FONT_TIME = 48            # sun times (header) and tide-peak times
SMALLCAP = 0.72           # am/pm small-cap height relative to the time


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
