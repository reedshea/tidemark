# Tidemark
E-ink picture frame showing upcoming tides

## Development
The project can be built for both Raspberry Pi (with real e-ink display) and MacOS (with SDL2-based display simulator).

### MacOS development with simulator
For faster development iteration, you can use the SDL2-based display simulator on MacOS:

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
`dev.sh` is a script that copies files to a Raspberry Pi, then builds and runs the program. It assumes local network SSH access to the Pi.

## Prerequisites

### Hardware
- Raspberry Pi
- Waveshare 7.8" E-Ink Display with IT8951 driver

### Software Dependencies
#### Raspberry Pi
- ARM GCC toolchain
- IT8951 driver library (included in `lib/IT8951`). The display driver code in `lib/IT8951` is from Waveshare's [IT8951 repository](https://github.com/waveshare/IT8951), included here for stability.

#### MacOS Development
- SDL2 and SDL2_ttf (for simulator)
- GCC or Clang
