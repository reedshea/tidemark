#ifndef SKY_DISPLAY_H
#define SKY_DISPLAY_H

#include <stdint.h>
#include <stdbool.h>
#include "display/display_layer.h"

// Sky display constants
#define SKY_HEIGHT 300  // Height of sky area (top portion of screen)

// Function to draw sky
void draw_sky(uint8_t* framebuf, uint16_t width, uint16_t height, bool is_night);

// Helper functions
void sky_draw_sun_or_moon(uint8_t* framebuf, uint16_t width, uint16_t height, 
                     int x, int y, int radius, bool is_night);
void draw_clouds(uint8_t* framebuf, uint16_t width, uint16_t height);
void draw_stars(uint8_t* framebuf, uint16_t width, uint16_t height);

#endif // SKY_DISPLAY_H