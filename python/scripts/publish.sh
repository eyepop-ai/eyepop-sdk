#!/usr/bin/env bash
# Build at the release tag's version and upload it to PyPI. Safe to re-run.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" pypi)

scripts/build.sh
uvx twine check dist/*
[ -z "$dry_run" ] || exit 0

status=$(curl -s -o /dev/null -w '%{http_code}' "https://pypi.org/pypi/eyepop/$version/json")
case $status in
  200) echo "eyepop $version is already on PyPI, skipping" ;;
  404) uv publish --trusted-publishing always ;;
  *) echo "PyPI lookup failed: HTTP $status" >&2; exit 1 ;;
esac
