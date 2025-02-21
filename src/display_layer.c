#include "display_layer.h"
#include <stdio.h>
#include <string.h>

#ifdef PLATFORM_LINUX
#include "IT8951.h"
#include "miniGUI.h"

// Global variables from IT8951 library
extern IT8951DevInfo gstI80DevInfo;
extern uint8_t* gpFrameBuf;

// Function declarations
void IT8951WaitForDisplayReady(void);
void IT8951HostAreaPackedPixelWrite(IT8951LdImgInfo* pstLdImgInfo, IT8951AreaImgInfo* pstAreaImgInfo);
void IT8951DisplayArea(uint16_t usX, uint16_t usY, uint16_t usW, uint16_t usH, uint16_t usDpyMode);

#else
// Forward declaration of the SDL interface (defined in display_sdl.c)
extern DisplayInterface sdl_interface;
#endif

// The active display interface and config (used by both platforms)
static DisplayInterface* active_interface = NULL;
static DisplayConfig display_config;

#ifdef PLATFORM_LINUX
// E-ink display interface implementation
static bool eink_init(DisplayConfig* config) {
    if (IT8951_Init()) {
        return false;
    }
    config->width = gstI80DevInfo.usPanelW;
    config->height = gstI80DevInfo.usPanelH;
    config->framebuffer = gpFrameBuf;
    
    // Clear our framebuffer to white
    memset(gpFrameBuf, 0xFF, gstI80DevInfo.usPanelW * gstI80DevInfo.usPanelH);
    
    // Do a full display update to clear the screen
    IT8951LdImgInfo stLdImgInfo;
    IT8951AreaImgInfo stAreaImgInfo;
    
    stLdImgInfo.usEndianType = IT8951_LDIMG_L_ENDIAN;
    stLdImgInfo.usPixelFormat = IT8951_8BPP;
    stLdImgInfo.usRotate = IT8951_ROTATE_0;
    stLdImgInfo.ulStartFBAddr = (uint32_t)gpFrameBuf;
    stLdImgInfo.ulImgBufBaseAddr = (gstI80DevInfo.usImgBufAddrH << 16) | gstI80DevInfo.usImgBufAddrL;
    
    stAreaImgInfo.usX = 0;
    stAreaImgInfo.usY = 0;
    stAreaImgInfo.usWidth = gstI80DevInfo.usPanelW;
    stAreaImgInfo.usHeight = gstI80DevInfo.usPanelH;
    
    IT8951WaitForDisplayReady();
    IT8951HostAreaPackedPixelWrite(&stLdImgInfo, &stAreaImgInfo);
    IT8951DisplayArea(0, 0, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH, IT8951_MODE_0);
    
    return true;
}

static void eink_cleanup(void) {
    IT8951_Cancel();
}

static void eink_update(void) {
    IT8951LdImgInfo stLdImgInfo;
    IT8951AreaImgInfo stAreaImgInfo;
    
    // Wait for display
    IT8951WaitForDisplayReady();
    
    // Setup load image info
    stLdImgInfo.usEndianType = IT8951_LDIMG_L_ENDIAN;
    stLdImgInfo.usPixelFormat = IT8951_8BPP;  // Use 8-bit mode
    stLdImgInfo.usRotate = IT8951_ROTATE_0;
    stLdImgInfo.ulStartFBAddr = (uint32_t)gpFrameBuf;  // Use framebuffer directly
    stLdImgInfo.ulImgBufBaseAddr = (gstI80DevInfo.usImgBufAddrH << 16) | gstI80DevInfo.usImgBufAddrL;
    
    // Setup area info
    stAreaImgInfo.usX = 0;
    stAreaImgInfo.usY = 0;
    stAreaImgInfo.usWidth = gstI80DevInfo.usPanelW;
    stAreaImgInfo.usHeight = gstI80DevInfo.usPanelH;
    
    // Load image
    IT8951WaitForDisplayReady();
    IT8951HostAreaPackedPixelWrite(&stLdImgInfo, &stAreaImgInfo);
    
    // Display area
    IT8951WaitForDisplayReady();
    IT8951DisplayArea(0, 0, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH, IT8951_MODE_2);
}

static void eink_draw_text(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color) {
    EPD_Text(x, y, (uint8_t*)text, color, bg_color);
}

static uint8_t* eink_get_framebuffer(void) {
    if (!gpFrameBuf) {
        return NULL;
    }
    return gpFrameBuf;
}

// E-ink display interface
static DisplayInterface eink_interface = {
    .init = eink_init,
    .cleanup = eink_cleanup,
    .update = eink_update,
    .draw_text = eink_draw_text,
    .get_framebuffer = eink_get_framebuffer
};
#endif

DisplayInterface* get_display_interface(bool use_simulator) {
#ifdef PLATFORM_LINUX
    (void)use_simulator; // Unused on Linux
    return &eink_interface;
#else
    return &sdl_interface;
#endif
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
