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

Rendered at 2x and downsampled so the curve and hairlines are smooth.
"""

import math
import datetime

from PIL import Image, ImageDraw

from render import theme as T
from data.sun import sun_altitude

SS = 2  # supersampling factor
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


class _Canvas:
    """Thin wrapper that scales all drawing by the supersample factor."""

    def __init__(self, w, h):
        self.img = Image.new("L", (_s(w), _s(h)), T.PAPER)
        self.d = ImageDraw.Draw(self.img)

    def line(self, pts, fill, width=1):
        self.d.line([(_s(x), _s(y)) for x, y in pts], fill=fill,
                    width=max(1, _s(width)), joint="curve")

    def rect(self, box, fill=None, outline=None, width=1):
        self.d.rectangle([_s(box[0]), _s(box[1]), _s(box[2]), _s(box[3])],
                         fill=fill, outline=outline, width=max(1, _s(width)))

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
        self.d.text((_s(xy[0]), _s(xy[1])), s, fill=fill,
                    font=T.font(style, _s(size)), anchor=anchor)

    def text_width(self, s, style, size):
        """Logical-pixel width of `s` at the given style/size (after FONT_MIN)."""
        size = max(size, T.FONT_MIN)
        box = self.d.textbbox((0, 0), s, font=T.font(style, _s(size)))
        return (box[2] - box[0]) / SS

    def finish(self):
        return self.img.resize((T.WIDTH, T.HEIGHT), Image.LANCZOS)


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

    def X(dt):
        return T.PLOT_LEFT + (dt - start).total_seconds() / span_s \
            * (T.PLOT_RIGHT - T.PLOT_LEFT)

    # Fixed scale from the station's annual extremes: the annual low sits at the
    # horizon baseline and the curve fills upward, with headroom for peak labels.
    sc = ctx["scale"]
    lo, hi = to_disp(sc["lo"]), to_disp(sc["hi"])
    rng = hi - lo
    y_lo, y_hi = lo - rng * 0.02, hi + rng * 0.10

    def Y(h_m):
        v = to_disp(h_m)
        return T.PLOT_BOTTOM - (v - y_lo) / (y_hi - y_lo) \
            * (T.PLOT_BOTTOM - T.PLOT_TOP)

    curve = [(X(t), Y(h)) for t, h in zip(series.times, series.heights)]

    _draw_night_bands(c, ctx, X, curve)
    _draw_engraved_sea(c, curve)
    _draw_title_and_axis(c, ctx, X)
    _draw_moon(c, ctx, X)
    _draw_curve(c, curve, X, now)
    _draw_extrema(c, series, X, Y, now)
    _draw_now(c, series, X, Y, now)
    if ctx.get("weather") is not None:
        _draw_temperature(c, ctx, X)
    _draw_frame(c)

    return c.finish(), _now_marker_rect(X, now)


def _now_marker_rect(X, now):
    """Bounding box (logical px, x/y/w/h) of the region the now-marker can
    occupy during the current clock hour.

    The window is anchored to the top of the hour, so between hourly full
    refreshes only the now-marker moves — and it stays within this single
    one-hour-wide column. The host refreshes just this strip every few minutes
    (partial GC16) and repaints the whole panel when the hour rolls over. The
    box spans the full curve height so the dot is never clipped as it rides the
    tide up and down, plus the dot's outer ring and a little label headroom."""
    hour0 = now.replace(minute=0, second=0, microsecond=0)
    x0 = X(hour0)
    x1 = X(hour0 + datetime.timedelta(hours=1))
    pad_x = 18                       # now-dot outer ring (12) + slack
    rx0 = int(max(T.PLOT_LEFT, x0 - pad_x))
    rx1 = int(min(T.PLOT_RIGHT, x1 + pad_x))
    ry0 = int(T.PLOT_TOP - 40)       # headroom for a high-tide crest label
    ry1 = int(T.HORIZON_Y + 4)       # down to the tick's foot on the horizon
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


def _draw_engraved_sea(c, curve):
    """Fill below the tide curve with evenly spaced hairlines (an engraving),
    clipped to the area under the curve via a polygon mask. The lines undulate
    as a gentle sum of sine swells (see _SEA_SWELL) so the sea reads as rolling
    water. One uniform line shade everywhere — day and night sea read the same;
    night is shown by the sky bands above. Pure black-on-white hairlines: ideal
    for e-ink."""
    full = Image.new("L", (_s(T.WIDTH), _s(T.HEIGHT)), T.PAPER)
    fd = ImageDraw.Draw(full)
    y = T.PLOT_TOP
    i = 0
    while y <= T.HORIZON_Y:
        pts = []
        x = T.PLOT_LEFT
        while x <= T.PLOT_RIGHT:
            yy = y + sum(a * math.sin(2 * math.pi * x / w + p + i * d)
                         for a, w, p, d in _SEA_SWELL)
            pts.append((_s(x), _s(yy)))
            x += 4
        fd.line(pts, fill=T.SEA_LINE, width=max(1, _s(1)))
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
                w = c.text_width("noon", "sans", T.FONT_TIME)
                lx = min(x, T.PLOT_RIGHT - w)
                c.text((lx, T.SUN_LABEL_Y), "noon", T.INK, "sans",
                       T.FONT_TIME, anchor="ls")
            else:
                w = _time_width(c, label, T.FONT_TIME)
                lx = min(x, T.PLOT_RIGHT - w)   # left-align at the tick, clamp
                _draw_time(c, lx, T.SUN_LABEL_Y, label, T.FONT_TIME,
                           T.INK, "sans", align="l")
        d += datetime.timedelta(days=1)

    # --- axis line + hour ticks at 3 / 6 / 9 / 12 (ticks hang into night) ---
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


def _moon_glyph(c, cx, cy, r, frac, illum):
    """True-phase moon: dark disk with the illuminated lune in paper."""
    c.dot(cx, cy, r, fill=T.INK_SOFT)
    waxing = frac < 0.5
    rx = r * (1 - 2 * illum)
    steps = 48
    poly = []
    for i in range(steps + 1):
        a = -math.pi / 2 + math.pi * i / steps
        poly.append((cx + (r if waxing else -r) * math.cos(a),
                     cy + r * math.sin(a)))
    for i in range(steps + 1):
        a = math.pi / 2 - math.pi * i / steps
        poly.append((cx + (rx if waxing else -rx) * math.cos(a),
                     cy + r * math.sin(a)))
    if illum > 0.01:
        c.polygon(poly, fill=T.PAPER)
    c.dot(cx, cy, r, fill=None, outline=T.INK, width=2)


def _draw_moon(c, ctx, X):
    """Moon at each transit (highest point): x = transit time, y by altitude.
    Sitting over a night band vs. clear sky tells you day-moon or night-moon."""
    moon = ctx["moon"]
    track = moon["track"]
    frac, illum = moon["frac"], moon["illum"]
    r = 40

    def moon_y(alt):
        a = max(0.0, min(alt, T.ALT_SCALE))
        return T.MOON_STRIP_BOT - a / T.ALT_SCALE \
            * (T.MOON_STRIP_BOT - T.MOON_STRIP_TOP)

    for i in range(1, len(track) - 1):
        (_, a0), (ti, a1), (_, a2) = track[i - 1], track[i], track[i + 1]
        if a1 > 0 and a1 >= a0 and a1 >= a2:
            x = X(ti)
            if T.PLOT_LEFT + r < x < T.PLOT_RIGHT - r:
                _moon_glyph(c, x, moon_y(a1), r, frac, illum)


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
    next_high = series.next_high(now)
    for e in series.extrema:
        x, y = X(e.time), Y(e.height)
        if x < T.PLOT_LEFT + 4 or x > T.PLOT_RIGHT - 4:
            continue
        future = e.time >= now
        ink = T.INK if future else T.GRID
        if e.kind == "H":
            is_next = (e is next_high)
            c.dot(x, y, 6, fill=ink)
            _draw_time(c, x, y - 22, e.time, T.FONT_TIME, T.INK,
                       "sans_bold" if is_next else "sans", align="m")
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


def _draw_frame(c):
    """A hairline border inset from the panel edge — the mat around the print."""
    c.rect((T.MARGIN, T.MARGIN, T.WIDTH - T.MARGIN, T.HEIGHT - T.MARGIN),
           outline=T.BORDER, width=2)
