# shellcheck shell=bash
# Sourced by package.sh and publish.sh, from rust/, with TAG set. Stamps the release tag's version into the
# manifest and puts the manifest and lockfile back on exit so the tree is left as it was found.
# cargo needs --allow-dirty because of the stamp, so the stamp must be the only change that gets packaged.
[ -z "$(git status --porcelain -- .)" ] || { echo "uncommitted changes in rust/, refusing to stamp" >&2; exit 1; }
trap 'git checkout -- crates/eyepop/Cargo.toml Cargo.lock' EXIT
scripts/stamp.sh
