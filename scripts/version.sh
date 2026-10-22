#!/usr/bin/env bash
# Map a release tag (vX.Y.Z or vX.Y.Z-{alpha,beta,rc}.N) to one ecosystem's version.
# usage: version.sh <tag> <npm|cargo|nuget|pypi|go-tag>
set -euo pipefail

tag=${1:?tag required}
eco=${2:?ecosystem required}

re='^v([0-9]+\.[0-9]+\.[0-9]+)(-(alpha|beta|rc)\.([0-9]+))?$'
[[ $tag =~ $re ]] || { echo "invalid release tag: $tag" >&2; exit 1; }
core=${BASH_REMATCH[1]} pre=${BASH_REMATCH[3]:-} n=${BASH_REMATCH[4]:-}

case $eco in
  npm | cargo | nuget) echo "$core${pre:+-$pre.$n}" ;;
  pypi) echo "$core${pre:+$([[ $pre == alpha ]] && echo a || { [[ $pre == beta ]] && echo b || echo rc; })$n}" ;;
  go-tag) echo "go/$tag" ;;
  *) echo "unknown ecosystem: $eco" >&2; exit 1 ;;
esac
