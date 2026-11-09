// Package eyepop is the EyePop Go SDK (Scaffold package: reports its version only).
package eyepop

import "runtime/debug"

const modulePath = "github.com/eyepop-ai/eyepop-sdk/go/v4"

// Version returns the module version (the git tag go/vX.Y.Z) when consumed as a
// dependency, or "(devel)" when built locally.
func Version() string {
	if bi, ok := debug.ReadBuildInfo(); ok {
		for _, d := range bi.Deps {
			if d.Path == modulePath {
				return d.Version
			}
		}
	}
	return "(devel)"
}
