# AGENTS.md

Orientation for an agent (or a new contributor) working on Tidemark. For the
product overview and setup, read `README.md` first; this file documents the
internal contracts so you can change one part without breaking another.

## What it is

A two-process tide display. A **Python renderer** turns tide/sun/moon math into
an 8-bit grayscale BMP; a small **C host** loads that BMP and pushes it to an
e-ink panel (or an SDL simulator). They are decoupled by files, so you can work
on either side in isolation.

## Project map

```
src/python/   renderer + math (Pillow is the only third-party dep)
  main.py             entry point: build_context() -> ribbon.render() -> BMP + .meta
  config.py           static knobs; loads location.json over a bundled default
  location.json       active location (written by setup_location.py; gitignored)
  setup_location.py   fetch a NOAA station -> data/stations/<id>.json + location.json
  data/               harmonics, tide, sun, moon, weather, station loader
  data/stations/      one JSON record per station (pure data)
  render/             theme (palette/fonts/geometry) + ribbon (the chart)
src/c/        display host
  main.c              CLI + refresh loop; one-shot on the Pi, looping in the sim
  display/display_layer.{h,c}   DisplayInterface + dispatch
  display/display_bitmap.c      refresh strategy + runs the renderer (vendor-neutral)
  display/display_eink.c        IT8951 driver (DisplayInterface impl)
sim/display_sdl.c     SDL simulator (DisplayInterface impl)
lib/IT8951/           vendored Waveshare driver — external; do not refactor
tests/                unittest suite
deploy/               systemd .service (templated) + .timer
```

## Contract: Python renderer ↔ C host

The host runs `python3 src/python/main.py --output /tmp/tide_chart.bmp`, then
reads two files:

- **`<output>.bmp`** — 8-bit grayscale (PIL mode `L`), exactly `1872×1404`
  (`render/theme.py` `WIDTH`/`HEIGHT`), 0 = black, 255 = white.
- **`<output>.meta`** — two lines:
  - line 1: integer epoch of the window start — a "which clock hour" token.
  - line 2: `x y w h` of the now-marker strip (the only thing that moves within
    an hour).

The host (`display_bitmap.c`) compares the token against `/run/tidemark.state`:
same hour → `REFRESH_PARTIAL` of the strip; new hour (or no meta) → `REFRESH_FULL`;
3am or `TIDEMARK_FULL_CLEAR` set → `REFRESH_FULL_DEEP`. The binary locates the
project via `$TIDEMARK_HOME` (then `$PWD`, stripping a trailing `/build`).

If you change the BMP size, the `.meta` format, or the output path, update both
sides.

## How to add a tide station

US/territories: `python3 src/python/setup_location.py <noaa-station-id>` (or
`--near LAT,LON`). It writes `data/stations/<id>.json` and points
`location.json` at it. Elsewhere: hand-write `data/stations/<id>.json` with the
same schema — `station_id`, `name`, `mean_tide_level` (m above chart datum),
and `constituents` `[{name, amplitude (m), phase (deg, ref. GMT), speed (deg/h)}]`
— then set `station_id` (and lat/long/timezone) in `location.json`. The engine
in `data/harmonics.py` applies the astronomical corrections; unknown constituent
names fall back to speed-only and are harmless.

## How to add a display driver/vendor

Implement one `DisplayInterface` (`src/c/display/display_layer.h`):
`init/cleanup/update/draw_text/get_framebuffer/present`. `present(path, mode,
rx,ry,rw,rh)` loads the BMP and shows it; honor `RefreshMode` if your panel
ghosts, or ignore it (like the SDL backend) if it doesn't. Then add your `.c`
to the Makefile's platform branch and reference your interface in
`display_layer.c`. Nothing else changes — the refresh strategy and renderer
invocation are vendor-neutral. Leave `lib/IT8951/` untouched (it's vendored).

## Conventions & gotchas

- All datetimes are timezone-aware; the harmonic engine converts to UTC.
- Heights are meters internally; display converts to ft when `units == "ft"`.
- `ribbon.render` seeds `random` from the window start so texture is stable
  within an hour (needed for clean partial refreshes) and reproducible in tests.
- The IT8951 SPI bus is single-writer: never run `./tidemark` while the timer is
  live (`deploy.sh` stops it first).
- Build the simulator anywhere with `PLATFORM=macos make` (SDL2 via pkg-config);
  the real Pi build needs the bcm2835 library.

## Verify your changes

```bash
python3 -m unittest discover -s tests           # math + render smoke test
python3 src/python/main.py --now 2026-05-30T14:23 --output /tmp/t.bmp
cd build && make clean && PLATFORM=macos make    # simulator compiles
```
