#!/usr/bin/env python3
"""
Render the ribbon with SYNTHETIC weather so the sky graphics can be developed
without hitting the network. Injects a fake forecast (a clear -> cloudy ->
overcast+rain -> clearing -> snow arc) into the render context.

    python3 tools/weather_preview.py --style clouds --out /tmp/wx.bmp
    python3 tools/weather_preview.py --style bank   --out /tmp/wx_bank.bmp

Pillow-only; imports the renderer directly.
"""

import argparse
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

import main as tide_main          # noqa: E402
from render import ribbon         # noqa: E402


class FakeForecast:
    """Hour-indexed synthetic forecast over the render window."""

    def __init__(self, start):
        self.start = start

    def _h(self, dt):
        return (dt - self.start).total_seconds() / 3600.0

    def cloud(self, dt):
        # smooth arc 0->100 and back, with a clear gap, then a snowy bank
        h = self._h(dt)
        v = 50 + 50 * math.sin((h - 9) / 24 * 2 * math.pi)
        if 4 <= h <= 7:
            v = 10                     # a clear afternoon window
        if 10 <= h <= 16:
            v = 12                     # a clear night (-> constellation)
        return max(0, min(100, v))

    def precip_prob(self, dt):
        h = self._h(dt)
        if 13 <= h <= 19:
            return 80                  # midday rain
        if 30 <= h <= 35:
            return 70                  # snow next day
        return 5

    def precip_kind(self, dt):
        h = self._h(dt)
        if 13 <= h <= 19:
            return "rain"
        if 30 <= h <= 35:
            return "snow"
        return None

    def temp_f(self, dt):
        h = self._h(dt)
        return 52 + 14 * math.sin((h - 15) / 24 * 2 * math.pi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default="2026-06-08T15:00:00")
    ap.add_argument("--out", default="/tmp/wx.bmp")
    args = ap.parse_args()

    now = datetime.datetime.fromisoformat(args.now)
    ctx = tide_main.build_context(now)
    ctx["weather"] = FakeForecast(ctx["start"])

    img, _ = ribbon.render(ctx)
    img.save(args.out, "BMP")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
