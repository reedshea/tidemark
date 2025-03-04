# Tidemark Bitmap Approach

This is a new approach for the Tidemark project that uses Python to generate bitmap images of tide charts, which are then displayed on the e-ink screen.

## Overview

Instead of attempting to render complex graphics directly in C, this approach:

1. Uses Python with libraries like PIL (Pillow), matplotlib, and numpy to generate high-quality tide chart images
2. Saves these images as bitmap (BMP) files
3. Displays them on the e-ink screen using the existing IT8951 library

This provides several advantages:
- Much easier to create complex visualizations in Python
- Better quality graphics
- More maintainable code
- Easier to add new features to the visualizations

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - PIL (Pillow)
  - numpy
  - matplotlib
- C compilation environment (same as main project)

## Installation

1. Install Python requirements:

```bash
pip install pillow numpy matplotlib
```

2. Build the bitmap version of Tidemark:

```bash
cd build
make clean
make bitmap
```

## Usage

### Running the Bitmap Version

```bash
cd build
./tidemark_bitmap
```

Command line options:
- `--sim`: Use simulator (automatically used on macOS)
- `--night`: Force night mode display
- `--day`: Force day mode display
- `--help`: Show help

### Running Just the Python Script

You can also run the Python script directly to generate charts:

```bash
cd src
python3 sky_display.py --output tide_chart.bmp
```

Python script options:
- `--sample`: Generate sample charts (day and night versions)
- `--night`: Force night mode
- `--day`: Force day mode
- `--output FILE`: Specify output file path (default: tide_chart.bmp)

## How It Works

1. The Python script (`sky_display.py`) generates a bitmap image with:
   - Sky background with sun/moon based on time of day
   - Tide chart showing tide levels over 24 hours
   - High and low tide markings with times
   - Labels and time information

2. The C program:
   - Initializes the display (either SDL simulator or e-ink)
   - Runs the Python script to generate the bitmap
   - Loads and displays the bitmap
   - Refreshes periodically (every 5 minutes by default)

## Customization

### Tide Data Source

The Python script currently uses sample tide data. To use real tide data, you'll need to:

1. Find a tide data API or data source
2. Write code to fetch and parse the data
3. Modify the script to use this data

### Visual Customization

The visualization can be easily modified in the Python script:
- Change colors and styles in the `draw_sky()` function
- Modify graph appearance in `draw_graph_axes()`
- Change tide curve appearance in `plot_tide_data()`

## For Raspberry Pi Deployment

For deployment on a Raspberry Pi, you can:

1. Set up as a systemd service to run at boot
2. Use cron to periodically update the display
3. Set the `TIDEMARK_DAEMON` environment variable to keep the program running continuously

## Building the Original C Version

You can still build the original C-only version:

```bash
cd build
make clean
make original
```