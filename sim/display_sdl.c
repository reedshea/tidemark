#include "SDL.h"
#include "SDL_ttf.h"
#include "display/display_layer.h"
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
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return false;
    }

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

    // Load font at larger size for better readability
    font = TTF_OpenFont("/System/Library/Fonts/Supplemental/Arial.ttf", 40);
    if (!font) {
        printf("Failed to load font: %s\n", TTF_GetError());
        SDL_DestroyTexture(texture);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        TTF_Quit();
        SDL_Quit();
        return false;
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

// Create and return the SDL display interface
DisplayInterface sdl_interface = {
    .init = sdl_init,
    .cleanup = sdl_cleanup,
    .update = sdl_update,
    .draw_text = sdl_draw_text,
    .get_framebuffer = sdl_get_framebuffer
};
