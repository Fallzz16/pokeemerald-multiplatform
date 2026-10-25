#!/usr/bin/env python3
"""Build a signed-by-checksum, data-only ZIP pack from an assets directory.

Hashes verify byte integrity, not asset copyright or publisher authenticity.
Packs cannot execute code. No source assets are distributed in this repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

try:
    from .modpacks import ALLOWED, PackError, MAX_FILE, MAX_FILES, validate_zip, valid_id, valid_path
except ImportError:
    from modpacks import ALLOWED, PackError, MAX_FILE, MAX_FILES, validate_zip, valid_id, valid_path

def build_pack(assets_root, pack_id, version, dest):
    assets_root = Path(assets_root).resolve()
    dest = Path(dest).resolve()
    if not valid_id(pack_id):
        raise PackError("invalid pack id")
    if not assets_root.is_dir() or assets_root.name != "assets":
        raise PackError("input must be a folder named assets")
    if not isinstance(version, str) or len(version.split(".")) != 3 or any(not x.isdigit() for x in version.split(".")):
        raise PackError("version must be 1.2.3")
    all_files = sorted(assets_root.rglob("*"))
    resources = [p for p in all_files if p.is_file()]
    if not resources or len(resources) > MAX_FILES - 1:
        raise PackError("pack must have between 1 and 2047 resource files")
    manifest = {"api": 1, "id": pack_id, "version": version, "assets": []}
    seen = set()
    file_paths = []
    for source in resources:
        if source.is_symlink() or not source.resolve().is_relative_to(assets_root):
            raise PackError("unsafe symlink inside asset root")
        rel = source.relative_to(assets_root).as_posix()
        logical_path = "assets/" + rel
        parts = rel.split("/")
        if not valid_path(logical_path) or len(parts) < 2 or parts[0] not in ALLOWED:
            raise PackError("invalid category/path: " + rel)
        if source.suffix.lower() not in ALLOWED[parts[0]]:
            raise PackError("asset extension not allowed: " + rel)
        if source.stat().st_size > MAX_FILE:
            raise PackError("asset exceeds max size: " + rel)
        asset_id = "/".join((parts[0], *parts[1:-1], source.stem)).lower()
        if not asset_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-._/" for c in asset_id):
            raise PackError("invalid asset ID: " + asset_id)
        if asset_id.casefold() in seen:
            raise PackError("asset id collision")
        seen.add(asset_id.casefold())
        manifest["assets"].append({
            "id": asset_id,
            "path": logical_path,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()
        })
        file_paths.append((source, logical_path))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", dir=dest.parent, delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
            for source, logical_path in file_paths:
                archive.write(source, arcname=logical_path)
        checked = validate_zip(staging)
        if dest.exists():
            raise PackError("output exists: refusing to overwrite")
        staging.replace(dest)
        return checked
    finally:
        staging.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build_pack(args.assets, args.id, args.version, args.output), indent=2))
    except (OSError, PackError) as exc:
        parser.exit(1, "BUILD REJECTED: %s\n" % exc)

if __name__ == "__main__":
    main()
