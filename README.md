# Tidemark

A hybrid C/Python application for displaying tide charts on an e-ink display.

## Project Overview

Tidemark combines Python for data fetching and visualization with C for hardware interfacing. This approach provides:

- Easy creation of complex visualizations in Python
- Efficient hardware interfacing in C
- Simple deployment to Raspberry Pi

The application displays a tide chart with:
- Sky visualization (day/night with sun/moon)
- Tide graph showing tide levels over 24 hours
- High and low tide markings with times
- Periodic refreshing (configurable)

## Project Structure

```
tidemark/
├── build/           # Build outputs and Makefile
├── lib/             # Third-party C libraries (IT8951)
├── src/             # Source code
│   ├── c/           # C code
│   │   ├── display/ # Display driver code
│   │   │   ├── display_layer.c/h   # Common display interface
│   │   │   ├── display_bitmap.c/h  # Bitmap handling
│   │   │   └── display_eink.c      # E-ink specific code
│   │   └── main.c  # Main application
│   └── python/     # Python code
│       ├── render/  # Visualization rendering code
│       │   ├── sky.py      # Sky visualization
│       │   └── tide.py     # Tide chart visualization 
│       ├── data/           # Data fetching and processing
│       │   └── tide_api.py # Tide data fetching
│       └── main.py         # Main Python entry point
├── sim/             # SDL simulator
├── venv/            # Python virtual environment
└── CLAUDE.md        # Project notes and commands
```

## Requirements

### Hardware
- Raspberry Pi
- Waveshare 7.8" E-Ink Display with IT8951 driver

### Software Dependencies
- **C Development**:
  - GCC or compatible compiler
  - SDL2 and SDL2_ttf (for macOS simulator)
  - bcm2835 library (for Raspberry Pi)

- **Python**:
  - Python 3.6+
  - pillow (PIL fork)
  - numpy

## Setup and Build

### 1. Set up Python environment

```bash
# Create and activate virtual environment
make venv
source venv/bin/activate
```

### 2. Build the application

```bash
cd build
make clean
make
```

### 3. Run the application

```bash
# On macOS (simulator)
./tidemark_sim

# On Raspberry Pi
sudo ./tidemark
```

## Command Line Options

- `--day`: Force day mode display
- `--night`: Force night mode display
- `--sim`: Use simulator (automatically used on macOS)
- `--help`: Show help information

## Customization

### Tide Data Source

The sample tide data in `src/python/data/tide_api.py` should be replaced with a real API integration.
Implement the `get_tide_data()` function to fetch data from your preferred source.

### Visual Customization

- Sky visualization: `src/python/render/sky.py`
- Tide graph: `src/python/render/tide.py`
- Main layout: `src/python/main.py`

## Development

### macOS Development with Simulator
For faster development iteration, you can use the SDL2-based display simulator on macOS:

1. Install dependencies:
```bash
brew install sdl2 sdl2_ttf
```

2. From the `build` directory, build & run the simulator:
```bash
make clean && PLATFORM=macos make && ./tidemark_sim
```

The simulator creates a window that matches the e-ink display's dimensions and grayscale levels, allowing for rapid development without needing to deploy to the Raspberry Pi for every change.

### Raspberry Pi Deployment
`deploy.sh` is a script that copies files to a Raspberry Pi, then builds and runs the program. It assumes local network SSH access to the Pi.
