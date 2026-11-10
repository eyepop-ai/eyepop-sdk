# shellcheck shell=bash
# Sourced by package.sh and publish.sh, from node/, with TAG set. Installs, stamps the release tag's version
# into the manifests, builds, and puts the manifests back on exit so the tree is left as it was found.
stamped=(package.json package-lock.json packages/*/package.json)

npm ci --no-audit --no-fund
[ -z "$(git status --porcelain -- "${stamped[@]}")" ] || { echo "uncommitted changes in the node manifests, refusing to stamp" >&2; exit 1; }
trap 'git checkout -- "${stamped[@]}"' EXIT
scripts/stamp.sh
npm run build --workspaces
