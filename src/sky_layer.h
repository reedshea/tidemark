#ifndef SKY_LAYER_H
#define SKY_LAYER_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include <stdio.h>
#include "display/display_layer.h"
#include "data/tide_data.h"

// Sky dimensions 
#define SKY_HEIGHT 150  // Height of sky area above the graph

// Day/night times (for simplicity, fixed times)
#define SUNRISE_HOUR 6
#define SUNSET_HOUR 18

// Sky elements
void draw_sky_layer(uint8_t* framebuf, uint16_t width, uint16_t height, const TidePoint* tide_data, size_t num_points);
bool is_night_time(int hour);
void draw_sun_or_moon(uint8_t* framebuf, uint16_t width, uint16_t height, int x, int y, bool is_night);
void draw_day_night_gradient(uint8_t* framebuf, uint16_t width, uint16_t height, int hour);

#endif // SKY_LAYER_H