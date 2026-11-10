#!/usr/bin/env bash
# Package the eyepop crate at the release tag's version into OUT. Leaves the tree unchanged.
# usage: TAG=v4.0.0 OUT=dir package.sh
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)

# shellcheck source=rust/scripts/stamped.sh
source scripts/stamped.sh
cargo package -p eyepop --allow-dirty
target=$(cargo metadata --format-version 1 --no-deps | jq -r .target_directory)
cp -f "$target/package/eyepop-$version.crate" "$out"
