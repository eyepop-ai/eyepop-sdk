// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.

package eyepop

import (
	"encoding/json"
	"fmt"
	"math"
	"math/big"
	"strconv"
	"strings"
)

func parseObject(value any) (map[string]any, error) {
	obj, ok := value.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("expected an object, got %v", value)
	}
	return obj, nil
}

func parseString(value any) (string, error) {
	text, ok := value.(string)
	if !ok {
		return "", fmt.Errorf("expected a string, got %v", value)
	}
	return text, nil
}

func wholeInt64(number float64) (int64, bool) {
	if math.IsInf(number, 0) || number != math.Trunc(number) {
		return 0, false
	}
	whole, accuracy := big.NewFloat(number).Int64()
	return whole, accuracy == big.Exact
}

func integerToken(token string) (int64, bool) {
	sign := ""
	if strings.HasPrefix(token, "-") {
		sign, token = "-", token[1:]
	}
	mantissa, exponentText, _ := strings.Cut(strings.ToLower(token), "e")
	whole, fraction, _ := strings.Cut(mantissa, ".")
	digits := strings.TrimLeft(whole+fraction, "0")
	if digits == "" {
		return 0, true
	}
	exponent := int64(0)
	if exponentText != "" {
		parsed, err := strconv.ParseInt(strings.TrimPrefix(exponentText, "+"), 10, 32)
		if err != nil {
			return 0, false
		}
		exponent = parsed
	}
	exponent -= int64(len(fraction))
	trimmed := strings.TrimRight(digits, "0")
	exponent += int64(len(digits) - len(trimmed))
	if exponent < 0 || int64(len(trimmed))+exponent > integerDigits {
		return 0, false
	}
	parsed, err := strconv.ParseInt(sign+trimmed+strings.Repeat("0", int(exponent)), 10, 64)
	return parsed, err == nil
}

func parseInteger(value any) (int64, error) {
	whole, ok := int64(0), false
	switch number := value.(type) {
	case int64:
		whole, ok = number, true
	case int:
		whole, ok = int64(number), true
	case float64:
		whole, ok = wholeInt64(number)
	case json.Number:
		whole, ok = integerToken(string(number))
	}
	if !ok || whole < integerMinimum || whole > integerMaximum {
		return 0, fmt.Errorf("expected an integer from %d to %d, got %v", int64(integerMinimum), int64(integerMaximum), value)
	}
	return whole, nil
}

func parseNumber(value any) (float64, error) {
	switch number := value.(type) {
	case float64:
		if !math.IsInf(number, 0) && !math.IsNaN(number) {
			return number, nil
		}
	case int64:
		return float64(number), nil
	case int:
		return float64(number), nil
	case json.Number:
		if parsed, err := number.Float64(); err == nil {
			return parsed, nil
		}
	}
	return 0, fmt.Errorf("expected a number, got %v", value)
}

func parseBoolean(value any) (bool, error) {
	flag, ok := value.(bool)
	if !ok {
		return false, fmt.Errorf("expected a boolean, got %v", value)
	}
	return flag, nil
}

func parseFree(value any) (map[string]any, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	return copyMap(obj), nil
}

type bound struct {
	set   bool
	value float64
}

var noBound = bound{}

func at(value float64) bound {
	return bound{set: true, value: value}
}

func limitNumeric[T int64 | float64](parse func(any) (T, error), minimum, exclusiveMinimum, exclusiveMaximum bound) func(any) (T, error) {
	return func(value any) (T, error) {
		parsed, err := parse(value)
		if err != nil {
			return parsed, err
		}
		size := float64(parsed)
		if (minimum.set && size < minimum.value) ||
			(exclusiveMinimum.set && size <= exclusiveMinimum.value) ||
			(exclusiveMaximum.set && size >= exclusiveMaximum.value) {
			var zero T
			return zero, fmt.Errorf("%v is out of range", value)
		}
		return parsed, nil
	}
}

func limitString(parse func(any) (string, error), minLength int) func(any) (string, error) {
	return func(value any) (string, error) {
		parsed, err := parse(value)
		if err != nil {
			return parsed, err
		}
		if length(parsed) < minLength {
			return "", fmt.Errorf("shorter than %d", minLength)
		}
		return parsed, nil
	}
}

func exactlyOne(obj map[string]any, keys ...string) error {
	present := 0
	for _, key := range keys {
		if _, ok := obj[key]; ok {
			present++
		}
	}
	if present != 1 {
		return fmt.Errorf("expected exactly one of %v, got %d", keys, present)
	}
	return nil
}

func within(value any, levels int) bool {
	var items []any
	switch typed := value.(type) {
	case map[string]any:
		for _, item := range typed {
			items = append(items, item)
		}
	case []any:
		items = typed
	default:
		return true
	}
	if levels == 0 {
		return false
	}
	for _, item := range items {
		if !within(item, levels-1) {
			return false
		}
	}
	return true
}

func putNumber(out map[string]any, key string, number float64) {
	if existing, ok := out[key]; ok {
		if current, err := parseNumber(existing); err == nil && current == number {
			return
		}
	}
	out[key] = number
}

func parseConst(expected string) func(any) (string, error) {
	return func(value any) (string, error) {
		if value != expected {
			return "", fmt.Errorf("expected %q, got %v", expected, value)
		}
		return expected, nil
	}
}

func parseArray[T any](item func(any) (T, error)) func(any) ([]T, error) {
	return func(value any) ([]T, error) {
		elements, ok := value.([]any)
		if !ok {
			return nil, fmt.Errorf("expected an array, got %v", value)
		}
		out := make([]T, 0, len(elements))
		for _, element := range elements {
			parsed, err := item(element)
			if err != nil {
				return nil, err
			}
			out = append(out, parsed)
		}
		return out, nil
	}
}

func required[T any](obj map[string]any, key string, parse func(any) (T, error)) (T, error) {
	value, ok := obj[key]
	if !ok {
		var zero T
		return zero, fmt.Errorf("missing %s", key)
	}
	return parse(value)
}

func optional[T any](obj map[string]any, key string, parse func(any) (T, error)) (*T, error) {
	value, ok := obj[key]
	if !ok {
		return nil, nil
	}
	parsed, err := parse(value)
	if err != nil {
		return nil, err
	}
	return &parsed, nil
}

func optionalNil[T any](obj map[string]any, key string, parse func(any) (T, error)) (T, error) {
	value, ok := obj[key]
	if !ok {
		var zero T
		return zero, nil
	}
	return parse(value)
}

func hasKey(obj map[string]any, key string) bool {
	_, ok := obj[key]
	return ok
}

func deepCopy(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		return copyMap(typed)
	case []any:
		out := make([]any, len(typed))
		for i, element := range typed {
			out[i] = deepCopy(element)
		}
		return out
	default:
		return value
	}
}

func copyMap(source map[string]any) map[string]any {
	out := make(map[string]any, len(source))
	for key, value := range source {
		out[key] = deepCopy(value)
	}
	return out
}

func mapList[T any](items []T, convert func(T) any) []any {
	out := make([]any, 0, len(items))
	for _, item := range items {
		out = append(out, convert(item))
	}
	return out
}

const (
	integerMinimum = -9223372036854775808
	integerMaximum = 9223372036854775807
	integerDigits  = 19
	maxDepth       = 64
)

func length(text string) int {
	return len([]rune(text))
}

type EndReason string

const (
	EndReasonEos       EndReason = "eos"
	EndReasonError     EndReason = "error"
	EndReasonPreempted EndReason = "preempted"
	EndReasonStopped   EndReason = "stopped"
)

func EndReasonFromJSON(value any) (EndReason, error) {
	switch parsed := EndReason(fmt.Sprint(value)); parsed {
	case EndReasonEos, EndReasonError, EndReasonPreempted, EndReasonStopped:
		return parsed, nil
	}
	return "", fmt.Errorf("unexpected value %v", value)
}

type GetGraphFormat string

const (
	GetGraphFormatDot GetGraphFormat = "dot"
	GetGraphFormatPng GetGraphFormat = "png"
	GetGraphFormatPdf GetGraphFormat = "pdf"
)

func GetGraphFormatFromJSON(value any) (GetGraphFormat, error) {
	switch parsed := GetGraphFormat(fmt.Sprint(value)); parsed {
	case GetGraphFormatDot, GetGraphFormatPng, GetGraphFormatPdf:
		return parsed, nil
	}
	return "", fmt.Errorf("unexpected value %v", value)
}

type SetSourceMode string

const (
	SetSourceModeQueue   SetSourceMode = "queue"
	SetSourceModePreempt SetSourceMode = "preempt"
)

func SetSourceModeFromJSON(value any) (SetSourceMode, error) {
	switch parsed := SetSourceMode(fmt.Sprint(value)); parsed {
	case SetSourceModeQueue, SetSourceModePreempt:
		return parsed, nil
	}
	return "", fmt.Errorf("unexpected value %v", value)
}

type Ability struct {
	Ability     *string
	AbilityUuid *string
	Params      map[string]any
	Raw         map[string]any
}

func AbilityFromJSON(value any) (Ability, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Ability{}, err
	}
	if err := exactlyOne(obj, "ability", "abilityUuid"); err != nil {
		return Ability{}, err
	}
	v0, err := optional(obj, "ability", parseString)
	if err != nil {
		return Ability{}, err
	}
	v1, err := optional(obj, "abilityUuid", parseString)
	if err != nil {
		return Ability{}, err
	}
	v2, err := optionalNil(obj, "params", parseFree)
	if err != nil {
		return Ability{}, err
	}
	return Ability{Ability: v0, AbilityUuid: v1, Params: v2, Raw: copyMap(obj)}, nil
}

func (v Ability) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Ability != nil {
		out["ability"] = (*v.Ability)
	} else {
		delete(out, "ability")
	}
	if v.AbilityUuid != nil {
		out["abilityUuid"] = (*v.AbilityUuid)
	} else {
		delete(out, "abilityUuid")
	}
	if v.Params != nil {
		out["params"] = deepCopy(v.Params)
	} else {
		delete(out, "params")
	}
	return out
}

type CameraIntrinsics struct {
	Fx  float64
	Fy  float64
	Cx  float64
	Cy  float64
	Raw map[string]any
}

func CameraIntrinsicsFromJSON(value any) (CameraIntrinsics, error) {
	obj, err := parseObject(value)
	if err != nil {
		return CameraIntrinsics{}, err
	}
	v0, err := required(obj, "fx", parseNumber)
	if err != nil {
		return CameraIntrinsics{}, err
	}
	v1, err := required(obj, "fy", parseNumber)
	if err != nil {
		return CameraIntrinsics{}, err
	}
	v2, err := required(obj, "cx", parseNumber)
	if err != nil {
		return CameraIntrinsics{}, err
	}
	v3, err := required(obj, "cy", parseNumber)
	if err != nil {
		return CameraIntrinsics{}, err
	}
	return CameraIntrinsics{Fx: v0, Fy: v1, Cx: v2, Cy: v3, Raw: copyMap(obj)}, nil
}

func (v CameraIntrinsics) ToJSON() any {
	out := copyMap(v.Raw)
	putNumber(out, "fx", v.Fx)
	putNumber(out, "fy", v.Fy)
	putNumber(out, "cx", v.Cx)
	putNumber(out, "cy", v.Cy)
	return out
}

type CameraDistortion struct {
	K1  *float64
	K2  *float64
	P1  *float64
	P2  *float64
	K3  *float64
	Raw map[string]any
}

func CameraDistortionFromJSON(value any) (CameraDistortion, error) {
	obj, err := parseObject(value)
	if err != nil {
		return CameraDistortion{}, err
	}
	v0, err := optional(obj, "k1", parseNumber)
	if err != nil {
		return CameraDistortion{}, err
	}
	v1, err := optional(obj, "k2", parseNumber)
	if err != nil {
		return CameraDistortion{}, err
	}
	v2, err := optional(obj, "p1", parseNumber)
	if err != nil {
		return CameraDistortion{}, err
	}
	v3, err := optional(obj, "p2", parseNumber)
	if err != nil {
		return CameraDistortion{}, err
	}
	v4, err := optional(obj, "k3", parseNumber)
	if err != nil {
		return CameraDistortion{}, err
	}
	return CameraDistortion{K1: v0, K2: v1, P1: v2, P2: v3, K3: v4, Raw: copyMap(obj)}, nil
}

func (v CameraDistortion) ToJSON() any {
	out := copyMap(v.Raw)
	if v.K1 != nil {
		putNumber(out, "k1", *v.K1)
	} else {
		delete(out, "k1")
	}
	if v.K2 != nil {
		putNumber(out, "k2", *v.K2)
	} else {
		delete(out, "k2")
	}
	if v.P1 != nil {
		putNumber(out, "p1", *v.P1)
	} else {
		delete(out, "p1")
	}
	if v.P2 != nil {
		putNumber(out, "p2", *v.P2)
	} else {
		delete(out, "p2")
	}
	if v.K3 != nil {
		putNumber(out, "k3", *v.K3)
	} else {
		delete(out, "k3")
	}
	return out
}

type CameraExtrinsicsRotation struct {
	W   float64
	X   float64
	Y   float64
	Z   float64
	Raw map[string]any
}

func CameraExtrinsicsRotationFromJSON(value any) (CameraExtrinsicsRotation, error) {
	obj, err := parseObject(value)
	if err != nil {
		return CameraExtrinsicsRotation{}, err
	}
	v0, err := required(obj, "w", parseNumber)
	if err != nil {
		return CameraExtrinsicsRotation{}, err
	}
	v1, err := required(obj, "x", parseNumber)
	if err != nil {
		return CameraExtrinsicsRotation{}, err
	}
	v2, err := required(obj, "y", parseNumber)
	if err != nil {
		return CameraExtrinsicsRotation{}, err
	}
	v3, err := required(obj, "z", parseNumber)
	if err != nil {
		return CameraExtrinsicsRotation{}, err
	}
	return CameraExtrinsicsRotation{W: v0, X: v1, Y: v2, Z: v3, Raw: copyMap(obj)}, nil
}

func (v CameraExtrinsicsRotation) ToJSON() any {
	out := copyMap(v.Raw)
	putNumber(out, "w", v.W)
	putNumber(out, "x", v.X)
	putNumber(out, "y", v.Y)
	putNumber(out, "z", v.Z)
	return out
}

type CameraExtrinsicsTranslation struct {
	X   float64
	Y   float64
	Z   float64
	Raw map[string]any
}

func CameraExtrinsicsTranslationFromJSON(value any) (CameraExtrinsicsTranslation, error) {
	obj, err := parseObject(value)
	if err != nil {
		return CameraExtrinsicsTranslation{}, err
	}
	v0, err := required(obj, "x", parseNumber)
	if err != nil {
		return CameraExtrinsicsTranslation{}, err
	}
	v1, err := required(obj, "y", parseNumber)
	if err != nil {
		return CameraExtrinsicsTranslation{}, err
	}
	v2, err := required(obj, "z", parseNumber)
	if err != nil {
		return CameraExtrinsicsTranslation{}, err
	}
	return CameraExtrinsicsTranslation{X: v0, Y: v1, Z: v2, Raw: copyMap(obj)}, nil
}

func (v CameraExtrinsicsTranslation) ToJSON() any {
	out := copyMap(v.Raw)
	putNumber(out, "x", v.X)
	putNumber(out, "y", v.Y)
	putNumber(out, "z", v.Z)
	return out
}

type CameraExtrinsics struct {
	Rotation    *CameraExtrinsicsRotation
	Translation *CameraExtrinsicsTranslation
	Raw         map[string]any
}

func CameraExtrinsicsFromJSON(value any) (CameraExtrinsics, error) {
	obj, err := parseObject(value)
	if err != nil {
		return CameraExtrinsics{}, err
	}
	v0, err := optional(obj, "rotation", CameraExtrinsicsRotationFromJSON)
	if err != nil {
		return CameraExtrinsics{}, err
	}
	v1, err := optional(obj, "translation", CameraExtrinsicsTranslationFromJSON)
	if err != nil {
		return CameraExtrinsics{}, err
	}
	return CameraExtrinsics{Rotation: v0, Translation: v1, Raw: copyMap(obj)}, nil
}

func (v CameraExtrinsics) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Rotation != nil {
		out["rotation"] = (*v.Rotation).ToJSON()
	} else {
		delete(out, "rotation")
	}
	if v.Translation != nil {
		out["translation"] = (*v.Translation).ToJSON()
	} else {
		delete(out, "translation")
	}
	return out
}

type Camera struct {
	Intrinsics  *CameraIntrinsics
	HfovDegrees *float64
	Distortion  *CameraDistortion
	Extrinsics  *CameraExtrinsics
	Raw         map[string]any
}

func CameraFromJSON(value any) (Camera, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Camera{}, err
	}
	if err := exactlyOne(obj, "intrinsics", "hfovDegrees"); err != nil {
		return Camera{}, err
	}
	v0, err := optional(obj, "intrinsics", CameraIntrinsicsFromJSON)
	if err != nil {
		return Camera{}, err
	}
	v1, err := optional(obj, "hfovDegrees", limitNumeric(parseNumber, noBound, at(0), at(180)))
	if err != nil {
		return Camera{}, err
	}
	v2, err := optional(obj, "distortion", CameraDistortionFromJSON)
	if err != nil {
		return Camera{}, err
	}
	v3, err := optional(obj, "extrinsics", CameraExtrinsicsFromJSON)
	if err != nil {
		return Camera{}, err
	}
	return Camera{Intrinsics: v0, HfovDegrees: v1, Distortion: v2, Extrinsics: v3, Raw: copyMap(obj)}, nil
}

func (v Camera) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Intrinsics != nil {
		out["intrinsics"] = (*v.Intrinsics).ToJSON()
	} else {
		delete(out, "intrinsics")
	}
	if v.HfovDegrees != nil {
		putNumber(out, "hfovDegrees", *v.HfovDegrees)
	} else {
		delete(out, "hfovDegrees")
	}
	if v.Distortion != nil {
		out["distortion"] = (*v.Distortion).ToJSON()
	} else {
		delete(out, "distortion")
	}
	if v.Extrinsics != nil {
		out["extrinsics"] = (*v.Extrinsics).ToJSON()
	} else {
		delete(out, "extrinsics")
	}
	return out
}

type ComponentParams struct {
	ComponentId int64
	Values      map[string]any
	Raw         map[string]any
}

func ComponentParamsFromJSON(value any) (ComponentParams, error) {
	obj, err := parseObject(value)
	if err != nil {
		return ComponentParams{}, err
	}
	v0, err := required(obj, "componentId", parseInteger)
	if err != nil {
		return ComponentParams{}, err
	}
	v1, err := required(obj, "values", parseFree)
	if err != nil {
		return ComponentParams{}, err
	}
	return ComponentParams{ComponentId: v0, Values: v1, Raw: copyMap(obj)}, nil
}

func (v ComponentParams) ToJSON() any {
	out := copyMap(v.Raw)
	out["componentId"] = v.ComponentId
	out["values"] = deepCopy(v.Values)
	return out
}

type Contour struct {
	Points  []Point
	Cutouts [][]Point
	Raw     map[string]any
}

func ContourFromJSON(value any) (Contour, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Contour{}, err
	}
	v0, err := optionalNil(obj, "points", parseArray(PointFromJSON))
	if err != nil {
		return Contour{}, err
	}
	v1, err := optionalNil(obj, "cutouts", parseArray(parseArray(PointFromJSON)))
	if err != nil {
		return Contour{}, err
	}
	return Contour{Points: v0, Cutouts: v1, Raw: copyMap(obj)}, nil
}

func (v Contour) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Points != nil {
		out["points"] = mapList(v.Points, func(x Point) any { return x.ToJSON() })
	} else {
		delete(out, "points")
	}
	if v.Cutouts != nil {
		out["cutouts"] = mapList(v.Cutouts, func(x []Point) any { return mapList(x, func(x Point) any { return x.ToJSON() }) })
	} else {
		delete(out, "cutouts")
	}
	return out
}

type Credit struct {
	Id     string
	Bytes  int64
	Member *int64
	Raw    map[string]any
}

func CreditFromJSON(value any) (Credit, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Credit{}, err
	}
	if _, err := required(obj, "type", parseConst("credit")); err != nil {
		return Credit{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Credit{}, err
	}
	v1, err := required(obj, "bytes", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Credit{}, err
	}
	v2, err := optional(obj, "member", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Credit{}, err
	}
	return Credit{Id: v0, Bytes: v1, Member: v2, Raw: copyMap(obj)}, nil
}

func (v Credit) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["bytes"] = v.Bytes
	if v.Member != nil {
		out["member"] = (*v.Member)
	} else {
		delete(out, "member")
	}
	out["type"] = "credit"
	return out
}

func (Credit) isMessage() {}

type Depth struct {
	Width    *int64
	Height   *int64
	Semantic *string
	Values   *string
	World    *string
	Raw      map[string]any
}

func DepthFromJSON(value any) (Depth, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Depth{}, err
	}
	v0, err := optional(obj, "width", parseInteger)
	if err != nil {
		return Depth{}, err
	}
	v1, err := optional(obj, "height", parseInteger)
	if err != nil {
		return Depth{}, err
	}
	v2, err := optional(obj, "semantic", parseString)
	if err != nil {
		return Depth{}, err
	}
	v3, err := optional(obj, "values", parseString)
	if err != nil {
		return Depth{}, err
	}
	v4, err := optional(obj, "world", parseString)
	if err != nil {
		return Depth{}, err
	}
	return Depth{Width: v0, Height: v1, Semantic: v2, Values: v3, World: v4, Raw: copyMap(obj)}, nil
}

func (v Depth) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Width != nil {
		out["width"] = (*v.Width)
	} else {
		delete(out, "width")
	}
	if v.Height != nil {
		out["height"] = (*v.Height)
	} else {
		delete(out, "height")
	}
	if v.Semantic != nil {
		out["semantic"] = (*v.Semantic)
	} else {
		delete(out, "semantic")
	}
	if v.Values != nil {
		out["values"] = (*v.Values)
	} else {
		delete(out, "values")
	}
	if v.World != nil {
		out["world"] = (*v.World)
	} else {
		delete(out, "world")
	}
	return out
}

type Done struct {
	Raw map[string]any
}

func DoneFromJSON(value any) (Done, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Done{}, err
	}
	if _, err := required(obj, "type", parseConst("done")); err != nil {
		return Done{}, err
	}

	return Done{Raw: copyMap(obj)}, nil
}

func (v Done) ToJSON() any {
	out := copyMap(v.Raw)
	out["type"] = "done"
	return out
}

func (Done) isMessage() {}

type Dropped struct {
	Id    string
	Count int64
	Raw   map[string]any
}

func DroppedFromJSON(value any) (Dropped, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Dropped{}, err
	}
	if _, err := required(obj, "type", parseConst("dropped")); err != nil {
		return Dropped{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Dropped{}, err
	}
	v1, err := required(obj, "count", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Dropped{}, err
	}
	return Dropped{Id: v0, Count: v1, Raw: copyMap(obj)}, nil
}

func (v Dropped) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["count"] = v.Count
	out["type"] = "dropped"
	return out
}

func (Dropped) isJobMessage() {}
func (Dropped) isMessage()    {}

type End struct {
	Id                string
	Reason            EndReason
	Message           *string
	MilliComputeUnits *int64
	Raw               map[string]any
}

func EndFromJSON(value any) (End, error) {
	obj, err := parseObject(value)
	if err != nil {
		return End{}, err
	}
	if _, err := required(obj, "type", parseConst("end")); err != nil {
		return End{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return End{}, err
	}
	v1, err := required(obj, "reason", EndReasonFromJSON)
	if err != nil {
		return End{}, err
	}
	v2, err := optional(obj, "message", parseString)
	if err != nil {
		return End{}, err
	}
	v3, err := optional(obj, "milliComputeUnits", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return End{}, err
	}
	return End{Id: v0, Reason: v1, Message: v2, MilliComputeUnits: v3, Raw: copyMap(obj)}, nil
}

func (v End) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["reason"] = string(v.Reason)
	if v.Message != nil {
		out["message"] = (*v.Message)
	} else {
		delete(out, "message")
	}
	if v.MilliComputeUnits != nil {
		out["milliComputeUnits"] = (*v.MilliComputeUnits)
	} else {
		delete(out, "milliComputeUnits")
	}
	out["type"] = "end"
	return out
}

func (End) isJobMessage() {}
func (End) isMessage()    {}

type ErrorMessage struct {
	Id      *string
	Error   string
	Message string
	Raw     map[string]any
}

func ErrorMessageFromJSON(value any) (ErrorMessage, error) {
	obj, err := parseObject(value)
	if err != nil {
		return ErrorMessage{}, err
	}
	if _, err := required(obj, "type", parseConst("error")); err != nil {
		return ErrorMessage{}, err
	}
	v0, err := optional(obj, "id", limitString(parseString, 1))
	if err != nil {
		return ErrorMessage{}, err
	}
	v1, err := required(obj, "error", limitString(parseString, 1))
	if err != nil {
		return ErrorMessage{}, err
	}
	v2, err := required(obj, "message", parseString)
	if err != nil {
		return ErrorMessage{}, err
	}
	return ErrorMessage{Id: v0, Error: v1, Message: v2, Raw: copyMap(obj)}, nil
}

func (v ErrorMessage) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Id != nil {
		out["id"] = (*v.Id)
	} else {
		delete(out, "id")
	}
	out["error"] = v.Error
	out["message"] = v.Message
	out["type"] = "error"
	return out
}

func (ErrorMessage) isMessage() {}

type GetGraph struct {
	Id      string
	Format  GetGraphFormat
	Verbose *bool
	Raw     map[string]any
}

func GetGraphFromJSON(value any) (GetGraph, error) {
	obj, err := parseObject(value)
	if err != nil {
		return GetGraph{}, err
	}
	if _, err := required(obj, "type", parseConst("getGraph")); err != nil {
		return GetGraph{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return GetGraph{}, err
	}
	v1, err := required(obj, "format", GetGraphFormatFromJSON)
	if err != nil {
		return GetGraph{}, err
	}
	v2, err := optional(obj, "verbose", parseBoolean)
	if err != nil {
		return GetGraph{}, err
	}
	return GetGraph{Id: v0, Format: v1, Verbose: v2, Raw: copyMap(obj)}, nil
}

func (v GetGraph) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["format"] = string(v.Format)
	if v.Verbose != nil {
		out["verbose"] = (*v.Verbose)
	} else {
		delete(out, "verbose")
	}
	out["type"] = "getGraph"
	return out
}

func (GetGraph) isCommand() {}

type InferenceComponent struct {
	Ability     *string
	AbilityUuid *string
	Params      map[string]any
	Id          *int64
	Raw         map[string]any
}

func InferenceComponentFromJSON(value any) (InferenceComponent, error) {
	obj, err := parseObject(value)
	if err != nil {
		return InferenceComponent{}, err
	}
	if _, err := required(obj, "type", parseConst("inference")); err != nil {
		return InferenceComponent{}, err
	}
	if err := exactlyOne(obj, "ability", "abilityUuid"); err != nil {
		return InferenceComponent{}, err
	}
	v0, err := optional(obj, "ability", parseString)
	if err != nil {
		return InferenceComponent{}, err
	}
	v1, err := optional(obj, "abilityUuid", parseString)
	if err != nil {
		return InferenceComponent{}, err
	}
	v2, err := optionalNil(obj, "params", parseFree)
	if err != nil {
		return InferenceComponent{}, err
	}
	v3, err := optional(obj, "id", parseInteger)
	if err != nil {
		return InferenceComponent{}, err
	}
	return InferenceComponent{Ability: v0, AbilityUuid: v1, Params: v2, Id: v3, Raw: copyMap(obj)}, nil
}

func (v InferenceComponent) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Ability != nil {
		out["ability"] = (*v.Ability)
	} else {
		delete(out, "ability")
	}
	if v.AbilityUuid != nil {
		out["abilityUuid"] = (*v.AbilityUuid)
	} else {
		delete(out, "abilityUuid")
	}
	if v.Params != nil {
		out["params"] = deepCopy(v.Params)
	} else {
		delete(out, "params")
	}
	if v.Id != nil {
		out["id"] = (*v.Id)
	} else {
		delete(out, "id")
	}
	out["type"] = "inference"
	return out
}

func (InferenceComponent) isPopComponent() {}

type Mask struct {
	Width  *int64
	Height *int64
	Stride *int64
	Bitmap *string
	World  *string
	Raw    map[string]any
}

func MaskFromJSON(value any) (Mask, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Mask{}, err
	}
	v0, err := optional(obj, "width", parseInteger)
	if err != nil {
		return Mask{}, err
	}
	v1, err := optional(obj, "height", parseInteger)
	if err != nil {
		return Mask{}, err
	}
	v2, err := optional(obj, "stride", parseInteger)
	if err != nil {
		return Mask{}, err
	}
	v3, err := optional(obj, "bitmap", parseString)
	if err != nil {
		return Mask{}, err
	}
	v4, err := optional(obj, "world", parseString)
	if err != nil {
		return Mask{}, err
	}
	return Mask{Width: v0, Height: v1, Stride: v2, Bitmap: v3, World: v4, Raw: copyMap(obj)}, nil
}

func (v Mask) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Width != nil {
		out["width"] = (*v.Width)
	} else {
		delete(out, "width")
	}
	if v.Height != nil {
		out["height"] = (*v.Height)
	} else {
		delete(out, "height")
	}
	if v.Stride != nil {
		out["stride"] = (*v.Stride)
	} else {
		delete(out, "stride")
	}
	if v.Bitmap != nil {
		out["bitmap"] = (*v.Bitmap)
	} else {
		delete(out, "bitmap")
	}
	if v.World != nil {
		out["world"] = (*v.World)
	} else {
		delete(out, "world")
	}
	return out
}

type Ping struct {
	Id  string
	Raw map[string]any
}

func PingFromJSON(value any) (Ping, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Ping{}, err
	}
	if _, err := required(obj, "type", parseConst("ping")); err != nil {
		return Ping{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Ping{}, err
	}
	return Ping{Id: v0, Raw: copyMap(obj)}, nil
}

func (v Ping) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "ping"
	return out
}

func (Ping) isCommand() {}

type Point struct {
	X      *float64
	Y      *float64
	Z      *float64
	WorldX *float64
	WorldY *float64
	WorldZ *float64
	Raw    map[string]any
}

func PointFromJSON(value any) (Point, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Point{}, err
	}
	v0, err := optional(obj, "x", parseNumber)
	if err != nil {
		return Point{}, err
	}
	v1, err := optional(obj, "y", parseNumber)
	if err != nil {
		return Point{}, err
	}
	v2, err := optional(obj, "z", parseNumber)
	if err != nil {
		return Point{}, err
	}
	v3, err := optional(obj, "worldX", parseNumber)
	if err != nil {
		return Point{}, err
	}
	v4, err := optional(obj, "worldY", parseNumber)
	if err != nil {
		return Point{}, err
	}
	v5, err := optional(obj, "worldZ", parseNumber)
	if err != nil {
		return Point{}, err
	}
	return Point{X: v0, Y: v1, Z: v2, WorldX: v3, WorldY: v4, WorldZ: v5, Raw: copyMap(obj)}, nil
}

func (v Point) ToJSON() any {
	out := copyMap(v.Raw)
	if v.X != nil {
		putNumber(out, "x", *v.X)
	} else {
		delete(out, "x")
	}
	if v.Y != nil {
		putNumber(out, "y", *v.Y)
	} else {
		delete(out, "y")
	}
	if v.Z != nil {
		putNumber(out, "z", *v.Z)
	} else {
		delete(out, "z")
	}
	if v.WorldX != nil {
		putNumber(out, "worldX", *v.WorldX)
	} else {
		delete(out, "worldX")
	}
	if v.WorldY != nil {
		putNumber(out, "worldY", *v.WorldY)
	} else {
		delete(out, "worldY")
	}
	if v.WorldZ != nil {
		putNumber(out, "worldZ", *v.WorldZ)
	} else {
		delete(out, "worldZ")
	}
	return out
}

type Pong struct {
	Id  string
	Raw map[string]any
}

func PongFromJSON(value any) (Pong, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Pong{}, err
	}
	if _, err := required(obj, "type", parseConst("pong")); err != nil {
		return Pong{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Pong{}, err
	}
	return Pong{Id: v0, Raw: copyMap(obj)}, nil
}

func (v Pong) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "pong"
	return out
}

func (Pong) isMessage() {}

type Pop struct {
	Components    []PopComponent
	PostTransform *string
	Defaults      *SourceDefaults
	DepthMap      *PopDepthMap
	Raw           map[string]any
}

func PopFromJSON(value any) (Pop, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Pop{}, err
	}
	v0, err := required(obj, "components", parseArray(PopComponentFromJSON))
	if err != nil {
		return Pop{}, err
	}
	v1, err := optional(obj, "postTransform", parseString)
	if err != nil {
		return Pop{}, err
	}
	v2, err := optional(obj, "defaults", SourceDefaultsFromJSON)
	if err != nil {
		return Pop{}, err
	}
	v3, err := optional(obj, "depthMap", PopDepthMapFromJSON)
	if err != nil {
		return Pop{}, err
	}
	return Pop{Components: v0, PostTransform: v1, Defaults: v2, DepthMap: v3, Raw: copyMap(obj)}, nil
}

func (v Pop) ToJSON() any {
	out := copyMap(v.Raw)
	out["components"] = mapList(v.Components, func(x PopComponent) any { return x.ToJSON() })
	if v.PostTransform != nil {
		out["postTransform"] = (*v.PostTransform)
	} else {
		delete(out, "postTransform")
	}
	if v.Defaults != nil {
		out["defaults"] = (*v.Defaults).ToJSON()
	} else {
		delete(out, "defaults")
	}
	if v.DepthMap != nil {
		out["depthMap"] = (*v.DepthMap).ToJSON()
	} else {
		delete(out, "depthMap")
	}
	return out
}

type PopDepthMap struct {
	Ability     *string
	AbilityUuid *string
	ToWorld     *bool
	Raw         map[string]any
}

func PopDepthMapFromJSON(value any) (PopDepthMap, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PopDepthMap{}, err
	}
	if err := exactlyOne(obj, "ability", "abilityUuid"); err != nil {
		return PopDepthMap{}, err
	}
	v0, err := optional(obj, "ability", parseString)
	if err != nil {
		return PopDepthMap{}, err
	}
	v1, err := optional(obj, "abilityUuid", parseString)
	if err != nil {
		return PopDepthMap{}, err
	}
	v2, err := optional(obj, "toWorld", parseBoolean)
	if err != nil {
		return PopDepthMap{}, err
	}
	return PopDepthMap{Ability: v0, AbilityUuid: v1, ToWorld: v2, Raw: copyMap(obj)}, nil
}

func (v PopDepthMap) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Ability != nil {
		out["ability"] = (*v.Ability)
	} else {
		delete(out, "ability")
	}
	if v.AbilityUuid != nil {
		out["abilityUuid"] = (*v.AbilityUuid)
	} else {
		delete(out, "abilityUuid")
	}
	if v.ToWorld != nil {
		out["toWorld"] = (*v.ToWorld)
	} else {
		delete(out, "toWorld")
	}
	return out
}

type PredictedClass struct {
	ClassLabel *string
	Confidence *float64
	Category   *string
	Raw        map[string]any
}

func PredictedClassFromJSON(value any) (PredictedClass, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedClass{}, err
	}
	v0, err := optional(obj, "classLabel", parseString)
	if err != nil {
		return PredictedClass{}, err
	}
	v1, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedClass{}, err
	}
	v2, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedClass{}, err
	}
	return PredictedClass{ClassLabel: v0, Confidence: v1, Category: v2, Raw: copyMap(obj)}, nil
}

func (v PredictedClass) ToJSON() any {
	out := copyMap(v.Raw)
	if v.ClassLabel != nil {
		out["classLabel"] = (*v.ClassLabel)
	} else {
		delete(out, "classLabel")
	}
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	return out
}

type PredictedKeyPoint struct {
	X          *float64
	Y          *float64
	Z          *float64
	WorldX     *float64
	WorldY     *float64
	WorldZ     *float64
	ClassLabel *string
	Confidence *float64
	Category   *string
	Visible    *bool
	Raw        map[string]any
}

func PredictedKeyPointFromJSON(value any) (PredictedKeyPoint, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v0, err := optional(obj, "x", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v1, err := optional(obj, "y", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v2, err := optional(obj, "z", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v3, err := optional(obj, "worldX", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v4, err := optional(obj, "worldY", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v5, err := optional(obj, "worldZ", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v6, err := optional(obj, "classLabel", parseString)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v7, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v8, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	v9, err := optional(obj, "visible", parseBoolean)
	if err != nil {
		return PredictedKeyPoint{}, err
	}
	return PredictedKeyPoint{X: v0, Y: v1, Z: v2, WorldX: v3, WorldY: v4, WorldZ: v5, ClassLabel: v6, Confidence: v7, Category: v8, Visible: v9, Raw: copyMap(obj)}, nil
}

func (v PredictedKeyPoint) ToJSON() any {
	out := copyMap(v.Raw)
	if v.X != nil {
		putNumber(out, "x", *v.X)
	} else {
		delete(out, "x")
	}
	if v.Y != nil {
		putNumber(out, "y", *v.Y)
	} else {
		delete(out, "y")
	}
	if v.Z != nil {
		putNumber(out, "z", *v.Z)
	} else {
		delete(out, "z")
	}
	if v.WorldX != nil {
		putNumber(out, "worldX", *v.WorldX)
	} else {
		delete(out, "worldX")
	}
	if v.WorldY != nil {
		putNumber(out, "worldY", *v.WorldY)
	} else {
		delete(out, "worldY")
	}
	if v.WorldZ != nil {
		putNumber(out, "worldZ", *v.WorldZ)
	} else {
		delete(out, "worldZ")
	}
	if v.ClassLabel != nil {
		out["classLabel"] = (*v.ClassLabel)
	} else {
		delete(out, "classLabel")
	}
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	if v.Visible != nil {
		out["visible"] = (*v.Visible)
	} else {
		delete(out, "visible")
	}
	return out
}

type PredictedKeyPoints struct {
	Confidence *float64
	Category   *string
	Points     []PredictedKeyPoint
	Raw        map[string]any
}

func PredictedKeyPointsFromJSON(value any) (PredictedKeyPoints, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedKeyPoints{}, err
	}
	v0, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedKeyPoints{}, err
	}
	v1, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedKeyPoints{}, err
	}
	v2, err := optionalNil(obj, "points", parseArray(PredictedKeyPointFromJSON))
	if err != nil {
		return PredictedKeyPoints{}, err
	}
	return PredictedKeyPoints{Confidence: v0, Category: v1, Points: v2, Raw: copyMap(obj)}, nil
}

func (v PredictedKeyPoints) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	if v.Points != nil {
		out["points"] = mapList(v.Points, func(x PredictedKeyPoint) any { return x.ToJSON() })
	} else {
		delete(out, "points")
	}
	return out
}

type PredictedMesh struct {
	Confidence *float64
	Category   *string
	Points     []Point
	Raw        map[string]any
}

func PredictedMeshFromJSON(value any) (PredictedMesh, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedMesh{}, err
	}
	v0, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedMesh{}, err
	}
	v1, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedMesh{}, err
	}
	v2, err := optionalNil(obj, "points", parseArray(PointFromJSON))
	if err != nil {
		return PredictedMesh{}, err
	}
	return PredictedMesh{Confidence: v0, Category: v1, Points: v2, Raw: copyMap(obj)}, nil
}

func (v PredictedMesh) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	if v.Points != nil {
		out["points"] = mapList(v.Points, func(x Point) any { return x.ToJSON() })
	} else {
		delete(out, "points")
	}
	return out
}

type PredictedObject struct {
	ClassLabel     *string
	Confidence     *float64
	Category       *string
	X              *float64
	Y              *float64
	Width          *float64
	Height         *float64
	Orientation    *float64
	TrackId        *int64
	GlobalObjectId *int64
	Outline        []Point
	Contours       []Contour
	Mask           *Mask
	Objects        []PredictedObject
	Classes        []PredictedClass
	Texts          []PredictedText
	KeyPoints      []PredictedKeyPoints
	Meshes         []PredictedMesh
	Details        []map[string]any
	Raw            map[string]any
}

func PredictedObjectFromJSON(value any) (PredictedObject, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedObject{}, err
	}
	v0, err := optional(obj, "classLabel", parseString)
	if err != nil {
		return PredictedObject{}, err
	}
	v1, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v2, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedObject{}, err
	}
	v3, err := optional(obj, "x", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v4, err := optional(obj, "y", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v5, err := optional(obj, "width", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v6, err := optional(obj, "height", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v7, err := optional(obj, "orientation", parseNumber)
	if err != nil {
		return PredictedObject{}, err
	}
	v8, err := optional(obj, "trackId", parseInteger)
	if err != nil {
		return PredictedObject{}, err
	}
	v9, err := optional(obj, "globalObjectId", parseInteger)
	if err != nil {
		return PredictedObject{}, err
	}
	v10, err := optionalNil(obj, "outline", parseArray(PointFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v11, err := optionalNil(obj, "contours", parseArray(ContourFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v12, err := optional(obj, "mask", MaskFromJSON)
	if err != nil {
		return PredictedObject{}, err
	}
	v13, err := optionalNil(obj, "objects", parseArray(PredictedObjectFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v14, err := optionalNil(obj, "classes", parseArray(PredictedClassFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v15, err := optionalNil(obj, "texts", parseArray(PredictedTextFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v16, err := optionalNil(obj, "keyPoints", parseArray(PredictedKeyPointsFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v17, err := optionalNil(obj, "meshes", parseArray(PredictedMeshFromJSON))
	if err != nil {
		return PredictedObject{}, err
	}
	v18, err := optionalNil(obj, "details", parseArray(parseFree))
	if err != nil {
		return PredictedObject{}, err
	}
	return PredictedObject{ClassLabel: v0, Confidence: v1, Category: v2, X: v3, Y: v4, Width: v5, Height: v6, Orientation: v7, TrackId: v8, GlobalObjectId: v9, Outline: v10, Contours: v11, Mask: v12, Objects: v13, Classes: v14, Texts: v15, KeyPoints: v16, Meshes: v17, Details: v18, Raw: copyMap(obj)}, nil
}

func (v PredictedObject) ToJSON() any {
	out := copyMap(v.Raw)
	if v.ClassLabel != nil {
		out["classLabel"] = (*v.ClassLabel)
	} else {
		delete(out, "classLabel")
	}
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	if v.X != nil {
		putNumber(out, "x", *v.X)
	} else {
		delete(out, "x")
	}
	if v.Y != nil {
		putNumber(out, "y", *v.Y)
	} else {
		delete(out, "y")
	}
	if v.Width != nil {
		putNumber(out, "width", *v.Width)
	} else {
		delete(out, "width")
	}
	if v.Height != nil {
		putNumber(out, "height", *v.Height)
	} else {
		delete(out, "height")
	}
	if v.Orientation != nil {
		putNumber(out, "orientation", *v.Orientation)
	} else {
		delete(out, "orientation")
	}
	if v.TrackId != nil {
		out["trackId"] = (*v.TrackId)
	} else {
		delete(out, "trackId")
	}
	if v.GlobalObjectId != nil {
		out["globalObjectId"] = (*v.GlobalObjectId)
	} else {
		delete(out, "globalObjectId")
	}
	if v.Outline != nil {
		out["outline"] = mapList(v.Outline, func(x Point) any { return x.ToJSON() })
	} else {
		delete(out, "outline")
	}
	if v.Contours != nil {
		out["contours"] = mapList(v.Contours, func(x Contour) any { return x.ToJSON() })
	} else {
		delete(out, "contours")
	}
	if v.Mask != nil {
		out["mask"] = (*v.Mask).ToJSON()
	} else {
		delete(out, "mask")
	}
	if v.Objects != nil {
		out["objects"] = mapList(v.Objects, func(x PredictedObject) any { return x.ToJSON() })
	} else {
		delete(out, "objects")
	}
	if v.Classes != nil {
		out["classes"] = mapList(v.Classes, func(x PredictedClass) any { return x.ToJSON() })
	} else {
		delete(out, "classes")
	}
	if v.Texts != nil {
		out["texts"] = mapList(v.Texts, func(x PredictedText) any { return x.ToJSON() })
	} else {
		delete(out, "texts")
	}
	if v.KeyPoints != nil {
		out["keyPoints"] = mapList(v.KeyPoints, func(x PredictedKeyPoints) any { return x.ToJSON() })
	} else {
		delete(out, "keyPoints")
	}
	if v.Meshes != nil {
		out["meshes"] = mapList(v.Meshes, func(x PredictedMesh) any { return x.ToJSON() })
	} else {
		delete(out, "meshes")
	}
	if v.Details != nil {
		out["details"] = mapList(v.Details, func(x map[string]any) any { return deepCopy(x) })
	} else {
		delete(out, "details")
	}
	return out
}

type PredictedText struct {
	Text       *string
	Confidence *float64
	Category   *string
	Raw        map[string]any
}

func PredictedTextFromJSON(value any) (PredictedText, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictedText{}, err
	}
	v0, err := optional(obj, "text", parseString)
	if err != nil {
		return PredictedText{}, err
	}
	v1, err := optional(obj, "confidence", parseNumber)
	if err != nil {
		return PredictedText{}, err
	}
	v2, err := optional(obj, "category", parseString)
	if err != nil {
		return PredictedText{}, err
	}
	return PredictedText{Text: v0, Confidence: v1, Category: v2, Raw: copyMap(obj)}, nil
}

func (v PredictedText) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Text != nil {
		out["text"] = (*v.Text)
	} else {
		delete(out, "text")
	}
	if v.Confidence != nil {
		putNumber(out, "confidence", *v.Confidence)
	} else {
		delete(out, "confidence")
	}
	if v.Category != nil {
		out["category"] = (*v.Category)
	} else {
		delete(out, "category")
	}
	return out
}

type Prediction struct {
	Timestamp           *int64
	Seconds             *float64
	Offset              *int64
	Duration            *int64
	Captured_at         *int64
	Source_id           *string
	Source_width        *int64
	Source_height       *int64
	Compute_units       *float64
	Milli_compute_units *int64
	Selected            *bool
	Objects             []PredictedObject
	Classes             []PredictedClass
	Texts               []PredictedText
	KeyPoints           []PredictedKeyPoints
	Meshes              []PredictedMesh
	Depth               *Depth
	Tokens              map[string]any
	Details             []map[string]any
	Track_events        []TrackEvent
	Raw                 map[string]any
}

func PredictionFromJSON(value any) (Prediction, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Prediction{}, err
	}
	v0, err := optional(obj, "timestamp", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v1, err := optional(obj, "seconds", parseNumber)
	if err != nil {
		return Prediction{}, err
	}
	v2, err := optional(obj, "offset", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v3, err := optional(obj, "duration", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v4, err := optional(obj, "captured_at", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v5, err := optional(obj, "source_id", parseString)
	if err != nil {
		return Prediction{}, err
	}
	v6, err := optional(obj, "source_width", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v7, err := optional(obj, "source_height", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v8, err := optional(obj, "compute_units", parseNumber)
	if err != nil {
		return Prediction{}, err
	}
	v9, err := optional(obj, "milli_compute_units", parseInteger)
	if err != nil {
		return Prediction{}, err
	}
	v10, err := optional(obj, "selected", parseBoolean)
	if err != nil {
		return Prediction{}, err
	}
	v11, err := optionalNil(obj, "objects", parseArray(PredictedObjectFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	v12, err := optionalNil(obj, "classes", parseArray(PredictedClassFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	v13, err := optionalNil(obj, "texts", parseArray(PredictedTextFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	v14, err := optionalNil(obj, "keyPoints", parseArray(PredictedKeyPointsFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	v15, err := optionalNil(obj, "meshes", parseArray(PredictedMeshFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	v16, err := optional(obj, "depth", DepthFromJSON)
	if err != nil {
		return Prediction{}, err
	}
	v17, err := optionalNil(obj, "tokens", parseFree)
	if err != nil {
		return Prediction{}, err
	}
	v18, err := optionalNil(obj, "details", parseArray(parseFree))
	if err != nil {
		return Prediction{}, err
	}
	v19, err := optionalNil(obj, "track_events", parseArray(TrackEventFromJSON))
	if err != nil {
		return Prediction{}, err
	}
	return Prediction{Timestamp: v0, Seconds: v1, Offset: v2, Duration: v3, Captured_at: v4, Source_id: v5, Source_width: v6, Source_height: v7, Compute_units: v8, Milli_compute_units: v9, Selected: v10, Objects: v11, Classes: v12, Texts: v13, KeyPoints: v14, Meshes: v15, Depth: v16, Tokens: v17, Details: v18, Track_events: v19, Raw: copyMap(obj)}, nil
}

func (v Prediction) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Timestamp != nil {
		out["timestamp"] = (*v.Timestamp)
	} else {
		delete(out, "timestamp")
	}
	if v.Seconds != nil {
		putNumber(out, "seconds", *v.Seconds)
	} else {
		delete(out, "seconds")
	}
	if v.Offset != nil {
		out["offset"] = (*v.Offset)
	} else {
		delete(out, "offset")
	}
	if v.Duration != nil {
		out["duration"] = (*v.Duration)
	} else {
		delete(out, "duration")
	}
	if v.Captured_at != nil {
		out["captured_at"] = (*v.Captured_at)
	} else {
		delete(out, "captured_at")
	}
	if v.Source_id != nil {
		out["source_id"] = (*v.Source_id)
	} else {
		delete(out, "source_id")
	}
	if v.Source_width != nil {
		out["source_width"] = (*v.Source_width)
	} else {
		delete(out, "source_width")
	}
	if v.Source_height != nil {
		out["source_height"] = (*v.Source_height)
	} else {
		delete(out, "source_height")
	}
	if v.Compute_units != nil {
		putNumber(out, "compute_units", *v.Compute_units)
	} else {
		delete(out, "compute_units")
	}
	if v.Milli_compute_units != nil {
		out["milli_compute_units"] = (*v.Milli_compute_units)
	} else {
		delete(out, "milli_compute_units")
	}
	if v.Selected != nil {
		out["selected"] = (*v.Selected)
	} else {
		delete(out, "selected")
	}
	if v.Objects != nil {
		out["objects"] = mapList(v.Objects, func(x PredictedObject) any { return x.ToJSON() })
	} else {
		delete(out, "objects")
	}
	if v.Classes != nil {
		out["classes"] = mapList(v.Classes, func(x PredictedClass) any { return x.ToJSON() })
	} else {
		delete(out, "classes")
	}
	if v.Texts != nil {
		out["texts"] = mapList(v.Texts, func(x PredictedText) any { return x.ToJSON() })
	} else {
		delete(out, "texts")
	}
	if v.KeyPoints != nil {
		out["keyPoints"] = mapList(v.KeyPoints, func(x PredictedKeyPoints) any { return x.ToJSON() })
	} else {
		delete(out, "keyPoints")
	}
	if v.Meshes != nil {
		out["meshes"] = mapList(v.Meshes, func(x PredictedMesh) any { return x.ToJSON() })
	} else {
		delete(out, "meshes")
	}
	if v.Depth != nil {
		out["depth"] = (*v.Depth).ToJSON()
	} else {
		delete(out, "depth")
	}
	if v.Tokens != nil {
		out["tokens"] = deepCopy(v.Tokens)
	} else {
		delete(out, "tokens")
	}
	if v.Details != nil {
		out["details"] = mapList(v.Details, func(x map[string]any) any { return deepCopy(x) })
	} else {
		delete(out, "details")
	}
	if v.Track_events != nil {
		out["track_events"] = mapList(v.Track_events, func(x TrackEvent) any { return x.ToJSON() })
	} else {
		delete(out, "track_events")
	}
	return out
}

type PredictionMessage struct {
	Id         string
	Prediction Prediction
	Raw        map[string]any
}

func PredictionMessageFromJSON(value any) (PredictionMessage, error) {
	obj, err := parseObject(value)
	if err != nil {
		return PredictionMessage{}, err
	}
	if _, err := required(obj, "type", parseConst("prediction")); err != nil {
		return PredictionMessage{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return PredictionMessage{}, err
	}
	v1, err := required(obj, "prediction", PredictionFromJSON)
	if err != nil {
		return PredictionMessage{}, err
	}
	return PredictionMessage{Id: v0, Prediction: v1, Raw: copyMap(obj)}, nil
}

func (v PredictionMessage) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["prediction"] = v.Prediction.ToJSON()
	out["type"] = "prediction"
	return out
}

func (PredictionMessage) isJobMessage() {}
func (PredictionMessage) isMessage()    {}

type Quit struct {
	Id  string
	Raw map[string]any
}

func QuitFromJSON(value any) (Quit, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Quit{}, err
	}
	if _, err := required(obj, "type", parseConst("quit")); err != nil {
		return Quit{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Quit{}, err
	}
	return Quit{Id: v0, Raw: copyMap(obj)}, nil
}

func (v Quit) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "quit"
	return out
}

func (Quit) isCommand() {}

type RawComponent struct {
	Type string
	Raw  map[string]any
}

func RawComponentFromJSON(value any) (RawComponent, error) {
	obj, err := parseObject(value)
	if err != nil {
		return RawComponent{}, err
	}
	v0, err := required(obj, "type", parseString)
	if err != nil {
		return RawComponent{}, err
	}
	return RawComponent{Type: v0, Raw: copyMap(obj)}, nil
}

func (v RawComponent) ToJSON() any {
	out := copyMap(v.Raw)
	out["type"] = v.Type
	return out
}

func (RawComponent) isPopComponent() {}

type Result struct {
	Id  string
	Raw map[string]any
}

func ResultFromJSON(value any) (Result, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Result{}, err
	}
	if _, err := required(obj, "type", parseConst("result")); err != nil {
		return Result{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Result{}, err
	}
	return Result{Id: v0, Raw: copyMap(obj)}, nil
}

func (v Result) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "result"
	return out
}

func (Result) isMessage() {}

type Send struct {
	Id     string
	Credit int64
	Member *int64
	Raw    map[string]any
}

func SendFromJSON(value any) (Send, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Send{}, err
	}
	if _, err := required(obj, "type", parseConst("send")); err != nil {
		return Send{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Send{}, err
	}
	v1, err := required(obj, "credit", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Send{}, err
	}
	v2, err := optional(obj, "member", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Send{}, err
	}
	return Send{Id: v0, Credit: v1, Member: v2, Raw: copyMap(obj)}, nil
}

func (v Send) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["credit"] = v.Credit
	if v.Member != nil {
		out["member"] = (*v.Member)
	} else {
		delete(out, "member")
	}
	out["type"] = "send"
	return out
}

func (Send) isMessage() {}

type SetPop struct {
	Id  string
	Pop Pop
	Raw map[string]any
}

func SetPopFromJSON(value any) (SetPop, error) {
	obj, err := parseObject(value)
	if err != nil {
		return SetPop{}, err
	}
	if _, err := required(obj, "type", parseConst("setPop")); err != nil {
		return SetPop{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return SetPop{}, err
	}
	v1, err := required(obj, "pop", PopFromJSON)
	if err != nil {
		return SetPop{}, err
	}
	return SetPop{Id: v0, Pop: v1, Raw: copyMap(obj)}, nil
}

func (v SetPop) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["pop"] = v.Pop.ToJSON()
	out["type"] = "setPop"
	return out
}

func (SetPop) isCommand() {}

type SetSourceUpload struct {
	ContentType string
	Raw         map[string]any
}

func SetSourceUploadFromJSON(value any) (SetSourceUpload, error) {
	obj, err := parseObject(value)
	if err != nil {
		return SetSourceUpload{}, err
	}
	v0, err := required(obj, "contentType", parseString)
	if err != nil {
		return SetSourceUpload{}, err
	}
	return SetSourceUpload{ContentType: v0, Raw: copyMap(obj)}, nil
}

func (v SetSourceUpload) ToJSON() any {
	out := copyMap(v.Raw)
	out["contentType"] = v.ContentType
	return out
}

type SetSource struct {
	Id        string
	Url       *string
	AssetUuid *string
	Upload    *SetSourceUpload
	Group     []GroupMember
	Params    []ComponentParams
	Fps       *string
	Roi       *Roi
	Camera    *Camera
	Live      *bool
	Mode      *SetSourceMode
	Raw       map[string]any
}

func SetSourceFromJSON(value any) (SetSource, error) {
	obj, err := parseObject(value)
	if err != nil {
		return SetSource{}, err
	}
	if _, err := required(obj, "type", parseConst("setSource")); err != nil {
		return SetSource{}, err
	}
	if err := exactlyOne(obj, "url", "assetUuid", "upload", "group"); err != nil {
		return SetSource{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return SetSource{}, err
	}
	v1, err := optional(obj, "url", parseString)
	if err != nil {
		return SetSource{}, err
	}
	v2, err := optional(obj, "assetUuid", parseString)
	if err != nil {
		return SetSource{}, err
	}
	v3, err := optional(obj, "upload", SetSourceUploadFromJSON)
	if err != nil {
		return SetSource{}, err
	}
	v4, err := optionalNil(obj, "group", parseArray(GroupMemberFromJSON))
	if err != nil {
		return SetSource{}, err
	}
	v5, err := optionalNil(obj, "params", parseArray(ComponentParamsFromJSON))
	if err != nil {
		return SetSource{}, err
	}
	v6, err := optional(obj, "fps", parseString)
	if err != nil {
		return SetSource{}, err
	}
	v7, err := optional(obj, "roi", RoiFromJSON)
	if err != nil {
		return SetSource{}, err
	}
	v8, err := optional(obj, "camera", CameraFromJSON)
	if err != nil {
		return SetSource{}, err
	}
	v9, err := optional(obj, "live", parseBoolean)
	if err != nil {
		return SetSource{}, err
	}
	v10, err := optional(obj, "mode", SetSourceModeFromJSON)
	if err != nil {
		return SetSource{}, err
	}
	return SetSource{Id: v0, Url: v1, AssetUuid: v2, Upload: v3, Group: v4, Params: v5, Fps: v6, Roi: v7, Camera: v8, Live: v9, Mode: v10, Raw: copyMap(obj)}, nil
}

func (v SetSource) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	if v.Url != nil {
		out["url"] = (*v.Url)
	} else {
		delete(out, "url")
	}
	if v.AssetUuid != nil {
		out["assetUuid"] = (*v.AssetUuid)
	} else {
		delete(out, "assetUuid")
	}
	if v.Upload != nil {
		out["upload"] = (*v.Upload).ToJSON()
	} else {
		delete(out, "upload")
	}
	if v.Group != nil {
		out["group"] = mapList(v.Group, func(x GroupMember) any { return x.ToJSON() })
	} else {
		delete(out, "group")
	}
	if v.Params != nil {
		out["params"] = mapList(v.Params, func(x ComponentParams) any { return x.ToJSON() })
	} else {
		delete(out, "params")
	}
	if v.Fps != nil {
		out["fps"] = (*v.Fps)
	} else {
		delete(out, "fps")
	}
	if v.Roi != nil {
		out["roi"] = (*v.Roi).ToJSON()
	} else {
		delete(out, "roi")
	}
	if v.Camera != nil {
		out["camera"] = (*v.Camera).ToJSON()
	} else {
		delete(out, "camera")
	}
	if v.Live != nil {
		out["live"] = (*v.Live)
	} else {
		delete(out, "live")
	}
	if v.Mode != nil {
		out["mode"] = string((*v.Mode))
	} else {
		delete(out, "mode")
	}
	out["type"] = "setSource"
	return out
}

func (SetSource) isCommand() {}

type SourceDefaults struct {
	Camera            *Camera
	Fps               *string
	Roi               *Roi
	MotionDetect      *bool
	MotionSensitivity *float64
	MotionThreshold   *float64
	MotionGap         *int64
	MotionGridX       *int64
	MotionGridY       *int64
	Raw               map[string]any
}

func SourceDefaultsFromJSON(value any) (SourceDefaults, error) {
	obj, err := parseObject(value)
	if err != nil {
		return SourceDefaults{}, err
	}
	v0, err := optional(obj, "camera", CameraFromJSON)
	if err != nil {
		return SourceDefaults{}, err
	}
	v1, err := optional(obj, "fps", parseString)
	if err != nil {
		return SourceDefaults{}, err
	}
	v2, err := optional(obj, "roi", RoiFromJSON)
	if err != nil {
		return SourceDefaults{}, err
	}
	v3, err := optional(obj, "motionDetect", parseBoolean)
	if err != nil {
		return SourceDefaults{}, err
	}
	v4, err := optional(obj, "motionSensitivity", parseNumber)
	if err != nil {
		return SourceDefaults{}, err
	}
	v5, err := optional(obj, "motionThreshold", parseNumber)
	if err != nil {
		return SourceDefaults{}, err
	}
	v6, err := optional(obj, "motionGap", parseInteger)
	if err != nil {
		return SourceDefaults{}, err
	}
	v7, err := optional(obj, "motionGridX", parseInteger)
	if err != nil {
		return SourceDefaults{}, err
	}
	v8, err := optional(obj, "motionGridY", parseInteger)
	if err != nil {
		return SourceDefaults{}, err
	}
	return SourceDefaults{Camera: v0, Fps: v1, Roi: v2, MotionDetect: v3, MotionSensitivity: v4, MotionThreshold: v5, MotionGap: v6, MotionGridX: v7, MotionGridY: v8, Raw: copyMap(obj)}, nil
}

func (v SourceDefaults) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Camera != nil {
		out["camera"] = (*v.Camera).ToJSON()
	} else {
		delete(out, "camera")
	}
	if v.Fps != nil {
		out["fps"] = (*v.Fps)
	} else {
		delete(out, "fps")
	}
	if v.Roi != nil {
		out["roi"] = (*v.Roi).ToJSON()
	} else {
		delete(out, "roi")
	}
	if v.MotionDetect != nil {
		out["motionDetect"] = (*v.MotionDetect)
	} else {
		delete(out, "motionDetect")
	}
	if v.MotionSensitivity != nil {
		putNumber(out, "motionSensitivity", *v.MotionSensitivity)
	} else {
		delete(out, "motionSensitivity")
	}
	if v.MotionThreshold != nil {
		putNumber(out, "motionThreshold", *v.MotionThreshold)
	} else {
		delete(out, "motionThreshold")
	}
	if v.MotionGap != nil {
		out["motionGap"] = (*v.MotionGap)
	} else {
		delete(out, "motionGap")
	}
	if v.MotionGridX != nil {
		out["motionGridX"] = (*v.MotionGridX)
	} else {
		delete(out, "motionGridX")
	}
	if v.MotionGridY != nil {
		out["motionGridY"] = (*v.MotionGridY)
	} else {
		delete(out, "motionGridY")
	}
	return out
}

type Start struct {
	Id  string
	Raw map[string]any
}

func StartFromJSON(value any) (Start, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Start{}, err
	}
	if _, err := required(obj, "type", parseConst("start")); err != nil {
		return Start{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Start{}, err
	}
	return Start{Id: v0, Raw: copyMap(obj)}, nil
}

func (v Start) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "start"
	return out
}

func (Start) isJobMessage() {}
func (Start) isMessage()    {}

type StopSource struct {
	Id  string
	Raw map[string]any
}

func StopSourceFromJSON(value any) (StopSource, error) {
	obj, err := parseObject(value)
	if err != nil {
		return StopSource{}, err
	}
	if _, err := required(obj, "type", parseConst("stopSource")); err != nil {
		return StopSource{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return StopSource{}, err
	}
	return StopSource{Id: v0, Raw: copyMap(obj)}, nil
}

func (v StopSource) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["type"] = "stopSource"
	return out
}

func (StopSource) isCommand() {}

type TrackEvent struct {
	Track_id   *int64
	Is_ended   *bool
	Started_at *int64
	Ended_at   *int64
	Raw        map[string]any
}

func TrackEventFromJSON(value any) (TrackEvent, error) {
	obj, err := parseObject(value)
	if err != nil {
		return TrackEvent{}, err
	}
	v0, err := optional(obj, "track_id", parseInteger)
	if err != nil {
		return TrackEvent{}, err
	}
	v1, err := optional(obj, "is_ended", parseBoolean)
	if err != nil {
		return TrackEvent{}, err
	}
	v2, err := optional(obj, "started_at", parseInteger)
	if err != nil {
		return TrackEvent{}, err
	}
	v3, err := optional(obj, "ended_at", parseInteger)
	if err != nil {
		return TrackEvent{}, err
	}
	return TrackEvent{Track_id: v0, Is_ended: v1, Started_at: v2, Ended_at: v3, Raw: copyMap(obj)}, nil
}

func (v TrackEvent) ToJSON() any {
	out := copyMap(v.Raw)
	if v.Track_id != nil {
		out["track_id"] = (*v.Track_id)
	} else {
		delete(out, "track_id")
	}
	if v.Is_ended != nil {
		out["is_ended"] = (*v.Is_ended)
	} else {
		delete(out, "is_ended")
	}
	if v.Started_at != nil {
		out["started_at"] = (*v.Started_at)
	} else {
		delete(out, "started_at")
	}
	if v.Ended_at != nil {
		out["ended_at"] = (*v.Ended_at)
	} else {
		delete(out, "ended_at")
	}
	return out
}

type Uploaded struct {
	Id     string
	Member *int64
	Raw    map[string]any
}

func UploadedFromJSON(value any) (Uploaded, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Uploaded{}, err
	}
	if _, err := required(obj, "type", parseConst("uploaded")); err != nil {
		return Uploaded{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Uploaded{}, err
	}
	v1, err := optional(obj, "member", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Uploaded{}, err
	}
	return Uploaded{Id: v0, Member: v1, Raw: copyMap(obj)}, nil
}

func (v Uploaded) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	if v.Member != nil {
		out["member"] = (*v.Member)
	} else {
		delete(out, "member")
	}
	out["type"] = "uploaded"
	return out
}

func (Uploaded) isCommand() {}

type Usage struct {
	Id                string
	MilliComputeUnits int64
	Raw               map[string]any
}

func UsageFromJSON(value any) (Usage, error) {
	obj, err := parseObject(value)
	if err != nil {
		return Usage{}, err
	}
	if _, err := required(obj, "type", parseConst("usage")); err != nil {
		return Usage{}, err
	}
	v0, err := required(obj, "id", limitString(parseString, 1))
	if err != nil {
		return Usage{}, err
	}
	v1, err := required(obj, "milliComputeUnits", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return Usage{}, err
	}
	return Usage{Id: v0, MilliComputeUnits: v1, Raw: copyMap(obj)}, nil
}

func (v Usage) ToJSON() any {
	out := copyMap(v.Raw)
	out["id"] = v.Id
	out["milliComputeUnits"] = v.MilliComputeUnits
	out["type"] = "usage"
	return out
}

func (Usage) isJobMessage() {}
func (Usage) isMessage()    {}

type GroupMemberUrl struct {
	Url string
	Raw map[string]any
}

func GroupMemberUrlFromJSON(value any) (GroupMemberUrl, error) {
	obj, err := parseObject(value)
	if err != nil {
		return GroupMemberUrl{}, err
	}
	v0, err := required(obj, "url", parseString)
	if err != nil {
		return GroupMemberUrl{}, err
	}
	return GroupMemberUrl{Url: v0, Raw: copyMap(obj)}, nil
}

func (v GroupMemberUrl) ToJSON() any {
	out := copyMap(v.Raw)
	out["url"] = v.Url
	return out
}

func (GroupMemberUrl) isGroupMember() {}

type GroupMemberUploadUpload struct {
	ContentType string
	Bytes       *int64
	Raw         map[string]any
}

func GroupMemberUploadUploadFromJSON(value any) (GroupMemberUploadUpload, error) {
	obj, err := parseObject(value)
	if err != nil {
		return GroupMemberUploadUpload{}, err
	}
	v0, err := required(obj, "contentType", parseString)
	if err != nil {
		return GroupMemberUploadUpload{}, err
	}
	v1, err := optional(obj, "bytes", limitNumeric(parseInteger, at(0), noBound, noBound))
	if err != nil {
		return GroupMemberUploadUpload{}, err
	}
	return GroupMemberUploadUpload{ContentType: v0, Bytes: v1, Raw: copyMap(obj)}, nil
}

func (v GroupMemberUploadUpload) ToJSON() any {
	out := copyMap(v.Raw)
	out["contentType"] = v.ContentType
	if v.Bytes != nil {
		out["bytes"] = (*v.Bytes)
	} else {
		delete(out, "bytes")
	}
	return out
}

type GroupMemberUpload struct {
	Upload GroupMemberUploadUpload
	Raw    map[string]any
}

func GroupMemberUploadFromJSON(value any) (GroupMemberUpload, error) {
	obj, err := parseObject(value)
	if err != nil {
		return GroupMemberUpload{}, err
	}
	v0, err := required(obj, "upload", GroupMemberUploadUploadFromJSON)
	if err != nil {
		return GroupMemberUpload{}, err
	}
	return GroupMemberUpload{Upload: v0, Raw: copyMap(obj)}, nil
}

func (v GroupMemberUpload) ToJSON() any {
	out := copyMap(v.Raw)
	out["upload"] = v.Upload.ToJSON()
	return out
}

func (GroupMemberUpload) isGroupMember() {}

type RoiRectangle struct {
	X      float64
	Y      float64
	Width  float64
	Height float64
	Raw    map[string]any
}

func RoiRectangleFromJSON(value any) (RoiRectangle, error) {
	obj, err := parseObject(value)
	if err != nil {
		return RoiRectangle{}, err
	}
	if _, err := required(obj, "type", parseConst("rectangle")); err != nil {
		return RoiRectangle{}, err
	}
	v0, err := required(obj, "x", parseNumber)
	if err != nil {
		return RoiRectangle{}, err
	}
	v1, err := required(obj, "y", parseNumber)
	if err != nil {
		return RoiRectangle{}, err
	}
	v2, err := required(obj, "width", parseNumber)
	if err != nil {
		return RoiRectangle{}, err
	}
	v3, err := required(obj, "height", parseNumber)
	if err != nil {
		return RoiRectangle{}, err
	}
	return RoiRectangle{X: v0, Y: v1, Width: v2, Height: v3, Raw: copyMap(obj)}, nil
}

func (v RoiRectangle) ToJSON() any {
	out := copyMap(v.Raw)
	putNumber(out, "x", v.X)
	putNumber(out, "y", v.Y)
	putNumber(out, "width", v.Width)
	putNumber(out, "height", v.Height)
	out["type"] = "rectangle"
	return out
}

func (RoiRectangle) isRoi() {}

type RoiContourPoint struct {
	X   float64
	Y   float64
	Raw map[string]any
}

func RoiContourPointFromJSON(value any) (RoiContourPoint, error) {
	obj, err := parseObject(value)
	if err != nil {
		return RoiContourPoint{}, err
	}
	v0, err := required(obj, "x", parseNumber)
	if err != nil {
		return RoiContourPoint{}, err
	}
	v1, err := required(obj, "y", parseNumber)
	if err != nil {
		return RoiContourPoint{}, err
	}
	return RoiContourPoint{X: v0, Y: v1, Raw: copyMap(obj)}, nil
}

func (v RoiContourPoint) ToJSON() any {
	out := copyMap(v.Raw)
	putNumber(out, "x", v.X)
	putNumber(out, "y", v.Y)
	return out
}

type RoiContour struct {
	Points []RoiContourPoint
	Raw    map[string]any
}

func RoiContourFromJSON(value any) (RoiContour, error) {
	obj, err := parseObject(value)
	if err != nil {
		return RoiContour{}, err
	}
	if _, err := required(obj, "type", parseConst("contour")); err != nil {
		return RoiContour{}, err
	}
	v0, err := required(obj, "points", parseArray(RoiContourPointFromJSON))
	if err != nil {
		return RoiContour{}, err
	}
	return RoiContour{Points: v0, Raw: copyMap(obj)}, nil
}

func (v RoiContour) ToJSON() any {
	out := copyMap(v.Raw)
	out["points"] = mapList(v.Points, func(x RoiContourPoint) any { return x.ToJSON() })
	out["type"] = "contour"
	return out
}

func (RoiContour) isRoi() {}

type Command interface {
	ToJSON() any
	isCommand()
}

func CommandFromJSON(value any) (Command, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if obj["type"] == "setPop" {
		parsed, err := SetPopFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "ping" {
		parsed, err := PingFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "setSource" {
		parsed, err := SetSourceFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "uploaded" {
		parsed, err := UploadedFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "stopSource" {
		parsed, err := StopSourceFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "getGraph" {
		parsed, err := GetGraphFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "quit" {
		parsed, err := QuitFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	return nil, fmt.Errorf("no variant matches")
}

type UnknownCommand struct {
	Raw map[string]any
}

func (UnknownCommand) isCommand() {}

func (u UnknownCommand) ToJSON() any {
	return copyMap(u.Raw)
}

func DecodeCommand(value any) Command {
	if !within(value, maxDepth) {
		return UnknownCommand{Raw: map[string]any{}}
	}
	parsed, err := CommandFromJSON(value)
	if err != nil {
		raw, _ := value.(map[string]any)
		return UnknownCommand{Raw: copyMap(raw)}
	}
	return parsed
}

type GroupMember interface {
	ToJSON() any
	isGroupMember()
}

func GroupMemberFromJSON(value any) (GroupMember, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if hasKey(obj, "url") {
		if err := exactlyOne(obj, "url", "upload"); err != nil {
			return nil, err
		}
		parsed, err := GroupMemberUrlFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if hasKey(obj, "upload") {
		if err := exactlyOne(obj, "url", "upload"); err != nil {
			return nil, err
		}
		parsed, err := GroupMemberUploadFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	return nil, fmt.Errorf("no variant matches")
}

type JobMessage interface {
	ToJSON() any
	isJobMessage()
}

func JobMessageFromJSON(value any) (JobMessage, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if obj["type"] == "start" {
		parsed, err := StartFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "prediction" {
		parsed, err := PredictionMessageFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "dropped" {
		parsed, err := DroppedFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "usage" {
		parsed, err := UsageFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "end" {
		parsed, err := EndFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	return nil, fmt.Errorf("no variant matches")
}

type Message interface {
	ToJSON() any
	isMessage()
}

func MessageFromJSON(value any) (Message, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if obj["type"] == "result" {
		parsed, err := ResultFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "send" {
		parsed, err := SendFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "credit" {
		parsed, err := CreditFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "start" {
		parsed, err := StartFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "prediction" {
		parsed, err := PredictionMessageFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "dropped" {
		parsed, err := DroppedFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "usage" {
		parsed, err := UsageFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "end" {
		parsed, err := EndFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "done" {
		parsed, err := DoneFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "pong" {
		parsed, err := PongFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "error" {
		parsed, err := ErrorMessageFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	return nil, fmt.Errorf("no variant matches")
}

type UnknownMessage struct {
	Raw map[string]any
}

func (UnknownMessage) isMessage() {}

func (u UnknownMessage) ToJSON() any {
	return copyMap(u.Raw)
}

func DecodeMessage(value any) Message {
	if !within(value, maxDepth) {
		return UnknownMessage{Raw: map[string]any{}}
	}
	parsed, err := MessageFromJSON(value)
	if err != nil {
		raw, _ := value.(map[string]any)
		return UnknownMessage{Raw: copyMap(raw)}
	}
	return parsed
}

type PopComponent interface {
	ToJSON() any
	isPopComponent()
}

func PopComponentFromJSON(value any) (PopComponent, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if obj["type"] == "inference" {
		parsed, err := InferenceComponentFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	parsed, err := RawComponentFromJSON(value)
	if err != nil {
		return nil, err
	}
	return parsed, nil
}

type Roi interface {
	ToJSON() any
	isRoi()
}

func RoiFromJSON(value any) (Roi, error) {
	obj, err := parseObject(value)
	if err != nil {
		return nil, err
	}
	if obj["type"] == "rectangle" {
		parsed, err := RoiRectangleFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	if obj["type"] == "contour" {
		parsed, err := RoiContourFromJSON(value)
		if err != nil {
			return nil, err
		}
		return parsed, nil
	}
	return nil, fmt.Errorf("no variant matches")
}
