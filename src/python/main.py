#!/usr/bin/env python3
"""
Tidemark — generate the e-ink tide ribbon as a BMP.

Pulls together the offline data layer (tide / sun / moon) and the ribbon
renderer, writing an 8-bit grayscale BMP sized for the IT8951 panel. The C
host loads that BMP and pushes it to the display (or the SDL simulator).
"""

import argparse
import datetime
import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data.tide import predict_series, extreme_range
from data.sun import daylight_intervals
from data import moon as moonmod
from render import ribbon


def build_context(now=None):
    loc = config.LOCATION
    tz = ZoneInfo(loc["timezone"])
    now = now or datetime.datetime.now(tz)
    now = now.astimezone(tz)

    start = (now.replace(minute=0, second=0, microsecond=0)
             - datetime.timedelta(hours=config.WINDOW_LOOKBACK_HOURS))
    end = start + datetime.timedelta(hours=config.WINDOW_HOURS)

    series = predict_series(loc["station"], start, config.WINDOW_HOURS)
    daylight = daylight_intervals(start, end, loc["latitude"],
                                  loc["longitude"], tz)

    # Fixed vertical scale: the station's annual extremes (cached), centered on
    # mean tide level so the middle line sits halfway between highs and lows.
    cache_dir = os.path.expanduser("~/.tidemark")
    ext_lo, ext_hi = extreme_range(loc["station"], now, cache_dir=cache_dir)
    scale = {"lo": ext_lo, "hi": ext_hi, "mid": loc["station"]["mean_tide_level"]}

    frac, illum = moonmod.phase(now)
    moon_events = moonmod.rise_set(start, end, loc["latitude"],
                                   loc["longitude"], tz)
    moon_track = moonmod.altitude_track(start, end, loc["latitude"],
                                        loc["longitude"])
    moon = {
        "frac": frac,
        "illum": illum,
        "name": moonmod.phase_name(frac),
        "events": moon_events,   # all rise/set within the window
        "track": moon_track,     # (datetime, altitude_deg) for the sky arc
    }

    weather = None
    if config.WEATHER_ENABLED:
        from data import weather as wx
        cache_dir = os.path.expanduser("~/.tidemark")
        weather = wx.get_forecast(
            loc["latitude"], loc["longitude"], cache_dir,
            max_age_hours=config.WEATHER_MAX_AGE_HOURS,
            allow_network=config.WEATHER_ALLOW_NETWORK,
            contact=config.WEATHER_CONTACT)

    return {
        "location": loc,
        "now": now,
        "start": start,
        "end": end,
        "series": series,
        "scale": scale,
        "daylight": daylight,
        "moon": moon,
        "weather": weather,
        "units": config.HEIGHT_UNITS,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate the tide ribbon")
    parser.add_argument("--output", default="/tmp/tide_chart.bmp")
    parser.add_argument("--now", default=None,
                        help="ISO datetime override for testing")
    args = parser.parse_args()

    now = None
    if args.now:
        now = datetime.datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(config.LOCATION["timezone"]))

    ctx = build_context(now)
    img, rect = ribbon.render(ctx)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    img.save(args.output, "BMP")

    # Sidecar the C host reads to choose its e-ink refresh strategy:
    #   line 1: the window's start as an integer epoch — a "which hour" token.
    #           When it changes (the hour rolled over) the host does a full
    #           crisp GC16 repaint; otherwise only the now-marker moved.
    #   line 2: "x y w h" of the marker strip to refresh on a partial update.
    base, _ = os.path.splitext(os.path.abspath(args.output))
    with open(base + ".meta", "w") as f:
        f.write(f"{int(ctx['start'].timestamp())}\n")
        f.write("{} {} {} {}\n".format(*rect))
    nh = ctx["series"].next_high(ctx["now"])
    if nh:
        print(f"Next high tide: {nh.time.strftime('%a %-I:%M %p')} "
              f"({nh.height * (3.28084 if config.HEIGHT_UNITS == 'ft' else 1):.1f}"
              f"{config.HEIGHT_UNITS})")
    print(f"Tide ribbon saved to {args.output}")


if __name__ == "__main__":
    main()
