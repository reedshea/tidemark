#!/usr/bin/env python3
"""
The Tidemark ribbon: a framed, nautical-chart-style tide piece for e-ink.

Composition (chosen to read as deliberate wall art and to survive e-ink):
  - a hairline border inset from the panel edge, like a matted print;
  - a sky region up top holding the weekday labels and the moon at its transit,
    with hard-edged night bands (no smudgy gradients);
  - a horizon baseline; the tide curve is the surface of the sea;
  - the sea is "engraved" with horizontal hairlines below the curve — depth and
    texture with pure black-on-white lines (no mid-gray fills that band/ghost).

Rendered at 4x and downsampled so the curve and hairlines are smooth (see the
TIDE_SS / TIDE_FILTER env knobs below for tuning the antialiasing).
"""

import math
import datetime
import os
import random

from PIL import Image, ImageDraw

from render import theme as T
from render import eink
from data.sun import sun_altitude

# Antialiasing / e-ink experiment knobs (env-overridable so the simulator can
# sweep combinations without code edits):
#   TIDE_SS=N            supersample factor for the main canvas (default 4)
#   TIDE_FILTER=name     downsample filter: lanczos|bicubic|bilinear|box|hamming
#   TIDE_LINEAR=0        disable linear-light downsampling (default on; AA edge
#                        ramps are only correct when averaged in linear light)
#   TIDE_POSTERIZE16=1   quantize to the 16 GC16 levels (preview the panel's
#                        depth/banding from the simulator)
#   TIDE_SNAP=0          disable pixel-grid snapping of axis-aligned lines
#   TIDE_TEXT_GAMMA=g    stem-darken text by gamma g on glyph coverage (e.g.
#                        1.4); default 1.0 (off).
def _envflag(name, default=False):
    v = os.environ.get(name)
    if v is None:
        return default
    return v not in ("", "0", "false", "False")


SS = int(os.environ.get("TIDE_SS", "4"))  # supersampling factor
_FILTER_NAME = os.environ.get("TIDE_FILTER", "lanczos")
_RESAMPLE = eink.resolve_filter(_FILTER_NAME)
_LINEAR = _envflag("TIDE_LINEAR", True)
_POSTERIZE16 = _envflag("TIDE_POSTERIZE16", False)
_SNAP = _envflag("TIDE_SNAP", True)
_TEXT_GAMMA = float(os.environ.get("TIDE_TEXT_GAMMA", "1.0"))
M2FT = 3.28084

# The engraved sea's hairlines undulate as a sum of sine swells rather than
# lying flat: a long lazy roller + the main swell + a little chop. Summed, they
# read as rolling sets of larger and smaller waves. Each entry is
# (amplitude px, wavelength px, base phase, phase-drift per line); the per-line
# drift keeps swells from stacking into rigid vertical columns. Amplitudes stay
# well below the bold tide curve so the chart is still mostly Tufte.
_SEA_SWELL = [
    (3.6, 430.0, 0.0, 0.18),
    (4.4, 165.0, 1.7, 0.55),
    (1.6, 73.0, 3.9, 1.05),
]


def _s(v):
    return int(round(v * SS))


def _snap_center(v):
    """Snap a device coordinate to the center of an output pixel (k*SS + SS/2),
    so an axis-aligned stroke of width SS covers exactly one output pixel."""
    half = SS // 2
    return int(round((v - half) / SS)) * SS + half


class _Canvas:
    """Thin wrapper that scales all drawing by the supersample factor."""

    def __init__(self, w, h):
        self.img = Image.new("L", (_s(w), _s(h)), T.PAPER)
        self.d = ImageDraw.Draw(self.img)

    def line(self, pts, fill, width=1):
        dev = [(_s(x), _s(y)) for x, y in pts]
        # Pixel-grid fitting: a purely horizontal/vertical stroke whose center
        # falls between output pixels gets antialiased into a fuzzy two-row gray
        # smear that then quantizes harshly. Snap the constant axis so the
        # stroke lands centered on a single output pixel. Curves/diagonals are
        # left untouched so they keep their (wanted) antialiasing.
        if _SNAP and len(dev) >= 2:
            xs = {p[0] for p in dev}
            ys = {p[1] for p in dev}
            if len(xs) == 1:                       # vertical
                sx = _snap_center(dev[0][0])
                dev = [(sx, y) for _, y in dev]
            elif len(ys) == 1:                     # horizontal
                sy = _snap_center(dev[0][1])
                dev = [(x, sy) for x, _ in dev]
        self.d.line(dev, fill=fill, width=max(1, _s(width)), joint="curve")

    def rect(self, box, fill=None, outline=None, width=1):
        dev = [_s(box[0]), _s(box[1]), _s(box[2]), _s(box[3])]
        if _SNAP:
            dev = [int(round(v / SS)) * SS for v in dev]
        self.d.rectangle(dev, fill=fill, outline=outline,
                         width=max(1, _s(width)))

    def polygon(self, pts, fill=None, outline=None):
        self.d.polygon([(_s(x), _s(y)) for x, y in pts], fill=fill,
                       outline=outline)

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse([_s(box[0]), _s(box[1]), _s(box[2]), _s(box[3])],
                       fill=fill, outline=outline, width=max(1, _s(width)))

    def dot(self, x, y, r, fill, outline=None, width=1):
        self.ellipse((x - r, y - r, x + r, y + r), fill=fill,
                     outline=outline, width=width)

    def text(self, xy, s, fill, style, size, anchor="la"):
        size = max(size, T.FONT_MIN)  # enforce the legibility floor (logical pt)
        fnt = T.font(style, _s(size))
        pos = (_s(xy[0]), _s(xy[1]))
        if _TEXT_GAMMA == 1.0:
            self.d.text(pos, s, fill=fill, font=fnt, anchor=anchor)
            return
        # Stem darkening: render glyph coverage on a scratch layer, raise it by
        # a gamma so partial-coverage (stem-edge) pixels read darker — thin
        # serifs survive the 16-level quantization instead of washing out — then
        # composite with that coverage as the mask.
        box = self.d.textbbox(pos, s, font=fnt, anchor=anchor)
        pad = 2
        x0, y0 = box[0] - pad, box[1] - pad
        w, h = max(1, box[2] - x0 + pad), max(1, box[3] - y0 + pad)
        cover = Image.new("L", (w, h), 0)
        ImageDraw.Draw(cover).text((pos[0] - x0, pos[1] - y0), s, fill=255,
                                   font=fnt, anchor=anchor)
        cover = cover.point(
            [round((i / 255.0) ** (1.0 / _TEXT_GAMMA) * 255) for i in range(256)])
        self.img.paste(Image.new("L", (w, h), fill), (x0, y0), cover)

    def text_width(self, s, style, size):
        """Logical-pixel width of `s` at the given style/size (after FONT_MIN)."""
        size = max(size, T.FONT_MIN)
        box = self.d.textbbox((0, 0), s, font=T.font(style, _s(size)))
        return (box[2] - box[0]) / SS

    def finish(self):
        size = (T.WIDTH, T.HEIGHT)
        if _LINEAR:
            out = eink.downsample_linear(self.img, size, _RESAMPLE)
        else:
            out = self.img.resize(size, _RESAMPLE)
        if _POSTERIZE16:
            out = eink.quantize_gc16(out)
        return out


def _time_parts(dt):
    """('1:42', 'p.m.') — 12-hour clock with a Chicago-style meridiem."""
    h = dt.hour % 12 or 12
    mer = "a.m." if dt.hour < 12 else "p.m."
    return f"{h}:{dt.minute:02d}", mer


def _time_width(c, dt, size, style="sans"):
    """Logical width of a time drawn by _draw_time (number + small-caps mer)."""
    num, mer = _time_parts(dt)
    sc = max(T.FONT_MIN, round(size * T.SMALLCAP))
    return (c.text_width(num, style, size) + size * 0.16
            + c.text_width(mer.upper(), style, sc))


def _draw_time(c, x, baseline, dt, size, fill, style="sans", align="l"):
    """Draw a time as '8:38' + small-caps 'p.m.' sharing one baseline. The
    meridiem is set in (faux) small caps with periods, per late-20th-century
    Chicago style. `align` (l/m/r) is relative to x. Returns total width."""
    num, mer = _time_parts(dt)
    sc_size = max(T.FONT_MIN, round(size * T.SMALLCAP))
    gap = size * 0.16
    num_w = c.text_width(num, style, size)
    sc = mer.upper()                          # uppercase reads as small caps
    sc_w = c.text_width(sc, style, sc_size)
    total = num_w + gap + sc_w
    lx = x - total / 2 if align == "m" else (x - total if align == "r" else x)
    c.text((lx, baseline), num, fill, style, size, anchor="ls")
    c.text((lx + num_w + gap, baseline), sc, fill, style, sc_size, anchor="ls")
    return total


def render(ctx):
    c = _Canvas(T.WIDTH, T.HEIGHT)
    units = ctx["units"]
    to_disp = (lambda m: m * M2FT) if units == "ft" else (lambda m: m)

    start, end, now = ctx["start"], ctx["end"], ctx["now"]
    series = ctx["series"]
    span_s = (end - start).total_seconds()

    # Seed the sea-swell / moon-stipple randomness from the window start so the
    # texture is identical for every render within an hour. That keeps the
    # background stable under partial (now-marker only) refreshes, and makes
    # renders reproducible for tests.
    random.seed(int(start.timestamp()))

    def X(dt):
        return T.PLOT_LEFT + (dt - start).total_seconds() / span_s \
            * (T.PLOT_RIGHT - T.PLOT_LEFT)

    # Fixed scale with soft knees. The robust p5/p99 bounds (floor/ceil) map
    # across the bulk of the plot height, so a normal day fills the panel and
    # the low troughs sit near the horizon. The rare spring extremes beyond those
    # bounds aren't clamped flat: floor..hardmin and ceil..hardmax get thin,
    # compressed knee bands at the very bottom/top, so an unusually low (or high)
    # tide still reads as a dip (or peak) into that reserved sliver.
    sc = ctx["scale"]
    floor, ceil = to_disp(sc["floor"]), to_disp(sc["ceil"])
    hardmin = min(to_disp(sc["hardmin"]), floor)
    hardmax = max(to_disp(sc["hardmax"]), ceil)
    span = (ceil - floor) or 1.0
    floor -= span * 0.02            # nudge so p5/p99 tides sit just inside the
    ceil += span * 0.06             # main band rather than exactly on a knee

    Hpx = T.PLOT_BOTTOM - T.PLOT_TOP
    y_floor = T.PLOT_BOTTOM - Hpx * 0.07     # p5 sits a sliver above the horizon
    y_ceil = T.PLOT_TOP + Hpx * 0.07         # p99 sits a sliver below the top

    def Y(h_m):
        v = to_disp(h_m)
        if v >= ceil:                        # high soft knee (compressed)
            if hardmax <= ceil:
                return y_ceil
            f = min(1.0, (v - ceil) / (hardmax - ceil))
            return y_ceil - f * (y_ceil - T.PLOT_TOP)
        if v <= floor:                       # low soft knee (compressed)
            if hardmin >= floor:
                return y_floor
            f = min(1.0, (floor - v) / (floor - hardmin))
            return y_floor + f * (T.PLOT_BOTTOM - y_floor)
        f = (v - floor) / (ceil - floor)     # main band (linear)
        return y_floor - f * (y_floor - y_ceil)

    curve = [(X(t), Y(h)) for t, h in zip(series.times, series.heights)]

    _draw_night_bands(c, ctx, X, curve)
    _draw_engraved_sea(c, curve, X(now))
    _draw_title_and_axis(c, ctx, X)
    _draw_moon(c, ctx, X)
    _draw_curve(c, curve, X, now)
    _draw_extrema(c, series, X, Y, now)
    _draw_now(c, series, X, Y, now)
    if ctx.get("weather") is not None:
        _draw_weather(c, ctx, X)
    _draw_frame(c)

    return c.finish(), _now_marker_rect(X, now)


def _now_marker_rect(X, now):
    """Bounding box (logical px, x/y/w/h) of the region the now-marker can
    occupy during the current clock hour.

    The window is anchored to the top of the hour, so between hourly full
    refreshes only the now-marker moves — and it stays within this single
    one-hour-wide column. The host refreshes just this strip every few minutes
    (partial GC16) and repaints the whole panel when the hour rolls over.

    The strip spans the FULL panel height, not just the curve. On the IT8951 the
    source-driver lines for these x-columns run the whole height of the glass, so
    repeated partial pulses slowly disturb (fade) the bistable pixels in the same
    columns above the curve — notably the slice of the day/date title that sits
    over the marker. Refreshing the whole column repaints that header slice crisp
    every cycle (its content is identical frame-to-frame), so it heals instead of
    fading. The flash stays confined to this one narrow column."""
    hour0 = now.replace(minute=0, second=0, microsecond=0)
    x0 = X(hour0)
    x1 = X(hour0 + datetime.timedelta(hours=1))
    pad_x = 18                       # now-dot outer ring (12) + slack
    rx0 = int(max(T.PLOT_LEFT, x0 - pad_x))
    rx1 = int(min(T.PLOT_RIGHT, x1 + pad_x))
    ry0 = 0                          # full height: heal header cross-talk in the
    ry1 = T.HEIGHT                   # marker's columns (date/sun labels above)
    return (rx0, ry0, rx1 - rx0, ry1 - ry0)


def _night_spans(ctx):
    """Night intervals (as datetimes) within [start, end] — the complement of
    the daylight intervals."""
    start, end = ctx["start"], ctx["end"]
    spans = []
    cur = start
    for sr, ss in sorted(ctx["daylight"]):
        if ss <= start or sr >= end:
            continue
        if sr > cur:
            spans.append((max(start, cur), min(sr, end)))
        cur = max(cur, ss)
    if cur < end:
        spans.append((cur, end))
    return spans


def _sky_mask(curve):
    """Mask (2x) of the sky region: everything inside the plot above the tide
    curve. Used to clip the night bands so they never cover the sea."""
    mask = Image.new("L", (_s(T.WIDTH), _s(T.HEIGHT)), 0)
    md = ImageDraw.Draw(mask)
    poly = [(_s(T.PLOT_LEFT), _s(T.SKY_TOP))]
    poly += [(_s(x), _s(yy)) for x, yy in curve]
    poly += [(_s(T.PLOT_RIGHT), _s(T.SKY_TOP))]
    md.polygon(poly, fill=255)
    return mask


def _draw_night_bands(c, ctx, X, curve):
    """Night as crisp rectangles in the SKY only — hard edges, clipped to above
    the tide curve so the sea engraving below stays clean. The sea engraving is
    a single uniform shade; night is shown only by these sky bands."""
    band = Image.new("L", (_s(T.WIDTH), _s(T.HEIGHT)), T.PAPER)
    bd = ImageDraw.Draw(band)
    drew = False
    for a, b in _night_spans(ctx):
        x0 = max(T.PLOT_LEFT, X(a))
        x1 = min(T.PLOT_RIGHT, X(b))
        if x1 > x0:
            bd.rectangle([_s(x0), _s(T.SKY_TOP), _s(x1), _s(T.HORIZON_Y)],
                         fill=T.NIGHT_SKY)
            drew = True
    if drew:
        c.img.paste(band, (0, 0), _sky_mask(curve))
        c.d = ImageDraw.Draw(c.img)


def _draw_engraved_sea(c, curve, nx):
    """Fill below the tide curve with evenly spaced hairlines (an engraving),
    clipped to the area under the curve via a polygon mask. The lines undulate
    as a gentle sum of sine swells (see _SEA_SWELL) so the sea reads as rolling
    water. One uniform line shade everywhere — day and night sea read the same;
    night is shown by the sky bands above. Pure black-on-white hairlines: ideal
    for e-ink.

    The wavy fill is only drawn to the RIGHT of the now-marker (`nx`); the sea
    behind now is left blank. The partial-refresh strip travels that region, so
    keeping it plain (not textured) lets the 5-min marker updates refresh cleanly
    instead of accumulating ghosting in the engraving."""
    full = Image.new("L", (_s(T.WIDTH), _s(T.HEIGHT)), T.PAPER)
    fd = ImageDraw.Draw(full)
    x_start = max(T.PLOT_LEFT, nx)
    y = T.PLOT_TOP
    i = 0
    while y <= T.HORIZON_Y:
        pts = []
        x = x_start
        while x <= T.PLOT_RIGHT:
            yy = y + sum(a * math.sin(2 * math.pi * x / w + p + i * d)
                         for a, w, p, d in _SEA_SWELL)
            pts.append((_s(x), _s(yy)))
            x += 4
        if len(pts) >= 2:
            fd.line(pts, fill=T.SEA_LINE, width=max(1, _s(T.SEA_LINE_W)))
        y += T.SEA_LINE_GAP
        i += 1

    mask = Image.new("L", (_s(T.WIDTH), _s(T.HEIGHT)), 0)
    md = ImageDraw.Draw(mask)
    poly = [(_s(T.PLOT_LEFT), _s(T.HORIZON_Y))]
    poly += [(_s(x), _s(yy)) for x, yy in curve]
    poly += [(_s(T.PLOT_RIGHT), _s(T.HORIZON_Y))]
    md.polygon(poly, fill=255)

    c.img.paste(full, (0, 0), mask)
    c.d = ImageDraw.Draw(c.img)
    # horizon baseline
    c.line([(T.PLOT_LEFT, T.HORIZON_Y), (T.PLOT_RIGHT, T.HORIZON_Y)], T.INK, 1)


def _draw_title_and_axis(c, ctx, X):
    """Top chart furniture, in three rows:
      1) title row: "Weekday  Month D" on a single line per day, left-aligned to
         that day's sunrise and pushed left only as far as needed to fit;
      2) sun times row: sunrise / solar noon / sunset times;
      3) axis row: the x-axis line (the night-box ceiling) with 3h/6h/midnight
         ticks plus longer marks at the sun events.
    """
    from data.sun import sun_events
    start, end = ctx["start"], ctx["end"]
    loc = ctx["location"]
    tz = start.tzinfo

    # --- title row: one line per day, anchored at sunrise ----------------------
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        d0, d1 = day, day + datetime.timedelta(days=1)
        vis0, vis1 = max(d0, start), min(d1, end)
        label = f"{day.strftime('%A')} {day.strftime('%B %-d')}"
        w = c.text_width(label, "serif", T.FONT_DATE)
        # don't bother if the day's visible slice is too narrow to read the label
        if vis1 > vis0 and (X(vis1) - X(vis0)) >= w * 0.92:
            ev = sun_events(d0.date(), loc["latitude"], loc["longitude"], tz)
            sr = ev["sunrise"]
            # ideal left edge = sunrise; clamp into the visible span and plot,
            # so the title sits at sunrise but slides left to keep room.
            left = X(sr) if sr else X(vis0)
            left = min(left, X(vis1) - w)      # don't run past the day's end
            left = max(left, X(vis0))          # don't start before the day
            left = max(left, T.PLOT_LEFT)      # stay inside the plot
            left = min(left, T.PLOT_RIGHT - w)
            c.text((left, T.TITLE_Y), label, T.INK, "serif", T.FONT_DATE,
                   anchor="ls")
        day = d1

    # --- sun times row (above the axis), left-aligned near each event tick ---
    yt = T.AXIS_TICK_Y                # axis line; also the top of the night box
    d = start.astimezone(tz).date()
    last = end.astimezone(tz).date()
    while d <= last:
        ev = sun_events(d, loc["latitude"], loc["longitude"], tz)
        sr, ss = ev["sunrise"], ev["sunset"]
        noon = datetime.datetime(d.year, d.month, d.day, 12, tzinfo=tz)
        marks = []
        if sr:
            marks.append((sr, sr))                        # sunrise time
        marks.append(("noon", noon))                      # clock noon — at its tick
        if ss:
            marks.append((ss, ss))                        # sunset time
        for label, when in marks:
            x = X(when)
            if not (T.PLOT_LEFT <= x <= T.PLOT_RIGHT):
                continue
            if label == "noon":
                # "Noon" as true small caps: full-size cap N + small-caps OON,
                # sharing a baseline (same treatment as the small-caps meridiem).
                sc = max(T.FONT_MIN, round(T.FONT_TIME * T.SMALLCAP))
                w_n = c.text_width("N", "sans", T.FONT_TIME)
                total = w_n + c.text_width("OON", "sans", sc)
                lx = min(x, T.PLOT_RIGHT - total)
                c.text((lx, T.SUN_LABEL_Y), "N", T.INK, "sans",
                       T.FONT_TIME, anchor="ls")
                c.text((lx + w_n, T.SUN_LABEL_Y), "OON", T.INK, "sans",
                       sc, anchor="ls")
            else:
                # sunrise / sunset: a short tick UP from the upper axis toward
                # the time label.
                c.line([(x, T.AXIS_TICK_Y),
                        (x, T.AXIS_TICK_Y - T.AXIS_TICK_SHORT)], T.INK_SOFT, 1)
                w = _time_width(c, label, T.FONT_TIME)
                lx = min(x, T.PLOT_RIGHT - w)   # left-align at the tick, clamp
                _draw_time(c, lx, T.SUN_LABEL_Y, label, T.FONT_TIME,
                           T.INK, "sans", align="l")
        d += datetime.timedelta(days=1)

    # --- upper axis line + 3h hour ticks (hanging down into the weather row) ---
    c.line([(T.PLOT_LEFT, yt), (T.PLOT_RIGHT, yt)], T.INK_SOFT, 1)
    t = start.replace(minute=0, second=0, microsecond=0)
    while t < start or t.hour % 3 != 0:
        t += datetime.timedelta(hours=1)
    while t <= end:
        x = X(t)
        if t.hour == 0:
            c.line([(x, yt), (x, yt + T.AXIS_TICK_LONG + 6)], T.INK, 1)
        elif t.hour % 6 == 0:
            c.line([(x, yt), (x, yt + T.AXIS_TICK_LONG)], T.INK_SOFT, 1)
        else:
            c.line([(x, yt), (x, yt + T.AXIS_TICK_SHORT)], T.INK_SOFT, 1)
        t += datetime.timedelta(hours=3)

    # --- lower axis line (no ticks): floor of the weather row, top of night ---
    c.line([(T.PLOT_LEFT, T.WX_AXIS2_Y), (T.PLOT_RIGHT, T.WX_AXIS2_Y)],
           T.INK_SOFT, 1)


def _galileo_moon(c, cx, cy, r, frac, illum, rng):
    """An engraved-sphere moon. The dark hemisphere is shaded with fine meridian
    (constant-longitude) arcs that converge at the poles and compress toward the
    limb, so the edge darkens on its own while the terminator stays crisp; the
    lit hemisphere is left clean white. A few named craters sit on the lit side
    as small bowls (a shadow crescent plus a faint rim). Pure crisp line work —
    no gray wash — kin to the engraved sea. Anti-aliased by rendering the moon on
    a high-res sub-layer and downsampling once, then clipped to the disk."""
    ms = 4                                      # moon-only supersample (crisp arcs)
    pad = 4
    waxing = frac < 0.5
    sun = 1 if waxing else -1
    rxe = r * (1 - 2 * illum)                   # signed terminator half-width
    D = int(round((2 * r + 2 * pad) * ms))
    lc = D / 2.0
    layer = Image.new("L", (D, D), 255)
    wd = ImageDraw.Draw(layer)

    def L(dx, dy):                              # moon-relative logical → sublayer
        return (lc + dx * ms, lc + dy * ms)

    def termx(dy):                              # clean (un-roughened) terminator
        return rxe * math.sqrt(max(0.0, 1 - (dy / r) ** 2))

    def off_of(dx, dy):                         # >0 lit, <0 dark
        return (dx - termx(dy)) if waxing else (-dx - termx(dy))

    lw = max(1, ms - 1)

    # meridian arcs (constant longitude) on the dark hemisphere only; they bunch
    # toward the limb so the edge reads darkest, and converge at the poles.
    lon = -88.0
    while lon <= 88.0:
        lo = math.radians(lon)
        seg = []
        lat = -90.0
        while lat <= 90.0:
            la = math.radians(lat)
            dx = r * math.cos(la) * math.sin(lo)
            dy = -r * math.sin(la)
            if off_of(dx, dy) < 0:
                seg.append(L(dx, dy))
            else:
                if len(seg) >= 2:
                    wd.line(seg, fill=0, width=lw, joint="curve")
                seg = []
            lat += 1.5
        if len(seg) >= 2:
            wd.line(seg, fill=0, width=lw, joint="curve")
        lon += 5.0

    # craters on the lit side: a shadow crescent on the anti-sun inner wall
    # (the depth cue) plus a faint full rim so each reads as a bowl.
    real = [(-11, -43, 0.11),   # Tycho
            (-20, 10, 0.10),    # Copernicus
            (-9, 51, 0.085),    # Plato
            (26, -11, 0.08),    # Theophilus
            (61, -9, 0.08),     # Langrenus
            (-40, -18, 0.08)]   # Gassendi
    for lon0, lat0, sz in real:
        la, lo = math.radians(lat0), math.radians(lon0)
        cdx = r * 0.92 * math.cos(la) * math.sin(lo)
        cdy = -r * 0.92 * math.sin(la)
        cr = sz * r
        if off_of(cdx, cdy) < 0.05 * r:
            continue                            # lit-side craters only
        d0 = math.sqrt(cdx * cdx + cdy * cdy) or 1.0
        rho = d0 / r
        fore = max(0.18, math.sqrt(1 - rho * rho))
        rhx, rhy = cdx / d0, cdy / d0
        thx, thy = -rhy, rhx

        def place(u, v):                        # crater surface (u,v) → screen
            radc = (u * rhx + v * rhy) * fore
            tanc = u * thx + v * thy
            return (cr * (radc * rhx + tanc * thx),
                    cr * (radc * rhy + tanc * thy))

        sh = []                                 # shadow crescent (anti-sun wall)
        for k in range(19):
            v = 1 - 2.0 * k / 18
            ox, oy = place(-1.0 * sun * math.sqrt(max(0.0, 1 - v * v)), v)
            sh.append(L(cdx + ox, cdy + oy))
        for k in range(19):
            v = -1 + 2.0 * k / 18
            ox, oy = place(-0.45 * sun * math.sqrt(max(0.0, 1 - v * v)), v)
            sh.append(L(cdx + ox, cdy + oy))
        wd.polygon(sh, fill=110)
        ring = []                               # faint rim → reads as a bowl
        for k in range(33):
            a = 2 * math.pi * k / 32
            ox, oy = place(math.cos(a), math.sin(a))
            ring.append(L(cdx + ox, cdy + oy))
        wd.line(ring, fill=175, width=lw, joint="curve")

    # downsample to the canvas (SS) scale for crisp AA, clip to the disk so
    # nothing spills past the rim, then composite.
    target = int(round((2 * r + 2 * pad) * SS))
    out = layer.resize((target, target), Image.LANCZOS)
    mask = Image.new("L", (D, D), 0)
    ImageDraw.Draw(mask).ellipse([L(-r, -r), L(r, r)], fill=255)
    mask = mask.resize((target, target), Image.LANCZOS)
    x0 = int(round((cx - r - pad) * SS))
    y0 = int(round((cy - r - pad) * SS))
    c.img.paste(out, (x0, y0), mask)
    c.d = ImageDraw.Draw(c.img)

    c.dot(cx, cy, r, fill=None, outline=165, width=2)   # light-gray rim


def _draw_moon(c, ctx, X):
    """Moon at each transit (highest point): x = transit time, y by altitude.
    Sitting over a night band vs. clear sky tells you day-moon or night-moon."""
    moon = ctx["moon"]
    track = moon["track"]
    frac, illum = moon["frac"], moon["illum"]
    r = 80                  # ~2x the previous 40px radius
    top_pin = 40            # the old radius: keeps the top edge where it was

    def moon_y(alt):
        a = max(0.0, min(alt, T.ALT_SCALE))
        return T.MOON_STRIP_BOT - a / T.ALT_SCALE \
            * (T.MOON_STRIP_BOT - T.MOON_STRIP_TOP)

    for i in range(1, len(track) - 1):
        (_, a0), (ti, a1), (_, a2) = track[i - 1], track[i], track[i + 1]
        if a1 > 0 and a1 >= a0 and a1 >= a2:
            x = X(ti)
            if T.PLOT_LEFT + r < x < T.PLOT_RIGHT - r:
                # grow downward from the old top edge (top stays put); seed by
                # transit time so the stipple is stable across refreshes
                _galileo_moon(c, x, moon_y(a1) - top_pin + r + T.MOON_DROP, r,
                              frac, illum, random.Random(int(ti.timestamp())))


def _draw_curve(c, curve, X, now):
    nx = X(now)
    past = [p for p in curve if p[0] <= nx]
    future = [p for p in curve if p[0] >= nx]
    if len(past) > 1:
        c.line(past, T.GRID, 3)
    if len(future) > 1:
        c.line(future, T.INK, 3)


def _draw_extrema(c, series, X, Y, now):
    """Highs get a time label above the crest; lows are bare open dots."""
    for e in series.extrema:
        x, y = X(e.time), Y(e.height)
        if x < T.PLOT_LEFT + 4 or x > T.PLOT_RIGHT - 4:
            continue
        future = e.time >= now
        ink = T.INK if future else T.GRID
        if e.kind == "H":
            c.dot(x, y, 6, fill=ink)
            ly = max(y - 22, T.PLOT_TOP + 10)   # keep the label out of the sky
            _draw_time(c, x, ly, e.time, T.FONT_TIME, T.INK,
                       "sans", align="m")
        else:
            c.dot(x, y, 5, fill=T.PAPER, outline=ink, width=2)


def _draw_now(c, series, X, Y, now):
    if now < series.times[0] or now > series.times[-1]:
        return
    x = X(now)
    y = Y(series.height_at(now))
    # a short tick from the horizon up to the marker — no full-height spike
    c.line([(x, y), (x, T.HORIZON_Y)], T.INK_SOFT, 1)
    c.dot(x, y, 7, fill=T.INK)
    c.dot(x, y, 12, fill=None, outline=T.PAPER, width=3)
    c.dot(x, y, 12, fill=None, outline=T.INK, width=1)


def _draw_temperature(c, ctx, X):
    """Optional air-temperature line along the bottom of the sky region."""
    wx = ctx["weather"]
    start, end = ctx["start"], ctx["end"]
    hours = []
    t = start.replace(minute=0, second=0, microsecond=0)
    while t <= end:
        hours.append(t)
        t += datetime.timedelta(hours=1)
    pts = [(X(h), wx.temp_f(h)) for h in hours if wx.temp_f(h) is not None]
    if len(pts) < 2:
        return
    vals = [v for _, v in pts]
    tmin, tmax = min(vals), max(vals)
    pad = max(2.0, (tmax - tmin) * 0.25)
    span = (tmax + pad) - (tmin - pad)
    top, bot = T.MOON_STRIP_TOP, T.MOON_STRIP_BOT

    def ty(v):
        return bot - (v - (tmin - pad)) / span * (bot - top)

    c.line([(x, ty(v)) for x, v in pts], T.INK_SOFT, 2)
    for label_v, want_max in ((tmax, True), (tmin, False)):
        x, v = next(p for p in pts if p[1] == label_v)
        y = ty(v)
        c.dot(x, y, 3, fill=T.INK_SOFT)
        c.text((x, y - 14 if want_max else y + 14), f"{round(v)}°",
               T.INK_SOFT, "sans", 20, anchor="md" if want_max else "ma")


def _is_day(ctx, t):
    return any(sr <= t < ss for sr, ss in ctx["daylight"])


# IBM Carbon weather pictograms (Apache-2.0), pre-rasterized to PNG by
# tools/fetch_carbon_weather.py so the renderer stays Pillow-only on the Pi.
_GLYPH_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                          "assets", "weather")
_glyph_cache = {}


def _glyph_alpha(name, size_dev):
    """Cached alpha (ink coverage) mask of a Carbon glyph at `size_dev` px."""
    key = (name, size_dev)
    if key not in _glyph_cache:
        path = os.path.join(_GLYPH_DIR, name + ".png")
        im = Image.open(path).convert("RGBA")
        _glyph_cache[key] = im.split()[3].resize((size_dev, size_dev),
                                                  Image.LANCZOS)
    return _glyph_cache[key]


def _place_glyph(c, name, cx, cy, size):
    """Paste Carbon glyph `name` centered at logical (cx,cy), `size` logical."""
    sd = _s(size)
    alpha = _glyph_alpha(name, sd)
    box = (_s(cx) - sd // 2, _s(cy) - sd // 2)
    c.img.paste(Image.new("L", (sd, sd), T.INK), box, alpha)
    c.d = ImageDraw.Draw(c.img)


_WINDY_MPH = 25            # gust threshold (mph) for the windy glyph


def _weather_class(wx, t):
    """A day/night-agnostic sky class used for change detection (so a pure
    sunset swap of sun<->constellation is NOT treated as a weather change).
    Precip/thunder win over wind, which wins over cloud cover."""
    kind = wx.precip_kind(t)
    if kind == "thunder":
        return "thunder"
    if kind == "snow":
        return "snow"
    if kind == "rain":
        return "rain_heavy" if (wx.precip_prob(t) or 0) >= 70 else "rain"
    gust = wx.gust_mph(t)
    if gust is not None and gust >= _WINDY_MPH:
        return "windy"
    cov = wx.cloud(t) or 0
    if cov >= 90:
        return "overcast"
    if cov >= 70:
        return "cloudy"
    if cov >= 30:
        return "partly"
    return "clear"


def _condition(wx, t, day):
    """The Carbon glyph to show: the weather class, but clear and partly skies
    pick a day vs night form (sun/constellation, partly/cloudy)."""
    cls = _weather_class(wx, t)
    if cls == "clear":
        return "sunny" if day else "constellation"
    if cls == "partly":
        return "partly" if day else "cloudy"
    if cls == "thunder":
        return "lightning"
    return cls


def _tick_times(ctx):
    """The 3-hour tick times across the window (same marks the axis ticks use)."""
    start, end = ctx["start"], ctx["end"]
    t = start.replace(minute=0, second=0, microsecond=0)
    while t < start or t.hour % 3 != 0:
        t += datetime.timedelta(hours=1)
    out = []
    while t <= end:
        out.append(t)
        t += datetime.timedelta(hours=3)
    return out


def _draw_weather(c, ctx, X):
    """Carbon weather pictograms in their own row between the two axis lines,
    one every 3 hours centered on the ticks. A clear night shows no glyph (the
    moon below stands in for it)."""
    wx = ctx["weather"]
    size = T.WX_GLYPH_SIZE
    # Show a glyph at: the first ("now") cell; the noon/midnight anchors; and any
    # cell where the WEATHER CLASS changes from the previous cell. Change uses
    # the day/night-agnostic class, so a plain sunset (sun -> constellation) does
    # not count as a transition — only real weather shifts do.
    prev = None
    for i, t in enumerate(_tick_times(ctx)):
        cls = _weather_class(wx, t)
        change = i > 0 and cls != prev
        prev = cls
        if not (i == 0 or t.hour in (0, 12) or change):
            continue
        name = _condition(wx, t, _is_day(ctx, t))
        cx = X(t + datetime.timedelta(hours=1.5))    # center of the 3h section
        if name and T.PLOT_LEFT + size * 0.5 < cx < T.PLOT_RIGHT - size * 0.5:
            _place_glyph(c, name, cx, T.WX_ROW_Y, size)


def _draw_frame(c):
    """A hairline border inset from the panel edge — the mat around the print."""
    c.rect((T.MARGIN, T.MARGIN, T.WIDTH - T.MARGIN, T.HEIGHT - T.MARGIN),
           outline=T.BORDER, width=2)
