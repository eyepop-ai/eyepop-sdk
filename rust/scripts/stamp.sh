#!/usr/bin/env bash
# Write the release tag's version into the eyepop crate's manifest.
# shortcut: one hard-coded crate, loop over crates/*/ when a second one is added.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)
manifest=crates/eyepop/Cargo.toml

# The first `version = ` line in the manifest is the [package] one.
sed -E "1,/^version = /s/^version = \".*\"/version = \"$version\"/" "$manifest" >"$manifest.tmp"
mv -f "$manifest.tmp" "$manifest"
grep -qx "version = \"$version\"" "$manifest"
echo "stamped $version"
