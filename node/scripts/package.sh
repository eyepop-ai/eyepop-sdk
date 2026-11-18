#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

# shellcheck source=node/scripts/stamped-build.sh
source scripts/stamped-build.sh
npm pack --workspaces --pack-destination "$out"
