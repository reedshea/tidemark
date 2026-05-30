CC = gcc
COMMON_FLAGS = -Wall -Wextra -I../src -I../lib/IT8951

# Source files
SRCS = ../src/c/main.c ../src/c/display/display_layer.c ../src/c/display/display_bitmap.c

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
    PLATFORM_SRCS = ../sim/display_sdl.c
    BIN = tidemark_sim
else
    PLATFORM_CFLAGS = -DPLATFORM_LINUX
    PLATFORM_LDFLAGS = -L/usr/local/lib -lbcm2835
    PLATFORM_SRCS = ../src/c/display/display_eink.c ../lib/IT8951/IT8951.c ../lib/IT8951/miniGUI.c ../lib/IT8951/AsciiLib.c
    BIN = tidemark
endif

# All source files
ALL_SRCS = $(SRCS) $(PLATFORM_SRCS)

# Object files
OBJS = $(notdir $(ALL_SRCS:.c=.o))

# Default target
all: $(BIN)

# Build target
$(BIN): $(OBJS)
	$(CC) $(COMMON_FLAGS) $^ -o $@ $(PLATFORM_LDFLAGS)

# Compile rules for files in subdirectories
%.o: ../src/c/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../src/c/display/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../sim/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

%.o: ../lib/IT8951/%.c
	$(CC) $(COMMON_FLAGS) $(PLATFORM_CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -f tidemark tidemark_sim *.o

# Run target
run: $(BIN)
	./$(BIN)

# Generate Python virtual environment (Pillow is the only runtime dependency)
venv:
	cd .. && python3 -m venv venv && \
	. venv/bin/activate && \
	pip3 install pillow

.PHONY: all clean run venv