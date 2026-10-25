#!/usr/bin/env bash
# Run in the MSYS2 MINGW64 shell only. Bundle non-system dynamic dependencies
# so the diagnostic host works when launched outside the GitHub Actions PATH.
set -euo pipefail
out="${1:?Usage: bundle_mingw_dlls.sh OUTPUT_DIR}"
test -d "$out"
shopt -s nullglob nocaseglob
queue=( "$out"/*.exe )
declare -A scanned=()
while (("${#queue[@]}" > 0)); do
    current="${queue[0]}"
    queue=("${queue[@]:1}")
    key="${current,,}"
    [[ -n "${scanned[$key]:-}" ]] && continue
    scanned["$key"]=1
    while IFS= read -r dll; do
        src="/mingw64/bin/$dll"
        if [[ -f "$src" ]]; then
            dst="$out/$dll"
            if [[ ! -f "$dst" ]]; then
                cp "$src" "$dst"
                queue+=( "$dst" )
            fi
        fi
    done < <(objdump -p "$current" | awk '/DLL Name:/{print $3}')
done
printf 'Bundled %s non-system DLL files\n' "$(find "$out" -maxdepth 1 -iname '*.dll' | wc -l)"
