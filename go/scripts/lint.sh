#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

unformatted=$(gofmt -l .)
[ -z "$unformatted" ] || { echo "gofmt needed:" >&2; echo "$unformatted" >&2; exit 1; }
go vet ./...
