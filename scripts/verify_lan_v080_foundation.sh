#!/usr/bin/env bash
# Standalone v0.8 protocol and save-profile tests; NEVER creates gameplay saves.
set -euo pipefail
cd "$(dirname "$0")/.."
DIR="$(mktemp -d)"
trap 'rm -rf "$DIR"' EXIT
: "${CC:=cc}"
BASE_FLAGS=(-std=c99 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -pedantic -O1 -g)
if [[ "${SANITIZE:-0}" == "1" ]]; then
  BASE_FLAGS+=(-fsanitize=address,undefined -fno-omit-frame-pointer)
fi
"$CC" "${BASE_FLAGS[@]}" -I src/lnet \
  src/lnet/lnet_session_v1.c tests/test_lnet_session_v1.c \
  -o "$DIR/test_session_v1"
"$DIR/test_session_v1"
"$CC" "${BASE_FLAGS[@]}" -I src/profile \
  src/profile/save_profiles.c tests/test_save_profiles.c \
  -o "$DIR/test_profiles"
"$DIR/test_profiles"
"$CC" "${BASE_FLAGS[@]}" -I src/profile \
  src/profile/save_profiles.c tools/emerald_profilectl.c \
  -o "$DIR/emerald_profilectl"
"$DIR/emerald_profilectl" --help > /dev/null
mkdir -p "$DIR/profiles"
"$DIR/emerald_profilectl" new "$DIR/profiles" new_game > /dev/null
test -s "$DIR/profiles/new_game/pokeemerald.sav"
# Erased flash is intentionally not yet a valid saved game.
if "$DIR/emerald_profilectl" backup "$DIR/profiles" new_game > /dev/null 2>&1; then
  echo "ERROR: erased-flash new game was incorrectly accepted for backup" >&2
  exit 1
fi
if "$DIR/emerald_profilectl" new "$DIR/profiles" ../escape > /dev/null 2>&1; then
  echo "ERROR: profile path traversal was accepted" >&2
  exit 1
fi
echo 'passed: developer CLI new/profile isolation/invalid save rejected'
echo 'v0.8 M0/M1 standalone tests: PASS (does not prove gameplay integration)'
