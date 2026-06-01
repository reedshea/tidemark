#!/usr/bin/env python3
"""Render the experimental tide-ribbon styles to /tmp as BMP (for the panel)
and PNG (for on-screen preview). Usage: experiment_styles.py [--now ISO]."""

import argparse
import datetime
import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import main as tm
from render import styles

STYLES = [
    ("sumi", styles.render_sumi),
    ("durer", styles.render_durer),
    ("rembrandt", styles.render_rembrandt),
]


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None)
    ap.add_argument("--outdir", default="/tmp")
    args = ap.parse_args()

    now = None
    if args.now:
        now = datetime.datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(config.LOCATION["timezone"]))

    ctx = tm.build_context(now)
    for name, fn in STYLES:
        img = fn(ctx)
        bmp = os.path.join(args.outdir, f"style_{name}.bmp")
        png = os.path.join(args.outdir, f"style_{name}.png")
        img.save(bmp, "BMP")
        img.save(png)
        print(f"wrote {bmp} / {png}")


if __name__ == "__main__":
    run()
