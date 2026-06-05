#include "display_layer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

/**
 * Choose a refresh strategy for a freshly-rendered BMP and present it.
 *
 * The Python renderer writes a sidecar (.meta) next to the BMP:
 *   line 1: the window-start epoch — a "which clock hour" token;
 *   line 2: "x y w h" of the now-marker strip.
 * The window is anchored to the top of the hour, so within an hour only the
 * now-marker moves: we refresh just that narrow strip (REFRESH_PARTIAL) so any
 * flash stays confined to it. When the hour rolls over the token changes and we
 * do a full crisp repaint (REFRESH_FULL), which is self-cleaning — so ghosting
 * from partial updates can accumulate for at most an hour before it's wiped. A
 * deeper full clean (REFRESH_FULL_DEEP) is forced on the daily 3am pass and when
 * TIDEMARK_FULL_CLEAR is set (deploys). The token is kept in /run (tmpfs), so
 * after a reboot it's gone and the first render is a clean full repaint.
 *
 * This logic is vendor-neutral: how each mode is actually drawn lives in the
 * active display driver's present() (e.g. IT8951 deep-clear + GC16, or an SDL
 * blit). See display_layer.h.
 *
 * @param file_path Path to the BMP file to display
 * @return true if successful, false otherwise
 */
bool display_bitmap(const char* file_path) {
    if (access(file_path, F_OK) != 0) {
        printf("Error: Bitmap file not found: %s\n", file_path);
        return false;
    }

    printf("Loading bitmap file: %s\n", file_path);

    // Derive the .meta sidecar path (same name, .meta extension).
    char meta_path[512];
    snprintf(meta_path, sizeof(meta_path), "%s", file_path);
    char *dot = strrchr(meta_path, '.');
    if (dot) {
        strcpy(dot, ".meta");
    } else {
        strncat(meta_path, ".meta", sizeof(meta_path) - strlen(meta_path) - 1);
    }

    long start_tok = 0;
    int rx = 0, ry = 0, rw = 0, rh = 0;
    int have_meta = 0;
    FILE *mf = fopen(meta_path, "r");
    if (mf) {
        if (fscanf(mf, "%ld", &start_tok) == 1 &&
            fscanf(mf, "%d %d %d %d", &rx, &ry, &rw, &rh) == 4) {
            have_meta = 1;
        }
        fclose(mf);
    }

    const char *state_path = "/run/tidemark.state";
    long prev_tok = 0;
    int have_prev = 0;
    FILE *sf = fopen(state_path, "r");
    if (sf) {
        if (fscanf(sf, "%ld", &prev_tok) == 1) have_prev = 1;
        fclose(sf);
    }

    time_t now_t = time(NULL);
    struct tm *lt = localtime(&now_t);
    int daily = (lt && lt->tm_hour == 3 && lt->tm_min < 5);  // once, at 3am
    int forced = (getenv("TIDEMARK_FULL_CLEAR") != NULL);
    int hour_rolled = !have_meta || !have_prev || start_tok != prev_tok;
    int no_rect = (rw <= 0 || rh <= 0);

    RefreshMode mode;
    if (forced || daily) {
        mode = REFRESH_FULL_DEEP;
    } else if (hour_rolled || no_rect) {
        mode = REFRESH_FULL;
    } else {
        mode = REFRESH_PARTIAL;
    }

    bool ok = display_present(file_path, mode, rx, ry, rw, rh);

    // Remember this hour's token so the next fire can tell if the hour rolled.
    if (ok && have_meta) {
        FILE *wf = fopen(state_path, "w");
        if (wf) {
            fprintf(wf, "%ld\n", start_tok);
            fclose(wf);
        }
    }
    return ok;
}

/**
 * Resolve the project root directory.
 *
 * Uses $TIDEMARK_HOME when set; otherwise falls back to $PWD (stripping a
 * trailing /build so it works when launched from the build directory); finally
 * the current directory.
 */
static const char* project_root(char* buf, size_t n) {
    const char *home = getenv("TIDEMARK_HOME");
    if (home && home[0]) {
        snprintf(buf, n, "%s", home);
        return buf;
    }
    const char *pwd = getenv("PWD");
    if (pwd && pwd[0]) {
        snprintf(buf, n, "%s", pwd);
        char *slash = strrchr(buf, '/');
        if (slash && strcmp(slash, "/build") == 0) {
            *slash = '\0';  // launched from build/: go up to the project root
        }
        return buf;
    }
    snprintf(buf, n, ".");
    return buf;
}

/**
 * Convenience function to generate and display a tide chart.
 *
 * Runs the Python renderer to produce the BMP (+ .meta), then displays it.
 * Set $TIDEMARK_HOME to point at the project root if not launching from it.
 *
 * @return true if successful, false otherwise
 */
bool display_tide_chart(void) {
    const char* bitmap_path = "/tmp/tide_chart.bmp";

    char root[256];
    project_root(root, sizeof(root));
    printf("Using project directory: %s\n", root);

    // Prefer the project virtualenv's Python; fall back to system python3.
    char python_path[320];
    snprintf(python_path, sizeof(python_path), "%s/venv/bin/python", root);
    if (access(python_path, F_OK | X_OK) != 0) {
        snprintf(python_path, sizeof(python_path), "python3");
    }

    char script_path[320];
    snprintf(script_path, sizeof(script_path), "%s/src/python/main.py", root);
    if (access(script_path, F_OK) != 0) {
        printf("ERROR: tide renderer not found at %s\n", script_path);
        printf("Set TIDEMARK_HOME to the project root, or run from it.\n");
        return false;
    }
    printf("Found Python script at: %s\n", script_path);

    char command[1024];
    snprintf(command, sizeof(command), "\"%s\" \"%s\" --output \"%s\"",
             python_path, script_path, bitmap_path);
    printf("Generating tide chart: %s\n", command);

    int result = system(command);
    if (result != 0) {
        printf("Error generating tide chart image, system() returned: %d\n", result);
        return false;
    }
    if (access(bitmap_path, F_OK) != 0) {
        printf("Python ran but the bitmap was not created at: %s\n", bitmap_path);
        return false;
    }

    bool display_result = display_bitmap(bitmap_path);
    printf("display_bitmap() returned: %d\n", display_result);
    return display_result;
}
