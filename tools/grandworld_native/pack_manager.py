#!/usr/bin/env python3
"""Install/enable/disable data-only Grand World Native packs outside game saves.

The actual in-game asset resolver is a future milestone. No executable plugin
code is accepted or run by this manager. Do not point --root at a save folder.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

try:
    from .modpacks import validate_zip, PackError
    from .asset_catalog import generate_catalog
except ImportError:
    from modpacks import validate_zip, PackError
    from asset_catalog import generate_catalog

INDEX = "enabled.json"


def check_root(root):
    root = Path(root).resolve()
    if root.exists() and not root.is_dir():
        raise PackError("mod root must be a directory")
    return root


def safe_index(root):
    index = root / INDEX
    if not index.is_file():
        return {"schema": 1, "enabled": []}
    data = json.loads(index.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != 1
            or not isinstance(data.get("enabled"), list)
            or any(not isinstance(x, str) or not x.isascii()
                   or not x.replace("-", "").replace("_", "").replace(".", "").isalnum()
                   for x in data["enabled"])
            or len(data["enabled"]) != len(set(data["enabled"]))):
        raise PackError("invalid enabled.json")
    return data


def write_index(root, data):
    root.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".enabled-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")
        os.replace(name, root / INDEX)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def pack_path(root, pack_id):
    path = (root / pack_id).resolve()
    if path.parent != root:
        raise PackError("invalid pack id/path")
    return path


def install(archive, root):
    info = validate_zip(archive)
    root = check_root(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = pack_path(root, info["id"])
    if destination.exists():
        raise PackError("pack already installed: " + info["id"])
    temp = Path(tempfile.mkdtemp(prefix=".pack-", dir=root))
    try:
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.endswith("/"):
                    continue
                # validate_zip already validated paths, hashes, sizes, types.
                target = temp.joinpath(*name.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(name) as incoming, target.open("wb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
        (temp / "install-info.json").write_text(
            json.dumps({"schema": 1, "id": info["id"], "version": info["version"]}, indent=2) + "\n",
            encoding="utf-8")
        temp.rename(destination)
        generate_catalog(root)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return info


def toggle(root, pack_id, enabled):
    root = check_root(root)
    destination = pack_path(root, pack_id)
    if not (destination / "manifest.json").is_file():
        raise PackError("pack not installed")
    state = safe_index(root)
    items = state["enabled"]
    if enabled and pack_id not in items:
        items.append(pack_id)
    elif not enabled and pack_id in items:
        items.remove(pack_id)
    old_state = safe_index(root)
    write_index(root, state)
    try:
        generate_catalog(root)
    except (PackError, OSError):
        write_index(root, old_state)
        generate_catalog(root)
        raise
    return state


def list_packs(root):
    root = check_root(root)
    state = safe_index(root)
    if not root.is_dir():
        return []
    result = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.is_symlink() or not (path / "manifest.json").is_file():
            continue
        try:
            m = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            if m.get("id") != path.name:
                continue
            result.append({"id": path.name, "version": m.get("version"),
                           "enabled": path.name in state["enabled"]})
        except (ValueError, OSError):
            continue
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="dedicated modpacks folder (NOT saves)")
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("list")
    a = subs.add_parser("install")
    a.add_argument("zip_file")
    a.add_argument("--enable", action="store_true", help="activate pack after validated install")
    for command in ("enable", "disable"):
        p = subs.add_parser(command)
        p.add_argument("pack_id")
    args = parser.parse_args()
    try:
        if args.action == "install":
            result = install(args.zip_file, args.root)
            if args.enable:
                toggle(args.root, result["id"], True)
                result["enabled"] = True
        elif args.action in ("enable", "disable"):
            result = toggle(args.root, args.pack_id, args.action == "enable")
        else:
            result = list_packs(args.root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (PackError, OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, "mod manager rejected action: %s\n" % exc)


if __name__ == "__main__":
    main()
