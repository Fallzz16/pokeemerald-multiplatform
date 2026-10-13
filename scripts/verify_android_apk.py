#!/usr/bin/env python3
"""Inspect experimental Emerald Hybrid LAN APK before publishing the CI artifact.

Static package smoke test, NOT gameplay, touch, networking, or install testing.
Android build-tools 'aapt' and 'apksigner' are needed.
"""
from pathlib import Path
import re
import subprocess
import sys
import zipfile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("Android APK verification FAILED: " + message)


def run(*args: str) -> str:
    done = subprocess.run(args, check=True, capture_output=True, text=True)
    return done.stdout + done.stderr


def main() -> None:
    require(len(sys.argv) == 3, "usage: verify_android_apk.py APP.apk ANDROID_BUILD_TOOLS")
    apk = Path(sys.argv[1]).resolve()
    tools = Path(sys.argv[2]).resolve()
    require(apk.is_file() and apk.stat().st_size > 1_000_000, "APK absent or unexpectedly small")

    with zipfile.ZipFile(apk) as bundle:
        entries = set(bundle.namelist())
        expected = {
            "AndroidManifest.xml", "classes.dex",
            "lib/armeabi-v7a/libSDL2.so",
            "lib/armeabi-v7a/libmain.so",
        }
        missing = expected - entries
        require(not missing, f"APK missing essential resources: {sorted(missing)}")
        abis = {part.split("/")[1] for part in entries if part.startswith("lib/") and len(part.split("/")) >= 3}
        require(abis == {"armeabi-v7a"}, f"unexpected ABI set: {abis}")
        require(bundle.testzip() is None, "corrupt ZIP entries (CRC error)")

    aapt = tools / "aapt"
    apksigner = tools / "apksigner"
    require(aapt.is_file() and apksigner.is_file(), "Android build-tools 34.0.0 not available")
    badging = run(str(aapt), "dump", "badging", str(apk))
    permissions = run(str(aapt), "dump", "permissions", str(apk))
    require("package: name='com.pokeemerald.experimental'" in badging, "wrong package identifier")
    require("launchable-activity: name='com.pokeemerald.experimental.LanLauncherActivity'" in badging,
            "LAN launcher is not the entry point")
    require(re.search(r"sdkVersion:'21'", badging) is not None, "unexpected minSdk")
    require("android.permission.INTERNET" in permissions, "LAN INTERNET permission missing")
    # Gradle assembleDebug signs with a debug key. Check that Android can verify
    # the resulting APK, rather than shipping an unusable unsigned package.
    signature = run(str(apksigner), "verify", "--verbose", str(apk))
    require("Verified using" in signature, "APK is not verifiably signed")
    print("APK static smoke test: PASS")
    print(f"  file: {apk.name} ({apk.stat().st_size:,} bytes)")
    print("  ABI: armeabi-v7a; libs: SDL2 + native Emerald")
    print("  package: com.pokeemerald.experimental")
    print("  launch: LanLauncherActivity")
    print("  permission: INTERNET; minSdk: 21; debug signature: verified")
    print("  Reminder: runtime startup and real link battle/trade still need device testing.")


if __name__ == "__main__":
    main()
