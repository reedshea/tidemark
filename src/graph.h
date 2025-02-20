#ifndef GRAPH_H
#define GRAPH_H

#include <stdint.h>
#include "tide_data.h"

// Graph dimensions and margins
#define GRAPH_MARGIN_LEFT   100  // Space for y-axis labels
#define GRAPH_MARGIN_RIGHT  50
#define GRAPH_MARGIN_TOP    50
#define GRAPH_MARGIN_BOTTOM 100  // Space for x-axis labels

// External function declarations from miniGUI.h
extern void EPD_Text(uint16_t Xpos, uint16_t Ypos, uint8_t* str, uint8_t Color, uint8_t bkColor);

// Graph drawing functions
void draw_graph_axes(uint8_t* framebuf, uint16_t width, uint16_t height);
void plot_tide_data(uint8_t* framebuf, uint16_t width, uint16_t height, 
                   const TidePoint* data, size_t num_points);
void draw_time_labels(uint8_t* framebuf, uint16_t width, uint16_t height);
void draw_height_labels(uint8_t* framebuf, uint16_t width, uint16_t height);

#endif // GRAPH_H
