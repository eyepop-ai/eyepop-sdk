#!/usr/bin/env bash
# usage: verify-tag.sh vX.Y.Z
set -euo pipefail
cd "$(dirname "$0")"

tag=${1:?usage: verify-tag.sh vX.Y.Z}

# Until every Language SDK is ready, only v4.0.0 and v4.0.0-* may be released.
[[ $tag == v4.0.0 || $tag == v4.0.0-* ]] || { echo "only v4.0.0 and v4.0.0-* may be released: $tag" >&2; exit 1; }
for ecosystem in npm pypi cargo nuget go-tag; do
  # Assign first: a failure inside echo "$(...)" would not stop the script.
  version=$(./version.sh "$tag" "$ecosystem")
  echo "$ecosystem: $version"
done
