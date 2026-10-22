#!/usr/bin/env bash
# Publish every workspace to npm at the release tag's version. Safe to re-run.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
want=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" npm)
workspaces=$(node scripts/workspaces.mjs list) # "dir name version" lines, dependencies first
[ -n "$workspaces" ] || { echo "no workspaces found" >&2; exit 1; }

# Publish nothing unless every manifest carries the tag's version.
while read -r _ name version; do
  [ "$version" = "$want" ] || { echo "$name is $version, expected $want: run stamp first" >&2; exit 1; }
done <<<"$workspaces"

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
