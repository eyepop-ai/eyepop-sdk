#!/usr/bin/env bash
# Pack every workspace at the release tag's version into OUT. Leaves the tree unchanged.
# usage: TAG=v4.0.0 OUT=dir package.sh
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

# shellcheck source=node/scripts/stamped-build.sh
source scripts/stamped-build.sh
npm pack --workspaces --pack-destination "$out"
