#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#ifdef PLATFORM_MACOS
#include "SDL.h"
#include "SDL_ttf.h"
#endif
#include "display_layer.h"
#include "graph.h"
#include "tide_data.h"

// Sample tide data (replace with actual data)
// static const float tide_data[] = {
//     1.2, 2.5, 3.8, 2.1, 1.0, 2.2, 3.5, 2.8, 1.5, 2.0,
//     3.0, 2.3, 1.8, 2.7, 3.2, 2.4, 1.7, 2.9, 3.4, 2.6
// };
// static const int num_tide_points = sizeof(tide_data) / sizeof(tide_data[0]);

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

    // Draw the graph components
    printf("Drawing graph axes...\n");
    draw_graph_axes(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    printf("Drawing height labels...\n");
    draw_height_labels(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    printf("Drawing time labels...\n");
    draw_time_labels(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    printf("Plotting tide data...\n");
    plot_tide_data(framebuffer, DISPLAY_WIDTH, DISPLAY_HEIGHT, 
                  SAMPLE_TIDE_DATA, NUM_TIDE_POINTS);

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
