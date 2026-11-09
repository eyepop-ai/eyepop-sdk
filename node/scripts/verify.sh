#!/usr/bin/env bash
# Install each published package from npm and check eyepop.version() equals the release tag's version.
set -euo pipefail
cd "$(dirname "$0")/.."

want=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" npm)
names=$(node scripts/workspaces.mjs list | cut -d' ' -f2)

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
npm init -y >/dev/null

for name in $names; do
  # A fresh publish takes a moment to show up on the registry.
  for attempt in 1 2 3 4 5 6; do
    npm install --no-audit --no-fund --prefer-online "$name@$want" >/dev/null 2>&1 && break
    [ "$attempt" -lt 6 ] || { echo "cannot install $name@$want" >&2; exit 1; }
    sleep 10
  done

  node --input-type=module - "$name" "$want" <<'JS'
import { createRequire } from 'node:module'

const [name, want] = process.argv.slice(2)
const esm = (await import(name)).eyepop.version()
const cjs = createRequire(`${process.cwd()}/`)(name).eyepop.version()
if (esm !== want || cjs !== want) {
  console.error(`${name}: esm=${esm} cjs=${cjs}, want ${want}`)
  process.exit(1)
}
console.log(`ok ${name}@${want}`)
JS
done
