#ifndef GUARD_LNET_WAIT_OVERLAY_H
#define GUARD_LNET_WAIT_OVERLAY_H
/*
 * End-user overlay for EHL8 before START. Drawn by the SDL renderer thread;
 * no network, game loop, save, or Cable Club state is changed by this code.
 * SDL.h must be included before this header by the platform adapter.
 * All labels use unaccented ASCII to avoid dependencies on SDL_ttf/fonts.
 */
static void lnet_wait_overlay_glyph(SDL_Renderer *renderer, char c, int x, int y)
{
    static const unsigned char alpha[26][5] = {
        {2,5,7,5,5}, /* A */ {6,5,6,5,6}, /* B */
        {3,4,4,4,3}, /* C */ {6,5,5,5,6}, /* D */
        {7,4,6,4,7}, /* E */ {7,4,6,4,4}, /* F */
        {3,4,5,5,3}, /* G */ {5,5,7,5,5}, /* H */
        {7,2,2,2,7}, /* I */ {1,1,1,5,2}, /* J */
        {5,5,6,5,5}, /* K */ {4,4,4,4,7}, /* L */
        {5,7,7,5,5}, /* M */ {5,7,7,7,5}, /* N */
        {2,5,5,5,2}, /* O */ {6,5,6,4,4}, /* P */
        {2,5,5,7,3}, /* Q */ {6,5,6,5,5}, /* R */
        {3,4,2,1,6}, /* S */ {7,2,2,2,2}, /* T */
        {5,5,5,5,7}, /* U */ {5,5,5,5,2}, /* V */
        {5,5,7,7,5}, /* W */ {5,5,2,5,5}, /* X */
        {5,5,2,2,2}, /* Y */ {7,1,2,4,7}  /* Z */
    };
    int row, col;
    SDL_Rect pixel = {x, y, 2, 2};
    if (c < 'A' || c > 'Z')
        return;
    for (row = 0; row < 5; row++)
        for (col = 0; col < 3; col++)
            if (alpha[(int)(c - 'A')][row] & (1 << (2 - col)))
            {
                pixel.x = x + 2 * col;
                pixel.y = y + 2 * row;
                SDL_RenderFillRect(renderer, &pixel);
            }
}

static void lnet_wait_overlay_text(SDL_Renderer *renderer,
                                   const char *value, int y)
{
    int count = 0, col = 0;
    while (value[count])
        count++;
    for (col = 0; col < count; col++)
        lnet_wait_overlay_glyph(renderer, value[col],
                               (240 - count * 8) / 2 + col * 8, y);
}

static void lnet_wait_overlay_render(SDL_Renderer *renderer, int state)
{
    SDL_Rect area = {17, 49, 206, 63};
    SDL_Rect border = {17, 49, 206, 63};
    /* 4/5: a small, non-blocking notice after START. The game remains
     * playable locally, and state 2 removes the notice on reconnection. */
    if (state == 4 || state == 5)
    {
        SDL_Rect strip = {16, 6, 208, 30};
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
        SDL_SetRenderDrawColor(renderer, 5, 22, 16, 218);
        SDL_RenderFillRect(renderer, &strip);
        if (state == 4)
            SDL_SetRenderDrawColor(renderer, 255, 196, 96, 255);
        else
            SDL_SetRenderDrawColor(renderer, 255, 128, 116, 255);
        SDL_RenderDrawRect(renderer, &strip);
        SDL_SetRenderDrawColor(renderer, 233, 255, 245, 255);
        lnet_wait_overlay_text(renderer,
            state == 4 ? "RECONECTANDO" : "CONEXAO PERDIDA", 10);
        lnet_wait_overlay_text(renderer, "JOGO LOCAL ATIVO", 22);
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        return;
    }
    /* state 1: wait; 3: terminal startup failure. Never overlay offline. */
    if (state != 1 && state != 3)
        return;
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(renderer, 5, 22, 16, 232);
    SDL_RenderFillRect(renderer, &area);
    if (state == 3)
        SDL_SetRenderDrawColor(renderer, 255, 173, 104, 255);
    else
        SDL_SetRenderDrawColor(renderer, 73, 213, 160, 255);
    SDL_RenderDrawRect(renderer, &border);
    lnet_wait_overlay_text(renderer, "SALA ONLINE", 58);
    SDL_SetRenderDrawColor(renderer, 233, 255, 245, 255);
    if (state == 3)
    {
        lnet_wait_overlay_text(renderer, "CONEXAO FALHOU", 79);
        lnet_wait_overlay_text(renderer, "FECHE E REENTRE", 95);
    }
    else
    {
        lnet_wait_overlay_text(renderer, "AGUARDANDO AMIGO", 79);
        lnet_wait_overlay_text(renderer, "HOST INICIA SALA", 95);
    }
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
}
#endif
