#!/usr/bin/env bash
# Pack artifacts/EyePop.<version>.nupkg at the release tag's version.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" nuget)

rm -rf artifacts
dotnet pack src/EyePop/EyePop.csproj -c Release -o artifacts -p:Version="$version"
