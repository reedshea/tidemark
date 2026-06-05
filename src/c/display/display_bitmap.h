#ifndef DISPLAY_BITMAP_H
#define DISPLAY_BITMAP_H

#include <stdbool.h>

/**
 * Display a pre-rendered BMP, choosing a refresh strategy from its .meta
 * sidecar. Vendor-neutral: the active display driver decides how to draw it.
 *
 * @param file_path Path to the BMP file to display
 * @return true if successful, false otherwise
 */
bool display_bitmap(const char* file_path);

/**
 * Generate a fresh tide chart (runs the Python renderer) and display it.
 * Set $TIDEMARK_HOME to the project root if not launching from it.
 *
 * @return true if successful, false otherwise
 */
bool display_tide_chart(void);

#endif // DISPLAY_BITMAP_H
