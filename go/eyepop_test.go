package eyepop

import "testing"

func TestVersionIsDevelLocally(t *testing.T) {
	if got := Version(); got != "(devel)" {
		t.Fatalf("Version() = %q, want (devel)", got)
	}
}
