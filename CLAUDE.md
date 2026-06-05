# Tidemark Development Guide

## Build & Run Commands
- Simulator (macOS or Linux+SDL2): `cd build && make clean && PLATFORM=macos make && ./tidemark_sim`
- Raspberry Pi: `cd build && make clean && make && sudo ./tidemark`
- Generate just the image: `python3 src/python/main.py --output /tmp/tide.bmp` (add `--now ISO` to test a time)
- Set up a location: `python3 src/python/setup_location.py <noaa-station-id>`
- Run tests: `python3 -m unittest discover -s tests`
- Deploy to Pi: `TIDEMARK_PI=user@host ./deploy.sh`

## Code Style Guidelines
- **Indentation**: 4 spaces (not tabs)
- **Naming**: snake_case for functions and variables
- **Functions**: Descriptive names, static for file-local functions
- **Types**: Standard C types (uint8_t, uint16_t), use typedefs for complex structures
- **Constants**: Use #define for constants, ALL_CAPS naming
- **Error Handling**: Check return values, print errors to console
- **Memory Management**: Always free allocated memory
- **Comments**: 
  - Function descriptions above declarations
  - Inline comments for complex logic
- **Includes**: Group system headers first, then project headers
- **Platform-specific code**: Use #ifdef PLATFORM_MACOS/#else/#endif blocks

## Project Architecture
- `src/python/` - Tide/sun/moon math + Pillow rendering; emits an 8-bit BMP and
  a `.meta` sidecar. Pillow is the only third-party dependency; astronomy is
  hand-rolled on stdlib `math`. Location lives in `location.json` (data), with
  station harmonics in `data/stations/*.json`.
- `src/c/` - Display host: main loop, the full-vs-partial refresh strategy, and
  a `DisplayInterface` driver layer (`display_layer.h`). The renderer is
  invoked via the BMP+`.meta` contract; the binary finds the project via
  `$TIDEMARK_HOME`.
- `sim/` - SDL2 simulator (one `DisplayInterface` implementation).
- `lib/` - Vendored IT8951 display driver (Waveshare); treat as external — do
  not refactor.
- `build/` - Build output and Makefile.
- `tests/` - unittest suite. `deploy/` - systemd unit templates.

See `AGENTS.md` for the cross-component contracts (Python↔C, adding a station,
adding a display driver).