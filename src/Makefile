CC=gcc
CFLAGS=-I../lib/IT8951 -Wall -DPLATFORM_LINUX
LDFLAGS=-L/usr/local/lib -lbcm2835
DEPS=graph.h tide_data.h display_layer.h
OBJ=main.o graph.o display_layer.o ../lib/IT8951/IT8951.o ../lib/IT8951/miniGUI.o ../lib/IT8951/AsciiLib.o

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

tidemark: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) $(LDFLAGS)

.PHONY: clean

clean:
	rm -f *.o tidemark
