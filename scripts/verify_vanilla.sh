#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "This source tree is Emerald Vanilla+ v0.3 Classic Enhanced; running the v0.3 preservation verifier."
exec bash "$ROOT/scripts/verify_modern_ui.sh"
