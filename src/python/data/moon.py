#!/usr/bin/env python3
"""
Lunar phase and rise/set, computed astronomically (offline).

Uses a compact low-precision lunar theory (good to a few arc-minutes), which is
ample for phase illustration and rise/set times accurate to a few minutes.
"""

import math
import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
D2R = math.pi / 180.0
R2D = 180.0 / math.pi
OBLIQ = 23.4393 * D2R

# Standard altitude of the Moon's center at rise/set (refraction - parallax).
MOON_H0 = 0.125


def _days_since_j2000(dt):
    dt = dt.astimezone(UTC)
    jd = (dt - datetime.datetime(2000, 1, 1, 12, tzinfo=UTC)).total_seconds() \
        / 86400.0
    return jd


def _sun_longitude(d):
    """Apparent ecliptic longitude of the Sun (deg)."""
    M = (357.529 + 0.98560028 * d) % 360.0
    L = (280.459 + 0.98564736 * d) % 360.0
    lam = (L + 1.915 * math.sin(M * D2R) + 0.020 * math.sin(2 * M * D2R))
    return lam % 360.0


def _moon_ecliptic(d):
    """Geocentric ecliptic longitude & latitude of the Moon (deg)."""
    L = (218.316 + 13.176396 * d) % 360.0
    M = (134.963 + 13.064993 * d) % 360.0
    F = (93.272 + 13.229350 * d) % 360.0
    Mr, Fr = M * D2R, F * D2R
    lon = L + 6.289 * math.sin(Mr)
    lat = 5.128 * math.sin(Fr)
    return lon % 360.0, lat


def phase(dt):
    """
    Moon phase as a fraction 0..1 (0 = new, 0.25 first quarter, 0.5 full,
    0.75 last quarter) plus illuminated fraction 0..1.
    """
    d = _days_since_j2000(dt)
    moon_lon, _ = _moon_ecliptic(d)
    sun_lon = _sun_longitude(d)
    elong = (moon_lon - sun_lon) % 360.0
    illum = (1 - math.cos(elong * D2R)) / 2.0
    return elong / 360.0, illum


def _equatorial(d):
    lon, lat = _moon_ecliptic(d)
    lon_r, lat_r = lon * D2R, lat * D2R
    sin_dec = (math.sin(lat_r) * math.cos(OBLIQ)
               + math.cos(lat_r) * math.sin(OBLIQ) * math.sin(lon_r))
    dec = math.asin(sin_dec)
    y = (math.sin(lon_r) * math.cos(OBLIQ)
         - math.tan(lat_r) * math.sin(OBLIQ))
    x = math.cos(lon_r)
    ra = math.atan2(y, x)
    return ra * R2D, dec * R2D


def _altitude(dt, lat, lon):
    """Moon altitude (deg) at a given instant and location."""
    d = _days_since_j2000(dt)
    ra, dec = _equatorial(d)
    jd = d + 2451545.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0
    lst = (gmst + lon) % 360.0
    ha = (lst - ra) % 360.0
    ha_r = ha * D2R
    lat_r, dec_r = lat * D2R, dec * D2R
    alt = math.asin(math.sin(lat_r) * math.sin(dec_r)
                    + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
    return alt * R2D


def altitude(dt, lat, lon):
    """Public alias: Moon altitude (deg) above the horizon."""
    return _altitude(dt, lat, lon)


def altitude_track(start, end, lat, lon, step_minutes=6):
    """Sampled (datetime, altitude_deg) over [start, end] for plotting the
    moon's arc across the sky."""
    track = []
    t = start
    step = datetime.timedelta(minutes=step_minutes)
    while t <= end:
        track.append((t, _altitude(t, lat, lon)))
        t += step
    return track


def rise_set(start, end, lat, lon, tz):
    """
    Moonrise and moonset events (tz-aware) in [start, end].

    Returns list of (kind, datetime) with kind in {"moonrise", "moonset"},
    found by scanning altitude crossings of MOON_H0 and refining by bisection.
    """
    events = []
    step = datetime.timedelta(minutes=10)
    t = start
    prev_alt = _altitude(t, lat, lon) - MOON_H0
    while t < end:
        nt = t + step
        alt = _altitude(nt, lat, lon) - MOON_H0
        if prev_alt == 0:
            prev_alt = 1e-9
        if prev_alt < 0 <= alt or prev_alt > 0 >= alt:
            kind = "moonrise" if alt > prev_alt else "moonset"
            lo, hi = t, nt
            for _ in range(20):
                mid = lo + (hi - lo) / 2
                am = _altitude(mid, lat, lon) - MOON_H0
                if (am < 0) == (prev_alt < 0):
                    lo = mid
                else:
                    hi = mid
            events.append((kind, (lo + (hi - lo) / 2).astimezone(tz)))
        prev_alt = alt
        t = nt
    return events


_PHASE_NAMES = [
    (0.033, "New Moon"), (0.217, "Waxing Crescent"), (0.283, "First Quarter"),
    (0.467, "Waxing Gibbous"), (0.533, "Full Moon"), (0.717, "Waning Gibbous"),
    (0.783, "Last Quarter"), (0.967, "Waning Crescent"), (1.001, "New Moon"),
]


def phase_name(frac):
    for upper, name in _PHASE_NAMES:
        if frac < upper:
            return name
    return "New Moon"
