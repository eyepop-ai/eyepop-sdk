#!/usr/bin/env bash
# Stamp, build and publish every workspace to npm at the release tag's version. Safe to re-run. Leaves the tree unchanged.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
want=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" npm)

# shellcheck source=node/scripts/stamped-build.sh
source scripts/stamped-build.sh

workspaces=$(node scripts/workspaces.mjs list) # "dir name version" lines, dependencies first
[ -n "$workspaces" ] || { echo "no workspaces found" >&2; exit 1; }

# Prereleases go to the "next" dist-tag so a plain `npm install` never picks them up.
case $want in *-*) dist_tag=next ;; *) dist_tag=latest ;; esac

while read -r dir name version; do
  if [ -n "$dry_run" ]; then
    npm publish --workspace "$dir" --tag "$dist_tag" --dry-run </dev/null
  elif [ -n "$(npm view "$name@$version" version 2>/dev/null </dev/null)" ]; then
    echo "$name@$version is already published, skipping"
  else
    npm publish --workspace "$dir" --tag "$dist_tag" --provenance </dev/null
  fi
done <<<"$workspaces"
