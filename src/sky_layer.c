#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include "sky_layer.h"
#include "graph.h"

#ifdef PLATFORM_MACOS
#include "SDL.h"
#endif

// Check if a given hour is night time (between sunset and sunrise)
bool is_night_time(int hour) {
    return hour >= SUNSET_HOUR || hour < SUNRISE_HOUR;
}

// Draw a sun (day) or moon (night) at the specified position
void draw_sun_or_moon(uint8_t* framebuf, uint16_t width, uint16_t height, int x, int y, bool is_night) {
    (void)height; // Unused parameter

    int radius = 25; // Slightly larger
    
    // Draw black outline first to create contrast
    for (int i = -(radius+2); i <= (radius+2); i++) {
        for (int j = -(radius+2); j <= (radius+2); j++) {
            if (i*i + j*j <= (radius+2)*(radius+2) && i*i + j*j >= radius*radius) {
                int pixel_x = x + i;
                int pixel_y = y + j;
                
                // Check within display bounds
                if (pixel_x >= 0 && pixel_x < width && pixel_y >= 0 && pixel_y < height) {
                    framebuf[pixel_y * width + pixel_x] = DISPLAY_BLACK;
                }
            }
        }
    }
    
    // Draw the circular body
    for (int i = -radius; i <= radius; i++) {
        for (int j = -radius; j <= radius; j++) {
            if (i*i + j*j <= radius*radius) {
                int pixel_x = x + i;
                int pixel_y = y + j;
                
                // Check within display bounds
                if (pixel_x >= 0 && pixel_x < width && pixel_y >= 0 && pixel_y < height) {
                    if (is_night) {
                        // For moon, make a pure white circle for maximum contrast against black sky
                        framebuf[pixel_y * width + pixel_x] = DISPLAY_WHITE;
                    } else {
                        // For sun, inverse - make a solid black circle against white sky
                        framebuf[pixel_y * width + pixel_x] = DISPLAY_BLACK;
                    }
                }
            }
        }
    }
    
    // For the sun, add rays
    if (!is_night) {
        int ray_length = radius + 15; // Longer rays
        int num_rays = 8;
        
        for (int r = 0; r < num_rays; r++) {
            double angle = 2.0 * M_PI * r / num_rays;
            int ray_x = x + (int)(ray_length * cos(angle));
            int ray_y = y + (int)(ray_length * sin(angle));
            
            // Draw a line from the edge of the circle to the ray tip
            int start_x = x + (int)(radius * cos(angle));
            int start_y = y + (int)(radius * sin(angle));
            
            // Simple line drawing with thickness
            int dx = ray_x - start_x;
            int dy = ray_y - start_y;
            int steps = (abs(dx) > abs(dy)) ? abs(dx) : abs(dy);
            
            float x_inc = (float)dx / steps;
            float y_inc = (float)dy / steps;
            
            float curr_x = start_x;
            float curr_y = start_y;
            
            for (int s = 0; s <= steps; s++) {
                // Make rays thicker (3 pixels wide)
                for (int t = -1; t <= 1; t++) {
                    for (int u = -1; u <= 1; u++) {
                        int px = (int)curr_x + t;
                        int py = (int)curr_y + u;
                        
                        if (px >= 0 && px < width && py >= 0 && py < height) {
                            framebuf[py * width + px] = DISPLAY_BLACK; // Draw outline in black
                        }
                    }
                }
                // Draw the white center
                int px = (int)curr_x;
                int py = (int)curr_y;
                if (px >= 0 && px < width && py >= 0 && py < height) {
                    framebuf[py * width + px] = DISPLAY_WHITE;
                }
                
                curr_x += x_inc;
                curr_y += y_inc;
            }
        }
    }
    // For moon, add stars around it (instead of a crescent)
    else {
        // Add stars around the moon (small white dots)
        srand(42); // Fixed seed for reproducible star pattern
        
        for (int i = 0; i < 100; i++) {
            int star_x = rand() % width;
            int star_y = rand() % GRAPH_MARGIN_TOP;
            
            // Don't place stars too close to the moon
            int dx = star_x - x;
            int dy = star_y - y;
            if (dx*dx + dy*dy < radius*radius*4) {
                continue;
            }
            
            // Draw a 2x2 or 3x3 star
            int star_size = (rand() % 2) + 2;
            for (int sx = 0; sx < star_size; sx++) {
                for (int sy = 0; sy < star_size; sy++) {
                    int px = star_x + sx;
                    int py = star_y + sy;
                    if (px >= 0 && px < width && py >= 0 && py < GRAPH_MARGIN_TOP) {
                        framebuf[py * width + px] = DISPLAY_WHITE;
                    }
                }
            }
        }
    }
}

// Draw a gradient representing day/night transition in the sky
void draw_day_night_gradient(uint8_t* framebuf, uint16_t width, uint16_t height, int hour) {
    // Sky area starts above the graph area
    int sky_top = 0;  
    int sky_bottom = GRAPH_MARGIN_TOP;
    int sky_height = sky_bottom - sky_top;
    
    // Calculate gradient based on time of day
    // This uses a simple scale: dark at night, light during day, gradient at transitions
    uint8_t base_color;
    bool is_transition = false;
    
    if (hour == SUNRISE_HOUR || hour == SUNRISE_HOUR - 1 || 
        hour == SUNSET_HOUR || hour == SUNSET_HOUR - 1) {
        is_transition = true;
    }
    
    if (is_night_time(hour)) {
        base_color = 0x00; // Pure black for night (maximum contrast)
    } else {
        base_color = 0xFF; // Pure white for day
    }
    
    // Fill sky area with the appropriate shade
    for (int y = sky_top; y < sky_bottom; y++) {
        uint8_t color = base_color;
        
        // If it's a transition period, create a gradient
        if (is_transition) {
            float gradient_factor = (float)(y - sky_top) / sky_height;
            
            if (hour == SUNRISE_HOUR || hour == SUNRISE_HOUR - 1) {
                // Dawn transition: darker at top, lighter at bottom
                color = 0x00 + (uint8_t)((0xFF - 0x00) * gradient_factor);
            } else {  // SUNSET_HOUR
                // Dusk transition: lighter at top, darker at bottom
                color = 0xFF - (uint8_t)((0xFF - 0x00) * gradient_factor);
            }
        }
        
        // Fill row with the calculated color
        for (int x = 0; x < width; x++) {
            framebuf[y * width + x] = color;
        }
    }
}

// Main function to draw the sky layer
void draw_sky_layer(uint8_t* framebuf, uint16_t width, uint16_t height, const TidePoint* tide_data, size_t num_points) {
    // For testing purposes, set to midnight if there's no data
    // This ensures we see a night sky by default
    int current_hour = 0; 
    
    // Look for a night-time data point to showcase the night sky
    bool found_night = false;
    for (size_t i = 0; i < num_points; i++) {
        if (is_night_time(tide_data[i].hour)) {
            current_hour = tide_data[i].hour;
            found_night = true;
            break;
        }
    }
    
    // Fallback to first data point if no night time found
    if (!found_night && num_points > 0) {
        current_hour = tide_data[0].hour;
    }
    
    printf("Sky using hour: %d (night: %s)\n", current_hour, is_night_time(current_hour) ? "yes" : "no");
    
    // Draw day/night gradient for the sky background
    draw_day_night_gradient(framebuf, width, height, current_hour);
    
    // Calculate position for sun/moon - center it for visibility
    int celestial_x = width / 2;
    int celestial_y = GRAPH_MARGIN_TOP / 2;
    
    // Draw sun or moon based on time
    bool night = is_night_time(current_hour);
    draw_sun_or_moon(framebuf, width, height, celestial_x, celestial_y, night);
    
#ifdef PLATFORM_MACOS
    // Create a separate window just for the sky - useful for debugging
    static SDL_Window* sky_window = NULL;
    static SDL_Renderer* sky_renderer = NULL;
    static SDL_Texture* sky_texture = NULL;
    
    if (!sky_window) {
        sky_window = SDL_CreateWindow("SKY LAYER VIEW", 
                                    SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                    400, 200, SDL_WINDOW_SHOWN);
        if (sky_window) {
            sky_renderer = SDL_CreateRenderer(sky_window, -1, SDL_RENDERER_ACCELERATED);
            if (sky_renderer) {
                sky_texture = SDL_CreateTexture(sky_renderer, SDL_PIXELFORMAT_RGBA8888,
                                            SDL_TEXTUREACCESS_STREAMING, 400, 200);
            }
        }
    }
    
    if (sky_window && sky_renderer && sky_texture) {
        // Update texture with a simple pattern based on night/day
        uint32_t* pixels = NULL;
        int pitch = 0;
        SDL_LockTexture(sky_texture, NULL, (void**)&pixels, &pitch);
        
        for (int y = 0; y < 200; y++) {
            for (int x = 0; x < 400; x++) {
                uint32_t color;
                if (night) {
                    // Black background with white grid for night
                    color = ((x % 20 == 0) || (y % 20 == 0)) ? 0xFFFFFFFF : 0xFF000000;
                } else {
                    // White background with black grid for day
                    color = ((x % 20 == 0) || (y % 20 == 0)) ? 0xFF000000 : 0xFFFFFFFF;
                }
                pixels[y * (pitch / 4) + x] = color;
            }
        }
        
        // Draw text in center
        char info[20];
        snprintf(info, sizeof(info), "%s %d:00", night ? "NIGHT" : "DAY", current_hour);
        // Simple text visualization in the debug window
        for (int y = 80; y < 120; y++) {
            for (int x = 150; x < 250; x++) {
                pixels[y * (pitch / 4) + x] = night ? 0xFFFFFFFF : 0xFF000000;
            }
        }
        
        SDL_UnlockTexture(sky_texture);
        SDL_RenderClear(sky_renderer);
        SDL_RenderCopy(sky_renderer, sky_texture, NULL, NULL);
        SDL_RenderPresent(sky_renderer);
    }
#endif
    
    // Add a small label showing day/night status in the top corner
    char status_text[50];
    snprintf(status_text, sizeof(status_text), "SKY: %s (%d:00)", 
            night ? "NIGHT" : "DAY", current_hour);
    
    // Draw small background box for text in the top right corner
    int box_width = 200;
    int box_height = 30;
    int box_x = width - box_width - 10;  // Position in top right
    int box_y = 10;
    
    // Fill background box
    for (int y = box_y; y < box_y + box_height; y++) {
        for (int x = box_x; x < box_x + box_width; x++) {
            if (x >= 0 && x < width && y >= 0 && y < height) {
                // Use contrasting color based on night/day
                framebuf[y * width + x] = night ? DISPLAY_WHITE : DISPLAY_BLACK;
            }
        }
    }
    
    // Draw a thin border around the text box
    uint8_t border_color = night ? DISPLAY_BLACK : DISPLAY_WHITE;
    for (int t = 0; t < 2; t++) { // Make border 2 pixels thick
        // Top and bottom borders
        for (int x = box_x - t; x < box_x + box_width + t; x++) {
            if (x >= 0 && x < width) {
                int top_y = box_y - t;
                int bottom_y = box_y + box_height + t - 1;
                if (top_y >= 0 && top_y < height) 
                    framebuf[top_y * width + x] = border_color;
                if (bottom_y >= 0 && bottom_y < height)
                    framebuf[bottom_y * width + x] = border_color;
            }
        }
        
        // Left and right borders
        for (int y = box_y - t; y < box_y + box_height + t; y++) {
            if (y >= 0 && y < height) {
                int left_x = box_x - t;
                int right_x = box_x + box_width + t - 1;
                if (left_x >= 0 && left_x < width)
                    framebuf[y * width + left_x] = border_color;
                if (right_x >= 0 && right_x < width)
                    framebuf[y * width + right_x] = border_color;
            }
        }
    }
    
    // Use display_draw_text to write the text with inverted colors
    display_draw_text(box_x + 10, box_y + 10, status_text, 
                    night ? DISPLAY_BLACK : DISPLAY_WHITE, 
                    night ? DISPLAY_WHITE : DISPLAY_BLACK);

    // Add a bold horizon line at the bottom of the sky
    for (int x = 0; x < width; x++) {
        framebuf[GRAPH_MARGIN_TOP * width + x] = DISPLAY_BLACK;
        // Make it 2 pixels thick for visibility
        if ((GRAPH_MARGIN_TOP-1) >= 0) {
            framebuf[(GRAPH_MARGIN_TOP-1) * width + x] = DISPLAY_BLACK;
        }
    }
}