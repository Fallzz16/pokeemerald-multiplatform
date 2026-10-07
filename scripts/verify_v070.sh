#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/verify_v060.sh
python3 scripts/verify_v070.py
if python3 -c 'import PIL' >/dev/null 2>&1; then
    PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_sprite_bridge.py
else
    echo 'WARNING: Pillow missing; sprite image conversion unit tests NOT EXECUTED.'
    echo 'Install Pillow only when importing sprites (or for full CI QA).'
fi
printf '\nEmerald Hybrid v0.7 static source QA complete; Windows native runtime still PENDING.\n'
