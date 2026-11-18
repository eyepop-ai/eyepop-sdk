#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
: "${TAG:?set TAG, e.g. v4.0.0}"

scripts/build.sh
uvx twine check dist/*
[ -z "$dry_run" ] || exit 0

uv publish --trusted-publishing always --check-url https://pypi.org/simple/
