#!/usr/bin/env python3
"""
The Tidemark ribbon: a clean, Tufte-style tide chart for e-ink.

Layout: the time axis runs minimally along the top; the tide line is the hero;
the moon rides as a single glyph at its transit (high point) in a thin strip
near the top, so you can see at a glance whether it peaks by day or by night;
a slim day/night band sits at the bottom. Rendered at 2x and downsampled so
lines are smooth anti-aliased grays rather than jagged 1-bit edges.
"""

import math
import datetime

from PIL import Image, ImageDraw

from render import theme as T
from data.sun import sun_altitude

SS = 2  # supersampling factor
M2FT = 3.28084


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

    def finish(self):
        return self.img.resize((T.WIDTH, T.HEIGHT), Image.LANCZOS)


def _fmt_time(dt):
    """e.g. '1:42p' — compact 12-hour."""
    h = dt.hour % 12 or 12
    ap = "a" if dt.hour < 12 else "p"
    return f"{h}:{dt.minute:02d}{ap}"


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

    # Fixed scale centered on mean tide level: the middle line sits exactly
    # halfway, lows read as negative and highs as positive (local relative
    # level, not absolute feet). 15% headroom keeps even annual extremes — and
    # the labels above peaks — off the edges.
    sc = ctx["scale"]
    mid = to_disp(sc["mid"])
    half = max(to_disp(sc["hi"]) - mid, mid - to_disp(sc["lo"])) * 1.15
    y_lo, y_hi = mid - half, mid + half

    def Yv(v):
        return T.PLOT_BOTTOM - (v - y_lo) / (y_hi - y_lo) \
            * (T.PLOT_BOTTOM - T.PLOT_TOP)

    def Y(h_m):
        return Yv(to_disp(h_m))

    _draw_daynight(c, ctx, X)
    _draw_top_axis(c, ctx, X)
    _draw_midline(c, Yv, mid)
    _draw_moon(c, ctx, X)
    _draw_curve(c, series, X, Y, now)
    _draw_extrema(c, series, X, Y, now)
    _draw_now(c, series, X, Y, now)
    if ctx.get("weather") is not None:
        _draw_temperature(c, ctx, X)
    _draw_title(c, ctx)

    return c.finish()


def _sky_shade(alt):
    """Map a sun altitude (deg) to a sky gray: white at/above the horizon,
    darkening to NIGHT_SKY once the sun is TWILIGHT_SPAN below it."""
    if alt >= 0:
        return T.PAPER
    f = min(1.0, -alt / T.TWILIGHT_SPAN)   # 0 at horizon → 1 at full night
    return int(round(T.PAPER + f * (T.NIGHT_SKY - T.PAPER)))


def _draw_daynight(c, ctx, X):
    """A day/night gradient 'sky' block below the title (not full height): each
    column's gray tracks the sun's altitude — white by day, gray through dawn/
    dusk to its darkest at solar midnight. The moon rides on top at its transit.
    The tide panel itself stays clean white."""
    loc = ctx["location"]
    start, end = ctx["start"], ctx["end"]
    span_s = (end - start).total_seconds()
    top, bot = T.MOON_TOP, T.MOON_BOT
    n = int(T.PLOT_RIGHT - T.PLOT_LEFT)        # ~one sample per logical pixel
    w = (T.PLOT_RIGHT - T.PLOT_LEFT) / n
    for i in range(n):
        t = start + datetime.timedelta(seconds=span_s * (i + 0.5) / n)
        shade = _sky_shade(sun_altitude(t, loc["latitude"], loc["longitude"]))
        x0 = T.PLOT_LEFT + i * w
        c.rect((x0, top, x0 + w + 1, bot), fill=shade)
    c.line([(T.PLOT_LEFT, top), (T.PLOT_RIGHT, top)], T.GRID, 1)
    c.line([(T.PLOT_LEFT, bot), (T.PLOT_RIGHT, bot)], T.GRID, 1)


def _draw_top_axis(c, ctx, X):
    """Day labels only: each day's name centered at its local noon, sitting in
    the daytime (white) middle of the sky strip. No hour ticks — the gradient
    shows day/night and tide peaks carry their own times."""
    start, end = ctx["start"], ctx["end"]
    y = (T.MOON_TOP + T.MOON_BOT) / 2  # vertical middle of the sky strip
    noon = start.replace(hour=12, minute=0, second=0, microsecond=0)
    while noon < start:
        noon += datetime.timedelta(days=1)
    while noon <= end:
        x = X(noon)
        if T.PLOT_LEFT <= x <= T.PLOT_RIGHT:
            c.text((x, y), noon.strftime("%A"), T.INK_SOFT, "serif", 26,
                   anchor="mm")
        noon += datetime.timedelta(days=1)


def _draw_midline(c, Yv, mid):
    """A single reference line at mean tide level — roughly halfway between high
    and low. No numbers: it shows local relative level (below it reads as low/
    'negative'), not absolute height."""
    y = Yv(mid)
    c.line([(T.PLOT_LEFT, y), (T.PLOT_RIGHT, y)], T.GRID, 1)


def _moon_glyph(c, cx, cy, r, frac, illum):
    """Draw a true-phase moon: dark disk with the illuminated lune in paper."""
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
    """Place the moon at its transit (highest point): x = transit time, y by
    altitude. Sitting over a day or night column answers 'do we see it by day
    or night?'. No arc, no rise/set clutter."""
    moon = ctx["moon"]
    track = moon["track"]
    frac, illum = moon["frac"], moon["illum"]

    def moon_y(alt):
        a = max(0.0, min(alt, T.ALT_SCALE))
        return T.MOON_BOT - a / T.ALT_SCALE * (T.MOON_BOT - T.MOON_TOP)

    # transits = interior local maxima of altitude that are above the horizon
    best = None
    for i in range(1, len(track) - 1):
        (_, a0), (ti, a1), (_, a2) = track[i - 1], track[i], track[i + 1]
        if a1 > 0 and a1 >= a0 and a1 >= a2:
            x = X(ti)
            if x < T.PLOT_LEFT + 26 or x > T.PLOT_RIGHT - 26:
                continue
            _moon_glyph(c, x, moon_y(a1), 22, frac, illum)
            if best is None or a1 > best[1]:
                best = (x, a1, moon_y(a1), ti)
    if best is not None:
        # Phase is shown by the glyph itself; label the moonrise time instead.
        # Prefer the rise leading up to this transit; fall back to next rise,
        # then to the next moonset if the moon never rises in the window.
        rises = sorted(t for (k, t) in moon["events"] if k == "moonrise")
        transit_t = best[3]
        prior = [t for t in rises if t <= transit_t]
        rise = prior[-1] if prior else (rises[0] if rises else None)
        if rise is not None:
            label = f"moonrise {_fmt_time(rise)}"
        else:
            sets = sorted(t for (k, t) in moon["events"] if k == "moonset")
            label = f"moonset {_fmt_time(sets[0])}" if sets else None
        if label:
            c.text((best[0] + 34, best[2]), label, T.INK_SOFT, "serif", 22,
                   anchor="lm")


def _draw_curve(c, series, X, Y, now):
    pts = [(X(t), Y(h)) for t, h in zip(series.times, series.heights)]
    nx = X(now)
    past = [p for p in pts if p[0] <= nx]
    future = [p for p in pts if p[0] >= nx]
    if len(past) > 1:
        c.line(past, T.GRID, 3)
    if len(future) > 1:
        c.line(future, T.INK, 3)


def _draw_extrema(c, series, X, Y, now):
    """Mark highs and lows. Highs get a time label (the thing you plan around);
    lows are just a small open dot. No height labels — the y-axis is enough."""
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
            c.text((x, y - 18), _fmt_time(e.time), ink,
                   "sans_bold" if is_next else "sans", 28, anchor="md")
        else:
            c.dot(x, y, 5, fill=T.PAPER, outline=ink, width=2)


def _draw_now(c, series, X, Y, now):
    if now < series.times[0] or now > series.times[-1]:
        return
    x = X(now)
    y = Y(series.height_at(now))
    c.line([(x, T.TICK_Y), (x, T.PLOT_BOTTOM)], T.INK_SOFT, 1)
    c.dot(x, y, 7, fill=T.INK)
    c.dot(x, y, 12, fill=None, outline=T.PAPER, width=3)
    c.dot(x, y, 12, fill=None, outline=T.INK, width=1)
    c.text((x, T.TIME_LABEL_Y), "now", T.INK, "sans_bold", 22, anchor="mb")


def _draw_temperature(c, ctx, X):
    """Optional air-temperature line along the bottom (no cloud strip)."""
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

    def ty(v):
        return T.TEMP_BOT - (v - (tmin - pad)) / span * (T.TEMP_BOT - T.TEMP_TOP)

    c.line([(x, ty(v)) for x, v in pts], T.INK_SOFT, 2)
    c.text((T.PLOT_LEFT - 16, (T.TEMP_TOP + T.TEMP_BOT) / 2), "°F", T.INK_SOFT,
           "sans", 22, anchor="rm")
    for label_v, want_max in ((tmax, True), (tmin, False)):
        x, v = next(p for p in pts if p[1] == label_v)
        y = ty(v)
        c.dot(x, y, 3, fill=T.INK_SOFT)
        c.text((x, y - 14 if want_max else y + 14), f"{round(v)}°",
               T.INK_SOFT, "sans", 20, anchor="md" if want_max else "ma")


def _draw_title(c, ctx):
    """Date prominent at top-right; location small at top-left (we know where
    we are). 'now' time rides the now-line; this is the static heading."""
    loc = ctx["location"]
    now = ctx["now"]
    # the day, prominent at top-right
    c.text((T.PLOT_RIGHT, 88), now.strftime("%A, %B %-d"), T.INK, "serif",
           50, anchor="rb")
    # location, small and unobtrusive at top-left
    c.text((T.PLOT_LEFT - 4, 86), loc["name"], T.INK_SOFT, "serif", 30,
           anchor="lb")
    c.line([(T.PLOT_LEFT - 4, T.TOP_RULE_Y), (T.PLOT_RIGHT, T.TOP_RULE_Y)],
           T.GRID, 1)
