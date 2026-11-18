#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

version=0.0.0
[ -z "${TAG:-}" ] || version=$(../scripts/version.sh "$TAG" pypi)

rm -rf dist
SETUPTOOLS_SCM_PRETEND_VERSION=$version uv build
