#!/usr/bin/env bash
# Build a scratch project against the published crate and check eyepop::version() equals the release tag's version.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(../scripts/version.sh "${TAG:?set TAG, e.g. v4.0.0}" cargo)

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
mkdir src
cat >Cargo.toml <<TOML
[package]
name = "verify"
version = "0.0.0"
edition = "2021"

[dependencies]
eyepop = "=$version"
TOML
echo 'fn main() { println!("{}", eyepop::version()); }' >src/main.rs

# A fresh publish takes a moment to show up in the index.
for attempt in 1 2 3 4 5 6; do
  cargo build -q && break
  [ "$attempt" -lt 6 ] || { echo "cannot build against eyepop $version" >&2; exit 1; }
  sleep 10
done

got=$(cargo run -q)
[ "$got" = "$version" ] || { echo "got $got, want $version" >&2; exit 1; }
echo "ok eyepop $got"
