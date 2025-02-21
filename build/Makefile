CC = gcc
COMMON_FLAGS = -Wall -Wextra -I../src -I../lib/IT8951  # Adjusted paths from /build/

# Source files
COMMON_SRCS = ../src/graph.c ../src/display/display_layer.c ../src/main.c  # Adjusted paths

# Platform-specific settings
ifeq ($(PLATFORM),macos)
    PLATFORM_FLAGS = -I/opt/homebrew/include/SDL2 -L/opt/homebrew/lib -lSDL2 -lSDL2_ttf -DPLATFORM_MACOS
    PLATFORM_SRCS = ../sim/display_sdl.c  # Adjusted path
    BIN = tidemark_sim
else
    PLATFORM_FLAGS = -DPLATFORM_LINUX -L/usr/local/lib -lbcm2835
    PLATFORM_SRCS = ../lib/IT8951/IT8951.c ../lib/IT8951/miniGUI.c ../lib/IT8951/AsciiLib.c
    BIN = tidemark
endif

# All source files
SRCS = $(COMMON_SRCS) $(PLATFORM_SRCS)

# Object files
OBJS = $(SRCS:.c=.o)

# Default target
all: $(BIN)

# Build target
$(BIN): $(OBJS)
	$(CC) $(COMMON_FLAGS) $^ -o $@ $(PLATFORM_FLAGS)

# Compile rule
%.o: %.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_FLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -f tidemark tidemark_sim $(wildcard ../src/*.o) $(wildcard ../lib/IT8951/*.o)  # Adjusted paths

.PHONY: all clean