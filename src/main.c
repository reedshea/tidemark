#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../lib/IT8951/IT8951.h"
#include "../lib/IT8951/miniGUI.h"
#include "tide_data.h"
#include "graph.h"

// External variables from IT8951.c
extern IT8951DevInfo gstI80DevInfo;
extern uint8_t* gpFrameBuf;

// Function declarations
extern void IT8951DisplayArea(uint16_t usX, uint16_t usY, uint16_t usW, uint16_t usH, uint16_t usDpyMode);
extern void IT8951WaitForDisplayReady(void);
extern void IT8951HostAreaPackedPixelWrite(IT8951LdImgInfo* pstLdImgInfo, IT8951AreaImgInfo* pstAreaImgInfo);

int main(int argc, char *argv[]) {
    printf("Initializing tide display...\n");
    
    // Initialize IT8951 EPD
    if(IT8951_Init()) {
        printf("IT8951_Init error\n");
        return 1;
    }
    printf("Display initialized (%dx%d)\n", gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH);
    
    // Clear display to white
    memset(gpFrameBuf, 0xFF, gstI80DevInfo.usPanelW * gstI80DevInfo.usPanelH);
    
    // Draw the graph components
    draw_graph_axes(gpFrameBuf, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH);
    draw_height_labels(gpFrameBuf, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH);
    draw_time_labels(gpFrameBuf, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH);
    plot_tide_data(gpFrameBuf, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH, 
                  SAMPLE_TIDE_DATA, NUM_TIDE_POINTS);
    
    // Set up the image buffer info
    IT8951LdImgInfo stLdImgInfo;
    IT8951AreaImgInfo stAreaImgInfo;
    
    stLdImgInfo.usEndianType = IT8951_LDIMG_L_ENDIAN;
    stLdImgInfo.usPixelFormat = IT8951_8BPP;
    stLdImgInfo.usRotate = IT8951_ROTATE_0;
    stLdImgInfo.ulStartFBAddr = (uint32_t)gpFrameBuf;
    stLdImgInfo.ulImgBufBaseAddr = (gstI80DevInfo.usImgBufAddrH << 16) | gstI80DevInfo.usImgBufAddrL;
    
    stAreaImgInfo.usX = 0;
    stAreaImgInfo.usY = 0;
    stAreaImgInfo.usWidth = gstI80DevInfo.usPanelW;
    stAreaImgInfo.usHeight = gstI80DevInfo.usPanelH;
    
    // Update display
    printf("Updating display...\n");
    IT8951WaitForDisplayReady();
    IT8951HostAreaPackedPixelWrite(&stLdImgInfo, &stAreaImgInfo);
    IT8951DisplayArea(0, 0, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH, 2);
    IT8951WaitForDisplayReady();
    
    printf("Done!\n");
    IT8951_Cancel();
    return 0;
}
