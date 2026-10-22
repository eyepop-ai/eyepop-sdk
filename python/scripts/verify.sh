#!/usr/bin/env bash
# Install the published eyepop from PyPI and check eyepop.version() equals the release tag's version.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" pypi)

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
uv venv -q "$scratch/venv"

# A fresh publish takes a moment to show up on the index.
for attempt in 1 2 3 4 5 6; do
  uv pip install -q --python "$scratch/venv/bin/python" --prerelease allow --no-cache "eyepop==$version" && break
  [ "$attempt" -lt 6 ] || { echo "cannot install eyepop==$version" >&2; exit 1; }
  sleep 10
done

cd "$scratch"
"$scratch/venv/bin/python" -I - "$version" <<'PY'
import sys

import eyepop

got = eyepop.version()
assert got == sys.argv[1], f"got {got}, want {sys.argv[1]}"
print("ok", got)
PY
