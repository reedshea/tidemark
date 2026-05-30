#!/usr/bin/env python3
"""
Tidemark configuration.

Everything location-specific lives here so the display is modular: point it at
a different NOAA harmonic station (and its coordinates) and the tide curve,
daylight band, and moon all follow. No internet is required at runtime.
"""

from data.stations import GREAT_HILL

# ---- Active location -------------------------------------------------------
LOCATION = {
    "name": "Great Hill",
    "subtitle": "Buzzards Bay, MA",
    "latitude": 41.7138,      # NOAA station 8447368
    "longitude": -70.7506,
    "timezone": "America/New_York",
    "station": GREAT_HILL,    # harmonic constituents
}

# ---- Display window --------------------------------------------------------
# How many hours of tide to show, and how much of that is "already past" so the
# current moment sits a little in from the left edge (context, not a cliff).
WINDOW_HOURS = 36
WINDOW_LOOKBACK_HOURS = 3

# Units: heights are metric (m) from the harmonic data. Set to "ft" to display
# in feet (1 m = 3.28084 ft).
HEIGHT_UNITS = "ft"
