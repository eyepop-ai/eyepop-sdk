#!/usr/bin/env bash
# Build at the release tag's version and upload it to PyPI. Safe to re-run: files PyPI already has are skipped.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
: "${TAG:?set TAG, e.g. v4.0.0}"

scripts/build.sh
uvx twine check dist/*
[ -z "$dry_run" ] || exit 0

uv publish --trusted-publishing always --check-url https://pypi.org/simple/
