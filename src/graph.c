#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "graph.h"
#include "display/display_layer.h"

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

// Helper function to calculate a point on a cubic Bezier curve
static void bezier_point(float t, 
                        int x0, int y0,   // Start point
                        int x1, int y1,   // Control point 1
                        int x2, int y2,   // Control point 2
                        int x3, int y3,   // End point
                        int* x, int* y) {
    float t2 = t * t;
    float t3 = t2 * t;
    float mt = 1 - t;
    float mt2 = mt * mt;
    float mt3 = mt2 * mt;
    
    *x = x0 * mt3 + 3 * x1 * mt2 * t + 3 * x2 * mt * t2 + x3 * t3;
    *y = y0 * mt3 + 3 * y1 * mt2 * t + 3 * y2 * mt * t2 + y3 * t3;
}

// Draw a cubic Bezier curve
static void draw_bezier_curve(uint8_t* framebuf, uint16_t width,
                            int x0, int y0,   // Start point
                            int x1, int y1,   // Control point 1
                            int x2, int y2,   // Control point 2
                            int x3, int y3,   // End point
                            uint8_t color, uint8_t thickness) {
    int prev_x = x0;
    int prev_y = y0;
    
    // Draw curve with small steps
    for (float t = 0.01f; t <= 1.0f; t += 0.01f) {
        int x, y;
        bezier_point(t, x0, y0, x1, y1, x2, y2, x3, y3, &x, &y);
        draw_thick_line(framebuf, width, prev_x, prev_y, x, y, color, thickness);
        prev_x = x;
        prev_y = y;
    }
}

// Draw a uniform crosshatch pattern
static void draw_base_pattern(uint8_t* pattern_buf, uint16_t width, uint16_t height,
                            int start_x, int end_x, int start_y, int end_y) {
    const int spacing = 15;  // Space between lines
    
    // Clear pattern buffer to white
    memset(pattern_buf, DISPLAY_WHITE, width * height);
    
    // Draw diagonal lines (/)
    for (int x = start_x - height; x < end_x + height; x += spacing) {
        draw_thick_line(pattern_buf, width, 
                       x, end_y,
                       x + (end_y - start_y), start_y,
                       DISPLAY_BLACK, 1);
    }
    
    // Draw diagonal lines (\)
    for (int x = start_x - height; x < end_x + height; x += spacing) {
        draw_thick_line(pattern_buf, width,
                       x, start_y,
                       x + (end_y - start_y), end_y,
                       DISPLAY_BLACK, 1);
    }
}

void draw_graph_axes(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Clear the entire background to white
    memset(framebuf, DISPLAY_WHITE, width * height);
    
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
    
    // Adjust graph height to use only bottom 60% of display
    int max_graph_height = (height - GRAPH_MARGIN_TOP - GRAPH_MARGIN_BOTTOM) * 0.6;
    int graph_width = width - GRAPH_MARGIN_LEFT - GRAPH_MARGIN_RIGHT;
    int graph_height = max_graph_height;
    
    // Create temporary buffers
    uint8_t* pattern_buf = malloc(width * height);
    uint8_t* mask_buf = malloc(width * height);
    if (!pattern_buf || !mask_buf) {
        printf("Failed to allocate temporary buffers\n");
        free(pattern_buf);
        free(mask_buf);
        return;
    }
    
    // Clear mask buffer to white (fully transparent)
    memset(mask_buf, DISPLAY_WHITE, width * height);
    
    // Draw the base crosshatch pattern
    draw_base_pattern(pattern_buf, width, height,
                     GRAPH_MARGIN_LEFT, width - GRAPH_MARGIN_RIGHT,
                     height - GRAPH_MARGIN_BOTTOM - graph_height,
                     height - GRAPH_MARGIN_BOTTOM);
    
    // First find actual data range
    float data_min = data[0].height;
    float data_max = data[0].height;
    for (size_t i = 1; i < num_points; i++) {
        if (data[i].height < data_min) data_min = data[i].height;
        if (data[i].height > data_max) data_max = data[i].height;
    }
    
    // Use fixed range that comfortably contains the data
    float min_height = 0.0f;
    float max_height = 4.0f;
    
    // Find the start day to use as reference
    int start_day = data[0].day;
    
    // Create the mask by filling below the curve
    for (size_t i = 0; i < num_points - 1; i++) {
        float time1 = (data[i].day - start_day) * 24.0f + data[i].hour + (data[i].minute / 60.0f);
        float time2 = (data[i+1].day - start_day) * 24.0f + data[i+1].hour + (data[i+1].minute / 60.0f);
        
        int x0 = GRAPH_MARGIN_LEFT + (time1 * graph_width / 48);
        int x3 = GRAPH_MARGIN_LEFT + (time2 * graph_width / 48);
        
        int y0 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i].height / max_height) * graph_height);
        int y3 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i+1].height / max_height) * graph_height);
        
        // Calculate control points 1/3 and 2/3 of the way between points
        int x1 = x0 + (x3 - x0) / 3;
        int x2 = x0 + 2 * (x3 - x0) / 3;
        int y1 = y0;
        int y2 = y3;
        
        // Draw filled bezier curve in the mask buffer
        for (int x = x0; x <= x3; x++) {
            float t = (float)(x - x0) / (x3 - x0);
            float mt = 1 - t;
            float mt2 = mt * mt;
            float mt3 = mt2 * mt;
            float t2 = t * t;
            float t3 = t2 * t;
            
            int y = y0 * mt3 + 3 * y1 * mt2 * t + 3 * y2 * mt * t2 + y3 * t3;
            
            // Fill everything below the curve with black in the mask
            for (int fill_y = y; fill_y <= height - GRAPH_MARGIN_BOTTOM; fill_y++) {
                mask_buf[fill_y * width + x] = DISPLAY_BLACK;
            }
        }
    }
    
    // Combine pattern and mask into final framebuffer
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            int idx = y * width + x;
            // Only show pattern where mask is black
            framebuf[idx] = (mask_buf[idx] == DISPLAY_BLACK) ? pattern_buf[idx] : DISPLAY_WHITE;
        }
    }
    
    // Draw the smooth curve on top
    for (size_t i = 0; i < num_points - 1; i++) {
        float time1 = (data[i].day - start_day) * 24.0f + data[i].hour + (data[i].minute / 60.0f);
        float time2 = (data[i+1].day - start_day) * 24.0f + data[i+1].hour + (data[i+1].minute / 60.0f);
        
        int x0 = GRAPH_MARGIN_LEFT + (time1 * graph_width / 48);
        int x3 = GRAPH_MARGIN_LEFT + (time2 * graph_width / 48);
        
        int y0 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i].height / max_height) * graph_height);
        int y3 = height - GRAPH_MARGIN_BOTTOM - (int)((data[i+1].height / max_height) * graph_height);
        
        int x1 = x0 + (x3 - x0) / 3;
        int x2 = x0 + 2 * (x3 - x0) / 3;
        int y1 = y0;
        int y2 = y3;
        
        // Draw the curve
        draw_bezier_curve(framebuf, width,
                         x0, y0, x1, y1, x2, y2, x3, y3,
                         DISPLAY_BLACK, 3);
    }
    
    // Draw data points and labels
    for (size_t i = 0; i < num_points; i++) {
        float time = (data[i].day - start_day) * 24.0f + data[i].hour + (data[i].minute / 60.0f);
        int x = GRAPH_MARGIN_LEFT + (time * graph_width / 48);
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
                    framebuf[bg_y * width + bg_x] = DISPLAY_WHITE;
                }
            }
        }
        
        // Draw text on white background
        display_draw_text(x - 30, label_y, label, DISPLAY_BLACK, DISPLAY_WHITE);
    }
    
    // Clean up
    free(pattern_buf);
    free(mask_buf);
}
