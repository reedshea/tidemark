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
from data.tide import predict_series
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

    frac, illum = moonmod.phase(now)
    moon_events = moonmod.rise_set(start, end, loc["latitude"],
                                   loc["longitude"], tz)
    # prefer the next upcoming rise/set pair
    upcoming = [e for e in moon_events if e[1] >= now] or moon_events
    moon = {
        "frac": frac,
        "illum": illum,
        "name": moonmod.phase_name(frac),
        "events": upcoming,
    }

    return {
        "location": loc,
        "now": now,
        "start": start,
        "end": end,
        "series": series,
        "daylight": daylight,
        "moon": moon,
        "units": config.HEIGHT_UNITS,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate the tide ribbon")
    parser.add_argument("--output", default="/tmp/tide_chart.bmp")
    parser.add_argument("--now", default=None,
                        help="ISO datetime override for testing")
    # accepted for compatibility with the C host; no longer used
    parser.add_argument("--day", action="store_true")
    parser.add_argument("--night", action="store_true")
    args = parser.parse_args()

    now = None
    if args.now:
        now = datetime.datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(config.LOCATION["timezone"]))

    ctx = build_context(now)
    img = ribbon.render(ctx)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    img.save(args.output, "BMP")
    nh = ctx["series"].next_high(ctx["now"])
    if nh:
        print(f"Next high tide: {nh.time.strftime('%a %-I:%M %p')} "
              f"({nh.height * (3.28084 if config.HEIGHT_UNITS == 'ft' else 1):.1f}"
              f"{config.HEIGHT_UNITS})")
    print(f"Tide ribbon saved to {args.output}")


if __name__ == "__main__":
    main()
