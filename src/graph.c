#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "graph.h"
#include "../lib/IT8951/miniGUI.h"
#include "../lib/IT8951/AsciiLib.h"

// Function declarations
extern void EPD_DrawString(uint16_t Xstart, uint16_t Ystart, const char * pString, uint8_t Color);

// Helper function to map a value from one range to another
static float map_range(float value, float in_min, float in_max, float out_min, float out_max) {
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// Convert time point to minutes since start of first day
static int time_to_minutes(const TidePoint* point) {
    int day_offset = (point->day - SAMPLE_TIDE_DATA[0].day) * 24 * 60;
    return day_offset + point->hour * 60 + point->minute;
}

// Format time as HH:MM
static void format_time(char* buf, int hour, int minute) {
    sprintf(buf, "%02d:%02d", hour, minute);
}

void draw_graph_axes(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Draw Y axis (vertical line)
    EPD_DrawLine(GRAPH_MARGIN_LEFT, GRAPH_MARGIN_TOP, 
                 GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM, 0x00);
                 
    // Draw X axis (horizontal line)
    EPD_DrawLine(GRAPH_MARGIN_LEFT, height - GRAPH_MARGIN_BOTTOM,
                 width - GRAPH_MARGIN_RIGHT, height - GRAPH_MARGIN_BOTTOM, 0x00);
    
    // Draw axis labels
    EPD_Text(5, height - GRAPH_MARGIN_BOTTOM + 10, (uint8_t*)"Time", 0x00, 0xFF);
    EPD_Text(GRAPH_MARGIN_LEFT - 30, GRAPH_MARGIN_TOP - 10, (uint8_t*)"Height (ft)", 0x00, 0xFF);
}

void plot_tide_data(uint8_t* framebuf, uint16_t width, uint16_t height,
                   const TidePoint* data, size_t num_points) {
    // Find min/max values
    float min_height = data[0].height;
    float max_height = data[0].height;
    int start_time = time_to_minutes(&data[0]);
    int end_time = time_to_minutes(&data[num_points-1]);
    
    for(size_t i = 1; i < num_points; i++) {
        if(data[i].height < min_height) min_height = data[i].height;
        if(data[i].height > max_height) max_height = data[i].height;
    }
    
    // Add 10% padding to height range
    float height_padding = (max_height - min_height) * 0.1;
    min_height -= height_padding;
    max_height += height_padding;
    
    // Plot points and connect them with lines
    for(size_t i = 0; i < num_points - 1; i++) {
        int x1 = map_range(time_to_minutes(&data[i]), start_time, end_time,
                          GRAPH_MARGIN_LEFT, width - GRAPH_MARGIN_RIGHT);
        int y1 = map_range(data[i].height, min_height, max_height,
                          height - GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP);
                          
        int x2 = map_range(time_to_minutes(&data[i+1]), start_time, end_time,
                          GRAPH_MARGIN_LEFT, width - GRAPH_MARGIN_RIGHT);
        int y2 = map_range(data[i+1].height, min_height, max_height,
                          height - GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP);
        
        // Draw line connecting points
        EPD_DrawLine(x1, y1, x2, y2, 0x00);
        
        // Draw point markers
        EPD_FillCircle(x1, y1, 5, 0x00);
        
        // Add height label near each point
        char height_str[10];
        sprintf(height_str, "%.1f", data[i].height);
        EPD_Text(x1 - 15, y1 - 15, (uint8_t*)height_str, 0x00, 0xFF);
    }
    
    // Draw final point and its height
    int x = map_range(time_to_minutes(&data[num_points-1]), start_time, end_time,
                     GRAPH_MARGIN_LEFT, width - GRAPH_MARGIN_RIGHT);
    int y = map_range(data[num_points-1].height, min_height, max_height,
                     height - GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP);
    EPD_FillCircle(x, y, 5, 0x00);
    
    char height_str[10];
    sprintf(height_str, "%.1f", data[num_points-1].height);
    EPD_Text(x - 15, y - 15, (uint8_t*)height_str, 0x00, 0xFF);
}

void draw_time_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Draw time labels for each data point
    for(size_t i = 0; i < NUM_TIDE_POINTS; i++) {
        int x = map_range(time_to_minutes(&SAMPLE_TIDE_DATA[i]), 
                         time_to_minutes(&SAMPLE_TIDE_DATA[0]),
                         time_to_minutes(&SAMPLE_TIDE_DATA[NUM_TIDE_POINTS-1]),
                         GRAPH_MARGIN_LEFT, width - GRAPH_MARGIN_RIGHT);
        
        char time_str[10];
        format_time(time_str, SAMPLE_TIDE_DATA[i].hour, SAMPLE_TIDE_DATA[i].minute);
        
        // Draw time labels below x-axis
        EPD_Text(x - 20, height - GRAPH_MARGIN_BOTTOM + 10, (uint8_t*)time_str, 0x00, 0xFF);
        
        // Add date if it's the first point of the day
        if (i == 0 || SAMPLE_TIDE_DATA[i].day != SAMPLE_TIDE_DATA[i-1].day) {
            char date_str[20];
            sprintf(date_str, "%d/%d", SAMPLE_TIDE_DATA[i].month, SAMPLE_TIDE_DATA[i].day);
            EPD_Text(x - 20, height - GRAPH_MARGIN_BOTTOM + 30, (uint8_t*)date_str, 0x00, 0xFF);
        }
    }
}

void draw_height_labels(uint8_t* framebuf, uint16_t width, uint16_t height) {
    // Find min/max heights
    float min_height = SAMPLE_TIDE_DATA[0].height;
    float max_height = SAMPLE_TIDE_DATA[0].height;
    
    for(size_t i = 1; i < NUM_TIDE_POINTS; i++) {
        if(SAMPLE_TIDE_DATA[i].height < min_height) min_height = SAMPLE_TIDE_DATA[i].height;
        if(SAMPLE_TIDE_DATA[i].height > max_height) max_height = SAMPLE_TIDE_DATA[i].height;
    }
    
    // Add 10% padding
    float height_padding = (max_height - min_height) * 0.1;
    min_height -= height_padding;
    max_height += height_padding;
    
    // Draw height labels at regular intervals
    int num_labels = 5;
    for(int i = 0; i <= num_labels; i++) {
        float height = min_height + (max_height - min_height) * i / num_labels;
        int y = map_range(height, min_height, max_height,
                         height - GRAPH_MARGIN_BOTTOM, GRAPH_MARGIN_TOP);
        
        char height_str[10];
        sprintf(height_str, "%.1f ft", height);
        EPD_Text(5, y - 5, (uint8_t*)height_str, 0x00, 0xFF);
    }
}
