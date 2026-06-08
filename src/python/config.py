#!/usr/bin/env python3
"""
Tidemark configuration.

The location-specific bits live in ``location.json`` (next to this file), so you
never have to edit code to point the display somewhere new — run
``setup_location.py`` and it writes that file for you. If it's missing, we fall
back to the bundled default station so a fresh clone still runs. No internet is
required at runtime.
"""

import os
import json

from data.stations import load_station, DEFAULT_STATION_ID

# ---- Active location -------------------------------------------------------
# Defaults (used when location.json is absent). setup_location.py overwrites
# location.json with the chosen station's name/coordinates/timezone.
_DEFAULT_LOCATION = {
    "name": "Great Hill",
    "subtitle": "Buzzards Bay, MA",
    "latitude": 41.7138,      # NOAA station 8447368
    "longitude": -70.7506,
    "timezone": "America/New_York",
    "station_id": DEFAULT_STATION_ID,
    "units": "ft",            # display units: "ft" or "m"
}

_LOCATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "location.json")


def _load_location():
    """Merge location.json (if present) over the bundled defaults."""
    loc = dict(_DEFAULT_LOCATION)
    try:
        with open(_LOCATION_FILE) as fh:
            loc.update(json.load(fh))
    except FileNotFoundError:
        pass
    return loc


_loc = _load_location()

LOCATION = {
    "name": _loc["name"],
    "subtitle": _loc.get("subtitle", ""),
    "latitude": _loc["latitude"],
    "longitude": _loc["longitude"],
    "timezone": _loc["timezone"],
    "station": load_station(_loc["station_id"]),   # harmonic constituents
}

# ---- Display window --------------------------------------------------------
# How many hours of tide to show, and how much of that is "already past" so the
# current moment sits a little in from the left edge (context, not a cliff).
WINDOW_HOURS = 36
WINDOW_LOOKBACK_HOURS = 3

# Units: heights are metric (m) from the harmonic data. Set to "ft" to display
# in feet (1 m = 3.28084 ft). Driven by location.json when present.
HEIGHT_UNITS = _loc.get("units", "ft")

# ---- Weather (optional, needs internet; offline-safe) ----------------------
# Adds the Carbon weather pictogram row (cloud cover / precip / clear) from the
# US National Weather Service. Strictly additive: with no cache and no network,
# the display simply omits weather and everything else still works offline.
WEATHER_ENABLED = True            # Carbon weather pictograms in the sky row
WEATHER_ALLOW_NETWORK = True      # refresh from NWS when the cache is stale
WEATHER_MAX_AGE_HOURS = 3         # treat a cached forecast as fresh this long
WEATHER_CONTACT = "reed@reedshea.com"   # NWS asks for a contact in the request
