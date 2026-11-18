#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

: "${TAG:?set TAG, e.g. v4.0.0}"
scripts/build.sh
cp -f dist/* "$out"
