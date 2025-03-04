# Tidemark Development Guide

## Build Commands
- MacOS simulator: `cd build && make clean && PLATFORM=macos make && ./tidemark_sim`
- Raspberry Pi: `cd build && make clean && make && sudo ./tidemark`
- Deploy to Pi: `./dev.sh` (copies files to Pi, builds and runs)

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
- `src/` - Core application code
- `sim/` - SDL-based simulator for MacOS
- `lib/` - External libraries (IT8951 display driver)
- `build/` - Build output and Makefile