#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "graph.h"
#include "display_layer.h"

// Helper function to draw a pixel
static void draw_pixel(uint8_t* framebuf, uint16_t width, uint16_t x, uint16_t y, uint8_t color) {
    if (x < width && y < DISPLAY_HEIGHT) {
        framebuf[y * width + x] = color;
    }
}

// Helper function to draw a circle
static void draw_circle(uint8_t* framebuf, uint16_t width, 
                       uint16_t x0, uint16_t y0, uint16_t radius, uint8_t color) {
    int x = radius;
    int y = 0;
    int err = 0;

    while (x >= y) {
        draw_pixel(framebuf, width, x0 + x, y0 + y, color);
        draw_pixel(framebuf, width, x0 + y, y0 + x, color);
        draw_pixel(framebuf, width, x0 - y, y0 + x, color);
        draw_pixel(framebuf, width, x0 - x, y0 + y, color);
        draw_pixel(framebuf, width, x0 - x, y0 - y, color);
        draw_pixel(framebuf, width, x0 - y, y0 - x, color);
        draw_pixel(framebuf, width, x0 + y, y0 - x, color);
        draw_pixel(framebuf, width, x0 + x, y0 - y, color);

        if (err <= 0) {
            y += 1;
            err += 2*y + 1;
        }
        if (err > 0) {
            x -= 1;
            err -= 2*x + 1;
        }
    }
}

// Helper function to draw a line using Bresenham's algorithm
static void draw_line(uint8_t* framebuf, uint16_t width, 
                     uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, uint8_t color) {
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);
    int sx = x1 < x2 ? 1 : -1;
    int sy = y1 < y2 ? 1 : -1;
    int err = (dx > dy ? dx : -dy) / 2;
    int e2;

    while (1) {
        draw_pixel(framebuf, width, x1, y1, color);
        if (x1 == x2 && y1 == y2) break;
        e2 = err;
        if (e2 > -dx) { err -= dy; x1 += sx; }
        if (e2 < dy) { err += dx; y1 += sy; }
    }
}

// Helper function to draw a thick line
static void draw_thick_line(uint8_t* framebuf, uint16_t width,
                          uint16_t x1, uint16_t y1, uint16_t x2, uint16_t y2, 
                          uint8_t color, uint8_t thickness) {
    for (int i = -thickness/2; i <= thickness/2; i++) {
        for (int j = -thickness/2; j <= thickness/2; j++) {
            draw_line(framebuf, width,
                     x1 + i, y1 + j,
                     x2 + i, y2 + j,
                     color);
        }
    }
}

void draw_graph_axes(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Draw X axis (thicker)
    draw_thick_line(framebuf, width,
                   GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM,
                   width - GRAPH_MARGIN_RIGHT, height - GRAPH_MARGIN_BOTTOM,
                   0x00, 2);

    // Draw Y axis (thicker)
    draw_thick_line(framebuf, width,
                   GRAPH_MARGIN_LEFT, GRAPH_MARGIN_TOP,
                   GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM,
                   0x00, 2);

    // Draw tick marks on X axis
    for (int hour = 0; hour <= 24; hour += 3) {
        int x = GRAPH_MARGIN_LEFT + (hour * (width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT) / 24);
        draw_thick_line(framebuf, width,
                       x, height - GRAPH_MARGIN_BOTTOM,
                       x, height - GRAPH_MARGIN_BOTTOM + 10,
                       0x00, 2);
    }

    // Draw tick marks on Y axis
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    for (float tide = -2.0f; tide <= 2.0f; tide += 0.5f) {
        int y = height - GRAPH_MARGIN_BOTTOM - ((tide + 2.0f) * graph_height / 4.0f);
        draw_thick_line(framebuf, width,
                       GRAPH_MARGIN_LEFT - 10, y,
                       GRAPH_MARGIN_LEFT, y,
                       0x00, 2);
    }
}

void draw_time_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    char buf[32];
    for (int hour = 0; hour <= 24; hour += 3) {
        snprintf(buf, sizeof(buf), "%02d:00", hour);
        int x = GRAPH_MARGIN_LEFT + (hour * (width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT) / 24);
        display_draw_text(x - 20, height - GRAPH_MARGIN_BOTTOM + 20, buf, 0x00, 0xFF);
    }
}

void draw_height_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    char buf[32];
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    
    for (float tide = -2.0f; tide <= 2.0f; tide += 0.5f) {
        snprintf(buf, sizeof(buf), "%.1f", tide);
        int y = height - GRAPH_MARGIN_BOTTOM - ((tide + 2.0f) * graph_height / 4.0f);
        display_draw_text(GRAPH_MARGIN_LEFT - 50, y - 8, buf, 0x00, 0xFF);
        
        // Draw light horizontal grid line
        if (tide != 0.0f) {  // Don't draw grid line over x-axis
            draw_line(framebuf, width,
                     GRAPH_MARGIN_LEFT, y,
                     width - GRAPH_MARGIN_RIGHT, y,
                     0xE0);  // Very light gray
        }
    }
}

void plot_tide_data(uint8_t* framebuf, uint16_t width, uint16_t height,
                   const TidePoint* data, size_t num_points) {
    int graph_width = width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT;
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    
    // Draw lines connecting the points
    for (size_t i = 0; i < num_points - 1; i++) {
        float time1 = data[i].hour + (data[i].minute / 60.0f);
        float time2 = data[i+1].hour + (data[i+1].minute / 60.0f);
        
        int y1 = height - GRAPH_MARGIN_BOTTOM - ((data[i].height + 2.0f) * graph_height / 4.0f);
        int y2 = height - GRAPH_MARGIN_BOTTOM - ((data[i+1].height + 2.0f) * graph_height / 4.0f);
        
        int x1 = GRAPH_MARGIN_LEFT + (time1 * graph_width / 24);
        int x2 = GRAPH_MARGIN_LEFT + (time2 * graph_width / 24);
        
        draw_thick_line(framebuf, width, x1, y1, x2, y2, 0x00, 2);
    }
    
    // Draw data points on top
    for (size_t i = 0; i < num_points; i++) {
        float time = data[i].hour + (data[i].minute / 60.0f);
        int x = GRAPH_MARGIN_LEFT + (time * graph_width / 24);
        
        // Calculate y position using same formula as draw_height_labels
        float height_offset = (data[i].height + 2.0f) * graph_height / 4.0f;
        int y = height - GRAPH_MARGIN_BOTTOM - height_offset;
        
        // Clamp y to valid range (0 to height)
        if (y < 0) y = GRAPH_MARGIN_TOP;
        if (y >= height) y = height - GRAPH_MARGIN_BOTTOM;
        
        printf("Point %zu: height=%.1f, graph_height=%d, height_offset=%.1f, y=%d (clamped)\n", 
               i, data[i].height, graph_height, height_offset, y);
        
        // Draw larger circles for high/low points
        draw_circle(framebuf, width, x, y, 5, 0x00);
        
        // Add text label for tide height
        char buf[32];
        snprintf(buf, sizeof(buf), "%.1f", data[i].height);
        display_draw_text(x - 15, y - 20, buf, 0x00, 0xFF);  // Using y from above
    }
}
