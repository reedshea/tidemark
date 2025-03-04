#include "display_layer.h"
#include <stdio.h>
#include <string.h>

#ifdef PLATFORM_MACOS
// Forward declaration of the SDL interface (defined in display_sdl.c)
extern DisplayInterface sdl_interface;
#else
// Forward declaration of the e-ink interface (defined in display_eink.c)
extern DisplayInterface eink_interface;
#endif

// The active display interface and config (used by both platforms)
static DisplayInterface* active_interface = NULL;
static DisplayConfig display_config;

DisplayInterface* get_display_interface(bool use_simulator) {
    if (use_simulator) {
#ifdef PLATFORM_MACOS
        return &sdl_interface;
#else
        printf("Simulator requested but not available on this platform\n");
        return &eink_interface;
#endif
    } else {
#ifdef PLATFORM_MACOS
        printf("E-ink display not available on macOS, using simulator\n");
        return &sdl_interface;
#else
        return &eink_interface;
#endif
    }
}

bool display_init(bool use_simulator) {
    active_interface = get_display_interface(use_simulator);
    return active_interface->init(&display_config);
}

void display_cleanup(void) {
    if (active_interface) {
        active_interface->cleanup();
    }
}

uint8_t* display_get_framebuffer(void) {
    return active_interface ? active_interface->get_framebuffer() : NULL;
}

void display_update(void) {
    if (active_interface) {
        active_interface->update();
    }
}

void display_draw_text(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color)
{
    printf("Drawing text '%s' at (%d,%d)\n", text, x, y);
    if (active_interface && active_interface->draw_text) {
        active_interface->draw_text(x, y, text, color, bg_color);
    }
}
