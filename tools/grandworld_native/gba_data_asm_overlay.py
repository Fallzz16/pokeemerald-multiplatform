#!/usr/bin/env python3
"""Adapt original World/M8 GBA data-assembly syntax for an x86 host assembler.

Apply only to an expendable World tree AFTER its genuine GBA reference build.
No game content, script command, byte literal, or binary asset is fabricated.

ARM GAS .align N means 2**N bytes; x86 GAS .align N means N bytes, so
.p2align N is needed for *equivalent* alignment. ARM .word is a 32-bit
value, but i386 GAS .word is 16-bit; use .4byte without changing the value.
Three existing FRLG Celadon expressions need whitespace removed so native
GAS passes them to their *original* comparison macro as one argument.
"""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile

ALIGN = re.compile(r'^(?P<indent>[ \t]*)\.align[ \t]+(?P<n>[0-9]+)(?P<rest>(?:[ \t]*,[^\r\n]*)?)[ \t]*$')
WORD = re.compile(r'^(?P<indent>[ \t]*)\.word(?=[ \t]+)(?P<rest>[^\r\n]+)$')
CELE = re.compile(r'^(?P<prefix>[ \t]*goto_if_ge[ \t]+VAR_TEMP_1,[ \t]*)'
                  r'\(MAX_COINS[ \t]+\+[ \t]+1\)[ \t]+-[ \t]+(?P<coins>10|20)'
                  r'(?P<tail>,[ \t]*CeladonCity_GameCorner_EventScript_[A-Za-z0-9_]+[ \t]*)$')
SOURCE = "data/maps/CeladonCity_GameCorner_Frlg/scripts.inc"
EXPECTED_CELADON = 3


def _arm_comment(line):
    quote = None
    escape = False
    for at, char in enumerate(line):
        if escape:
            escape = False
        elif quote is not None and char == "\\":
            escape = True
        elif char in ("'", '"'):
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        elif char == '@' and quote is None:
            # ARM comments need not have a space after '@' (e.g. @Custom).
            # GAS ELF section/type annotations must keep @progbits/@function.
            if at == 0 or line[at-1].isspace():
                directive = line.lstrip().split(None, 1)[0] if line.strip() else ""
                operand = line[at + 1:].split(None, 1)[0].rstrip(",") if line[at + 1:].strip() else ""
                if directive in (".section", ".pushsection", ".type") and (
                        operand in ("progbits", "nobits", "function", "object")):
                    continue
                return line[:at] + "#" + line[at+1:], True
    return line, False


def transform_text(source, special_celadon=False):
    counters = {"align": 0, "word": 0, "arm_comment": 0, "celadon_expression": 0}
    output = []
    for raw in source.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        eol = raw[len(line):]
        if special_celadon:
            match = CELE.fullmatch(line)
            if match:
                line = (match.group("prefix") + "(MAX_COINS+1)-" +
                        match.group("coins") + match.group("tail"))
                counters["celadon_expression"] += 1
        line, changed = _arm_comment(line)
        if changed:
            counters["arm_comment"] += 1
        match = ALIGN.fullmatch(line)
        if match:
            power = int(match.group("n"))
            if power > 20:
                raise ValueError("unreasonable ARM alignment directive")
            if power == 0:
                power = 2  # ARM GAS .align 0 defaults to a 4-byte boundary.
            line = (match.group("indent") + ".p2align " + str(power) +
                    (match.group("rest") or ""))
            counters["align"] += 1
        match = WORD.fullmatch(line)
        if match:
            line = match.group("indent") + ".4byte" + match.group("rest")
            counters["word"] += 1
        output.append(line + eol)
    return "".join(output), counters


def scan(world, apply=False):
    world = Path(world).resolve()
    if not (world / "src/main.c").is_file():
        raise ValueError("not a World source tree")
    files = []
    for folder in ("asm", "data", "src"):
        root = world / folder
        if root.is_dir():
            for pattern in ("*.inc", "*.s"):
                files.extend(root.rglob(pattern))
    files = sorted(set(files))
    if len(files) > 30000:
        raise ValueError("unexpected number of assembly inputs")
    modifications = []
    total = {"align": 0, "word": 0, "arm_comment": 0, "celadon_expression": 0}
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(world):
            raise ValueError("unsafe symlink/assembly source path")
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("unexpectedly large assembly source")
        original = path.read_text(encoding="utf-8", errors="surrogateescape")
        relative = path.relative_to(world).as_posix()
        patched, changes = transform_text(original, relative == SOURCE)
        if relative == SOURCE and changes["celadon_expression"] != EXPECTED_CELADON:
            raise ValueError("Celadon script changed: expected exactly three expressions")
        if patched != original:
            modifications.append((path, patched))
        for key, count in changes.items():
            total[key] += count
    if total["celadon_expression"] != EXPECTED_CELADON:
        raise ValueError("Celadon macro argument locations missing")
    if apply:
        for path, content in modifications:
            fd, tmp = tempfile.mkstemp(prefix=".gw-gas-", suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape") as stream:
                    stream.write(content)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
    return {
        "schema": 1, "stage": "P2_original_GBA_data_assembly_to_x86_dialect",
        "source_files_scanned": len(files),
        "source_files_changed": len(modifications),
        "pure_directive_and_comment_transform": True,
        "content_assets_replaced": False, "GBA_reference_build_precedes_overlay": True,
        "applied_to_disposable_source": bool(apply),
        "changes": total, "native_game_linked": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report", default="native-gba-data-asm-overlay.json")
    args = p.parse_args()
    try:
        result = scan(args.world, args.apply)
        Path(args.report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    except (ValueError, OSError) as exc:
        p.exit(1, "NATIVE ASM DIALECT ADAPTER REFUSED: %s\n" % exc)


if __name__ == "__main__":
    main()
