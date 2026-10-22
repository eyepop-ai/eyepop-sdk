#!/usr/bin/env bash
# Push the go/vX.Y.Z git tag for the release tag, then ask proxy.golang.org to fetch it. Safe to re-run.
# Go has no registry upload: the git tag is the release.
# usage: publish.sh [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
tag=${TAG:?set TAG, e.g. v4.0.0}
go_tag=$(../scripts/version.sh "$tag" go-tag)
module=$(go list -m)

go vet ./...
if [ -n "$dry_run" ]; then
  echo "would push tag $go_tag for $module"
  exit 0
fi

if git ls-remote --exit-code --tags origin "refs/tags/$go_tag" >/dev/null 2>&1; then
  echo "$go_tag is already on origin, skipping the push"
else
  git tag "$go_tag"
  git push origin "refs/tags/$go_tag"
fi

# Asking the proxy now means the first `go get` does not wait on it.
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
GOWORK=off GOFLAGS=-mod=mod GOPROXY=https://proxy.golang.org go list -m "$module@$tag"
