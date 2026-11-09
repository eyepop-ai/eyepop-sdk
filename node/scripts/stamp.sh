#!/usr/bin/env bash
# Write the release tag's version into every workspace manifest.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" npm)
npm version "$version" --no-git-tag-version --allow-same-version --workspaces >/dev/null
node scripts/workspaces.mjs ranges "$version"
echo "stamped $version"
