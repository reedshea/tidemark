#!/usr/bin/env python3
"""
Optional weather (air temperature, cloud cover, precipitation).

This is the one piece that needs the internet. It is strictly additive and
offline-safe: it fetches an hourly forecast from the US National Weather
Service (api.weather.gov — free, no API key), caches it to disk, and is used
only when a cache exists. No network or no cache simply means no weather; the
tide, sun, and moon stay fully offline.
"""

import os
import json
import datetime
import urllib.request
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
_POINTS = "https://api.weather.gov/points/{lat:.4f},{lon:.4f}"


def _parse_duration(s):
    """Parse the subset of ISO-8601 durations NWS uses, e.g. PT2H, P1DT6H."""
    days = hours = minutes = 0
    s = s[1:]  # drop leading 'P'
    if "T" in s:
        date_part, time_part = s.split("T")
    else:
        date_part, time_part = s, ""
    if date_part.endswith("D"):
        days = int(date_part[:-1])
    num = ""
    for ch in time_part:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            hours = int(num); num = ""
        elif ch == "M":
            minutes = int(num); num = ""
        elif ch == "S":
            num = ""
    return datetime.timedelta(days=days, hours=hours, minutes=minutes)


def _parse_series(values):
    """[{validTime, value}] -> [(start, end, value)] with tz-aware datetimes."""
    out = []
    for v in values:
        tstr, dur = v["validTime"].split("/")
        start = datetime.datetime.fromisoformat(tstr)
        out.append((start, start + _parse_duration(dur), v["value"]))
    return out


class Forecast:
    """Sampler over NWS gridpoint series. All times tz-aware."""

    def __init__(self, raw):
        self.fetched_at = datetime.datetime.fromisoformat(raw["fetched_at"])
        self.temp = _parse_series(raw["temperature"])
        self.sky = _parse_series(raw["skyCover"])
        self.pop = _parse_series(raw["probabilityOfPrecipitation"])
        self.wx = _parse_series(raw["weather"])
        # wind is optional / may be missing from an older cache file
        self.wind = _parse_series(raw.get("windSpeed", []))
        self.gust = _parse_series(raw.get("windGust", []))

    @staticmethod
    def _lookup(series, dt):
        for start, end, value in series:
            if start <= dt < end:
                return value
        return None

    def temp_f(self, dt):
        c = self._lookup(self.temp, dt)
        return None if c is None else c * 9 / 5 + 32

    def cloud(self, dt):
        return self._lookup(self.sky, dt)        # percent 0-100 or None

    def precip_prob(self, dt):
        return self._lookup(self.pop, dt)        # percent or None

    def precip_kind(self, dt):
        v = self._lookup(self.wx, dt)
        if not v:
            return None
        kinds = " ".join((w.get("weather") or "") for w in v)
        if "thunder" in kinds:
            return "thunder"
        if "snow" in kinds or "sleet" in kinds or "ice" in kinds:
            return "snow"
        if "rain" in kinds or "shower" in kinds or "drizzle" in kinds:
            return "rain"
        return None

    def gust_mph(self, dt):
        """Wind gust in mph (falls back to sustained wind), or None. NWS
        gridpoint wind is km/h."""
        v = self._lookup(self.gust, dt)
        if v is None:
            v = self._lookup(self.wind, dt)
        return None if v is None else v * 0.621371


def _fetch(lat, lon, contact):
    hdr = {"User-Agent": f"tidemark (contact: {contact})",
           "Accept": "application/geo+json"}

    def get(url):
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    point = get(_POINTS.format(lat=lat, lon=lon))
    grid = get(point["properties"]["forecastGridData"])["properties"]
    return {
        "fetched_at": datetime.datetime.now(UTC).isoformat(),
        "temperature": grid["temperature"]["values"],
        "skyCover": grid["skyCover"]["values"],
        "probabilityOfPrecipitation":
            grid["probabilityOfPrecipitation"]["values"],
        "weather": grid["weather"]["values"],
        "windSpeed": grid.get("windSpeed", {}).get("values", []),
        "windGust": grid.get("windGust", {}).get("values", []),
    }


def get_forecast(lat, lon, cache_dir, max_age_hours=3,
                 allow_network=True, contact="tidemark@example.com"):
    """
    Return a Forecast, or None if unavailable.

    Uses a cached forecast if it is younger than `max_age_hours`. Otherwise,
    if `allow_network`, tries to refresh; on any failure it falls back to a
    stale cache when present, and only returns None if there is nothing at all.
    """
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"weather_{lat:.4f}_{lon:.4f}.json")

    cached = None
    if os.path.exists(path):
        try:
            cached = json.load(open(path))
        except (json.JSONDecodeError, IOError):
            cached = None

    if cached:
        age = (datetime.datetime.now(UTC)
               - datetime.datetime.fromisoformat(cached["fetched_at"]))
        if age <= datetime.timedelta(hours=max_age_hours):
            return Forecast(cached)

    if allow_network:
        try:
            raw = _fetch(lat, lon, contact)
            json.dump(raw, open(path, "w"))
            return Forecast(raw)
        except Exception as e:  # network/parse failure -> degrade gracefully
            print(f"weather: refresh failed ({e}); using cache if available")

    return Forecast(cached) if cached else None
