#!/usr/bin/env bash
# usage: verify-tag.sh vX.Y.Z
set -euo pipefail
cd "$(dirname "$0")"

tag=${1:?usage: verify-tag.sh vX.Y.Z}
for ecosystem in npm pypi cargo nuget go-tag; do
  # Assign first: a failure inside echo "$(...)" would not stop the script.
  version=$(./version.sh "$tag" "$ecosystem")
  echo "$ecosystem: $version"
done
