#include "display_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#ifdef PLATFORM_MACOS
#include "SDL.h"
#else
// Include IT8951 library - only on Raspberry Pi
// Since the IT8951 library depends on bcm2835, we need conditional compilation
#ifndef PLATFORM_MACOS
#include "../../lib/IT8951/IT8951.h"
#endif
#endif

/**
 * Load and display a bitmap file on the e-ink display
 * 
 * On Raspberry Pi: Uses the IT8951 library's BMP loading function
 * On macOS: Loads the bitmap via SDL and displays in the simulator
 * 
 * @param file_path Path to the BMP file to display
 * @return true if successful, false otherwise
 */
bool display_bitmap(const char* file_path) {
    // Check if file exists
    if (access(file_path, F_OK) != 0) {
        printf("Error: Bitmap file not found: %s\n", file_path);
        return false;
    }
    
    printf("Loading bitmap file: %s\n", file_path);
    
#ifdef PLATFORM_MACOS
    // For macOS simulator, use SDL to load and display the bitmap
    SDL_Surface* bitmap = SDL_LoadBMP(file_path);
    if (!bitmap) {
        printf("Error loading bitmap: %s\n", SDL_GetError());
        return false;
    }
    
    // Get framebuffer from display layer
    uint8_t* framebuffer = display_get_framebuffer();
    if (!framebuffer) {
        printf("Failed to get framebuffer\n");
        SDL_FreeSurface(bitmap);
        return false;
    }
    
    // Check dimensions match
    if (bitmap->w != DISPLAY_WIDTH || bitmap->h != DISPLAY_HEIGHT) {
        printf("Warning: Bitmap dimensions (%d x %d) don't match display (%d x %d)\n",
               bitmap->w, bitmap->h, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    }
    
    // Lock surface for pixel access
    SDL_LockSurface(bitmap);
    
    // Copy bitmap data to framebuffer - convert to grayscale if needed
    uint8_t* src = (uint8_t*)bitmap->pixels;
    int bpp = bitmap->format->BytesPerPixel;
    
    for (int y = 0; y < DISPLAY_HEIGHT && y < bitmap->h; y++) {
        for (int x = 0; x < DISPLAY_WIDTH && x < bitmap->w; x++) {
            int src_pos = y * bitmap->pitch + x * bpp;
            int dst_pos = y * DISPLAY_WIDTH + x;
            
            // Handle different bitmap formats
            uint8_t gray;
            if (bpp == 1) {
                // Already grayscale
                gray = src[src_pos];
            } else if (bpp == 3 || bpp == 4) {
                // RGB(A) to grayscale conversion
                uint8_t r = src[src_pos];
                uint8_t g = src[src_pos + 1];
                uint8_t b = src[src_pos + 2];
                gray = (uint8_t)(0.299*r + 0.587*g + 0.114*b);
            } else {
                // Unknown format, default to white
                gray = DISPLAY_WHITE;
            }
            
            framebuffer[dst_pos] = gray;
        }
    }
    
    SDL_UnlockSurface(bitmap);
    SDL_FreeSurface(bitmap);
    
    // Update display with loaded bitmap
    display_update();
    return true;
    
#else
    // For Raspberry Pi, use the IT8951 library's BMP function
    #ifndef PLATFORM_MACOS
    // Most refreshes are a plain GC16 update (no white flash) — subtle and
    // quick. Once a night (the first run in the 3am hour) do a full INIT-mode
    // clear to reset any ghosting that has accumulated through the day.
    time_t now_t = time(NULL);
    struct tm *lt = localtime(&now_t);
    if (lt && lt->tm_hour == 3 && lt->tm_min < 5) {
        printf("Nightly full INIT-mode refresh to reset ghosting...\n");
        IT8951_Clear_Refresh();
    }

    printf("Displaying bitmap on e-ink (GC16) using IT8951_BMP_Example...\n");
    // IT8951_BMP_Example returns void, so we're just calling it and assuming it works
    IT8951_BMP_Example(0, 0, (char*)file_path);
    printf("Successfully called IT8951_BMP_Example to display bitmap on e-ink display\n");
    #else
    printf("E-ink display not available on macOS. This code should not be reached.\n");
    #endif
    return true;
#endif
}

/**
 * Convenience function to generate and display a tide chart
 * 
 * This runs the Python script to generate the chart, then displays it
 * 
 * @param force_night Force night mode if true, day mode if false, or use current time if -1
 * @return true if successful, false otherwise
 */
bool display_tide_chart(int force_night) {
    // Path for the generated bitmap
    const char* bitmap_path = "/tmp/tide_chart.bmp";
    
    // Build command to run Python script - using venv
    char command[1024];  // Increased buffer size to prevent truncation
    char python_path[256];
    
    // Try to use the virtual environment's Python if it exists
    snprintf(python_path, sizeof(python_path), "%s/venv/bin/python", getenv("PWD") ? getenv("PWD") : ".");
    if (access(python_path, F_OK | X_OK) != 0) {
        // Fallback to system Python
        strcpy(python_path, "python3");
    }
    
    // Get the correct project root directory
    // On the Pi, we're running from /home/reed/tidemark/build
    // But we need to use /home/reed/tidemark as the project root
    char project_dir[256];
    const char *pwd = getenv("PWD");
    
    if (pwd) {
        printf("Current PWD: %s\n", pwd);
        strncpy(project_dir, pwd, sizeof(project_dir) - 1);
        project_dir[sizeof(project_dir) - 1] = '\0';  // Ensure null termination
    } else {
        strcpy(project_dir, ".");
    }
    
    // Go up one level from the build directory (if we're in it)
    char *last_slash = strrchr(project_dir, '/');
    if (last_slash != NULL && strcmp(last_slash, "/build") == 0) {
        printf("Detected we're in build directory, going up one level\n");
        *last_slash = '\0';  // Cut off the /build part to get parent directory
    }
    
    printf("Using project directory: %s\n", project_dir);
    
    // Create a full path to the Python script - try both direct and parent directory
    char script_path[512] = {0};
    
    // First try the path with the parent directory
    snprintf(script_path, sizeof(script_path), "%s/../src/python/main.py", project_dir);
    if (access(script_path, F_OK) == 0) {
        printf("Found Python script at: %s\n", script_path);
    } else {
        // Try directly with the project directory
        snprintf(script_path, sizeof(script_path), "%s/src/python/main.py", project_dir);
        if (access(script_path, F_OK) == 0) {
            printf("Found Python script at: %s\n", script_path);
        } else {
            // Try an absolute path
            snprintf(script_path, sizeof(script_path), "/home/reed/tidemark/src/python/main.py");
            if (access(script_path, F_OK) == 0) {
                printf("Found Python script at: %s\n", script_path);
            } else {
                printf("ERROR: Could not find Python script at any expected location\n");
                return false;
            }
        }
    }
    
    if (force_night == 1) {
        // Force night mode
        snprintf(command, sizeof(command), 
                "%s %s --night --output %s", 
                python_path, script_path, bitmap_path);
    } else if (force_night == 0) {
        // Force day mode
        snprintf(command, sizeof(command), 
                "%s %s --day --output %s", 
                python_path, script_path, bitmap_path);
    } else {
        // Auto mode based on current time
        snprintf(command, sizeof(command), 
                "%s %s --output %s", 
                python_path, script_path, bitmap_path);
    }
    
    printf("Generating tide chart with command: %s\n", command);
    
    // Run the Python script
    printf("Executing Python command: %s\n", command);
    int result = system(command);
    if (result != 0) {
        printf("Error generating tide chart image, system() returned: %d\n", result);
        return false;
    }
    
    // Check if the file was actually created
    if (access(bitmap_path, F_OK) != 0) {
        printf("Python script ran successfully but bitmap file was not created at: %s\n", bitmap_path);
        return false;
    }
    
    printf("Bitmap file successfully created at: %s\n", bitmap_path);
    
    // Display the generated bitmap
    bool display_result = display_bitmap(bitmap_path);
    printf("display_bitmap() returned: %d\n", display_result);
    return display_result;
}