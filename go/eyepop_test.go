package eyepop

import "testing"

// Run from this module itself, there is no dependency on it, so the build is local.
func TestVersionIsDevelLocally(t *testing.T) {
	if got := Version(); got != "(devel)" {
		t.Fatalf("Version() = %q, want (devel)", got)
	}
}
