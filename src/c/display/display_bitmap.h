#ifndef DISPLAY_BITMAP_H
#define DISPLAY_BITMAP_H

#include <stdbool.h>

/**
 * Load and display a bitmap file on the e-ink display
 * 
 * On Raspberry Pi: Uses the IT8951 library's BMP loading function
 * On macOS: Loads the bitmap via SDL and displays in the simulator
 * 
 * @param file_path Path to the BMP file to display
 * @return true if successful, false otherwise
 */
bool display_bitmap(const char* file_path);

/**
 * Convenience function to generate and display a tide chart
 * 
 * This runs the Python script to generate the chart, then displays it
 * 
 * @param force_night 1 to force night mode, 0 to force day mode, -1 to use current time
 * @return true if successful, false otherwise
 */
bool display_tide_chart(int force_night);

#endif // DISPLAY_BITMAP_H