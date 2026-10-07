#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export EMERALD_V060_QA=1
bash scripts/verify_v050.sh
python3 scripts/verify_v060.py
printf '\nEmerald Vanilla+ Hybrid v0.6.0 static QA PASSED (Windows runtime QA pending).\n'
