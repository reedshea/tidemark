#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>
#include <unistd.h>
#include <string.h>

#ifdef PLATFORM_MACOS
#include "SDL.h"
#endif

#include "display/display_layer.h"
#include "display/display_bitmap.h"

#define REFRESH_INTERVAL 300  // Refresh every 5 minutes (300 seconds)

int main(int argc, char* argv[]) {
    // Parse command line arguments
    bool use_simulator = false;
    int force_night = -1;  // -1 = auto, 0 = day, 1 = night
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--sim") == 0) {
            use_simulator = true;
        } else if (strcmp(argv[i], "--night") == 0) {
            force_night = 1;
        } else if (strcmp(argv[i], "--day") == 0) {
            force_night = 0;
        } else if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [options]\n", argv[0]);
            printf("Options:\n");
            printf("  --sim       Use simulator (forced on macOS)\n");
            printf("  --night     Force night mode\n");
            printf("  --day       Force day mode\n");
            printf("  --help      Show this help\n");
            return 0;
        }
    }

    // Initialize display layer
#ifdef PLATFORM_MACOS
    use_simulator = true;
#endif

    printf("Starting display initialization (simulator=%d)...\n", use_simulator);
    
    if (!display_init(use_simulator)) {
        printf("Failed to initialize display\n");
        return 1;
    }

    printf("Display initialized successfully\n");
    printf("Display dimensions: %d x %d\n", DISPLAY_WIDTH, DISPLAY_HEIGHT);
    
#ifndef PLATFORM_MACOS
    // For Raspberry Pi, check GPIO access - needed by bcm2835 for IT8951 display
    printf("Running on Raspberry Pi, checking if we have GPIO access...\n");
    if (geteuid() != 0) {
        printf("Warning: Not running as root. GPIO access may be restricted.\n");
        printf("Try running with sudo for proper hardware access.\n");
    }
#endif

    // Main loop
    time_t last_update = 0;
    bool running = true;
    
    while (running) {
        time_t current_time = time(NULL);
        
        // Update display if needed
        if (current_time - last_update >= REFRESH_INTERVAL) {
            printf("Refreshing tide chart at %s", ctime(&current_time));
            
            // Generate and display the tide chart
            if (!display_tide_chart(force_night)) {
                printf("Failed to display tide chart\n");
            }
            
            last_update = current_time;
        }
        
#ifdef PLATFORM_MACOS
        // Handle SDL events
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            }
        }
        
        // Small delay to prevent CPU hogging
        SDL_Delay(100);
#else
        // On Raspberry Pi, just do one update and exit if not in daemon mode
        // This allows running from cron or systemd timer
        if (getenv("TIDEMARK_DAEMON") == NULL) {
            running = false;
        } else {
            // In daemon mode, sleep for a bit to avoid CPU usage
            sleep(10); 
        }
#endif
    }

    display_cleanup();
    return 0;
}