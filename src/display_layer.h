#ifndef DISPLAY_LAYER_H
#define DISPLAY_LAYER_H

#include <stdint.h>
#include <stdbool.h>

// Platform detection
#ifndef PLATFORM_LINUX
#if defined(__APPLE__) || defined(__MACH__)
#define PLATFORM_MACOS
#else
#define PLATFORM_LINUX
#endif
#endif

// Display dimensions (matching e-ink display)
#define DISPLAY_WIDTH 1872
#define DISPLAY_HEIGHT 1404

// Display configuration
typedef struct {
    uint16_t width;
    uint16_t height;
    uint8_t* framebuffer;
} DisplayConfig;

// Display interface
typedef struct {
    bool (*init)(DisplayConfig* config);
    void (*cleanup)(void);
    void (*update)(void);
    void (*draw_text)(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color);
    uint8_t* (*get_framebuffer)(void);
} DisplayInterface;

// Get the appropriate display interface
DisplayInterface* get_display_interface(bool use_simulator);

// Initialize the display system
bool display_init(bool use_simulator);

// Cleanup display resources
void display_cleanup(void);

// Get the current framebuffer
uint8_t* display_get_framebuffer(void);

// Update the display with current framebuffer contents
void display_update(void);

// Draw text (compatible with your existing EPD_Text function)
void display_draw_text(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color);

#endif // DISPLAY_LAYER_H
