package com.pokeemerald.experimental;

import org.libsdl.app.SDLActivity;

public class PokeEmeraldActivity extends SDLActivity {
    @Override
    protected String[] getLibraries() {
        return new String[] { "SDL2", "main" };
    }

    @Override
    protected String[] getArguments() {
        int mode = getIntent().getIntExtra("lan_mode", 0);
        int port = getIntent().getIntExtra("lan_port", 45680);
        if (port < 1 || port > 65535) return new String[0];
        if (mode == 1) return new String[] { "--lan-host=" + port };
        if (mode == 2) {
            String host = getIntent().getStringExtra("lan_host");
            if (host != null && host.length() > 0)
                return new String[] { "--lan-client=" + host + ":" + port };
        }
        return new String[0];
    }
}
