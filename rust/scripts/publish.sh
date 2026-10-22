#!/usr/bin/env bash
# Stamp the release tag's version and publish the eyepop crate to crates.io. Safe to re-run.
# CARGO_REGISTRY_TOKEN comes from the CI environment.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)

scripts/stamp.sh
# The stamp leaves the tree dirty on purpose, so cargo must be told that is fine.
if [ -n "$dry_run" ]; then
  cargo publish --dry-run --allow-dirty -p eyepop
  exit 0
fi

# crates.io rejects API calls without a User-Agent.
status=$(curl -s --max-time 20 -o /dev/null -w '%{http_code}' -A "eyepop-sdk-release (https://github.com/eyepop-ai/eyepop-sdk)" \
  "https://crates.io/api/v1/crates/eyepop/$version")
case $status in
  200) echo "eyepop $version is already on crates.io, skipping" ;;
  404) cargo publish --allow-dirty -p eyepop ;;
  *) echo "crates.io lookup failed: HTTP $status" >&2; exit 1 ;;
esac
