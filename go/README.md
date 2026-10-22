# EyePop Go SDK

Scaffold package. Version comes from the git tag `go/vX.Y.Z` (no file holds it).

Module path is `github.com/eyepop-ai/eyepop-sdk/go/v4`: Go requires a `/vN`
suffix on the module path for major versions 2 and up, and the 4.0.0 line
must therefore import as `.../go/v4`. A future v5 means changing go.mod and
every import to `/v5`.

## Release

`task publish TAG=vX.Y.Z` creates and pushes the git tag `go/vX.Y.Z` (only if
absent on origin) and then asks proxy.golang.org for it. The release workflow
does not push this tag itself. `Version()` reports the module version when the
package is consumed as a dependency and `(devel)` when built from this checkout.
