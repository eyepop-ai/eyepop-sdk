#!/usr/bin/env bash
# Pack at the release tag's version and push it to nuget.org. Safe to re-run: --skip-duplicate ignores a version already there.
# NUGET_API_KEY comes from the CI environment.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}

scripts/pack.sh
[ -z "$dry_run" ] || exit 0

: "${NUGET_API_KEY:?set NUGET_API_KEY}"
dotnet nuget push artifacts/*.nupkg --source https://api.nuget.org/v3/index.json --api-key "$NUGET_API_KEY" --skip-duplicate
