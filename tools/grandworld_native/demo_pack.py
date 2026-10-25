#!/usr/bin/env python3
"""Generate an original PNG demo pack: menu background and animated-style follower.

No third-party or Pokémon assets. Uses only Python stdlib.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import zlib

try:
    from .build_pack import build_pack
    from .pack_manager import install, toggle
    from .asset_catalog import generate_catalog
except ImportError:
    from build_pack import build_pack
    from pack_manager import install, toggle
    from asset_catalog import generate_catalog

def png_bytes(width, height, pixel):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y))
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data +
                struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))

def landscape(x, y):
    grid = (x//16 + y//16) % 2
    r,g,b = (88,168,105) if grid else (73,151,94)
    if 98 <= x < 143 or 60 <= y < 96:
        r,g,b = (204,186,139)
    if (x * 31 + y * 19) % 127 < 3:
        r,g,b = (max(0,r-13), max(0,g-19), max(0,b-8))
    if (x-30)**2+(y-31)**2 < 18**2:
        r,g,b = (35,115,80)
    if (x-30)**2+(y-31)**2 < 11**2:
        r,g,b = (58,139,87)
    return r,g,b,255

def follower(x, y):
    # A tiny original teal creature; not any existing Pokémon.
    dx, dy = x-12, y-12
    if 6 <= y <= 21 and abs(dx) <= (7 if y < 18 else 5):
        if y < 11 and abs(dx) > 5:
            return (34,117,108,255)
        if 11 <= y <= 15 and x in (9,15):
            return (20,34,46,255)
        if y == 17 and 10 <= x <= 14:
            return (238,205,153,255)
        return (48,182,167,255)
    if 5 <= y <= 10 and x in (5,18):
        return (43,161,143,255)
    if y == 22 and 6 <= x <= 18:
        return (31,91,88,255)
    return (0,0,0,0)

def directional_follower(direction):
    """Original creature with visibly changing gaze in eight directions."""
    offsets = {
        "n": (0, -2), "ne": (2, -2), "e": (2, 0), "se": (2, 2),
        "s": (0, 2), "sw": (-2, 2), "w": (-2, 0), "nw": (-2, -2)
    }
    dx, dy = offsets[direction]
    def pixel(x, y):
        value = follower(x, y)
        # Erase default eyes so only the gaze selected for this direction appears.
        if 11 <= y <= 15 and x in (9, 15):
            value = (48, 182, 167, 255)
        if y == 12 + dy and x in (9 + dx, 15 + dx):
            return (20, 34, 46, 255)
        return value
    return pixel

def create(out):
    out = Path(out)
    assets = out / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    (assets / "menus").mkdir(parents=True)
    (assets / "sprites").mkdir(parents=True)
    (assets / "menus/background.png").write_bytes(png_bytes(240,160,landscape))
    (assets / "sprites/follower.png").write_bytes(png_bytes(24,24,follower))
    (assets / "sprites/follower").mkdir()
    for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
        (assets / "sprites/follower" / (direction + ".png")).write_bytes(
            png_bytes(24, 24, directional_follower(direction)))
    zipfile = out / "gw-demo-style.zip"
    if zipfile.exists():
        zipfile.unlink()
    info = build_pack(assets, "gw-demo-style", "1.0.0", zipfile)
    return {"path": str(zipfile), "assets": str(assets), "pack": info}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="build/gw-style-demo")
    p.add_argument("--install", action="store_true", help="also install and enable in out/mods")
    args=p.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report=create(out)
    if args.install:
        root=out/"mods"
        if not (root/"gw-demo-style").exists():
            install(report["path"], root)
        toggle(root,"gw-demo-style",True)
        report["catalog"]=generate_catalog(root)
        # Cosmetic settings only, never touch a Pokémon save.
        (root/"style-settings.ini").write_text(
            "GW_STYLE_V1\nmenus=gw-demo-style\nsprites=gw-demo-style\n",
            encoding="utf-8")
        report["mods_root"]=str(root)
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
