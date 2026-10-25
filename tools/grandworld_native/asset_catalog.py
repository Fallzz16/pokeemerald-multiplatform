#!/usr/bin/env python3
"""Publish a safe, deterministic, read-only catalog of installed enabled data packs.

C/SDL2 uses this TSV interface, so it needs no Python JSON parser at runtime.
This catalog is NOT game content, and does not touch player saves.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

try:
    from .modpacks import ALLOWED, PackError, valid_id, valid_path, MAX_FILE
except ImportError:
    from modpacks import ALLOWED, PackError, valid_id, valid_path, MAX_FILE

CATALOG = "runtime-assets.tsv"
HEADER = "GW_ASSETS_V1"

def _atomic_write(dest, content):
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, staging = tempfile.mkstemp(prefix=".gw-", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(staging, dest)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)

def _inside(root, path):
    path = root / path
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise PackError("symlink or escaped asset path")
    # Reject symlinked parents, including a symlink to an alternate pack root.
    relative = path.relative_to(root)
    parent = root
    for segment in relative.parts:
        parent = parent / segment
        if parent.is_symlink():
            raise PackError("symlink in pack path")
    return path

def generate_catalog(root):
    root = Path(root).resolve()
    from_pack_manager = (root / "enabled.json")
    if not from_pack_manager.exists():
        active = []
    else:
        try:
            state = json.loads(from_pack_manager.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise PackError("invalid enabled index") from exc
        active = state.get("enabled")
        if (not isinstance(state, dict) or state.get("schema") != 1
                or not isinstance(active, list)
                or any(not valid_id(i) for i in active)
                or len(set(active)) != len(active)):
            raise PackError("invalid enabled index")
    lines = [HEADER]
    ids = set()
    for pack_id in active:
        if pack_id in ids:
            raise PackError("duplicate enabled pack")
        ids.add(pack_id)
        pack = _inside(root, pack_id)
        manifest_file = _inside(root, pack_id + "/manifest.json")
        if not manifest_file.is_file():
            raise PackError("enabled pack does not exist")
        try:
            m = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise PackError("corrupt manifest") from exc
        if not isinstance(m, dict) or m.get("api") != 1 or m.get("id") != pack_id:
            raise PackError("manifest mismatch")
        assets = m.get("assets")
        if not isinstance(assets, list) or len(assets) > 2000:
            raise PackError("invalid asset entries")
        seen = set()
        for a in assets:
            if not isinstance(a, dict):
                raise PackError("invalid asset")
            logical, relpath, digest = a.get("id"), a.get("path"), a.get("sha256")
            if (not isinstance(logical, str) or not valid_path(logical)
                    or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-._/" for c in logical)
                    or not valid_path(relpath)):
                raise PackError("invalid logical id or path")
            parts = relpath.split("/")
            if (len(parts) < 3 or parts[0] != "assets" or parts[1] not in ALLOWED
                    or Path(relpath).suffix.lower() not in ALLOWED[parts[1]]):
                raise PackError("invalid asset category")
            if logical in seen:
                raise PackError("duplicate logical id")
            seen.add(logical)
            if not isinstance(digest, str) or len(digest) != 64:
                raise PackError("invalid declared digest")
            p = _inside(root, pack_id + "/" + relpath)
            if not p.is_file() or p.stat().st_size > MAX_FILE:
                raise PackError("missing or oversized installed resource")
            if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                raise PackError("installed resource checksum changed: " + relpath)
            lines.append("\t".join([parts[1], pack_id, logical, pack_id + "/" + relpath]))
    _atomic_write(root / CATALOG, "\n".join(lines) + "\n")
    return {"catalog": str(root / CATALOG), "enabled_packs": len(active), "assets": len(lines) - 1}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    args = p.parse_args()
    try:
        print(json.dumps(generate_catalog(args.root), indent=2))
    except (PackError, OSError) as exc:
        p.exit(1, "CATALOG REJECTED: %s\n" % exc)

if __name__ == "__main__":
    main()
