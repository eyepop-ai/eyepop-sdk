#!/usr/bin/env bash
# Print each release job's result and fail unless every one succeeded.
# NEEDS is the workflow's `needs` context as JSON.
set -euo pipefail

echo "${NEEDS:?set NEEDS}" | jq -r 'to_entries[] | "\(.key): \(.value.result)"'
echo "$NEEDS" | jq -e 'all(.[]; .result == "success")' >/dev/null
