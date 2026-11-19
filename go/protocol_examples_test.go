package eyepop

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestEveryValidExampleDecodesToAKnownVariantAndEncodesBackUnchanged(t *testing.T) {
	paths, err := filepath.Glob("../protocol/examples/valid/*.json")
	if err != nil || len(paths) < 30 {
		t.Fatalf("found %d examples, err %v", len(paths), err)
	}
	for _, path := range paths {
		name := filepath.Base(path)
		t.Run(name, func(t *testing.T) {
			raw, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			var data any
			if err := json.Unmarshal(raw, &data); err != nil {
				t.Fatal(err)
			}
			var encoded any
			if strings.HasPrefix(name, "command-") {
				command := DecodeCommand(data)
				if _, unknown := command.(UnknownCommand); unknown {
					t.Fatal("decoded to UnknownCommand")
				}
				encoded = command.ToJSON()
			} else {
				message := DecodeMessage(data)
				if _, unknown := message.(UnknownMessage); unknown {
					t.Fatal("decoded to UnknownMessage")
				}
				encoded = message.ToJSON()
			}
			bytes, err := json.Marshal(encoded)
			if err != nil {
				t.Fatal(err)
			}
			var again any
			if err := json.Unmarshal(bytes, &again); err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(again, data) {
				t.Fatalf("encoded %s, want %s", bytes, raw)
			}
		})
	}
}
