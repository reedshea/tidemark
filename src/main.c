#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>
#ifdef PLATFORM_MACOS
#include "SDL.h"
#include "SDL_ttf.h"
#endif
#include "display/display_layer.h"
#include "graph.h"
#include "data/tide_data.h"
#include "sky_layer.h"

int main(int argc, char* argv[]) {
    (void)argc;  // Unused
    (void)argv;  // Unused

    // Initialize display layer
#ifdef PLATFORM_MACOS
    bool use_simulator = true;
#else
    bool use_simulator = false;
#endif

    if (!display_init(use_simulator)) {
        printf("Failed to initialize display\n");
        return 1;
    }

    // Get framebuffer from display layer
    uint8_t* framebuffer = display_get_framebuffer();
    if (!framebuffer) {
        printf("Failed to get framebuffer\n");
        display_cleanup();
        return 1;
    }

    // Clear the framebuffer to white first
    memset(framebuffer, DISPLAY_WHITE, DISPLAY_WIDTH * DISPLAY_HEIGHT);
    
    // Print size information for debugging
    printf("Display dimensions: %d x %d\n", DISPLAY_WIDTH, DISPLAY_HEIGHT);
    
    // Draw the sky layer with tide data
    printf("Drawing sky layer...\n");
    // draw_sky_layer(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT, SAMPLE_TIDE_DATA, NUM_TIDE_POINTS);
    
    // Now draw the tide graph
    printf("Drawing graph axes...\n");
    draw_graph_axes(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    
    printf("Drawing height labels...\n");
    draw_height_labels(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    
    printf("Drawing time labels...\n");
    draw_time_labels(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    
    printf("Plotting tide data...\n");
    plot_tide_data(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT, 
                  SAMPLE_TIDE_DATA, NUM_TIDE_POINTS);
    
    // Add label at bottom for debugging
    char debug_label[100];
    // sprintf(debug_label, "TIDEMARK - SKY & TIDE COMBINED");
    int text_x = DISPLAY_WIDTH/2 - 250;  // Adjust for larger font and better centering
    int text_y = DISPLAY_HEIGHT - 50;    // Position at the bottom of the screen
    display_draw_text(text_x, text_y, debug_label, DISPLAY_BLACK, DISPLAY_WHITE);

    // Main loop
    bool running = true;
    while (running) {
        // Update display
        display_update();

#ifdef PLATFORM_MACOS
        // Handle SDL events
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            }
        }
#else
        // On the Pi, just update once and exit
        running = false;
#endif
    }

    display_cleanup();
    return 0;
}
