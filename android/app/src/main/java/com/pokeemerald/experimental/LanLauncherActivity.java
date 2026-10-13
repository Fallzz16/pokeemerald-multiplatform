package com.pokeemerald.experimental;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Enumeration;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Native LAN launcher. No edits to the existing Emerald Hybrid menus/saves.
 * TCP is used only on the local network, with no remote relay service.
 */
public final class LanLauncherActivity extends Activity {
    private static final int DEFAULT_PORT = 45680;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        int pad = (int) (24 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, pad);
        TextView title = new TextView(this);
        title.setText("Emerald Hybrid — LAN");
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER);
        root.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        TextView help = new TextView(this);
        help.setText("Both players need the same build and Wi-Fi network.\nOpen the Cable Club in-game for trades and battles.");
        help.setGravity(Gravity.CENTER);
        help.setPadding(0, pad / 2, 0, pad / 2);
        root.addView(help);
        addButton(root, "Play offline", v -> openGame(0, null, 0));
        addButton(root, "Host LAN", v -> showHostDialog());
        addButton(root, "Join LAN", v -> showJoinDialog());
        setContentView(root);
    }

    private void addButton(LinearLayout root, String label, android.view.View.OnClickListener onClick) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(onClick);
        root.addView(button, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
    }

    private void showHostDialog() {
        final EditText port = new EditText(this);
        port.setSingleLine(true);
        port.setInputType(InputType.TYPE_CLASS_NUMBER);
        port.setText(Integer.toString(DEFAULT_PORT));
        int pad = (int) (20 * getResources().getDisplayMetrics().density);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(pad, pad / 2, pad, pad / 2);
        TextView address = new TextView(this);
        address.setText("Local IPv4: " + findLanIpv4()
                + "\nShare this address and TCP port with the other player."
                + "\nBoth devices must be on the same local network.");
        panel.addView(address);
        panel.addView(port);
        new AlertDialog.Builder(this).setTitle("Host LAN session")
                .setView(panel)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Host", (dialog, which) -> {
                    int value = validPort(port.getText().toString());
                    if (value == 0) showError("Port must be between 1 and 65535.");
                    else openGame(1, null, value);
                }).show();
    }

    // Find a private IPv4 address without location, Wi-Fi or network-state
    // permissions. Fall back gracefully when Android hides interface details.
    private static String findLanIpv4() {
        String fallback = null;
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface network = interfaces.nextElement();
                if (!network.isUp() || network.isLoopback()) continue;
                Enumeration<InetAddress> addresses = network.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress ip = addresses.nextElement();
                    if (!(ip instanceof Inet4Address) || !ip.isSiteLocalAddress()) continue;
                    String candidate = ip.getHostAddress();
                    String name = network.getName();
                    if (name.startsWith("wlan") || name.startsWith("ap")
                            || name.startsWith("eth")) return candidate;
                    if (fallback == null) fallback = candidate;
                }
            }
        } catch (Exception ignored) {
            // Connection remains available even when Android restricts network info.
        }
        return fallback != null ? fallback : "unavailable (check Wi-Fi settings)";
    }

    private void showJoinDialog() {
        final EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setHint("192.168.1.50:45680");
        new AlertDialog.Builder(this).setTitle("Host's local IP and port")
                .setView(address)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Join", (dialog, which) -> {
                    String spec = address.getText().toString().trim();
                    String host = spec;
                    int port = DEFAULT_PORT;
                    int colon = spec.lastIndexOf(':');
                    if (colon >= 0) {
                        host = spec.substring(0, colon);
                        port = validPort(spec.substring(colon + 1));
                    }
                    if (!validIpv4(host) || port == 0) {
                        showError("Enter an IPv4 LAN address, optionally followed by :port.");
                        return;
                    }
                    openGame(2, host, port);
                }).show();
    }

    private static int validPort(String text) {
        try {
            int p = Integer.parseInt(text);
            return p >= 1 && p <= 65535 ? p : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static boolean validIpv4(String host) {
        String[] parts = host.split("\\.", -1);
        if (parts.length != 4) return false;
        for (String part : parts) {
            if (part.length() < 1 || part.length() > 3) return false;
            for (int i = 0; i < part.length(); i++)
                if (part.charAt(i) < '0' || part.charAt(i) > '9') return false;
            int value = Integer.parseInt(part);
            if (value < 0 || value > 255) return false;
        }
        return true;
    }

    private void showError(String message) {
        new AlertDialog.Builder(this).setTitle("Invalid LAN configuration")
                .setMessage(message).setPositiveButton("OK", null).show();
    }

    private void openGame(int mode, String host, int port) {
        Intent launch = new Intent(this, PokeEmeraldActivity.class);
        launch.putExtra("lan_mode", mode);
        launch.putExtra("lan_port", port);
        if (host != null) launch.putExtra("lan_host", host);
        startActivity(launch);
    }
}
