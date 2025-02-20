#ifndef TIDE_DATA_H
#define TIDE_DATA_H

#include <stdint.h>

typedef struct {
    int year;
    int month;
    int day;
    int hour;
    int minute;
    float height;
    char type;  // 'H' for high, 'L' for low
} TidePoint;

// Static tide data for initial development
static const TidePoint SAMPLE_TIDE_DATA[] = {
    {2025, 2, 19, 0,  6,  3.30, 'H'},
    {2025, 2, 19, 5,  35, 0.55, 'L'},
    {2025, 2, 19, 12, 26, 2.72, 'H'},
    {2025, 2, 19, 17, 27, 0.47, 'L'},
    {2025, 2, 20, 0,  47, 3.11, 'H'},
    {2025, 2, 20, 6,  41, 0.77, 'L'},
    {2025, 2, 20, 13, 11, 2.57, 'H'},
    {2025, 2, 20, 18, 22, 0.63, 'L'}
};

#define NUM_TIDE_POINTS (sizeof(SAMPLE_TIDE_DATA) / sizeof(TidePoint))

#endif // TIDE_DATA_H
