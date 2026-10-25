#!/usr/bin/env python3
"""P2: attempt a REAL 32-bit World/M8 + SDL2 executable link.

Inputs must be compiled from the composed game's genuine C, genuine game-data
ASM, platform backend C and SDL2 desktop entrypoint. No dummy symbols, fake
graphics, undefined-symbol suppression or no-op linker shims are permitted.
Failed linking is EXPECTED until the remaining World/ASM modules are ported.
A successful ELF link alone does not prove the game boots or is playable.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess

UNDEFINED = re.compile(r"undefined reference to [\x60\x27\u2018](.+?)[\x27\u2019]")
MULTIPLE = re.compile(r"multiple definition of [\x60\x27\u2018](.+?)[\x27\u2019]")


def attempt(code, data, platform, frontend, report, compiler="gcc",
            extra_libs=None):
    code, data, platform, frontend, report = (
        Path(p).resolve() for p in (code, data, platform, frontend, report)
    )
    collected = {
        "World_M8_C": sorted(code.glob("*.o")),
        "original_game_data": sorted(data.glob("*.o")),
        "portable_platform": sorted(platform.glob("*.o")),
    }
    result = {
        "schema": 1, "stage": "P2_full_native_World_M8_executable_link_attempt",
        "real_game_sources_only": True,
        "dummy_symbols_or_assets": False,
        "suppressed_linker_errors": False,
        "component_counts": {key: len(items) for key, items in collected.items()},
        "frontend_compiled": frontend.is_file(),
        "link_succeeded": False, "game_boot_verified": False,
        "gameplay_verified": False, "windows_executable_created": False,
        "game_sources_all_compiled": None,
        "game_data_all_compiled": None,
        "ready_for_distribution": False,
    }
    # An incomplete input set is not a link success and cannot create a
    # misleading desktop executable. The caller gets a machine-readable cause.
    if not all(collected.values()) or not frontend.is_file():
        result["error"] = "missing authentic compiled World, data, platform or SDL2 frontend objects"
        return result
    command = shutil.which(compiler)
    if not command:
        result["error"] = "native C linker missing"
        return result
    target = report.with_name("grandworld-WORLD-NOT-BOOT-VERIFIED")
    report.parent.mkdir(parents=True, exist_ok=True)
    objects = [frontend]
    for name in ("World_M8_C", "original_game_data", "portable_platform"):
        objects.extend(collected[name])
    # Never use -Wl,--unresolved-symbols=ignore-all or linker-generated stubs.
    args = [command, "-m32", "-no-pie", "-Wl,--no-undefined",
            *map(str, objects), "-o", str(target),
            *(extra_libs if extra_libs is not None
              else ["-lSDL2_image", "-lSDL2", "-lm"])]
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = "linker failed to run"
        result["diagnostic"] = str(exc)
        return result
    errors = completed.stderr.splitlines()
    result["link_exit_code"] = completed.returncode
    result["linker_error_lines"] = [line for line in errors
                                    if ("undefined reference" in line or
                                        "multiple definition" in line or
                                        "error:" in line)][:100]
    undefined = Counter(UNDEFINED.findall(completed.stderr))
    multiple = Counter(MULTIPLE.findall(completed.stderr))
    result["undefined_unique_count"] = len(undefined)
    result["undefined_reference_examples"] = [
        {"symbol": symbol, "occurrences": count}
        for symbol, count in undefined.most_common(100)]
    result["duplicate_definition_count"] = len(multiple)
    result["duplicate_definition_examples"] = sorted(multiple)[:60]
    result["diagnostic_tail"] = errors[-20:]
    if completed.returncode == 0 and target.is_file() and target.stat().st_size:
        result["link_succeeded"] = True
        result["output_bytes"] = target.stat().st_size
        result["output_name"] = target.name
        result["note"] = "Host ELF linked, but no gameplay, save or bootstrap test passed."
    else:
        target.unlink(missing_ok=True)
        result["error"] = "genuine World/M8 native executable link incomplete"
    return result


def verify_compiled_objects(source_audit, data_audit, code_dir, data_dir):
    """Require real compiled source entries to match the linked .o files.

    An old or partial .o that survived a failed build must never be silently
    treated as successful World code. The real linker may still fail, but its
    source inventory must be trustworthy.
    """
    source = json.loads(Path(source_audit).read_text(encoding="utf-8"))
    data = json.loads(Path(data_audit).read_text(encoding="utf-8"))
    crows = source.get("objects", [])
    drows = data.get("results", [])
    if not isinstance(crows, list) or not isinstance(drows, list):
        raise ValueError("malformed real source audit")
    expected_code = {
        Path(row["object"]).name for row in crows
        if row.get("status") == "object_compiled"
    }
    expected_data = {
        Path(row["source"]).with_suffix(".o").name for row in drows
        if row.get("native_object") is True
    }
    actual_code = {p.name for p in Path(code_dir).glob("*.o")}
    actual_data = {p.name for p in Path(data_dir).glob("*.o")}
    if len(expected_code) != len([r for r in crows if r.get("status") == "object_compiled"]):
        raise ValueError("duplicate engine object filenames in compilation audit")
    if len(expected_data) != len([r for r in drows if r.get("native_object") is True]):
        raise ValueError("duplicate original asset object filenames in ASM audit")
    return {
        "source_object_set_verified": bool(expected_code) and expected_code == actual_code,
        "data_object_set_verified": bool(expected_data) and expected_data == actual_data,
        "source_missing_object_files": sorted(expected_code - actual_code)[:50],
        "source_stale_object_files": sorted(actual_code - expected_code)[:50],
        "data_missing_object_files": sorted(expected_data - actual_data)[:50],
        "data_stale_object_files": sorted(actual_data - expected_data)[:50],
    }


def attach_coverage(result, source_audit, data_audit):
    """Attach real compiler coverage; never infer source completeness from link."""
    if source_audit:
        content = json.loads(Path(source_audit).read_text(encoding="utf-8"))
        result["game_sources_all_compiled"] = (
            content["compiled"] == content["requested"] and
            content["requested"] > 0)
        result["source_compiled"] = content["compiled"]
        result["source_requested"] = content["requested"]
    if data_audit:
        content = json.loads(Path(data_audit).read_text(encoding="utf-8"))
        result["game_data_all_compiled"] = (
            content["native_objects"] == content["original_source_files"]
            and content["original_source_files"] > 0)
        result["data_compiled"] = content["native_objects"]
        result["data_requested"] = content["original_source_files"]
    # Booting the real World plus map/save tests are separate mandatory gates.
    result["ready_for_distribution"] = False
    return result



def require_complete_input_coverage(result, report):
    """Reject linked output if genuine C/ASM source inventory is incomplete.

    Matching the files that happened to compile is not proof that *all*
    original World/M8 files compiled. A missing module must never produce
    an apparently successful game executable.
    """
    gates = ("source_object_set_verified", "data_object_set_verified",
             "game_sources_all_compiled", "game_data_all_compiled")
    missing = [key for key in gates if result.get(key) is not True]
    result["full_input_inventory_verified"] = not missing
    if missing:
        result["link_succeeded"] = False
        result["error"] = "original World/M8 compiled inventory is incomplete or mismatched"
        result["input_coverage_failed_gates"] = missing
        # A linker success with omitted game files is not a usable artifact.
        Path(report).with_name(
            "grandworld-WORLD-NOT-BOOT-VERIFIED").unlink(missing_ok=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--report", default="native-M8-full-link-attempt.json")
    parser.add_argument("--source-audit", help="real compiler survey JSON")
    parser.add_argument("--data-audit", help="original ASM source survey JSON")
    args = parser.parse_args()
    result = attempt(args.code, args.data, args.platform,
                     args.frontend, args.report)
    attach_coverage(result, args.source_audit, args.data_audit)
    if args.source_audit and args.data_audit:
        result.update(verify_compiled_objects(args.source_audit, args.data_audit,
                                              args.code, args.data))
        require_complete_input_coverage(result, args.report)
    Path(args.report).write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if not isinstance(value, list)}, indent=2))
    for item in result.get("undefined_reference_examples", [])[:20]:
        print("undefined:", item["symbol"], "x", item["occurrences"])
    if not result["link_succeeded"]:
        print("NOT PLAYABLE: real engine still has unresolved link dependencies.")


if __name__ == "__main__":
    main()
