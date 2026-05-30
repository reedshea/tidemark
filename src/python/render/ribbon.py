#!/usr/bin/env python3
"""
The Tidemark ribbon: a clean, Tufte-style tide chart for e-ink.

One black tide line edge to edge, directly-labeled highs and lows, a slim
day/night band along the time axis, and a small true-phase moon. Everything is
rendered at 2x and downsampled so lines are smooth (anti-aliased grays) instead
of jagged — which also reads far better on e-ink than hard 1-bit edges.
"""

import math
import datetime

from PIL import Image, ImageDraw

from render import theme as T

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
        self.d.text((_s(xy[0]), _s(xy[1])), s, fill=fill,
                    font=T.font(style, _s(size)), anchor=anchor)

    def text_w(self, s, style, size):
        f = T.font(style, _s(size))
        box = self.d.textbbox((0, 0), s, font=f)
        return (box[2] - box[0]) / SS

    def finish(self):
        return self.img.resize((T.WIDTH, T.HEIGHT), Image.LANCZOS)


def _fmt_time(dt):
    """e.g. '1:42p' — compact 12-hour."""
    h = dt.hour % 12 or 12
    ap = "a" if dt.hour < 12 else "p"
    return f"{h}:{dt.minute:02d}{ap}"


def _fmt_axis_hour(dt):
    h = dt.hour % 12 or 12
    ap = "a" if dt.hour < 12 else "p"
    if dt.hour == 0:
        return "12a"
    return f"{h}{ap}"


def render(ctx):
    c = _Canvas(T.WIDTH, T.HEIGHT)
    units = ctx["units"]
    to_disp = (lambda m: m * M2FT) if units == "ft" else (lambda m: m)
    unit_label = "ft" if units == "ft" else "m"

    start, end, now = ctx["start"], ctx["end"], ctx["now"]
    series = ctx["series"]
    span_s = (end - start).total_seconds()

    def X(dt):
        return T.PLOT_LEFT + (dt - start).total_seconds() / span_s \
            * (T.PLOT_RIGHT - T.PLOT_LEFT)

    # vertical range in display units, with breathing room above the highs and
    # below the lows so labels never collide with the curve or the frame. The
    # solid frame is the baseline; 0 (the MLLW datum) appears as a gridline.
    lo = to_disp(series.min)
    hi = to_disp(series.max)
    y_lo = lo - 0.7
    y_hi = hi + max(0.8, (hi - lo) * 0.16)

    def Yv(v):  # display-unit value -> pixel
        return T.PLOT_BOTTOM - (v - y_lo) / (y_hi - y_lo) \
            * (T.PLOT_BOTTOM - T.PLOT_TOP)

    def Y(h_m):  # meters -> pixel
        return Yv(to_disp(h_m))

    has_wx = ctx.get("weather") is not None
    arc_top = T.WX_MOON_TOP if has_wx else T.SKY_TOP

    _draw_daynight(c, ctx, X, start, end)
    if has_wx:
        _draw_weather(c, ctx, X)
    _draw_sky(c, ctx, X, arc_top)
    _draw_height_axis(c, Yv, y_lo, y_hi, unit_label)
    _draw_time_axis(c, ctx, X)
    _draw_curve(c, series, X, Y, now)
    _draw_extrema(c, series, X, Y, now, to_disp, unit_label)
    _draw_now(c, series, X, Y, now, to_disp, unit_label)
    _draw_header(c, ctx)
    _draw_footer(c, ctx)

    return c.finish()


def _draw_daynight(c, ctx, X, start, end):
    """Night rendered as a slim band under the plot plus a barely-there column
    wash above, so daylight high tides sit on white and night ones on faint
    gray — the swim answer at a glance, without a heavy full-screen wash."""
    band_top = T.BAND_TOP
    band_bot = T.BAND_TOP + T.BAND_H
    # paint everything (sky + sea) as night, then lift daylight back to paper
    c.rect((T.PLOT_LEFT, T.SKY_TOP, T.PLOT_RIGHT, T.PLOT_BOTTOM),
           fill=T.NIGHT_WASH)
    c.rect((T.PLOT_LEFT, band_top, T.PLOT_RIGHT, band_bot), fill=T.FAINT)
    for (sr, sset) in ctx["daylight"]:
        x0 = max(T.PLOT_LEFT, X(sr))
        x1 = min(T.PLOT_RIGHT, X(sset))
        if x1 <= x0:
            continue
        c.rect((x0, T.SKY_TOP, x1, T.PLOT_BOTTOM), fill=T.PAPER)
        c.rect((x0, band_top, x1, band_bot), fill=T.PAPER)
    c.line([(T.PLOT_LEFT, band_top), (T.PLOT_RIGHT, band_top)], T.GRID, 1)
    c.line([(T.PLOT_LEFT, band_bot), (T.PLOT_RIGHT, band_bot)], T.GRID, 1)


def _draw_height_axis(c, Yv, y_lo, y_hi, unit_label):
    # solid frame baseline
    c.line([(T.PLOT_LEFT, T.PLOT_BOTTOM), (T.PLOT_RIGHT, T.PLOT_BOTTOM)],
           T.INK, 1)
    step = 1 if (y_hi - y_lo) <= 7 else 2
    v = math.ceil(y_lo)
    while v <= y_hi + 0.001:
        y = Yv(v)
        c.line([(T.PLOT_LEFT, y), (T.PLOT_RIGHT, y)],
               T.GRID if v == 0 else T.FAINT, 1)
        c.line([(T.PLOT_LEFT - 8, y), (T.PLOT_LEFT, y)], T.GRID, 1)
        c.text((T.PLOT_LEFT - 16, y), f"{v}", T.INK_SOFT, "sans", 22,
               anchor="rm")
        v += step
    c.text((T.PLOT_LEFT - 16, T.PLOT_TOP - 34), unit_label, T.INK_SOFT,
           "sans", 22, anchor="rm")


def _draw_time_axis(c, ctx, X):
    start, end = ctx["start"], ctx["end"]
    tz = start.tzinfo
    # tick every 3 hours aligned to clock
    t = start.replace(minute=0, second=0, microsecond=0)
    if t < start:
        t += datetime.timedelta(hours=1)
    while t.hour % 3 != 0:
        t += datetime.timedelta(hours=1)
    while t <= end:
        x = X(t)
        is_midnight = (t.hour == 0)
        c.line([(x, T.BAND_TOP + T.BAND_H), (x, T.BAND_TOP + T.BAND_H + 8)],
               T.GRID, 1)
        c.text((x, T.AXIS_LABEL_Y), _fmt_axis_hour(t),
               T.INK_SOFT if not is_midnight else T.INK, "sans", 22,
               anchor="ma")
        if is_midnight:
            # day divider: faint full-height rule + date label
            c.line([(x, T.SKY_TOP), (x, T.BAND_TOP)], T.FAINT, 1)
            c.text((x, T.AXIS_LABEL_Y + 30), t.strftime("%a %b %-d"),
                   T.INK_SOFT, "serif", 22, anchor="ma")
        t += datetime.timedelta(hours=3)


def _draw_curve(c, series, X, Y, now):
    pts = [(X(t), Y(h)) for t, h in zip(series.times, series.heights)]
    # past in soft gray, future in ink, so the eye lands on what's ahead
    nx = X(now)
    past = [p for p in pts if p[0] <= nx]
    future = [p for p in pts if p[0] >= nx]
    if len(past) > 1:
        c.line(past, T.GRID, 3)
    if len(future) > 1:
        c.line(future, T.INK, 3)


def _draw_extrema(c, series, X, Y, now, to_disp, unit_label):
    next_high = series.next_high(now)
    for e in series.extrema:
        x, y = X(e.time), Y(e.height)
        if x < T.PLOT_LEFT + 4 or x > T.PLOT_RIGHT - 4:
            continue
        future = e.time >= now
        ink = T.INK if future else T.GRID
        is_next = (next_high is not None and e is next_high)
        val = to_disp(e.height)
        tstr = _fmt_time(e.time)
        hstr = f"{val:.1f}{unit_label}"
        if e.kind == "H":
            c.dot(x, y, 6, fill=ink)
            style = "sans_bold" if is_next else "sans"
            c.text((x, y - 20), tstr, ink, style, 30, anchor="md")
            c.text((x, y - 54), hstr, T.INK_SOFT if not is_next else ink,
                   "sans", 22, anchor="md")
            if is_next:
                c.dot(x, y, 11, fill=None, outline=T.INK, width=2)
        else:
            c.dot(x, y, 5, fill=T.PAPER, outline=ink, width=2)
            c.text((x, y + 18), tstr, T.INK_SOFT if future else T.GRID,
                   "sans", 24, anchor="ma")
            c.text((x, y + 46), hstr, T.GRID, "sans", 20, anchor="ma")


def _draw_now(c, series, X, Y, now, to_disp, unit_label):
    if now < series.times[0] or now > series.times[-1]:
        return
    x = X(now)
    h = series.height_at(now)
    y = Y(h)
    c.line([(x, T.SKY_TOP), (x, T.PLOT_BOTTOM)], T.INK_SOFT, 1)
    c.dot(x, y, 7, fill=T.INK)
    c.dot(x, y, 12, fill=None, outline=T.PAPER, width=3)
    c.dot(x, y, 12, fill=None, outline=T.INK, width=1)
    c.text((x + 16, T.PLOT_TOP - 2), "now", T.INK, "sans_bold", 22, anchor="lt")


def _draw_header(c, ctx):
    loc = ctx["location"]
    now = ctx["now"]
    c.text((T.PLOT_LEFT - 4, 70), loc["name"], T.INK, "serif", 64, anchor="ls")
    c.text((T.PLOT_LEFT - 2, 108), loc["subtitle"], T.INK_SOFT, "serif", 28,
           anchor="ls")
    # date / time, right aligned
    c.text((T.PLOT_RIGHT, 70), now.strftime("%A, %B %-d"), T.INK, "serif", 40,
           anchor="rs")
    c.text((T.PLOT_RIGHT, 108), now.strftime("%-I:%M %p").lower(), T.INK_SOFT,
           "sans", 26, anchor="rs")
    # header rule
    c.line([(T.PLOT_LEFT - 4, 150), (T.PLOT_RIGHT, 150)], T.GRID, 1)


def _moon_glyph(c, cx, cy, r, frac, illum):
    """Draw a true-phase moon: dark disk with the illuminated lune in paper."""
    c.dot(cx, cy, r, fill=T.INK_SOFT)
    waxing = frac < 0.5
    rx = r * (1 - 2 * illum)  # signed terminator x-radius
    steps = 48
    poly = []
    for i in range(steps + 1):  # limb side (top -> bottom)
        a = -math.pi / 2 + math.pi * i / steps
        poly.append((cx + (r if waxing else -r) * math.cos(a),
                     cy + r * math.sin(a)))
    for i in range(steps + 1):  # terminator side (bottom -> top)
        a = math.pi / 2 - math.pi * i / steps
        poly.append((cx + (rx if waxing else -rx) * math.cos(a),
                     cy + r * math.sin(a)))
    if illum > 0.01:
        c.polygon(poly, fill=T.PAPER)
    c.dot(cx, cy, r, fill=None, outline=T.INK, width=2)


def _cloud_gray(pct):
    """Quantize cloud cover into a few gray levels (avoids e-ink banding)."""
    if pct is None:
        return None
    for thresh, gray in ((12, T.PAPER), (37, 234), (62, 212),
                         (87, 190), (101, 170)):
        if pct < thresh:
            return gray
    return 170


def _draw_weather(c, ctx, X):
    """Air-temperature line (top of sky) and a cloud-cover strip with precip
    hatching just above the horizon. Drawn only when a forecast is available."""
    wx = ctx["weather"]
    start, end = ctx["start"], ctx["end"]
    hours = []
    t = start.replace(minute=0, second=0, microsecond=0)
    while t <= end:
        hours.append(t)
        t += datetime.timedelta(hours=1)

    # --- cloud-cover strip (just above the horizon) ---
    top, bot = T.WX_CLOUD_TOP, T.WX_CLOUD_TOP + T.WX_CLOUD_H
    for h in hours:
        x0 = max(T.PLOT_LEFT, X(h))
        x1 = min(T.PLOT_RIGHT, X(h + datetime.timedelta(hours=1)))
        if x1 <= x0:
            continue
        gray = _cloud_gray(wx.cloud(h + datetime.timedelta(minutes=30)))
        if gray is not None and gray < T.PAPER:
            c.rect((x0, top, x1, bot), fill=gray)
        # precipitation hatching
        mid = h + datetime.timedelta(minutes=30)
        pop = wx.precip_prob(mid) or 0
        kind = wx.precip_kind(mid)
        if kind and pop >= 25:
            if kind == "rain":
                step = 16 if pop < 60 else 9
                xx = x0
                while xx < x1:
                    c.line([(xx, bot - 3), (xx + 7, top + 3)], T.INK_SOFT, 1)
                    xx += step
            else:  # snow
                step = 16 if pop < 60 else 10
                xx = x0 + 4
                while xx < x1:
                    c.dot(xx, (top + bot) / 2, 1.6, fill=T.INK_SOFT)
                    xx += step
    c.line([(T.PLOT_LEFT, top), (T.PLOT_RIGHT, top)], T.GRID, 1)
    c.line([(T.PLOT_LEFT, bot), (T.PLOT_RIGHT, bot)], T.GRID, 1)
    c.text((T.PLOT_LEFT - 14, (top + bot) / 2), "cloud", T.GRID, "sans", 18,
           anchor="rm")

    # --- air-temperature line (top of the sky panel) ---
    pts = [(X(h), wx.temp_f(h)) for h in hours if wx.temp_f(h) is not None]
    if len(pts) < 2:
        return
    vals = [v for _, v in pts]
    tmin, tmax = min(vals), max(vals)
    pad = max(2.0, (tmax - tmin) * 0.25)
    lo, hi = tmin - pad, tmax + pad

    def ty(v):
        return T.WX_TEMP_BOT - (v - lo) / (hi - lo) \
            * (T.WX_TEMP_BOT - T.WX_TEMP_TOP)

    c.line([(x, ty(v)) for x, v in pts], T.INK_SOFT, 2)
    c.text((T.PLOT_LEFT - 14, T.WX_TEMP_TOP + 6), "°F", T.GRID, "sans", 18,
           anchor="rm")
    # mark the warmest and coolest points
    for label_v, want_max in ((tmax, True), (tmin, False)):
        x, v = next((p for p in pts if p[1] == label_v))
        y = ty(v)
        c.dot(x, y, 3, fill=T.INK_SOFT)
        c.text((x, y - 16 if want_max else y + 16),
               f"{round(v)}°", T.INK_SOFT, "sans", 20,
               anchor="md" if want_max else "ma")


def _draw_sky(c, ctx, X, arc_top):
    """The sky panel: the moon's real altitude arc from rise to set, with the
    phase glyph riding at its high point. Sun stays as the day/night band."""
    moon = ctx["moon"]
    track = moon["track"]
    frac, illum = moon["frac"], moon["illum"]

    def sky_y(alt):
        a = max(0.0, min(alt, T.ALT_SCALE))
        return T.HORIZON_Y - a / T.ALT_SCALE * (T.HORIZON_Y - arc_top)

    # horizon line
    c.line([(T.PLOT_LEFT, T.HORIZON_Y), (T.PLOT_RIGHT, T.HORIZON_Y)],
           T.GRID, 1)

    # split the track into above-horizon arc segments
    segments, seg = [], []
    for (t, alt) in track:
        if alt > 0:
            seg.append((X(t), sky_y(alt), alt))
        elif seg:
            segments.append(seg)
            seg = []
    if seg:
        segments.append(seg)

    best_apex = None  # (x, y, alt) of the highest transit, for the label
    for seg in segments:
        pts = [(x, y) for x, y, _ in seg]
        if len(pts) > 1:
            c.line(pts, T.INK_SOFT, 2)
        # only glyph a genuine transit: an interior altitude maximum, so partial
        # arcs clipped at the window edge show as a bare rising/setting line
        ai = max(range(len(seg)), key=lambda i: seg[i][2])
        apex = seg[ai]
        if 0 < ai < len(seg) - 1 and apex[2] > 6:
            _moon_glyph(c, apex[0], apex[1], 26, frac, illum)
            if best_apex is None or apex[2] > best_apex[2]:
                best_apex = apex

    # rise/set ticks + times at the horizon
    for kind, t in moon["events"]:
        x = X(t)
        if x < T.PLOT_LEFT + 4 or x > T.PLOT_RIGHT - 4:
            continue
        c.line([(x, T.HORIZON_Y - 7), (x, T.HORIZON_Y + 7)], T.INK_SOFT, 1)
        arrow = "▲" if kind == "moonrise" else "▼"
        c.text((x, T.HORIZON_Y + 14), f"{arrow} {_fmt_time(t)}", T.INK_SOFT,
               "sans", 20, anchor="ma")

    # phase name + illumination beside the highest moon
    if best_apex is not None:
        label = f"{moon['name']} · {int(round(illum * 100))}%"
        c.text((best_apex[0] + 40, best_apex[1] - 8), label, T.INK_SOFT,
               "serif", 24, anchor="lm")


def _draw_footer(c, ctx):
    now = ctx["now"]
    msg = (f"tidemark · {ctx['location']['name']} · predicted offline · "
           f"updated {now.strftime('%-I:%M %p').lower()}")
    c.text((T.PLOT_LEFT - 4, T.FOOTER_Y), msg, T.GRID, "sans", 20, anchor="lt")
