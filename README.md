# Tidemark
E-ink picture frame showing upcoming tides

## Development
The project can be built for both Raspberry Pi (with real e-ink display) and MacOS (with SDL2-based display simulator).

### MacOS Development with Simulator
For faster development iteration, you can use the SDL2-based display simulator on MacOS:

1. Install dependencies:
```bash
brew install sdl2 sdl2_ttf
```

2. Build the simulator:
```bash
make host
```

3. Run the simulator:
```bash
./tidemark_sim --sim
```

The simulator creates a window that exactly matches the e-ink display's dimensions and grayscale levels, allowing for rapid development without needing to deploy to the Raspberry Pi for every change.

### Raspberry Pi Deployment
Build the Raspberry Pi version using:
```bash
make pi
```

## Prerequisites

### Hardware
- Raspberry Pi
- Waveshare 7.8" E-Ink Display with IT8951 driver

### Software Dependencies
#### Raspberry Pi
- ARM GCC toolchain
- IT8951 driver library (included in `lib/IT8951`)

#### MacOS Development
- SDL2 and SDL2_ttf (for simulator)
- GCC or Clang

The display driver code in `lib/IT8951` is from Waveshare's [IT8951 repository](https://github.com/waveshare/IT8951), included here for stability.
