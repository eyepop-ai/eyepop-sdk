#!/usr/bin/env bash
set -euo pipefail

echo "${NEEDS:?set NEEDS}" | jq -r 'to_entries[] | "\(.key): \(.value.result)"'
echo "$NEEDS" | jq -e 'all(.[]; .result == "success")' >/dev/null
