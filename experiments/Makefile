CC=gcc
CFLAGS=-I../lib/IT8951 -Wall
LDFLAGS=-L/usr/local/lib -lbcm2835

DEPS = ../lib/IT8951/IT8951.h ../lib/IT8951/miniGUI.h ../lib/IT8951/AsciiLib.h
OBJ = draw_circle.o ../lib/IT8951/IT8951.o ../lib/IT8951/miniGUI.o ../lib/IT8951/AsciiLib.o

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

draw_circle: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) $(LDFLAGS)

.PHONY: clean

clean:
	rm -f *.o draw_circle
