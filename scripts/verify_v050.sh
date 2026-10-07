#!/usr/bin/env bash
# Source/asset regression suite. Build and runtime QA are still required.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify_v050_split.py
python3 scripts/verify_v050_fairy.py
python3 scripts/test_v050_damage.py
bash scripts/verify_v034.sh
printf '\nEmerald Vanilla+ Hybrid v0.5.0 static integration QA passed.\n'
