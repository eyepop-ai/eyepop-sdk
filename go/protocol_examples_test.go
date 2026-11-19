package eyepop

import (
	"encoding/json"
	"fmt"
	"math/big"
	"os"
	"reflect"
	"strings"
	"testing"
)

type decodingCase struct {
	Name      string            `json:"name"`
	File      string            `json:"file"`
	Union     string            `json:"union"`
	Text      string            `json:"text"`
	Variant   string            `json:"variant"`
	Unchanged bool              `json:"unchanged"`
	Keeps     string            `json:"keeps"`
	Diverges  map[string]string `json:"diverges"`
}

func TestEveryDecodingCaseHasItsStatedOutcome(t *testing.T) {
	raw, err := os.ReadFile("../protocol/examples/decoding.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []decodingCase
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	if len(cases) < 60 {
		t.Fatalf("found %d cases", len(cases))
	}
	for _, c := range cases {
		name, text := c.Name, c.Text
		if c.File != "" {
			bytes, err := os.ReadFile("../protocol/examples/" + c.File)
			if err != nil {
				t.Fatal(err)
			}
			name, text = c.File, string(bytes)
		}
		t.Run(name, func(t *testing.T) {
			problem := decodingProblem(c, text)
			reason, diverges := c.Diverges["go"]
			if diverges && problem == "" {
				t.Fatalf("passes but is marked as a known Go divergence (%s); remove the marker", reason)
			}
			if !diverges && problem != "" {
				t.Fatal(problem)
			}
		})
	}
}

func decodingProblem(c decodingCase, text string) string {
	data, err := exactJSON(text)
	if err != nil {
		return err.Error()
	}
	variant := "Unknown"
	var encoded any
	if c.Union == "command" {
		command := DecodeCommand(data)
		encoded = command.ToJSON()
		if _, unknown := command.(UnknownCommand); !unknown {
			variant = fmt.Sprint(encoded.(map[string]any)["type"])
		}
	} else {
		message := DecodeMessage(data)
		encoded = message.ToJSON()
		if _, unknown := message.(UnknownMessage); !unknown {
			variant = fmt.Sprint(encoded.(map[string]any)["type"])
		}
	}
	if variant != c.Variant {
		return fmt.Sprintf("decoded to %s, want %s", variant, c.Variant)
	}
	bytes, err := json.Marshal(encoded)
	if err != nil {
		return err.Error()
	}
	again, err := exactJSON(string(bytes))
	if err != nil {
		return err.Error()
	}
	if sameJSON(again, data) != c.Unchanged {
		return fmt.Sprintf("encoded %s, want unchanged = %v", bytes, c.Unchanged)
	}
	if !strings.Contains(string(bytes), c.Keeps) {
		return fmt.Sprintf("encoded %s, want it to contain %s", bytes, c.Keeps)
	}
	return ""
}

func exactJSON(text string) (any, error) {
	decoder := json.NewDecoder(strings.NewReader(text))
	decoder.UseNumber()
	var value any
	err := decoder.Decode(&value)
	return value, err
}

func sameJSON(a, b any) bool {
	switch x := a.(type) {
	case json.Number:
		y, ok := b.(json.Number)
		if !ok {
			return false
		}
		p, okP := new(big.Rat).SetString(string(x))
		q, okQ := new(big.Rat).SetString(string(y))
		return okP && okQ && p.Cmp(q) == 0
	case []any:
		y, ok := b.([]any)
		if !ok || len(x) != len(y) {
			return false
		}
		for i := range x {
			if !sameJSON(x[i], y[i]) {
				return false
			}
		}
		return true
	case map[string]any:
		y, ok := b.(map[string]any)
		if !ok || len(x) != len(y) {
			return false
		}
		for key, value := range x {
			other, has := y[key]
			if !has || !sameJSON(value, other) {
				return false
			}
		}
		return true
	default:
		return reflect.DeepEqual(a, b)
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
