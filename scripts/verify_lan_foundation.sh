#!/usr/bin/env bash
# Fast, isolated TCP link regression tests for the experimental hybrid branch.
set -euo pipefail
cd "$(dirname "$0")/.."

test -f src/lnet/lnet_link.c
test -f src/lnet/lnet_culling.c
grep -q 'LanRemoteIntersectsCamera' src/link.c
grep -q 'LAN_REMOTE_PREFETCH_PX 32' src/link.c
grep -q 'LAN_REMOTE_RETAIN_PX 48' src/link.c
test -f src/lnet/lnet_net.c
test -f src/lnet/lnet_session.c
test -f src/lnet/lnet_sio.c
grep -q 'void LanLinkOpenAsHost' src/link.c
grep -q 'bool8 HandleLinkConnection' src/link.c
# The native emulation must deliver completed TCP SIO words through Emerald's
# real serial interrupt callback. A missing registration silently kills the
# Cable Club handshake even when TCP connect and HELLO tests pass.
grep -q 'SetSerialCallback(SerialCB)' src/link.c
grep -q 'SetSerialCallback(NULL)' src/link.c
grep -q 'android.permission.INTERNET' android/app/src/main/AndroidManifest.xml
grep -q -- '--lan-host=' src/platform/sdl2.c
grep -q -- '--lan-client=' src/platform/sdl2.c
if grep -q 'STUB_FUNC_QUIET_BLOCK(bool8 HandleLinkConnection' src/stub.c; then
  echo "ERROR: old link stub still overrides real implementation"
  exit 1
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
source_files=(src/lnet/lnet_net.c src/lnet/lnet_session.c src/lnet/lnet_sio.c src/lnet/lnet_link.c src/lnet/lnet_presence.c src/lnet/lnet_culling.c)
for test_name in session link disconnect cable_handshake presence culling; do
    cc -DPORTABLE -std=gnu99 -Wall -Wextra -O2 -pthread \
       -I src/lnet "tests/test_lnet_${test_name}.c" \
       "${source_files[@]}" -o "$tmp/test_lnet_${test_name}"
    timeout 25s "$tmp/test_lnet_${test_name}"
done
echo "Native LAN transport tests passed. Gameplay exchange still requires 2-device QA."
