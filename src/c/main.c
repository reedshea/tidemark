#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>
#include <unistd.h>
#include <string.h>

#ifndef PLATFORM_MACOS
#include <sys/file.h>
#include <fcntl.h>
#include <errno.h>
#endif

#ifdef PLATFORM_MACOS
#include "SDL.h"
#endif

#include "display/display_layer.h"
#include "display/display_bitmap.h"

#define REFRESH_INTERVAL 300  // Refresh every 5 minutes (300 seconds)

int main(int argc, char* argv[]) {
    // Parse command line arguments
    bool use_simulator = false;
    const char* image_path = NULL;  // if set, display this BMP and exit

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--sim") == 0) {
            use_simulator = true;
        } else if (strcmp(argv[i], "--image") == 0 && i + 1 < argc) {
            image_path = argv[++i];
        } else if (strcmp(argv[i], "--help") == 0) {
            printf("Usage: %s [options]\n", argv[0]);
            printf("Options:\n");
            printf("  --sim          Use simulator (forced on macOS)\n");
            printf("  --image PATH   Display the given BMP and exit\n");
            printf("  --help         Show this help\n");
            return 0;
        }
    }

    // Initialize display layer
#ifdef PLATFORM_MACOS
    use_simulator = true;
#endif

#ifndef PLATFORM_MACOS
    // SPI bus guard: only one tidemark may drive the IT8951 at a time. Two
    // concurrent processes (e.g. a manual run racing the systemd timer, or a
    // deploy baseline overlapping a timer fire) collide mid-transfer and leave a
    // corrupted, half-written frame. Take an exclusive, non-blocking lock held
    // for our whole lifetime (released automatically on exit). If another
    // instance already holds it, skip this run rather than collide — the next
    // timer fire will refresh the panel.
    int lock_fd = open("/run/tidemark.lock", O_RDWR | O_CREAT, 0644);
    if (lock_fd < 0) lock_fd = open("/tmp/tidemark.lock", O_RDWR | O_CREAT, 0644);
    if (lock_fd >= 0) {
        if (flock(lock_fd, LOCK_EX | LOCK_NB) != 0) {
            printf("Another tidemark holds the display lock; skipping this run "
                   "to avoid an SPI collision.\n");
            close(lock_fd);
            return 0;
        }
    } else {
        printf("Warning: could not open display lock (%s); proceeding without "
               "the SPI guard.\n", strerror(errno));
    }
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

    // One-shot: display a specific image (style/weather experiments).
    if (image_path != NULL) {
        printf("Displaying image: %s\n", image_path);
        bool ok = display_bitmap(image_path);
#ifdef PLATFORM_MACOS
        // Keep the simulator window open until closed, so the image can be
        // inspected (on the real panel this path just returns).
        if (ok) {
            SDL_Event event;
            bool open = true;
            while (open) {
                while (SDL_PollEvent(&event)) {
                    if (event.type == SDL_QUIT) open = false;
                }
                SDL_Delay(16);
            }
        }
#endif
        display_cleanup();
        return ok ? 0 : 1;
    }

    // Main loop
    time_t last_update = 0;
    bool running = true;
    
    while (running) {
        time_t current_time = time(NULL);
        
        // Update display if needed
        if (current_time - last_update >= REFRESH_INTERVAL) {
            printf("Refreshing tide chart at %s", ctime(&current_time));
            
            // Generate and display the tide chart
            if (!display_tide_chart()) {
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