#include "display_layer.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifndef PLATFORM_MACOS
#include <bcm2835.h>
#include "../../lib/IT8951/IT8951.h"
#include "../../lib/IT8951/miniGUI.h"

// External variables from IT8951 library
extern IT8951DevInfo gstI80DevInfo;
extern uint8_t* gpFrameBuf;
extern uint32_t gulImgBufAddr;

// Function declarations from IT8951 library
void IT8951WaitForDisplayReady(void);
void IT8951HostAreaPackedPixelWrite(IT8951LdImgInfo* pstLdImgInfo, IT8951AreaImgInfo* pstAreaImgInfo);
void IT8951DisplayArea(uint16_t usX, uint16_t usY, uint16_t usW, uint16_t usH, uint16_t usDpyMode);
#endif

static uint8_t* framebuffer = NULL;
static bool display_initialized = false;

static bool eink_init(DisplayConfig* config) {
#ifndef PLATFORM_MACOS
    if (IT8951_Init()) {
        printf("IT8951_Init error\n");
        return false;
    }
    
    // Set dimensions
    config->width = DISPLAY_WIDTH;
    config->height = DISPLAY_HEIGHT;
    
    // Allocate framebuffer - use 8BPP (grayscale)
    framebuffer = (uint8_t*)calloc(DISPLAY_WIDTH * DISPLAY_HEIGHT, sizeof(uint8_t));
    if (!framebuffer) {
        printf("Failed to allocate framebuffer\n");
        return false;
    }
    
    // Clear to white
    memset(framebuffer, DISPLAY_WHITE, DISPLAY_WIDTH * DISPLAY_HEIGHT);
    
    config->framebuffer = framebuffer;
    display_initialized = true;
    return true;
#else
    // Should never be called on macOS
    (void)config;
    return false;
#endif
}

static void eink_cleanup(void) {
#ifndef PLATFORM_MACOS
    if (framebuffer) {
        free(framebuffer);
        framebuffer = NULL;
    }
    
    // Cancel/cleanup the IT8951
    IT8951_Cancel();
#endif
}

static void eink_update(void) {
#ifndef PLATFORM_MACOS
    if (!display_initialized || !framebuffer) {
        return;
    }
    
    // Wait for display to be ready
    IT8951WaitForDisplayReady();
    
    // Set up loading parameters
    IT8951LdImgInfo stLdImgInfo;
    IT8951AreaImgInfo stAreaImgInfo;
    
    // Configure image loading info
    stLdImgInfo.ulStartFBAddr    = (uint32_t)framebuffer;
    stLdImgInfo.usEndianType     = IT8951_LDIMG_L_ENDIAN;
    stLdImgInfo.usPixelFormat    = IT8951_8BPP;
    stLdImgInfo.usRotate         = IT8951_ROTATE_0;
    stLdImgInfo.ulImgBufBaseAddr = gulImgBufAddr;
    
    // Note: For the 7.8inch display (1872x1404), we must ensure we're using the correct display dimensions
    
    // Set area to update (full screen)
    stAreaImgInfo.usX      = 0;
    stAreaImgInfo.usY      = 0;
    stAreaImgInfo.usWidth  = DISPLAY_WIDTH;
    stAreaImgInfo.usHeight = DISPLAY_HEIGHT;
    
    // Transfer framebuffer to IT8951
    IT8951HostAreaPackedPixelWrite(&stLdImgInfo, &stAreaImgInfo);
    
    // Update display - using mode 2 for fast refresh, can be adjusted as needed
    IT8951DisplayArea(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, 2);
#endif
}

static void eink_draw_text(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color) {
#ifndef PLATFORM_MACOS
    if (!display_initialized || !framebuffer) {
        return;
    }
    
    // Use the miniGUI library's text drawing function
    // This writes directly to the framebuffer
    EPD_Text(x, y, (uint8_t*)text, color, bg_color);
#else
    // Should never be called on macOS
    (void)x;
    (void)y;
    (void)text;
    (void)color;
    (void)bg_color;
#endif
}

static uint8_t* eink_get_framebuffer(void) {
    return framebuffer;
}

// Create and return the E-Ink display interface
DisplayInterface eink_interface = {
    .init = eink_init,
    .cleanup = eink_cleanup,
    .update = eink_update,
    .draw_text = eink_draw_text,
    .get_framebuffer = eink_get_framebuffer
};