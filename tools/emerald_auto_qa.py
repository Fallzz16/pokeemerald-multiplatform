"""Emerald Hybrid Auto QA: deterministic regression runner, never edits real saves.

This runner exercises the existing production-server socket tests, simulated
players, launcher lifecycle and safety tests. It does NOT claim to drive the
graphical Emerald game or validate sprites / real in-game save operations.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SUITES = {
    "lab": (
        "test_ehl8_m23a_server_first.py",
        "test_emerald_qa_lab.py",
        "test_emerald_qa_lobby.py",
        "test_ehl8_m23_host_start.py",
        "test_ehl8_m23_bundle_safety.py",
    ),
    "protocol": (
        "test_emerald_qa_bots.py",
        "test_emerald_session_server.py",
        "test_ehl8_m30_port_lifecycle.py",
        "test_ehl8_launcher_manual_host.py",
        "test_emerald_session_admin.py",
        "test_ehl8_resume_v1.py",
        "test_ehl8_native_bridge.py",
        "test_ehl8_native_reconnect.py",
    ),
    "safety": (
        "test_emerald_launcher.py",
        "test_emerald_auto_qa_runner.py",
        "test_ehl8_m22b_bundle_safety.py",
        "test_emerald_qa_bots.py",
        "test_lan_remote_palette_regression.py",
    ),
}
# Explicit allowlist, bounded output, and no shell execution.
def execute(root: Path, pattern: str, timeout: int):
    started = time.monotonic()
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests",
               "-p", pattern, "-v"]
    try:
        result = subprocess.run(command, cwd=root, capture_output=True,
                                text=True, timeout=timeout, check=False,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        combined = (result.stdout + "\n" + result.stderr)[-24000:]
        return {"suite": pattern, "status": "PASS" if result.returncode == 0 else "FAIL",
                "exit_code": result.returncode, "seconds": round(time.monotonic()-started, 3),
                "output": combined}
    except subprocess.TimeoutExpired as exc:
        return {"suite": pattern, "status": "TIMEOUT", "exit_code": None,
                "seconds": round(time.monotonic()-started, 3),
                "output": "Test exceeded timeout; child process was stopped."}

def run(root: Path, group: str = "all", repeats: int = 1, timeout: int = 120):
    if not (1 <= repeats <= 20 and 5 <= timeout <= 600):
        raise ValueError("Use repeats 1..20 and timeout 5..600 seconds")
    selected = tuple(dict.fromkeys(p for g in (SUITES if group == "all" else (group,))
                                   for p in SUITES[g]))
    # Fail closed if source tree is not complete.
    missing = [name for name in selected if not (root / "tests" / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing test files: " + ", ".join(missing))
    rows = []
    # Native bridge tests build POSIX C fixtures with gcc -D_POSIX_C_SOURCE.
    # Keep real native socket coverage on Linux; do not mislabel a Windows
    # toolchain mismatch as an Emerald multiplayer/gameplay failure.
    posix_only = {'test_ehl8_native_bridge.py', 'test_ehl8_native_reconnect.py'}
    for repeat in range(1, repeats+1):
        for pattern in selected:
            if os.name == 'nt' and pattern in posix_only:
                item = {'suite': pattern, 'status': 'SKIP', 'exit_code': None,
                        'seconds': 0, 'output': 'POSIX native fixture: Linux-only; Windows QA suites still execute.'}
            else:
                item = execute(root, pattern, timeout)
            item['iteration'] = repeat
            rows.append(item)
            print(f"[{repeat}/{repeats}] {pattern}: {item['status']}", flush=True)
    return {"schema": 1, "project": "Emerald Hybrid", "runner": "AUTO_QA",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "group": group, "repeats": repeats, "results": rows,
            "passed": sum(x["status"] == "PASS" for x in rows),
            "failed": sum(x["status"] in ("FAIL", "TIMEOUT") for x in rows),
            "skipped": sum(x["status"] == "SKIP" for x in rows),
            "limitations": [
                "Automated tests include simulated protocol players and production server integration.",
                "Does not press controls inside pokeemerald.exe or validate pixels, animations or live save integrity.",
                "Legacy GBA ROM Compare and real Windows UI/gameplay require separate validation.",
            ]}

def main(argv=None):
    parser = argparse.ArgumentParser(description="Emerald Hybrid autonomous regression QA")
    parser.add_argument("--group", choices=["all", *SUITES], default="all")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--report", type=Path, default=Path("auto-qa-report.json"))
    args = parser.parse_args(argv)
    if not (1 <= args.repeats <= 20 and 5 <= args.timeout <= 600):
        parser.error("Invalid repeats or timeout")
    root = Path(__file__).resolve().parent.parent
    report = run(root, args.group, args.repeats, args.timeout)
    path = args.report.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"AUTO QA: {report['passed']} passed, {report['failed']} failed; {path}", flush=True)
    return 1 if report["failed"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
