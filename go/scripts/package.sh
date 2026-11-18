#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

tag=${TAG:?set TAG, e.g. v4.0.0}
../scripts/version.sh "$tag" go-tag >/dev/null
git -C .. archive --format=zip -o "$out/eyepop-go-$tag.zip" HEAD go
