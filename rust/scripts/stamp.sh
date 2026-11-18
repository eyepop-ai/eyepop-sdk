#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)
manifest=crates/eyepop/Cargo.toml

sed -E "1,/^version = /s/^version = \".*\"/version = \"$version\"/" "$manifest" >"$manifest.tmp"
mv -f "$manifest.tmp" "$manifest"
grep -qx "version = \"$version\"" "$manifest"
echo "stamped $version"
