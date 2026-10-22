#!/usr/bin/env bash
# Fail if any file is not gofmt-formatted, then run go vet.
set -euo pipefail
cd "$(dirname "$0")/.."

unformatted=$(gofmt -l .)
[ -z "$unformatted" ] || { echo "gofmt needed:" >&2; echo "$unformatted" >&2; exit 1; }
go vet ./...
