#!/usr/bin/env python3
"""
Solar events (sunrise, sunset, civil twilight) computed astronomically.

Implements the NOAA / Meeus solar-position algorithm so the daylight band is
correct for any date and location, fully offline. Accurate to about a minute.
"""

import math
import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
D2R = math.pi / 180.0
R2D = 180.0 / math.pi

# Sun-center altitudes (degrees) marking each event.
ALTITUDES = {
    "sunrise": -0.833,        # upper limb at horizon incl. refraction
    "sunset": -0.833,
    "civil_dawn": -6.0,
    "civil_dusk": -6.0,
}


def _julian_day(date):
    """Julian day number at 00:00 UTC of a calendar date."""
    y, m, d = date.year, date.month, date.day
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716))
            + math.floor(30.6001 * (m + 1)) + d + b - 1524.5)


def _solar_params(jd):
    """Solar declination (deg) and equation of time (minutes) for a Julian day."""
    t = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0
    M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    Mr = M * D2R
    C = ((1.914602 - t * (0.004817 + 0.000014 * t)) * math.sin(Mr)
         + (0.019993 - 0.000101 * t) * math.sin(2 * Mr)
         + 0.000289 * math.sin(3 * Mr))
    true_long = L0 + C
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(omega * D2R)
    obliq = (23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813)))
                     / 60.0) / 60.0)
    obliq_corr = obliq + 0.00256 * math.cos(omega * D2R)
    decl = math.asin(math.sin(obliq_corr * D2R) * math.sin(app_long * D2R)) * R2D

    y = math.tan(obliq_corr / 2 * D2R) ** 2
    L0r = L0 * D2R
    eot = R2D * (y * math.sin(2 * L0r)
                 - 2 * e * math.sin(Mr)
                 + 4 * e * y * math.sin(Mr) * math.cos(2 * L0r)
                 - 0.5 * y * y * math.sin(4 * L0r)
                 - 1.25 * e * e * math.sin(2 * Mr)) * 4.0  # minutes
    return decl, eot


def _event_times(date, lat, lon, altitude):
    """(morning, evening) UTC datetimes for the sun crossing `altitude`.

    Returns (None, None) if the event does not occur (polar day/night).
    """
    jd = _julian_day(date) + 0.5  # local-noon-ish reference
    decl, eot = _solar_params(jd)
    lat_r = lat * D2R
    decl_r = decl * D2R
    cos_ha = ((math.sin(altitude * D2R) - math.sin(lat_r) * math.sin(decl_r))
              / (math.cos(lat_r) * math.cos(decl_r)))
    if cos_ha > 1 or cos_ha < -1:
        return None, None
    ha = math.acos(cos_ha) * R2D  # degrees

    def to_dt(minutes_utc):
        base = datetime.datetime(date.year, date.month, date.day, tzinfo=UTC)
        return base + datetime.timedelta(minutes=minutes_utc)

    morning = 720.0 - 4.0 * (lon + ha) - eot
    evening = 720.0 - 4.0 * (lon - ha) - eot
    return to_dt(morning), to_dt(evening)


def sun_events(date, lat, lon, tz):
    """
    Dict of solar events for a local calendar `date` as tz-aware datetimes.
    Keys: civil_dawn, sunrise, sunset, civil_dusk. Missing events are None.
    """
    out = {}
    sr, ss = _event_times(date, lat, lon, ALTITUDES["sunrise"])
    cd, du = _event_times(date, lat, lon, ALTITUDES["civil_dawn"])
    pairs = {"sunrise": sr, "sunset": ss, "civil_dawn": cd, "civil_dusk": du}
    for k, v in pairs.items():
        out[k] = v.astimezone(tz) if v else None
    return out


def daylight_intervals(start, end, lat, lon, tz):
    """
    List of (sunrise, sunset) tz-aware intervals overlapping [start, end].
    Used to shade the daylight band along the time axis.
    """
    intervals = []
    day = start.astimezone(tz).date() - datetime.timedelta(days=1)
    last = end.astimezone(tz).date() + datetime.timedelta(days=1)
    while day <= last:
        ev = sun_events(day, lat, lon, tz)
        if ev["sunrise"] and ev["sunset"]:
            intervals.append((ev["sunrise"], ev["sunset"]))
        day += datetime.timedelta(days=1)
    return intervals
