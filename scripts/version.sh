#!/usr/bin/env bash
# Map a release tag (vX.Y.Z or vX.Y.Z-{alpha,beta,rc}.N) to one ecosystem's version.
# usage: version.sh <tag> <npm|cargo|nuget|pypi|go-tag>
set -euo pipefail

tag=${1:?tag required}
ecosystem=${2:?ecosystem required}

pattern='^v([0-9]+\.[0-9]+\.[0-9]+)(-(alpha|beta|rc)\.([0-9]+))?$'
[[ $tag =~ $pattern ]] || { echo "invalid release tag: $tag" >&2; exit 1; }
core=${BASH_REMATCH[1]}     # 4.0.0
stage=${BASH_REMATCH[3]:-}  # alpha, beta, rc, or empty for a stable release
number=${BASH_REMATCH[4]:-} # 1

# npm, cargo and nuget all take semver as is: 4.0.0-alpha.1
semver=$core${stage:+-$stage.$number}

# PyPI wants PEP 440: 4.0.0-alpha.1 becomes 4.0.0a1
case $stage in
  alpha) pep440=${core}a$number ;;
  beta) pep440=${core}b$number ;;
  rc) pep440=${core}rc$number ;;
  *) pep440=$core ;;
esac

case $ecosystem in
  npm | cargo | nuget) echo "$semver" ;;
  pypi) echo "$pep440" ;;
  go-tag) echo "go/$tag" ;;
  *) echo "unknown ecosystem: $ecosystem" >&2; exit 1 ;;
esac
