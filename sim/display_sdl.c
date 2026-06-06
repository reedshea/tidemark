#include "SDL.h"
#include "SDL_ttf.h"
#include "c/display/display_layer.h"
#include <string.h>
#include <stdlib.h>

#define WINDOW_TITLE "Grayscale E-Ink Display Simulator"

static SDL_Window* window = NULL;
static SDL_Renderer* renderer = NULL;
static SDL_Texture* texture = NULL;
static TTF_Font* font = NULL;
static uint8_t* framebuffer = NULL;
static uint32_t* texture_buffer = NULL;

// Convert 8-bit grayscale to SDL color
static SDL_Color get_sdl_color(uint8_t gray) {
    return (SDL_Color){gray, gray, gray, 255};
}

// Convert grayscale framebuffer to RGBA texture buffer
static void update_texture_buffer(void) {
    for (int i = 0; i < DISPLAY_WIDTH * DISPLAY_HEIGHT; i++) {
        uint8_t gray = framebuffer[i];
        
        // Using direct bit shifting approach for grayscale
        // This creates RGBA with identical R, G, B values (true grayscale)
        texture_buffer[i] = (gray << 24) | (gray << 16) | (gray << 8) | 0xFF;
    }
}

static bool sdl_init(DisplayConfig* config) {
    printf("Initializing SDL display simulator...\n");
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return false;
    }
    printf("SDL initialized successfully\n");

    if (TTF_Init() < 0) {
        printf("TTF initialization failed: %s\n", TTF_GetError());
        SDL_Quit();
        return false;
    }

    // Set display dimensions from constants
    config->width = DISPLAY_WIDTH;
    config->height = DISPLAY_HEIGHT;

    // Create a scaled window (e-ink display is quite large)
    int scale = 2;  // Scale down by 2 for better fit on desktop
    int window_width = DISPLAY_WIDTH / scale;
    int window_height = DISPLAY_HEIGHT / scale;
    
    window = SDL_CreateWindow(WINDOW_TITLE,
                            SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                            window_width, window_height,
                            SDL_WINDOW_SHOWN);
    if (!window) {
        printf("Window could not be created! SDL_Error: %s\n", SDL_GetError());
        TTF_Quit();
        SDL_Quit();
        return false;
    }

    // The window is shown at half the panel resolution (see scale above), so the
    // full-res texture is downscaled. Default SDL scaling is nearest-neighbor,
    // which drops every other pixel and turns anti-aliased text/lines coarse and
    // jagged. Linear filtering downsamples smoothly so the preview matches the
    // quality the e-ink panel gets from the same full-res bitmap.
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "linear");

    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (!renderer) {
        printf("Renderer could not be created! SDL_Error: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return false;
    }
    
    // IMPORTANT: Force grayscale rendering for e-ink display simulation
    // Use pure white (255,255,255) for background to simulate e-ink
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);

    // Create a texture with standard RGBA format - we'll explicitly handle grayscale conversion
    texture = SDL_CreateTexture(renderer,
                              SDL_PIXELFORMAT_RGBA8888,
                              SDL_TEXTUREACCESS_STREAMING,
                              DISPLAY_WIDTH, DISPLAY_HEIGHT);
    if (!texture) {
        printf("Texture could not be created! SDL_Error: %s\n", SDL_GetError());
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return false;
    }
    
    // Important: Make sure the texture blending mode is set to NONE for proper grayscale rendering
    SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_NONE);

    // Load a font for draw_text(). The tide display is a pre-rendered BMP and
    // doesn't use draw_text, so a missing font is only a warning (keeps the
    // simulator runnable on Linux/CI, not just macOS).
    const char* font_paths[] = {
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    };
    for (size_t i = 0; i < sizeof(font_paths) / sizeof(font_paths[0]); i++) {
        font = TTF_OpenFont(font_paths[i], 40);
        if (font) break;
    }
    if (!font) {
        printf("Warning: no font found; draw_text() disabled (chart still renders)\n");
    }

    // Allocate framebuffer
    framebuffer = (uint8_t*)calloc(DISPLAY_WIDTH * DISPLAY_HEIGHT, sizeof(uint8_t));
    texture_buffer = (uint32_t*)calloc(DISPLAY_WIDTH * DISPLAY_HEIGHT, sizeof(uint32_t));
    if (!framebuffer || !texture_buffer) {
        printf("Failed to allocate buffers\n");
        if (framebuffer) free(framebuffer);
        if (texture_buffer) free(texture_buffer);
        TTF_CloseFont(font);
        SDL_DestroyTexture(texture);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return false;
    }

    config->framebuffer = framebuffer;
    return true;
}

static void sdl_cleanup(void) {
    if (texture_buffer) free(texture_buffer);
    if (framebuffer) free(framebuffer);
    if (font) TTF_CloseFont(font);
    if (texture) SDL_DestroyTexture(texture);
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();
}

static void sdl_update(void) {
    // Update our texture buffer first
    update_texture_buffer();
    
    // Force the texture blend mode to NONE before updating
    SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_NONE);
    
    // Update the texture with our grayscale data
    SDL_UpdateTexture(texture, NULL, texture_buffer, DISPLAY_WIDTH * sizeof(uint32_t));
    
    // IMPORTANT: Enforce absolute grayscale rendering
    // Clear with pure white background (simulating e-ink)
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
    SDL_RenderClear(renderer);
    
    // Copy the texture to the renderer
    SDL_RenderCopy(renderer, texture, NULL, NULL);
    
    // Present the renderer
    SDL_RenderPresent(renderer);
    
    // Handle SDL events to keep window responsive
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_QUIT) {
            exit(0);  // Clean exit if window is closed
        }
    }
}

static void sdl_draw_text(uint16_t x, uint16_t y, const char* text, uint8_t color, uint8_t bg_color) {
    if (!font) return;  // no font loaded; draw_text is a no-op
    SDL_Color fg = get_sdl_color(color);
    SDL_Color bg = get_sdl_color(bg_color);
    
    SDL_Surface* surface = TTF_RenderText_Shaded(font, text, fg, bg);
    if (!surface) return;

    // Create a new surface in the correct format (8-bit grayscale)
    SDL_Surface* gray_surface = SDL_CreateRGBSurface(0, surface->w, surface->h, 8, 0, 0, 0, 0);
    if (!gray_surface) {
        SDL_FreeSurface(surface);
        return;
    }
    
    // Set up a grayscale palette
    SDL_Color palette[256];
    for (int i = 0; i < 256; i++) {
        palette[i].r = i;
        palette[i].g = i;
        palette[i].b = i;
        palette[i].a = 255;
    }
    SDL_SetPaletteColors(gray_surface->format->palette, palette, 0, 256);
    
    // Convert from RGB to grayscale
    SDL_LockSurface(surface);
    SDL_LockSurface(gray_surface);
    
    uint32_t* src_pixels = (uint32_t*)surface->pixels;
    uint8_t* dst_pixels = (uint8_t*)gray_surface->pixels;
    
    for (int i = 0; i < surface->h; i++) {
        for (int j = 0; j < surface->w; j++) {
            int src_idx = i * (surface->pitch / 4) + j;
            int dst_idx = i * gray_surface->pitch + j;
            
            SDL_Color pixel;
            SDL_GetRGBA(src_pixels[src_idx], surface->format, &pixel.r, &pixel.g, &pixel.b, &pixel.a);
            
            // Simple grayscale conversion (average of RGB)
            dst_pixels[dst_idx] = (pixel.r + pixel.g + pixel.b) / 3;
        }
    }
    
    SDL_UnlockSurface(gray_surface);
    SDL_UnlockSurface(surface);
    
    // Copy gray_surface pixels to framebuffer
    for (int dy = 0; dy < gray_surface->h; dy++) {
        for (int dx = 0; dx < gray_surface->w; dx++) {
            // Make sure we don't wrap around to the next line by checking x position is valid
            if ((x + dx) < DISPLAY_WIDTH && (y + dy) < DISPLAY_HEIGHT) {
                int fb_pos = (y + dy) * DISPLAY_WIDTH + (x + dx);
                framebuffer[fb_pos] = ((uint8_t*)gray_surface->pixels)[dy * gray_surface->pitch + dx];
            }
        }
    }
    
    SDL_FreeSurface(gray_surface);
    SDL_FreeSurface(surface);
}

static uint8_t* sdl_get_framebuffer(void) {
    return framebuffer;
}

// Load a BMP and blit it into the framebuffer. The simulator has no ghosting,
// so the refresh mode and partial rectangle are ignored — every present is a
// full repaint.
static bool sdl_present(const char* path, RefreshMode mode,
                        int rx, int ry, int rw, int rh) {
    (void)mode; (void)rx; (void)ry; (void)rw; (void)rh;

    SDL_Surface* bitmap = SDL_LoadBMP(path);
    if (!bitmap) {
        printf("Error loading bitmap: %s\n", SDL_GetError());
        return false;
    }
    if (bitmap->w != DISPLAY_WIDTH || bitmap->h != DISPLAY_HEIGHT) {
        printf("Warning: Bitmap dimensions (%d x %d) don't match display (%d x %d)\n",
               bitmap->w, bitmap->h, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    }

    SDL_LockSurface(bitmap);
    uint8_t* src = (uint8_t*)bitmap->pixels;
    int bpp = bitmap->format->BytesPerPixel;
    for (int y = 0; y < DISPLAY_HEIGHT && y < bitmap->h; y++) {
        for (int x = 0; x < DISPLAY_WIDTH && x < bitmap->w; x++) {
            int src_pos = y * bitmap->pitch + x * bpp;
            int dst_pos = y * DISPLAY_WIDTH + x;
            uint8_t gray;
            if (bpp == 1) {
                gray = src[src_pos];
            } else if (bpp == 3 || bpp == 4) {
                uint8_t r = src[src_pos], g = src[src_pos + 1], b = src[src_pos + 2];
                gray = (uint8_t)(0.299 * r + 0.587 * g + 0.114 * b);
            } else {
                gray = DISPLAY_WHITE;
            }
            framebuffer[dst_pos] = gray;
        }
    }
    SDL_UnlockSurface(bitmap);
    SDL_FreeSurface(bitmap);

    sdl_update();
    return true;
}

// Create and return the SDL display interface
DisplayInterface sdl_interface = {
    .init = sdl_init,
    .cleanup = sdl_cleanup,
    .update = sdl_update,
    .draw_text = sdl_draw_text,
    .get_framebuffer = sdl_get_framebuffer,
    .present = sdl_present
};
