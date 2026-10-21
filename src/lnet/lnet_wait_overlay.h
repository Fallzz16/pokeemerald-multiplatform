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
    static const unsigned char numbers[10][5] = {
        {7,5,5,5,7}, {2,6,2,2,7}, {6,1,7,4,7},
        {6,1,6,1,6}, {5,5,7,1,1}, {7,4,7,5,7},
        {3,4,7,5,7}, {7,1,1,1,1}, {7,5,7,5,7},
        {7,5,7,1,6}
    };
    int row, col;
    const unsigned char *glyph;
    SDL_Rect pixel = {x, y, 2, 2};
    if (c >= 'A' && c <= 'Z')
        glyph = alpha[(int)(c - 'A')];
    else if (c >= '0' && c <= '9')
        glyph = numbers[(int)(c - '0')];
    else
        return;
    for (row = 0; row < 5; row++)
        for (col = 0; col < 3; col++)
            if (glyph[row] & (1 << (2 - col)))
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
/* Compact 0/2, 1/2 or 2/2 obtained from actual EHL8 PLAYER_LIST.
 * Snapshot unknown: never display fictional connected players. */
static void lnet_wait_overlay_room(SDL_Renderer *renderer, int snapshot)
{
    char labelPlayers[] = "JOGADORES 0 DE 2";
    char labelReady[] = "PRONTOS 0 DE 2";
    SDL_Rect strip = {17, 112, 206, 29};
    int players, ready;
    if (snapshot < 0)
        return;
    players = (snapshot >> 2) & 3;
    ready = snapshot & 3;
    if (players > 2 || ready > players)
        return;
    labelPlayers[10] = (char)('0' + players);
    labelReady[8] = (char)('0' + ready);
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(renderer, 5, 22, 16, 232);
    SDL_RenderFillRect(renderer, &strip);
    SDL_SetRenderDrawColor(renderer, 73, 213, 160, 255);
    SDL_RenderDrawRect(renderer, &strip);
    SDL_SetRenderDrawColor(renderer, 233, 255, 245, 255);
    lnet_wait_overlay_text(renderer, labelPlayers, 116);
    lnet_wait_overlay_text(renderer, labelReady, 128);
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
}


/* F9 is a desktop keyboard control independent from the GBA key matrix.
 * Only shown to actual launcher clients with opt-in manual readiness. */
static void lnet_wait_overlay_ready_hint(SDL_Renderer *renderer, int ready)
{
    SDL_Rect banner = {32, 143, 176, 15};
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(renderer, 5, 22, 16, 232);
    SDL_RenderFillRect(renderer, &banner);
    SDL_SetRenderDrawColor(renderer, 73, 213, 160, 255);
    SDL_RenderDrawRect(renderer, &banner);
    SDL_SetRenderDrawColor(renderer, 233, 255, 245, 255);
    lnet_wait_overlay_text(renderer,
        ready ? "F9 CANCELAR" : "F9 FICAR PRONTO", 146);
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
}

#endif
