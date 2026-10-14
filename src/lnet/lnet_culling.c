#include "lnet_culling.h"

int lnet_culling_intersects(int x, int y, int width, int height,
                            int screenWidth, int screenHeight, int margin)
{
    if (width <= 0 || height <= 0 || screenWidth <= 0 ||
        screenHeight <= 0 || margin < 0)
        return 0;

    /* Half-open rectangles: touching an edge without crossing it is not
     * visible. No float calculations, no dependency on emulation framerate. */
    return x < screenWidth + margin && y < screenHeight + margin &&
           x + width > -margin && y + height > -margin;
}
