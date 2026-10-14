#ifndef GUARD_LNET_CULLING_H
#define GUARD_LNET_CULLING_H

/* Pure viewport rectangle test for optional remote-player sprites.
 * x/y are top-left screen pixels AFTER camera/viewport offsets. The sprite
 * is drawn only when its rectangle intersects the visible display (margin=0).
 * Use a separate small positive margin only for sprite preloading/retention.
 * Does not touch transport, save data or gameplay state. */
int lnet_culling_intersects(int x, int y, int width, int height,
                            int screenWidth, int screenHeight, int margin);

#endif
