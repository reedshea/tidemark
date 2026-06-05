# Tidemark

A clean, offline tide display for e-ink. Tidemark answers one question at a
glance — *when is high tide, and is it during daylight?* — so you can plan the
swim off the dock without checking a tide app.

It runs on a Raspberry Pi driving a Waveshare 7.8" IT8951 e-ink panel, needs no
internet, and is styled in the spirit of Edward Tufte: one black tide line, a
slim day/night band, directly-labeled highs and lows, and a true-phase moon.

![A Tidemark render](docs/sample.png)

## How it works

A small C host runs the display loop and pushes a bitmap to the panel (or to an
SDL simulator on macOS). A Python program generates that bitmap:

```
src/python/
  setup_location.py    One-command location setup (fetches a NOAA station)
  config.py            Static knobs (window, units, weather); reads location.json
  location.json        Active location (written by setup_location.py; optional)
  data/
    harmonics.py       Harmonic tide engine with full astronomical corrections
    stations.py        Loads station records from data/stations/*.json
    stations/          One JSON file per tide station (pure data)
    tide.py            Tide curve + high/low extrema over a time window
    sun.py             Sunrise/sunset/twilight (NOAA solar algorithm)
    moon.py            Moon phase + rise/set + altitude arc
    weather.py         Optional NWS forecast (temp/cloud/precip), offline-safe
  render/
    theme.py           Palette, fonts, geometry (e-ink friendly)
    ribbon.py          The Tufte-style tide ribbon
  main.py              Assembles data + renders the BMP
src/c/                 Display host (main loop, refresh strategy, driver layer)
sim/                   SDL2 simulator for desktop iteration
lib/IT8951/            Waveshare driver (vendored)
tests/                 unittest suite (tide math, astronomy, render smoke test)
```

### Accurate tides, fully offline

Tide height is predicted from NOAA harmonic constituents. The naïve model
`height = MSL + Σ A·cos(speed·t + phase)` is wrong by *hours* because it omits
the equilibrium argument (V₀+u) and nodal factor (f) that real harmonic
prediction needs. `harmonics.py` computes those from the astronomical mean
longitudes, so predictions are accurate with no network connection.

Validated against NOAA station 8447368 (Great Hill):

| metric | result |
|---|---|
| high-tide timing | ~3 min mean error (max 11 min) |
| low-tide timing | flat troughs; heights within ~0.1 m |
| full-curve RMS | ~0.17 m over a ~1.2 m range |
| timing bias | ~0 |

Sun and moon are likewise computed (no hardcoded tables): day length, moon
phase, and moonrise/moonset are correct for any date and location.

## Design

Built for e-ink, where large mid-gray fills and fine texture cause ghosting and
banding. So: white ground, a single black data line, a tiny restrained set of
grays, direct labels, no boxes or heavy gridlines. The chart is rendered at 2×
and downsampled for smooth anti-aliased lines. Daylight high tides sit on white;
night ones sit on a faint gray wash — the swim answer, read at a glance.

The canvas is split into a **sky panel** and a **sea panel** by a horizon line.
The moon traces its real altitude arc across the sky — rising, transiting, and
setting at the correct times and the correct height (a near-solstice full moon
rides low; a winter moon climbs high) — with the phase glyph at its high point.

### Optional weather (the only online piece)

When enabled (`config.WEATHER_ENABLED`), the sky panel also shows an air-
temperature line and a cloud-cover strip (with precip hatching) from the US
National Weather Service. It is strictly additive and offline-safe: the
forecast is cached to disk, refreshed only when stale, and simply omitted when
there is no cache and no network. Tide, sun, and moon never touch the internet.

## Build & run

```bash
# macOS simulator
cd build && make clean && PLATFORM=macos make && ./tidemark_sim

# Raspberry Pi
cd build && make clean && make && sudo ./tidemark

# Generate just the image (any platform with Python 3.9+ and Pillow)
python3 src/python/main.py --output /tmp/tide.bmp
python3 src/python/main.py --now 2026-05-30T14:23 --output /tmp/tide.bmp   # test a time
```

The only Python dependency is **Pillow**. (`make venv` sets up a virtualenv.)

Run the tests with `python3 -m unittest discover -s tests`.

## Configuring a location

Point Tidemark at a NOAA tide station and it fetches everything it needs —
harmonic constituents, coordinates, timezone, and datums — in one command:

```bash
python3 src/python/setup_location.py 8447368            # by NOAA station id
python3 src/python/setup_location.py --near 37.81,-122.47   # nearest station
python3 src/python/setup_location.py 9414290 --units m --name "San Francisco"
```

Find your station id at <https://tidesandcurrents.noaa.gov> (search your area,
then read the 7-digit id from the station page). Setup writes two files:
`data/stations/<id>.json` (the harmonic record) and `location.json` (the active
selection that `config.py` reads). Network is needed only here, at setup;
rendering stays fully offline. Window length, units, and the optional weather
panel are static knobs in `config.py`.

**Outside the US?** NOAA covers the US and its territories. For other coasts,
hand-write a `data/stations/<id>.json` by the same schema using published
harmonic constants — for example the global **TICON-4** dataset (4,383 tide
gauges, CC-BY): <https://doi.org/10.17882/109129>. Then set `station_id` in
`location.json` and fill in your latitude/longitude/timezone.

## Deploy to a Raspberry Pi

```bash
export TIDEMARK_PI=pi@raspberrypi.local     # your Pi's user@host
./deploy.sh                                 # sync, build, install the timer
```

`deploy.sh` syncs the repo, builds on the Pi, installs a systemd timer that
refreshes the panel every 5 minutes, and leaves it on a clean full repaint. The
Pi needs the **bcm2835** library installed (the IT8951 driver links against it);
build it once from <https://www.airspayce.com/mikem/bcm2835/>.

## Troubleshooting

- **`Failed to initialize display` / GPIO errors on the Pi** — the IT8951 driver
  needs root for SPI/GPIO; run via the systemd service (or `sudo`).
- **Garbled or sliver display after deploy** — `deploy.sh` forces a clean
  full-clear baseline; if you ran `./tidemark` manually while the timer was
  live, two processes hit the SPI bus. Stop the timer first (`deploy.sh` does).
- **`tide renderer not found`** — set `TIDEMARK_HOME` to the project root, or
  launch from it (the binary also accepts being run from `build/`).
- **Plain/fallback fonts** — the bundled ET Book lives in `assets/fonts/`; if
  text looks wrong, confirm that directory shipped with the deploy.
