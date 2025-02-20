#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../lib/IT8951/IT8951.h"
#include "../lib/IT8951/miniGUI.h"

// External variables from IT8951.c
extern IT8951DevInfo gstI80DevInfo;
extern uint8_t* gpFrameBuf;

// Function declarations
extern void IT8951DisplayArea(uint16_t usX, uint16_t usY, uint16_t usW, uint16_t usH, uint16_t usDpyMode);
extern void IT8951WaitForDisplayReady(void);
extern void IT8951SetVCOM(uint16_t vcom);

int main(int argc, char *argv[]) {
    printf("Starting program...\n");
    
    // Initialize IT8951 EPD
    if(IT8951_Init()) {
        printf("IT8951_Init error\n");
        return 1;
    }
    printf("IT8951 initialized\n");
    
    // Fill entire screen with black
    printf("Filling screen with black...\n");
    memset(gpFrameBuf, 0x00, gstI80DevInfo.usPanelW * gstI80DevInfo.usPanelH);
    
    // Set up the image buffer info
    IT8951LdImgInfo stLdImgInfo;
    IT8951AreaImgInfo stAreaImgInfo;
    
    // Setting load image info
    stLdImgInfo.usEndianType = IT8951_LDIMG_L_ENDIAN;
    stLdImgInfo.usPixelFormat = IT8951_8BPP;
    stLdImgInfo.usRotate = IT8951_ROTATE_0;
    stLdImgInfo.ulStartFBAddr = (uint32_t)gpFrameBuf;
    stLdImgInfo.ulImgBufBaseAddr = (gstI80DevInfo.usImgBufAddrH << 16) | gstI80DevInfo.usImgBufAddrL;
    
    // Set up area info
    stAreaImgInfo.usX = 0;
    stAreaImgInfo.usY = 0;
    stAreaImgInfo.usWidth = gstI80DevInfo.usPanelW;
    stAreaImgInfo.usHeight = gstI80DevInfo.usPanelH;
    
    // Write the image data to the IT8951 image buffer
    printf("Writing to display buffer...\n");
    IT8951HostAreaPackedPixelWrite(&stLdImgInfo, &stAreaImgInfo);
    
    // Update display
    printf("Updating display...\n");
    IT8951WaitForDisplayReady();
    IT8951DisplayArea(0, 0, gstI80DevInfo.usPanelW, gstI80DevInfo.usPanelH, 2);
    IT8951WaitForDisplayReady();
    
    // Cleanup
    printf("Cleaning up...\n");
    IT8951_Cancel();
    
    printf("Done!\n");
    return 0;
}
