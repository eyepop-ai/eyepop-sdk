#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${OUT:?set OUT}"
out=$(cd "$OUT" && pwd)
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" nuget)

dotnet pack src/EyePop/EyePop.csproj -c Release -o "$out" -p:Version="$version"
