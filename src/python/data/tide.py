#!/usr/bin/env python3
"""
Tide prediction over a time window.

Produces a dense water-level curve plus the high/low extrema, using the
astronomically-corrected harmonic engine in harmonics.py. All datetimes are
timezone-aware (local wall-clock); the engine converts to UTC internally.

Validated against NOAA station 8447368: high-tide timing within ~3 min,
full-curve RMS ~0.17 m on a ~1.2 m range.
"""

import os
import json
import datetime

from data.harmonics import build_constituents, predict_height


class Extremum:
    __slots__ = ("time", "height", "kind")

    def __init__(self, time, height, kind):
        self.time = time          # tz-aware datetime
        self.height = height      # meters
        self.kind = kind          # 'H' or 'L'


class TideSeries:
    """A sampled tide curve and its high/low extrema over a window."""

    def __init__(self, times, heights, extrema, station):
        self.times = times        # list[datetime]
        self.heights = heights    # list[float] meters
        self.extrema = extrema    # list[Extremum]
        self.station = station
        self.min = min(heights) if heights else 0.0
        self.max = max(heights) if heights else 1.0

    def height_at(self, when):
        """Interpolated height (m) at an arbitrary time inside the window."""
        if when <= self.times[0]:
            return self.heights[0]
        if when >= self.times[-1]:
            return self.heights[-1]
        # series is uniform; locate the bracketing samples
        span = (self.times[-1] - self.times[0]).total_seconds()
        frac = (when - self.times[0]).total_seconds() / span
        idx = frac * (len(self.times) - 1)
        i = int(idx)
        t = idx - i
        return self.heights[i] * (1 - t) + self.heights[i + 1] * t

    def next_high(self, after):
        for e in self.extrema:
            if e.kind == "H" and e.time >= after:
                return e
        return None


def predict_series(station, start, hours, step_minutes=3):
    """
    Build a TideSeries for `station` from `start` (tz-aware) spanning `hours`.

    A fine step (3 min) is used so extrema land on accurate minutes; the curve
    is smooth enough to plot directly.
    """
    resolved = build_constituents(station)
    mtl = station["mean_tide_level"]

    n = int(hours * 60 / step_minutes)
    times, heights = [], []
    for i in range(n + 1):
        t = start + datetime.timedelta(minutes=i * step_minutes)
        times.append(t)
        heights.append(predict_height(resolved, mtl, t))

    extrema = _find_extrema(times, heights)
    return TideSeries(times, heights, extrema, station)


def extreme_range(station, ref_dt, cache_dir=None, days=365,
                  step_minutes=30, max_age_days=30):
    """(min, max) predicted water level (m) over ~`days` from `ref_dt`.

    Used for a *fixed* vertical scale so the curve's height means the same thing
    every render. Scanning a year of predictions is slow, so the result is
    cached per station (it changes negligibly day to day).
    """
    name = station.get("name", "station")
    path = None
    if cache_dir:
        cache_dir = os.path.expanduser(cache_dir)
        safe = "".join(ch if ch.isalnum() else "_" for ch in name)
        path = os.path.join(cache_dir, f"range_{safe}.json")
        try:
            with open(path) as fh:
                d = json.load(fh)
            age = abs((ref_dt - datetime.datetime.fromisoformat(d["computed"]))
                      .days)
            if age <= max_age_days:
                return d["lo"], d["hi"]
        except (OSError, ValueError, KeyError):
            pass

    resolved = build_constituents(station)
    mtl = station["mean_tide_level"]
    lo = hi = predict_height(resolved, mtl, ref_dt)
    n = int(days * 24 * 60 / step_minutes)
    for i in range(1, n + 1):
        v = predict_height(resolved, mtl,
                           ref_dt + datetime.timedelta(minutes=i * step_minutes))
        if v < lo:
            lo = v
        elif v > hi:
            hi = v

    if path:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(path, "w") as fh:
                json.dump({"lo": lo, "hi": hi, "computed": ref_dt.isoformat()},
                          fh)
        except OSError:
            pass
    return lo, hi


def _find_extrema(times, heights):
    """Locate interior local maxima/minima with a parabolic refinement."""
    out = []
    for i in range(1, len(heights) - 1):
        a, b, c = heights[i - 1], heights[i], heights[i + 1]
        if b > a and b >= c:
            kind = "H"
        elif b < a and b <= c:
            kind = "L"
        else:
            continue
        # parabolic vertex refinement for sub-step timing/height
        denom = (a - 2 * b + c)
        offset = 0.5 * (a - c) / denom if denom != 0 else 0.0
        offset = max(-1.0, min(1.0, offset))
        dt = times[i] + (times[i + 1] - times[i]) * offset
        peak = b - 0.25 * (a - c) * offset
        out.append(Extremum(dt, peak, kind))
    return out
