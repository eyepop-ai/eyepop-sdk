#!/usr/bin/env bash
# Stamp the release tag's version and publish the eyepop crate to crates.io. Safe to re-run.
# CARGO_REGISTRY_TOKEN comes from the CI environment.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)

# cargo needs --allow-dirty because of the stamp, so the stamp must be the only change that gets published.
if [ -z "$dry_run" ] && [ -n "$(git status --porcelain -- .)" ]; then
  echo "uncommitted changes in rust/, refusing to publish (revert a leftover stamp with git checkout)" >&2
  exit 1
fi

scripts/stamp.sh
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
