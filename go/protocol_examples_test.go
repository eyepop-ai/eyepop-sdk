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

func TestDecodingCasesAreKnownOrUnknownAndKeepExactNumbers(t *testing.T) {
	raw, err := os.ReadFile("../protocol/examples/decoding.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		Name  string `json:"name"`
		Union string `json:"union"`
		Text  string `json:"text"`
		Known bool   `json:"known"`
		Keeps string `json:"keeps"`
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		t.Run(c.Name, func(t *testing.T) {
			decoder := json.NewDecoder(strings.NewReader(c.Text))
			decoder.UseNumber()
			var data any
			if err := decoder.Decode(&data); err != nil {
				t.Fatal(err)
			}
			var known bool
			var encoded any
			if c.Union == "command" {
				command := DecodeCommand(data)
				_, unknown := command.(UnknownCommand)
				known, encoded = !unknown, command.ToJSON()
			} else {
				message := DecodeMessage(data)
				_, unknown := message.(UnknownMessage)
				known, encoded = !unknown, message.ToJSON()
			}
			if known != c.Known {
				t.Fatalf("known = %v, want %v", known, c.Known)
			}
			bytes, err := json.Marshal(encoded)
			if err != nil {
				t.Fatal(err)
			}
			if c.Keeps != "" && !strings.Contains(string(bytes), c.Keeps) {
				t.Fatalf("encoded %s, want it to contain %s", bytes, c.Keeps)
			}
		})
	}
}

func TestEncodedValuesDecodeWithoutATextRoundTrip(t *testing.T) {
	values := []Message{
		Credit{Id: "c1", Bytes: 1},
	}
	for _, value := range values {
		if _, unknown := DecodeMessage(value.ToJSON()).(UnknownMessage); unknown {
			t.Fatalf("%T decoded to UnknownMessage", value)
		}
	}
	command := SetPop{Id: "p1", Pop: Pop{Components: []PopComponent{RawComponent{Type: "other"}}}}
	if _, unknown := DecodeCommand(command.ToJSON()).(UnknownCommand); unknown {
		t.Fatal("SetPop decoded to UnknownCommand")
	}
}

func TestAFieldSetToNilIsRemovedFromTheRetainedJSON(t *testing.T) {
	command := DecodeCommand(map[string]any{"type": "setSource", "id": "s1", "url": "u"}).(SetSource)
	command.Url = nil
	assetUuid := "a"
	command.AssetUuid = &assetUuid

	out := command.ToJSON().(map[string]any)

	if _, has := out["url"]; has || out["assetUuid"] != "a" {
		t.Fatalf("got %v", out)
	}
}

func TestDecodedJSONIsASnapshotOfTheInput(t *testing.T) {
	input := map[string]any{"type": "result", "id": "r1", "extra": map[string]any{"status": "original"}}
	message := DecodeMessage(input)

	input["extra"].(map[string]any)["status"] = "changed"

	if got := message.ToJSON().(map[string]any)["extra"].(map[string]any)["status"]; got != "original" {
		t.Fatalf("status = %v", got)
	}
}

func decodeExact(t *testing.T, text string) Message {
	t.Helper()
	decoder := json.NewDecoder(strings.NewReader(text))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		t.Fatal(err)
	}
	return DecodeMessage(value)
}

func TestAnIntegerTokenIsNeverRounded(t *testing.T) {
	if _, unknown := decodeExact(t, `{"type":"credit","id":"c1","bytes":1.00000000000000001}`).(UnknownMessage); !unknown {
		t.Fatal("a fraction that rounds to a whole number was accepted")
	}
	credit, ok := decodeExact(t, `{"type":"credit","id":"c1","bytes":9007199254740993.0}`).(Credit)
	if !ok || credit.Bytes != 9007199254740993 {
		t.Fatalf("got %v", credit)
	}
}

func TestIntegerTokensInExponentFormAreReadExactly(t *testing.T) {
	cases := map[string]int64{"1e3": 1000, "1.50e1": 15, "10e-1": 1, "2E+2": 200}
	for token, want := range cases {
		credit, ok := decodeExact(t, `{"type":"credit","id":"c1","bytes":`+token+`}`).(Credit)
		if !ok || credit.Bytes != want {
			t.Fatalf("%s: got %v, want %d", token, credit, want)
		}
	}
	for _, token := range []string{"1e-1", "1e-29", "1e19", "1e1000000", "1e-1000000", "9223372036854775808"} {
		if _, unknown := decodeExact(t, `{"type":"credit","id":"c1","bytes":`+token+`}`).(UnknownMessage); !unknown {
			t.Fatalf("%s was accepted", token)
		}
	}
}
