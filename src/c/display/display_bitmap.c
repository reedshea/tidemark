#include "display_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

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
    IT8951_BMP_Example(0, 0, (char*)file_path);
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
    char command[512];
    char python_path[256];
    
    // Try to use the virtual environment's Python if it exists
    snprintf(python_path, sizeof(python_path), "%s/venv/bin/python", getenv("PWD"));
    if (access(python_path, F_OK | X_OK) != 0) {
        // Fallback to system Python
        strcpy(python_path, "python3");
    }
    
    // Get the correct project root directory by going up one level from PWD
    // This is because we're running from the 'build' directory
    char project_dir[256];
    strncpy(project_dir, getenv("PWD"), sizeof(project_dir));
    char *last_slash = strrchr(project_dir, '/');
    if (last_slash != NULL && strcmp(last_slash, "/build") == 0) {
        *last_slash = '\0';  // Cut off the /build part to get parent directory
    }
    
    if (force_night == 1) {
        // Force night mode
        snprintf(command, sizeof(command), 
                "%s %s/src/python/main.py --night --output %s", 
                python_path, project_dir, bitmap_path);
    } else if (force_night == 0) {
        // Force day mode
        snprintf(command, sizeof(command), 
                "%s %s/src/python/main.py --day --output %s", 
                python_path, project_dir, bitmap_path);
    } else {
        // Auto mode based on current time
        snprintf(command, sizeof(command), 
                "%s %s/src/python/main.py --output %s", 
                python_path, project_dir, bitmap_path);
    }
    
    printf("Generating tide chart with command: %s\n", command);
    
    // Run the Python script
    int result = system(command);
    if (result != 0) {
        printf("Error generating tide chart image\n");
        return false;
    }
    
    printf("About to display bitmap at %s\n", bitmap_path);
    
    // Display the generated bitmap
    bool display_result = display_bitmap(bitmap_path);
    printf("display_bitmap() returned: %d\n", display_result);
    return display_result;
}