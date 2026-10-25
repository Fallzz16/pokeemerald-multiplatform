#!/usr/bin/env python3
"""Boot exactly one REAL World/M8 frame, but ONLY after complete native link.

This never substitutes game art, title screens, scripts or engine callbacks.
It runs in a temporary working directory and does not touch user .sav files.
A successful link is not a successful boot; both are reported separately.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


MARKERS = ("WORLD_NATIVE_REAL_ENGINE_INIT_RETURNED",
           "WORLD_NATIVE_REAL_ENGINE_FIRST_FRAME_PRESENTED")


def verify(link_report, executable, timeout_seconds=30):
    link = json.loads(Path(link_report).read_text(encoding="utf-8"))
    result = {
        "schema": 1,
        "stage": "P2_real_World_M8_first_frame_smoke",
        "link_succeeded": bool(link.get("link_succeeded")),
        "attempted": False,
        "real_game_initialized": False,
        "real_first_frame_presented": False,
        "save_files_modified": False,
        "gameplay_verified": False,
        "windows_build_verified": False,
    }
    if not result["link_succeeded"]:
        result["reason"] = "The genuine World/M8 linker did not produce an executable."
        return result
    executable = Path(executable).resolve()
    if not executable.is_file():
        result["reason"] = "Link report claims success but executable is missing."
        return result
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    result["attempted"] = True
    with tempfile.TemporaryDirectory(prefix="world-m8-native-boot-") as scratch:
        try:
            proc = subprocess.run([str(executable), "--smoke-test"],
                                  cwd=scratch, env=env, capture_output=True,
                                  text=True, timeout=timeout_seconds)
            result["exit_code"] = proc.returncode
            result["stdout_tail"] = proc.stdout[-4000:]
            result["stderr_tail"] = proc.stderr[-4000:]
            result["real_game_initialized"] = MARKERS[0] in proc.stdout
            result["real_first_frame_presented"] = (
                proc.returncode == 0 and all(m in proc.stdout for m in MARKERS))
        except (subprocess.TimeoutExpired, OSError) as exc:
            result["reason"] = "Boot failed or timed out: " + str(exc)[:500]
        # The disposable working directory is deleted; never use user saves.
        result["disposable_working_directory_used"] = True
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--link-report", required=True)
    p.add_argument("--executable", required=True)
    p.add_argument("--report", default="native-world-boot-smoke.json")
    args = p.parse_args()
    outcome = verify(args.link_report, args.executable)
    Path(args.report).write_text(json.dumps(outcome, indent=2) + "\n",
                                 encoding="utf-8")
    print(json.dumps(outcome, indent=2))
    if outcome["attempted"] and not outcome["real_first_frame_presented"]:
        p.exit(1, "REAL WORLD FIRST-FRAME SMOKE FAILED\n")
    if outcome["link_succeeded"] and not outcome["attempted"]:
        p.exit(1, "Native link claimed success but no binary available\n")


if __name__ == "__main__":
    main()
