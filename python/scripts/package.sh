#!/usr/bin/env bash
# Build the sdist and wheel at the release tag's version into OUT.
# usage: TAG=v4.0.0 OUT=dir package.sh
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

: "${TAG:?set TAG, e.g. v4.0.0}"
scripts/build.sh
cp -f dist/* "$out"
