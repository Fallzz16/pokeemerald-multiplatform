#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "This source tree is Emerald Vanilla+ v0.3.4; running the current verifier."
exec bash "$ROOT/scripts/verify_v034.sh"
