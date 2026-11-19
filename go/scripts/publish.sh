#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=${1:-}
tag=${TAG:?set TAG, e.g. v4.0.0}
go_tag=$(../scripts/version.sh "$tag" go-tag)
module=$(go list -m)

major=${module##*/v}
[[ $tag == v$major.* ]] || { echo "tag $tag does not match module path $module" >&2; exit 1; }

go vet ./...
if [ -n "$dry_run" ]; then
  echo "would push tag $go_tag for $module"
  exit 0
fi

head=$(git rev-parse HEAD)
remote=$(git ls-remote origin "refs/tags/$go_tag" | cut -f1)
if [ -n "$remote" ]; then
  [ "$remote" = "$head" ] || { echo "$go_tag on origin is $remote, not HEAD $head" >&2; exit 1; }
  echo "$go_tag is already on origin, skipping the push"
else
  git rev-parse -q --verify "refs/tags/$go_tag" >/dev/null || git tag "$go_tag"
  [ "$(git rev-parse "$go_tag^{commit}")" = "$head" ] || { echo "local $go_tag is not at HEAD $head" >&2; exit 1; }
  git push origin "refs/tags/$go_tag"
fi

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
GOWORK=off GOFLAGS=-mod=mod GOPROXY=https://proxy.golang.org go list -m "$module@$tag"
