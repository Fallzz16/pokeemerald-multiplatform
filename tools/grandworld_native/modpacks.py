#!/usr/bin/env python3
"""Validate *data-only* Grand World extension packs.

This deliberately does not load executable plugins, install packages, or change
game saves. It is the first stage of a future in-game asset pack loader.
"""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import stat
import sys
import zipfile

MAX_FILES = 2048
MAX_UNCOMPRESSED = 256 * 1024 * 1024
MAX_FILE = 32 * 1024 * 1024
MAX_RATIO = 150
ALLOWED = {
    "sprites": {".png", ".bmp"},
    "menus": {".png", ".bmp"},
    "tiles": {".png", ".bmp"},
    "audio": {".wav", ".ogg"},
}
PACK_ID = set("abcdefghijklmnopqrstuvwxyz0123456789-._")

class PackError(ValueError):
    pass

def valid_path(path):
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        return False
    if path.startswith("/") or ":" in path or "//" in path:
        return False
    parts = path.split("/")
    return all(part not in ("", ".", "..") and not part.startswith(".") for part in parts)

def valid_id(value):
    return (isinstance(value, str) and 3 <= len(value) <= 64
            and set(value) <= PACK_ID and value[0].isalnum())

def validate_zip(filename):
    with zipfile.ZipFile(filename) as z:
        entries = z.infolist()
        if len(entries) > MAX_FILES * 2:
            raise PackError("too many archive entries")
        files = [i for i in entries if not i.is_dir()]
        if len(files) > MAX_FILES:
            raise PackError("too many files")
        # Directory entries are not extracted, but must still be safe.
        for info in entries:
            path = info.filename[:-1] if info.is_dir() else info.filename
            if not valid_path(path):
                raise PackError("unsafe archive path")
            if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
                raise PackError("symlink entries are forbidden")
            if info.is_dir() and info.file_size:
                raise PackError("directory entry with data")
        all_names = [i.filename.rstrip("/") for i in entries]
        if len({name.casefold() for name in all_names}) != len(all_names):
            raise PackError("duplicated/case-colliding archive paths")
        names = [i.filename for i in files]
        total = 0
        for info in files:
            if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF):
                raise PackError("symlink entries are forbidden")
            if info.file_size > MAX_FILE:
                raise PackError("file too large")
            if info.file_size > MAX_RATIO * max(1, info.compress_size) and info.file_size > 1024 * 1024:
                raise PackError("suspicious compression ratio")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise PackError("pack uncompressed limit exceeded")
        if "manifest.json" not in names:
            raise PackError("manifest.json missing")
        if z.getinfo("manifest.json").file_size > 64 * 1024:
            raise PackError("manifest too large")
        try:
            manifest = json.loads(z.read("manifest.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackError("manifest is not valid JSON") from exc
        if not isinstance(manifest, dict) or manifest.get("api") != 1:
            raise PackError("unsupported manifest/API")
        if not valid_id(manifest.get("id")):
            raise PackError("invalid pack id")
        version = manifest.get("version")
        if not isinstance(version, str) or len(version) > 32 or not version or not all(c.isdigit() or c == "." for c in version) or len(version.split(".")) != 3 or any(not part.isdigit() for part in version.split(".")):
            raise PackError("version must be major.minor.patch")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets or len(assets) > 2000:
            raise PackError("assets must be a nonempty array")
        listed = set()
        logical = set()
        for asset in assets:
            if not isinstance(asset, dict):
                raise PackError("asset entry must be an object")
            path = asset.get("path")
            asset_id = asset.get("id")
            sha = asset.get("sha256")
            if not valid_path(path) or path not in names:
                raise PackError("missing or unsafe asset path")
            components = PurePosixPath(path).parts
            if len(components) < 3 or components[0] != "assets" or components[1] not in ALLOWED:
                raise PackError("invalid asset category")
            if PurePosixPath(path).suffix.lower() not in ALLOWED[components[1]]:
                raise PackError("unsupported asset type")
            if not isinstance(asset_id, str) or not 1 <= len(asset_id) <= 128 or any(c not in PACK_ID and c != "/" for c in asset_id):
                raise PackError("invalid logical asset id")
            if not valid_path(asset_id):
                raise PackError("unsafe logical asset id")
            if path.casefold() in listed or asset_id.casefold() in logical:
                raise PackError("duplicate asset entry/id")
            listed.add(path.casefold())
            logical.add(asset_id.casefold())
            if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                raise PackError("invalid sha256")
            h = hashlib.sha256()
            with z.open(path) as f:
                for data in iter(lambda: f.read(65536), b""):
                    h.update(data)
            if h.hexdigest() != sha:
                raise PackError("checksum mismatch: " + path)
        if {n for n in names if n != "manifest.json"} != {a["path"] for a in assets}:
            raise PackError("unlisted files are forbidden")
        return {"schema": 1, "id": manifest["id"], "version": version,
                "api": 1, "asset_count": len(assets), "total_uncompressed_bytes": total,
                "validated": True, "code_execution_supported": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pack", help="ZIP containing manifest.json and listed resources")
    args = p.parse_args()
    try:
        print(json.dumps(validate_zip(args.pack), indent=2))
    except (PackError, zipfile.BadZipFile, OSError) as exc:
        p.exit(1, "INVALID PACK: %s\n" % exc)

if __name__ == "__main__":
    main()
