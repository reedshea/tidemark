CC = gcc
COMMON_FLAGS = -Wall -Wextra -I../src -I../lib/IT8951  # Adjusted paths from /build/

# Source files - original version
ORIGINAL_COMMON_SRCS = ../src/graph.c ../src/display/display_layer.c ../src/sky_display.c ../src/sky_layer.c ../src/main.c  # Adjusted paths

# Source files - bitmap version
BITMAP_COMMON_SRCS = ../src/display/display_layer.c ../src/display/display_bitmap.c ../src/bitmap_main.c

# Platform detection - auto-detect macOS if not specified
ifndef PLATFORM
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        PLATFORM = macos
    endif
endif

# Platform-specific settings
ifeq ($(PLATFORM),macos)
    PLATFORM_CFLAGS = -I/opt/homebrew/include/SDL2 -DPLATFORM_MACOS
    PLATFORM_LDFLAGS = -L/opt/homebrew/lib -lSDL2 -lSDL2_ttf
    PLATFORM_SRCS = ../sim/display_sdl.c  # Adjusted path
    BIN = tidemark_sim
    BITMAP_BIN = tidemark_bitmap
else
    PLATFORM_CFLAGS = -DPLATFORM_LINUX
    PLATFORM_LDFLAGS = -L/usr/local/lib -lbcm2835
    PLATFORM_SRCS = ../src/display/display_eink.c ../lib/IT8951/IT8951.c ../lib/IT8951/miniGUI.c ../lib/IT8951/AsciiLib.c
    BIN = tidemark
    BITMAP_BIN = tidemark_bitmap
endif

# Choose which version to build (original or bitmap)
BUILD_BITMAP ?= 1

ifeq ($(BUILD_BITMAP),1)
    SRCS = $(BITMAP_COMMON_SRCS) $(PLATFORM_SRCS)
    TARGET = $(BITMAP_BIN)
else
    SRCS = $(ORIGINAL_COMMON_SRCS) $(PLATFORM_SRCS)
    TARGET = $(BIN)
endif

# Object files
OBJS = $(notdir $(SRCS:.c=.o))

# Default target
all: $(TARGET)

# Build targets
$(BIN): $(OBJS)
	$(CC) $(COMMON_FLAGS) $^ -o $@ $(PLATFORM_LDFLAGS)

$(BITMAP_BIN): $(OBJS)
	$(CC) $(COMMON_FLAGS) $^ -o $@ $(PLATFORM_LDFLAGS)

# Compile rules for files in subdirectories
%.o: ../src/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../src/display/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../sim/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../lib/IT8951/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -f tidemark tidemark_sim tidemark_bitmap *.o

# Targets to explicitly build each version
original:
	$(MAKE) BUILD_BITMAP=0

bitmap:
	$(MAKE) BUILD_BITMAP=1

.PHONY: all clean original bitmap