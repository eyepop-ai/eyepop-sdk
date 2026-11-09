#!/usr/bin/env bash
# Self-check for version.sh. Run: scripts/version.test.sh
set -euo pipefail
cd "$(dirname "$0")"
fail=0
check() { # tag eco expected
  got=$(./version.sh "$1" "$2" 2>/dev/null || echo ERROR)
  [[ $got == "$3" ]] || { echo "FAIL $1 $2: got $got want $3"; fail=1; }
}
check v4.0.0 npm 4.0.0
check v4.0.0-alpha.1 npm 4.0.0-alpha.1
check v4.0.0-alpha.1 cargo 4.0.0-alpha.1
check v4.0.0-alpha.1 nuget 4.0.0-alpha.1
check v4.0.0-alpha.1 pypi 4.0.0a1
check v4.0.0-beta.2 pypi 4.0.0b2
check v4.0.0-rc.3 pypi 4.0.0rc3
check v4.0.0 pypi 4.0.0
check v4.0.0-alpha.1 go-tag go/v4.0.0-alpha.1
check 4.0.0 npm ERROR
check v4.0 npm ERROR
check v4.0.0-foo.1 npm ERROR
check v4.0.0-rc.01 npm ERROR
check v04.0.0 npm ERROR
check v4.00.0 npm ERROR
check v4.0.0-rc.0 npm 4.0.0-rc.0
check v0.0.0 npm 0.0.0
check v4.0.0 bogus ERROR
exit $fail
