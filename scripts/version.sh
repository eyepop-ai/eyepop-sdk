#!/usr/bin/env bash
# usage: version.sh <tag> <npm|cargo|nuget|pypi|go-tag>
set -euo pipefail

tag=${1:?tag required}
ecosystem=${2:?ecosystem required}

pattern='^v([0-9]+\.[0-9]+\.[0-9]+)(-(alpha|beta|rc)\.([0-9]+))?$'
[[ $tag =~ $pattern ]] || { echo "invalid release tag: $tag" >&2; exit 1; }
core=${BASH_REMATCH[1]}     # 4.0.0
stage=${BASH_REMATCH[3]:-}  # alpha, beta, rc, or empty for a stable release
number=${BASH_REMATCH[4]:-} # 1

leading_zero='(^|\.)0[0-9]'
if [[ $core =~ $leading_zero || $number =~ $leading_zero ]]; then
  echo "invalid release tag (leading zero): $tag" >&2
  exit 1
fi

semver=$core${stage:+-$stage.$number}

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
