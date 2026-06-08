#!/usr/bin/env python3
"""
OFFLINE tool: download the IBM Carbon weather pictograms (Apache-2.0) and
rasterize them to PNG assets the renderer loads at runtime (Pillow-only on the
Pi can't render SVG, so we pre-rasterize here and commit the PNGs).

Needs network + `rsvg-convert` (librsvg). Re-run only to refresh the assets.

    python3 tools/fetch_carbon_weather.py [--size 256]

Source: https://github.com/carbon-design-system/carbon/tree/main/packages/pictograms
License: Apache-2.0 (see assets/weather/NOTICE).
"""

import argparse
import os
import subprocess
import urllib.request

CDN = "https://cdn.jsdelivr.net/npm/@carbon/pictograms/svg/{}.svg"

# our-semantic-name -> Carbon pictogram name
GLYPHS = {
    "sunny": "sunny",
    "constellation": "constellation",   # clear night
    "partly": "cloudy--partial",
    "cloudy": "cloudy",
    "overcast": "overcast",
    "rain": "rainy",
    "rain_heavy": "rainy--heavy",
    "snow": "snow",
    "hail": "hail",
    "windy": "windy",
    "lightning": "lightning",
}

NOTICE = """IBM Carbon Design System — Pictograms
Copyright IBM Corp.
Licensed under the Apache License, Version 2.0.
https://github.com/carbon-design-system/carbon  (packages/pictograms)

The PNGs in this directory are rasterized from the Carbon pictogram SVGs by
tools/fetch_carbon_weather.py for offline (Pillow-only) use on the device.
"""


def main():
    ap = argparse.ArgumentParser()
    # Rasterize large (masters are ~4x the largest on-screen device size of
    # WX_GLYPH_SIZE*SS), so the runtime only ever downscales — never upscales,
    # which would soften the linework.
    ap.add_argument("--size", type=int, default=1024)
    args = ap.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "assets", "weather"))
    svg_dir = os.path.join(root, "svg")
    os.makedirs(svg_dir, exist_ok=True)

    for name, carbon in GLYPHS.items():
        svg_path = os.path.join(svg_dir, f"{carbon}.svg")
        urllib.request.urlretrieve(CDN.format(carbon), svg_path)
        png_path = os.path.join(root, f"{name}.png")
        subprocess.run(
            ["rsvg-convert", "-w", str(args.size), "-h", str(args.size),
             svg_path, "-o", png_path], check=True)
        print(f"{name:10s} <- {carbon:16s} -> {os.path.relpath(png_path)}")

    with open(os.path.join(root, "NOTICE"), "w") as f:
        f.write(NOTICE)
    print(f"\nWrote {len(GLYPHS)} PNGs + NOTICE to {os.path.relpath(root)}")


if __name__ == "__main__":
    main()
