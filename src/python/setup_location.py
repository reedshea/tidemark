#!/usr/bin/env python3
"""
Set Tidemark up for a location, the easy way.

Give it a NOAA CO-OPS station id (or a latitude/longitude to find the nearest
station) and it fetches everything the display needs from NOAA's public API:
the harmonic constituents, the coordinates and timezone, and the datums used to
place the tide curve's mid-line. It writes two files:

    data/stations/<id>.json   the harmonic record (pure data)
    location.json             the active selection config.py reads

After that, `python3 main.py --output /tmp/tide.bmp` renders your location.

    python3 setup_location.py 8447368                 # by NOAA station id
    python3 setup_location.py --near 33.34,-118.33    # nearest station
    python3 setup_location.py 9410079 --name "Avalon" --subtitle "Santa Catalina Island"

NOAA covers the US and its territories (~3,400 stations). For locations outside
that, see the "international" note in the README (the TICON-4 global dataset),
or hand-write a data/stations/<id>.json by the same schema.

Network is needed only here, at setup time; rendering stays fully offline.
"""

import argparse
import json
import math
import os
import sys
import urllib.request
import urllib.error

MDAPI = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"
_HERE = os.path.dirname(os.path.abspath(__file__))
STATIONS_DIR = os.path.join(_HERE, "data", "stations")
LOCATION_FILE = os.path.join(_HERE, "location.json")

# Standard-time UTC offset + whether DST is observed -> IANA timezone, for the
# US and its territories (NOAA's coverage). --tz overrides any of these.
_TZ_BY_OFFSET = {
    (-5, True): "America/New_York",
    (-6, True): "America/Chicago",
    (-7, True): "America/Denver",
    (-7, False): "America/Phoenix",
    (-8, True): "America/Los_Angeles",
    (-9, True): "America/Anchorage",
    (-10, True): "America/Adak",
    (-10, False): "Pacific/Honolulu",
    (-4, False): "America/Puerto_Rico",
    (-11, False): "Pacific/Pago_Pago",
    (10, False): "Pacific/Guam",
    (9, False): "Pacific/Palau",
}


def _get_json(url):
    """Fetch and parse JSON, with a clear error on failure."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "tidemark-setup (github.com/reedshea/tidemark)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"NOAA request failed ({e.code}) for {url}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach NOAA ({e.reason}). "
                         f"Setup needs internet; rendering does not.")


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def nearest_station_id(lat, lon):
    """Id of the NOAA tide-prediction station nearest to (lat, lon)."""
    data = _get_json(f"{MDAPI}/stations.json?type=tidepredictions")
    stations = data.get("stations", [])
    if not stations:
        raise SystemExit("NOAA returned no stations to search.")
    best, best_km = None, None
    for s in stations:
        try:
            km = _haversine_km(lat, lon, float(s["lat"]), float(s["lng"]))
        except (KeyError, TypeError, ValueError):
            continue
        if best_km is None or km < best_km:
            best, best_km = s, km
    print(f"Nearest station: {best['id']} {best.get('name','')} "
          f"({best_km:.1f} km away)")
    return best["id"]


def fetch_constituents(station_id):
    """List of {name, amplitude, phase, speed} from NOAA (meters, GMT phase)."""
    data = _get_json(f"{MDAPI}/stations/{station_id}/harcon.json?units=metric")
    rows = data.get("HarmonicConstituents", [])
    out = []
    for c in rows:
        name = (c.get("name") or "").strip().upper()
        if not name:
            continue
        out.append({
            "name": name,
            "amplitude": round(float(c["amplitude"]), 4),
            "phase": round(float(c["phase_GMT"]), 1),
            "speed": float(c["speed"]),
        })
    if not out or all(c["amplitude"] == 0.0 for c in out):
        raise SystemExit(
            f"Station {station_id} has no harmonic constituents (it may be a "
            f"subordinate station that only stores offsets). Pick a reference "
            f"station near it instead.")
    return out


def fetch_metadata(station_id):
    """(name, lat, lon, iana_tz_or_None) for a station."""
    data = _get_json(f"{MDAPI}/stations/{station_id}.json")
    s = data["stations"][0]
    corr = int(s.get("timezonecorr", 0))
    dst = bool(s.get("observedst", False))
    tz = _TZ_BY_OFFSET.get((corr, dst))
    return s.get("name", station_id), float(s["lat"]), float(s["lng"]), tz


def fetch_mean_tide_level(station_id):
    """Mean tide level above chart datum (MTL - MLLW), meters. 0.0 if absent."""
    data = _get_json(f"{MDAPI}/stations/{station_id}/datums.json?units=metric")
    vals = {d.get("name"): d.get("value") for d in data.get("datums", [])}
    try:
        return round(float(vals["MTL"]) - float(vals["MLLW"]), 3)
    except (KeyError, TypeError, ValueError):
        print("  (no MTL/MLLW datums; defaulting mean_tide_level to 0.0)")
        return 0.0


def write_station(station_id, name, mtl, constituents):
    os.makedirs(STATIONS_DIR, exist_ok=True)
    path = os.path.join(STATIONS_DIR, f"{station_id}.json")
    record = {
        "station_id": station_id,
        "name": name,
        "mean_tide_level": mtl,
        "constituents": constituents,
    }
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    return path


def write_location(loc):
    with open(LOCATION_FILE, "w") as fh:
        json.dump(loc, fh, indent=2)
        fh.write("\n")
    return LOCATION_FILE


def main():
    ap = argparse.ArgumentParser(
        description="Fetch a NOAA tide station and set it as the active location.")
    ap.add_argument("station_id", nargs="?",
                    help="NOAA CO-OPS station id, e.g. 8447368")
    ap.add_argument("--near", metavar="LAT,LON",
                    help="find the nearest station to these coordinates")
    ap.add_argument("--name", help="override the display name")
    ap.add_argument("--subtitle", default="", help="a subtitle line (e.g. region)")
    ap.add_argument("--units", choices=["ft", "m"], default="ft",
                    help="display units (default: ft)")
    ap.add_argument("--tz", help="IANA timezone (e.g. America/New_York); "
                    "overrides the one inferred from NOAA")
    ap.add_argument("--no-activate", action="store_true",
                    help="write the station file but don't change location.json")
    args = ap.parse_args()

    if not args.station_id and not args.near:
        ap.error("give a station id or --near LAT,LON")

    station_id = args.station_id
    if args.near:
        try:
            lat, lon = (float(x) for x in args.near.split(","))
        except ValueError:
            ap.error("--near must look like 37.81,-122.47")
        station_id = nearest_station_id(lat, lon)

    print(f"Fetching station {station_id} from NOAA...")
    name, lat, lon, tz = fetch_metadata(station_id)
    constituents = fetch_constituents(station_id)
    mtl = fetch_mean_tide_level(station_id)

    path = write_station(station_id, name, mtl, constituents)
    print(f"Wrote {len(constituents)} constituents to {path}")

    if args.tz:
        tz = args.tz
    if not tz:
        raise SystemExit(
            f"Could not infer the timezone for station {station_id}. "
            f"Re-run with --tz, e.g. --tz America/New_York")

    if args.no_activate:
        print("Station saved. Not activated (--no-activate).")
        return

    loc = {
        "name": args.name or name,
        "subtitle": args.subtitle,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "timezone": tz,
        "station_id": station_id,
        "units": args.units,
    }
    write_location(loc)
    print(f"Active location set to {loc['name']} ({tz}).")
    print("Render it with:  python3 main.py --output /tmp/tide.bmp")


if __name__ == "__main__":
    main()
