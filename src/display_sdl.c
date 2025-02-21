#include "SDL.h"
#include "SDL_ttf.h"
#include "display_layer.h"
#include <string.h>
#include <stdlib.h>

#define WINDOW_TITLE "E-Ink Display Simulator"

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

    // Load font at moderate size (not too big, not too small)
    font = TTF_OpenFont("/System/Library/Fonts/Supplemental/Arial.ttf", 20);
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
    update_texture_buffer();
    SDL_UpdateTexture(texture, NULL, texture_buffer, DISPLAY_WIDTH * sizeof(uint32_t));
    SDL_RenderClear(renderer);
    SDL_RenderCopy(renderer, texture, NULL, NULL);
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

    // Copy text pixels to framebuffer
    uint8_t* src = (uint8_t*)surface->pixels;
    for (int dy = 0; dy < surface->h; dy++) {
        for (int dx = 0; dx < surface->w; dx++) {
            int fb_pos = (y + dy) * DISPLAY_WIDTH + (x + dx);
            if (fb_pos < DISPLAY_WIDTH * DISPLAY_HEIGHT) {
                framebuffer[fb_pos] = src[dy * surface->pitch + dx];
            }
        }
    }
    
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
