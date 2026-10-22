#!/usr/bin/env bash
# Build the sdist and wheel into dist/. Without TAG the version is 0.0.0.
set -euo pipefail
cd "$(dirname "$0")/.."

version=0.0.0
[ -z "${TAG:-}" ] || version=$(../scripts/version.sh "$TAG" pypi)

rm -rf dist
SETUPTOOLS_SCM_PRETEND_VERSION=$version uv build
