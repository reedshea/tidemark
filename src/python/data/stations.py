#!/usr/bin/env python3
"""
Tide station harmonic data, loaded from JSON.

Each station lives in its own file under ``data/stations/<station_id>.json`` so
new locations are pure data — drop in a file (or let ``setup_location.py``
generate one from NOAA) and point the config at its id; no code changes.

A station record has:
    station_id       NOAA (or other) station identifier, a string
    name             human-readable station name
    mean_tide_level  meters above the chart datum (NOAA: MTL - MLLW); sets where
                     the curve's mid-line sits on the fixed vertical scale
    constituents     list of {name, amplitude (m), phase (deg, ref. GMT),
                     speed (deg/hour)} — the published harmonic constants. The
                     astronomical corrections that make them accurate live in
                     harmonics.py.
"""

import os
import json

STATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "stations")

# The station bundled with the repo so a fresh clone runs out of the box.
DEFAULT_STATION_ID = "8447368"   # Great Hill, Buzzards Bay, MA


def station_path(station_id):
    """Filesystem path to a station's JSON record."""
    return os.path.join(STATIONS_DIR, f"{station_id}.json")


def available_stations():
    """Sorted list of station ids that have a JSON record on disk."""
    if not os.path.isdir(STATIONS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(STATIONS_DIR)
                  if f.endswith(".json"))


def load_station(station_id):
    """Load a station record by id.

    Raises FileNotFoundError with a helpful hint if the station isn't present
    (e.g. the user named a station they haven't fetched yet).
    """
    path = station_path(station_id)
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        have = ", ".join(available_stations()) or "(none)"
        raise FileNotFoundError(
            f"No tide station '{station_id}' in {STATIONS_DIR}. "
            f"Available: {have}. Add one with:\n"
            f"    python3 src/python/setup_location.py {station_id}")


# Bundled default, eagerly loaded for convenience / backward compatibility.
GREAT_HILL = load_station(DEFAULT_STATION_ID)
