#!/usr/bin/env bash
# Fetch the published module through the Go proxy and check eyepop.Version() equals the release tag.
set -euo pipefail
cd "$(dirname "$0")/.."

tag=${TAG:?set TAG, e.g. v4.0.0}
module=$(go list -m)

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
go mod init scratch >/dev/null 2>&1
cat >main.go <<GO
package main

import (
	"fmt"

	"$module"
)

func main() { fmt.Print(eyepop.Version()) }
GO

export GOWORK=off GOFLAGS=-mod=mod GOPROXY=https://proxy.golang.org
# A fresh tag takes a moment to show up on the proxy.
for attempt in 1 2 3 4 5 6; do
  go get "$module@$tag" && break
  [ "$attempt" -lt 6 ] || { echo "cannot fetch $module@$tag" >&2; exit 1; }
  sleep 10
done

got=$(go run .)
[ "$got" = "$tag" ] || { echo "got $got, want $tag" >&2; exit 1; }
echo "ok $module@$got"
