from .model import Always, Array, Const, Constrained, Enum, Field, Free, Key, Model, Naming, Object, Ref, Tag, Type, Union, Variant, Wire, is_number, pascal, value_name

HEADER = """// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.

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
"""

GO_TYPES = {"string": "string", "integer": "int64", "number": "float64", "boolean": "bool"}
PARSERS = {"string": "parseString", "integer": "parseInteger", "number": "parseNumber", "boolean": "parseBoolean"}
LENGTHS = {"code point": "len([]rune(text))"}
KEYWORDS = {
    *("break", "case", "chan", "const", "continue", "default", "defer", "else", "fallthrough", "for", "func", "go", "goto"),
    *("if", "import", "interface", "map", "package", "range", "return", "select", "struct", "switch", "type", "var"),
}


def field_name(name: str) -> str:
    exported = pascal(name)
    return exported + "_" if exported in KEYWORDS else exported


NAMING = Naming(
    field=lambda owner, name: field_name(name),
    reserved=lambda field, fields: {"Raw", "ToJSON"},
    value=value_name,
    values=frozenset({"FromJSON"}),
)


def constants(wire: Wire) -> str:
    return f"""
const (
\tintegerMinimum = {wire.integer_minimum}
\tintegerMaximum = {wire.integer_maximum}
\tintegerDigits = {wire.integer_digits}
\tmaxDepth = {wire.max_depth}
)

func length(text string) int {{
\treturn {LENGTHS[wire.length_unit]}
}}
"""


def emit(model: Model) -> str:
    parts = [emit_enum(e) for e in model.enums]
    parts += [emit_object(o, model.unions_of(o)) for o in model.objects]
    parts += [emit_union(u) for u in model.unions]
    return HEADER + constants(model.wire) + "\n" + "\n".join(parts)


def go_type(type_: Type) -> str:
    match type_:
        case Constrained(kind):
            return GO_TYPES[kind]
        case Enum(_, name):
            return name
        case Free():
            return "map[string]any"
        case Array(item):
            return f"[]{go_type(item)}"
        case Ref(name):
            return name
        case _:
            return GO_TYPES[type_]


def bound(value: float | None) -> str:
    return "noBound" if value is None else f"at({value!r})"


def parser(type_: Type) -> str:
    match type_:
        case Constrained("string", _, _, _, min_length):
            return f"limitString(parseString, {min_length or 0})"
        case Constrained(kind, minimum, exclusive_minimum, exclusive_maximum, _):
            return f"limitNumeric({PARSERS[kind]}, {bound(minimum)}, {bound(exclusive_minimum)}, {bound(exclusive_maximum)})"
        case Const(value):
            return f'parseConst("{value}")'
        case Enum(_, name):
            return f"{name}FromJSON"
        case Free():
            return "parseFree"
        case Array(item):
            return f"parseArray({parser(item)})"
        case Ref(name):
            return f"{name}FromJSON"
        case _:
            return PARSERS[type_]


def is_plain(type_: Type) -> bool:
    match type_:
        case Free() | Array():
            return False
        case _:
            return True


def dump(type_: Type, expr: str) -> str:
    match type_:
        case Enum():
            return f"string({expr})"
        case Ref():
            return f"{expr}.ToJSON()"
        case Free():
            return f"deepCopy({expr})"
        case Array(item):
            return f"mapList({expr}, func(x {go_type(item)}) any {{ return {dump(item, 'x')} }})"
        case _:
            return expr


def emit_enum(enum: Enum) -> str:
    names = [enum.name + n for n in enum.value_names]
    consts = "\n".join(f'\t{n} {enum.name} = "{v}"' for n, v in zip(names, enum.values))
    cases = ", ".join(names)
    return f"""
type {enum.name} string

const (
{consts}
)

func {enum.name}FromJSON(value any) ({enum.name}, error) {{
	switch parsed := {enum.name}(fmt.Sprint(value)); parsed {{
	case {cases}:
		return parsed, nil
	}}
	return "", fmt.Errorf("unexpected value %v", value)
}}
"""


def emit_object(obj: Object, unions: list[str]) -> str:
    decls = []
    for f in obj.typed:
        t = go_type(f.type)
        decls.append(f"\t{field_name(f.name)} {t if f.required or not is_plain(f.type) else '*' + t}")
    reads = []
    inits = []
    for i, f in enumerate(obj.typed):
        if f.required:
            call = "required"
        elif is_plain(f.type):
            call = "optional"
        else:
            call = "optionalNil"
        reads.append(
            f'\tv{i}, err := {call}(obj, "{f.name}", {parser(f.type)})\n\tif err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}'
        )
        inits.append(f"{field_name(f.name)}: v{i}")
    checks = "".join(
        f'\tif _, err := required(obj, "{f.name}", {parser(f.type)}); err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}\n'
        for f in obj.consts
    )
    if obj.exactly_one:
        keys = ", ".join(f'"{k}"' for k in obj.exactly_one)
        checks += f"\tif err := exactlyOne(obj, {keys}); err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}\n"
    writes = []
    for f in obj.typed:
        field = f"v.{field_name(f.name)}"
        if f.required:
            writes.append(
                f'\tputNumber(out, "{f.name}", {field})' if is_number(f.type) else f'\tout["{f.name}"] = {dump(f.type, field)}'
            )
        else:
            absent = f'\n\t}} else {{\n\t\tdelete(out, "{f.name}")\n\t}}'
            if is_plain(f.type):
                put = f'putNumber(out, "{f.name}", *{field})' if is_number(f.type) else f'out["{f.name}"] = {dump(f.type, "(*" + field + ")")}'
            else:
                put = f'out["{f.name}"] = {dump(f.type, field)}'
            writes.append(f"\tif {field} != nil {{\n\t\t{put}{absent}")
    writes += [f'\tout["{f.name}"] = "{f.type.value}"' for f in obj.consts]
    inits.append("Raw: copyMap(obj)")
    markers = "\n".join(f"func ({obj.name}) is{u}() {{}}" for u in unions)
    first = "\n".join(reads)
    return f"""
type {obj.name} struct {{
{chr(10).join(decls)}
	Raw map[string]any
}}

func {obj.name}FromJSON(value any) ({obj.name}, error) {{
	obj, err := parseObject(value)
	if err != nil {{
		return {obj.name}{{}}, err
	}}
{checks}{first}
	return {obj.name}{{{", ".join(inits)}}}, nil
}}

func (v {obj.name}) ToJSON() any {{
	out := copyMap(v.Raw)
{chr(10).join(writes)}
	return out
}}

{markers}
"""


def condition(variant: Variant) -> str | None:
    match variant.match:
        case Tag(value):
            return f'obj["type"] == "{value}"'
        case Key(name):
            return f'hasKey(obj, "{name}")'
        case Always():
            return None


def emit_union(union: Union) -> str:
    name = union.name
    branches = []
    for v in union.variants:
        body = f"\t\tparsed, err := {v.name}FromJSON(value)\n\t\tif err != nil {{\n\t\t\treturn nil, err\n\t\t}}\n\t\treturn parsed, nil"
        if isinstance(v.match, Key):
            keys = ", ".join(f'"{k}"' for k in union.selectors)
            body = f"\t\tif err := exactlyOne(obj, {keys}); err != nil {{\n\t\t\treturn nil, err\n\t\t}}\n" + body
        cond = condition(v)
        branches.append(f"\tif {cond} {{\n{body}\n\t}}" if cond else body.replace("\t\t", "\t"))
    tail = "" if any(condition(v) is None for v in union.variants) else '\treturn nil, fmt.Errorf("no variant matches")\n'
    unknown = ""
    if union.open:
        unknown = f"""
type Unknown{name} struct {{
	Raw map[string]any
}}

func (Unknown{name}) is{name}() {{}}

func (u Unknown{name}) ToJSON() any {{
	return copyMap(u.Raw)
}}

func Decode{name}(value any) {name} {{
	if !within(value, maxDepth) {{
		return Unknown{name}{{Raw: map[string]any{{}}}}
	}}
	parsed, err := {name}FromJSON(value)
	if err != nil {{
		raw, _ := value.(map[string]any)
		return Unknown{name}{{Raw: copyMap(raw)}}
	}}
	return parsed
}}
"""
    return f"""
type {name} interface {{
	ToJSON() any
	is{name}()
}}

func {name}FromJSON(value any) ({name}, error) {{
	obj, err := parseObject(value)
	if err != nil {{
		return nil, err
	}}
{chr(10).join(branches)}
{tail}}}
{unknown}"""
