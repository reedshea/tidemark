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
    // Clear only the graph area to white
    for (int y = GRAPH_MARGIN_TOP; y < height - GRAPH_MARGIN_BOTTOM; y++) {
        for (int x = GRAPH_MARGIN_LEFT; x < width - GRAPH_MARGIN_RIGHT; x++) {
            framebuf[y * width + x] = DISPLAY_WHITE;
        }
    }
    
    // Draw X axis (thicker)
    draw_thick_line(framebuf, width,
                   GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM,
                   width - GRAPH_MARGIN_RIGHT, height - GRAPH_MARGIN_BOTTOM,
                   DISPLAY_BLACK, 3);

    // Draw Y axis (thicker)
    draw_thick_line(framebuf, width,
                   GRAPH_MARGIN_LEFT, GRAPH_MARGIN_TOP,
                   GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM,
                   DISPLAY_BLACK, 3);

    // Draw tick marks on X axis
    for (int hour = 0; hour <= 48; hour += 6) {
        int x = GRAPH_MARGIN_LEFT + (hour * (width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT) / 48);
        draw_thick_line(framebuf, width,
                       x, height - GRAPH_MARGIN_BOTTOM,
                       x, height - GRAPH_MARGIN_BOTTOM + 10,
                       DISPLAY_BLACK, 3);
    }

    // Draw tick marks on Y axis
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    for (float tide = -2.0f; tide <= 2.0f; tide += 0.5f) {
        int y = height - GRAPH_MARGIN_BOTTOM - ((tide + 2.0f) * graph_height / 4.0f);
        draw_thick_line(framebuf, width,
                       GRAPH_MARGIN_LEFT - 10, y,
                       GRAPH_MARGIN_LEFT, y,
                       DISPLAY_BLACK, 3);
    }
}

void draw_time_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    printf("Drawing time labels...\n");
    char buf[32];
    
    // Draw hour labels
    for (int hour = 0; hour <= 48; hour += 6) {
        int x = GRAPH_MARGIN_LEFT + (hour * (width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT) / 48);
        
        snprintf(buf, sizeof(buf), "%02d:00", (hour % 24));
        
        // Draw white background
        int label_width = 50;
        int label_height = 20;
        for (int dy = -2; dy < label_height; dy++) {
            for (int dx = -2; dx < label_width; dx++) {
                int bg_x = x - label_width/2 + dx;
                int bg_y = height - GRAPH_MARGIN_BOTTOM + 15 + dy;
                if (bg_x >= 0 && bg_x < width && bg_y >= 0 && bg_y < height) {
                    draw_pixel(framebuf, width, bg_x, bg_y, DISPLAY_WHITE);
                }
            }
        }
        
        display_draw_text(x - 25, height - GRAPH_MARGIN_BOTTOM + 15, buf, DISPLAY_BLACK, DISPLAY_WHITE);
    }
}

void draw_height_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    printf("Drawing height labels...\n");
    char buf[32];
    
    // Use same range as data
    float max_height = 4.0f;
    float height_step = 0.5f;
    
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    
    for (float tide = 0.0f; tide <= max_height; tide += height_step) {
        int y = height - GRAPH_MARGIN_BOTTOM - (int)((tide / max_height) * graph_height);
        
        printf("Label height=%.1f, y=%d\n", tide, y);
        
        snprintf(buf, sizeof(buf), "%.1f", tide);
        
        // Draw white background
        int label_width = 40;
        int label_height = 20;
        for (int dy = -2; dy < label_height; dy++) {
            for (int dx = -2; dx < label_width; dx++) {
                int bg_x = GRAPH_MARGIN_LEFT - 45 + dx;
                int bg_y = y - label_height/2 + dy;
                if (bg_x >= 0 && bg_x < width && bg_y >= 0 && bg_y < height) {
                    draw_pixel(framebuf, width, bg_x, bg_y, DISPLAY_WHITE);
                }
            }
        }
        
        display_draw_text(GRAPH_MARGIN_LEFT - 45, y - 8, buf, DISPLAY_BLACK, DISPLAY_WHITE);
    }
}

void plot_tide_data(uint8_t* framebuf, uint16_t width, uint16_t height,
                   const TidePoint* data, size_t num_points) {
    printf("Plotting tide data...\n");
    
    int graph_width = width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT;
    int graph_height = height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM;
    
    // First find actual data range
    float data_min = data[0].height;
    float data_max = data[0].height;
    for (size_t i = 1; i < num_points; i++) {
        if (data[i].height < data_min) data_min = data[i].height;
        if (data[i].height > data_max) data_max = data[i].height;
    }
    printf("Data range: %.1f to %.1f\n", data_min, data_max);
    
    // Use fixed range that comfortably contains the data
    float min_height = 0.0f;
    float max_height = 4.0f;
    float height_range = max_height - min_height;
    
    printf("Graph range: %.1f to %.1f (range=%.1f)\n", min_height, max_height, height_range);
    printf("Graph height: %d pixels\n", graph_height);
    
    // Find the start day to use as reference
    int start_day = data[0].day;
    
    // Draw simple lines connecting the points
    for (size_t i = 0; i < num_points - 1; i++) {
        // Calculate hours since start of first day
        float time1 = (data[i].day - start_day) * 24.0f + data[i].hour + (data[i].minute / 60.0f);
        float time2 = (data[i+1].day - start_day) * 24.0f + data[i+1].hour + (data[i+1].minute / 60.0f);
        
        int x1 = GRAPH_MARGIN_LEFT + (time1 * graph_width / 48);  // Show 48 hours
        int x2 = GRAPH_MARGIN_LEFT + (time2 * graph_width / 48);
        
        // Calculate y positions using fixed range
        int y1 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i].height / max_height) * graph_height);
        int y2 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i+1].height / max_height) * graph_height);
        
        printf("Point %zu: height=%.1f, y=%d\n", i, data[i].height, y1);
        
        // Draw thicker line for better visibility
        draw_thick_line(framebuf, width, x1, y1, x2, y2, DISPLAY_BLACK, 3);
    }
    
    // Draw data points and labels
    for (size_t i = 0; i < num_points; i++) {
        float time = (data[i].day - start_day) * 24.0f + data[i].hour + (data[i].minute / 60.0f);
        int x = GRAPH_MARGIN_LEFT + (time * graph_width / 48);  // Show 48 hours
        
        int y = height - GRAPH_MARGIN_BOTTOM - (int)((data[i].height / max_height) * graph_height);
        
        // Draw data point
        draw_circle(framebuf, width, x, y, 4, DISPLAY_BLACK);
        
        // Format time and height
        char label[32];
        snprintf(label, sizeof(label), "%d %02d:%02d\n%.1f%c", 
                data[i].day, data[i].hour, data[i].minute, 
                data[i].height, data[i].type);
        
        // Position label with more spacing
        int label_y = (data[i].type == 'H') ? y - 35 : y + 20;
        
        // Draw white background for label
        int label_width = 70;
        int label_height = 30;
        for (int dy = -2; dy < label_height; dy++) {
            for (int dx = -2; dx < label_width; dx++) {
                int bg_x = x - label_width/2 + dx;
                int bg_y = label_y + dy;
                if (bg_x >= 0 && bg_x < width && bg_y >= 0 && bg_y < height) {
                    draw_pixel(framebuf, width, bg_x, bg_y, DISPLAY_WHITE);
                }
            }
        }
        
        // Draw text on white background
        display_draw_text(x - 30, label_y, label, DISPLAY_BLACK, DISPLAY_WHITE);
    }
}
