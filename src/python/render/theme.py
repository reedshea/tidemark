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

# Grayscale palette (0 = black, 255 = white). Kept deliberately sparse, and
# each value snapped to one of the panel's 16 GC16 levels (multiples of 17) so
# solid elements land exactly on a displayable level rather than getting rounded
# unpredictably — sometimes per-pixel — by the panel's quantizer.
def _gc16(v):
    """Nearest of the 16 GC16 levels (0, 17, 34, ... 255)."""
    return round(v / 255 * 15) * 255 // 15


INK = _gc16(0)          # primary data line + dark text
PAPER = _gc16(255)      # background
INK_SOFT = _gc16(76)    # secondary text / ticks / moon dark side
GRID = _gc16(187)       # past (already-happened) curve + extrema
SEA_LINE = _gc16(102)   # engraved hairlines filling the sea below the curve
NIGHT_SKY = _gc16(187)  # hard-edged night band behind the chart (sky)
BORDER = _gc16(150)     # the thin framing rectangle

# Framed composition: a hairline border inset from the panel edge, a sky region
# up top (day labels + moon, with hard-edged night bands), a horizon line, and
# the engraved sea filling from the tide curve down to the horizon baseline.
MARGIN = 70               # inset of the framing border from the panel edge
PAD = 54                  # breathing room from border to the drawing area

PLOT_LEFT = MARGIN + PAD
PLOT_RIGHT = WIDTH - MARGIN - PAD

# Top "chart furniture", top-to-bottom: day+date, sun times, the x-axis line
# with hour ticks, then a weather-glyph row, then a second (plain) axis line —
# the night bands hang from THAT lower line down.
TITLE_Y = MARGIN + 64             # baseline of the day + date title line
SUN_LABEL_Y = TITLE_Y + 72        # sunrise / noon / sunset times row
AXIS_TICK_Y = SUN_LABEL_Y + 24    # upper x-axis line + ticks
AXIS_TICK_LONG = 16               # tick length for 6h / midnight marks
AXIS_TICK_SHORT = 8              # tick length for 3h marks

# Weather pictograms ride in their own bar between the two axis lines. The bar
# height drives the layout below it: the lower axis, the night-band ceiling, and
# the top of the tide plot all hang off WX_AXIS2_Y.
WX_BAR_H = 150                    # weather bar height (upper axis -> lower axis)
WX_ROW_Y = AXIS_TICK_Y + WX_BAR_H // 2   # pictogram row, centered in the bar
WX_AXIS2_Y = AXIS_TICK_Y + WX_BAR_H      # lower x-axis line (no ticks); night top

SKY_TOP = WX_AXIS2_Y             # night bands hang from the lower line down
MOON_SKY_TOP = WX_AXIS2_Y         # moon rides just below the lower line
HORIZON_Y = HEIGHT - MARGIN - PAD  # the sea's baseline; engraved fill sits above
PLOT_TOP = WX_AXIS2_Y + 24        # highest the tide curve can reach
PLOT_BOTTOM = HORIZON_Y   # curve's low-water floor == horizon

MOON_STRIP_TOP = MOON_SKY_TOP
MOON_STRIP_BOT = PLOT_TOP - 36
ALT_SCALE = 72.0          # moon altitude (deg) mapped across the moon strip

SEA_LINE_GAP = 20         # vertical spacing of engraved sea hairlines (logical)
SEA_LINE_W = 2            # stroke weight of the engraved sea hairlines (logical)

# Weather: Carbon pictograms ride in a row just below the axis; the moon is
# pushed down so it doesn't collide with that row.
WX_GLYPH_SIZE = 96        # weather pictogram size (logical px)
MOON_DROP = 80            # how far the moon is nudged below its old position

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
    # Everything is set in Tufte's ET Book for a unified, framed-print voice, now
    # in the SEMIBOLD weight so the type carries across the room; roman is kept
    # as the next fallback. The sans styles are aliased to ET Book too.
    # DejaVu/Liberation are only fallbacks should the bundled fonts be missing.
    "serif": ["semibold.ttf", "roman.ttf", "DejaVuSerif.ttf",
              "LiberationSerif-Regular.ttf"],
    "serif_bold": ["bold.ttf", "semibold.ttf", "DejaVuSerif-Bold.ttf",
                   "LiberationSerif-Bold.ttf"],
    "serif_italic": ["italic.ttf", "DejaVuSerif-Italic.ttf"],
    "sans": ["semibold.ttf", "roman.ttf", "DejaVuSans.ttf",
             "LiberationSans-Regular.ttf"],
    "sans_bold": ["bold.ttf", "semibold.ttf", "DejaVuSans-Bold.ttf",
                  "LiberationSans-Bold.ttf"],
}

_cache = {}

# Smallest type we ever render (a safety floor below the intentional sizes).
FONT_MIN = 35

# Type scale (logical pt). Dates are the largest; times match the old date size.
FONT_DATE = 72            # weekday + date titles
FONT_TIME = 54            # sun times (header) and tide-peak times
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
