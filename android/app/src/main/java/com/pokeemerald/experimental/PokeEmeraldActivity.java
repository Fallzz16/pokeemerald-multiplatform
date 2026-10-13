package com.pokeemerald.experimental;

import android.graphics.Rect;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;

import java.util.Arrays;

import org.libsdl.app.SDLActivity;

public class PokeEmeraldActivity extends SDLActivity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        // Native GBA multitouch overlay, independent of the LAN launcher.
        GbaControlsView controls = new GbaControlsView(this);
        mLayout.addView(controls, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
    }

    @Override
    public void setOrientationBis(int width, int height, boolean resizable, String hint) {
        // Landscape is requested by the manifest. Avoid SDL rotating gameplay.
    }

    @Override
    public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (!focused) return;
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && mSurface != null) {
            mSurface.post(() -> {
                int w = mSurface.getWidth();
                int h = mSurface.getHeight();
                mSurface.setSystemGestureExclusionRects(Arrays.asList(
                        new Rect(0, h / 2, w / 5, h),
                        new Rect(w * 4 / 5, h / 2, w, h)));
            });
        }
    }

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
