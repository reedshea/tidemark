#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include "sky_display.h"

// Simple implementation to draw a basic sky with sun/moon and clouds or stars
void draw_sky(uint8_t* framebuf, uint16_t width, uint16_t height, bool is_night) {
    // For debugging - print the dimensions
    printf("Drawing sky area: %d x %d (screen: %d x %d)\n", 
           width, SKY_HEIGHT, width, height);
    
    // Draw the sky across the entire display for testing/debugging
    // We'll use a half-and-half approach - top half has sky
    int sky_area = height / 2;  // Use half the screen height for sky
    
    // First, fill the sky background
    uint8_t bg_color = is_night ? 30 : 240;  // Darker for night, lighter for day
    
    // Fill the sky area with background color
    for (int y = 0; y < sky_area && y < height; y++) {
        // Add a gradient effect - darker at top, lighter toward horizon
        float gradient_factor = (float)y / sky_area;
        uint8_t color;
        
        if (is_night) {
            // Night: Very dark at top to less dark at horizon
            color = 10 + (uint8_t)(40 * gradient_factor);
        } else {
            // Day: Light blue at top to white at horizon
            color = 180 + (uint8_t)(70 * gradient_factor);
        }
        
        for (int x = 0; x < width; x++) {
            framebuf[y * width + x] = color;
        }
    }
    
    // Draw a horizontal line at the horizon (bottom of sky area)
    int horizon_y = sky_area - 1;
    if (horizon_y >= 0 && horizon_y < height) {
        for (int x = 0; x < width; x++) {
            framebuf[horizon_y * width + x] = DISPLAY_BLACK;
        }
    }
    
    // Draw sun or moon in the middle of the sky
    int celestial_x = width / 2;
    int celestial_y = sky_area / 3;
    int celestial_radius = 80;  // Larger for better visibility
    
    sky_draw_sun_or_moon(framebuf, width, height, celestial_x, celestial_y, 
                    celestial_radius, is_night);
    
    // Draw clouds for day or stars for night
    if (is_night) {
        draw_stars(framebuf, width, height);
    } else {
        draw_clouds(framebuf, width, height);
    }
}

// Draw a sun (day) or moon (night)
void sky_draw_sun_or_moon(uint8_t* framebuf, uint16_t width, uint16_t height, 
                     int x, int y, int radius, bool is_night) {
    // Draw circle using the midpoint circle algorithm
    int f = 1 - radius;
    int ddF_x = 0;
    int ddF_y = -2 * radius;
    int px = 0;
    int py = radius;

    // Draw a filled circle
    // First, fill a square of the circle's diameter
    for (int cy = -radius; cy <= radius; cy++) {
        for (int cx = -radius; cx <= radius; cx++) {
            // Only fill pixels within the circle
            if (cx*cx + cy*cy <= radius*radius) {
                int draw_x = x + cx;
                int draw_y = y + cy;
                
                // Check bounds
                if (draw_x >= 0 && draw_x < width && draw_y >= 0 && draw_y < height) {
                    // Set color based on day or night
                    if (is_night) {
                        // Moon is white
                        framebuf[draw_y * width + draw_x] = DISPLAY_WHITE;
                    } else {
                        // Sun is a light gray to distinguish from sky
                        framebuf[draw_y * width + draw_x] = 200;
                    }
                }
            }
        }
    }
    
    // Add a black outline to the circle
    int outline_radius = radius + 2;
    for (int angle = 0; angle < 360; angle++) {
        float rad = angle * M_PI / 180.0;
        int draw_x = x + (int)(outline_radius * cos(rad));
        int draw_y = y + (int)(outline_radius * sin(rad));
        
        // Check bounds
        if (draw_x >= 0 && draw_x < width && draw_y >= 0 && draw_y < height) {
            framebuf[draw_y * width + draw_x] = DISPLAY_BLACK;
        }
    }
    
    // For sun, add rays
    if (!is_night) {
        int ray_length = radius + 20;
        int num_rays = 8;
        
        for (int i = 0; i < num_rays; i++) {
            float angle = i * 2 * M_PI / num_rays;
            int end_x = x + (int)(ray_length * cos(angle));
            int end_y = y + (int)(ray_length * sin(angle));
            int start_x = x + (int)(radius * cos(angle));
            int start_y = y + (int)(radius * sin(angle));
            
            // Draw the ray using Bresenham's line algorithm
            int dx = abs(end_x - start_x);
            int dy = abs(end_y - start_y);
            int sx = start_x < end_x ? 1 : -1;
            int sy = start_y < end_y ? 1 : -1;
            int err = dx - dy;
            int e2;
            
            int draw_x = start_x;
            int draw_y = start_y;
            
            while (draw_x != end_x || draw_y != end_y) {
                if (draw_x >= 0 && draw_x < width && draw_y >= 0 && draw_y < height) {
                    framebuf[draw_y * width + draw_x] = DISPLAY_BLACK;
                }
                
                e2 = 2 * err;
                if (e2 > -dy) {
                    err -= dy;
                    draw_x += sx;
                }
                if (e2 < dx) {
                    err += dx;
                    draw_y += sy;
                }
            }
        }
    }
}

// Draw some simple cloud shapes
void draw_clouds(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Calculate sky area (half the screen)
    int sky_area = height / 2;
    
    // We'll draw a few simple cloud shapes
    // Each cloud is formed by drawing several overlapping circles
    
    // Cloud positions
    int cloud_data[][2] = {
        {width/4, sky_area/2},
        {width*3/4, sky_area/4},
        {width/2, sky_area*2/3}
    };
    
    for (int c = 0; c < 3; c++) {
        int cloud_x = cloud_data[c][0];
        int cloud_y = cloud_data[c][1];
        
        // Draw cloud outline
        for (int i = 0; i < 4; i++) {
            int offset_x = (i - 2) * 50;  // Wider spacing for larger clouds
            int radius = 40 + (i % 3) * 10; // Larger radius for better visibility
            
            // For each circle that makes up the cloud
            for (int cy = -radius; cy <= radius; cy++) {
                for (int cx = -radius; cx <= radius; cx++) {
                    if (cx*cx + cy*cy <= radius*radius) {
                        int draw_x = cloud_x + offset_x + cx;
                        int draw_y = cloud_y + cy;
                        
                        // Check bounds
                        if (draw_x >= 0 && draw_x < width && 
                            draw_y >= 0 && draw_y < height) {
                            // Cloud is white or very light gray
                            framebuf[draw_y * width + draw_x] = DISPLAY_WHITE - 10;
                        }
                    }
                }
            }
        }
    }
}

// Draw some simple stars
void draw_stars(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Calculate sky area (half the screen)
    int sky_area = height / 2;
    
    // Use a fixed seed for reproducible pattern
    srand(42);
    
    // Draw about 200 stars
    for (int i = 0; i < 200; i++) {
        int star_x = rand() % width;
        int star_y = rand() % sky_area;
        
        // Make some stars larger
        int star_size = (rand() % 100 < 20) ? 3 : 2;
        
        // Draw the star - larger for better visibility
        for (int sy = 0; sy < star_size; sy++) {
            for (int sx = 0; sx < star_size; sx++) {
                int draw_x = star_x + sx;
                int draw_y = star_y + sy;
                
                // Check bounds
                if (draw_x >= 0 && draw_x < width && 
                    draw_y >= 0 && draw_y < height) {
                    framebuf[draw_y * width + draw_x] = DISPLAY_WHITE;
                }
            }
        }
    }
}