import re

from .model import Always, Array, Const, Constrained, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant, pascal

HEADER = """// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.

package eyepop

import (
	"encoding/json"
	"fmt"
	"math"
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
	if number != math.Trunc(number) || math.Abs(number) >= 9.2e18 {
		return 0, false
	}
	return int64(number), true
}

func parseInteger(value any) (int64, error) {
	switch number := value.(type) {
	case int64:
		return number, nil
	case int:
		return int64(number), nil
	case float64:
		if whole, ok := wholeInt64(number); ok {
			return whole, nil
		}
	case json.Number:
		if exact, err := number.Int64(); err == nil {
			return exact, nil
		}
		if approximate, err := number.Float64(); err == nil {
			if whole, ok := wholeInt64(approximate); ok {
				return whole, nil
			}
		}
	}
	return 0, fmt.Errorf("expected an integer, got %v", value)
}

func parseNumber(value any) (float64, error) {
	switch number := value.(type) {
	case float64:
		return number, nil
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
		if len([]rune(parsed)) < minLength {
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


def emit(model: Model) -> str:
    enums = sorted({e.name: e for e in collect_enums(model)}.values(), key=lambda e: e.name)
    memberships = {obj.name: [u.name for u in model.unions if any(v.name == obj.name for v in u.variants)] for obj in model.objects}
    parts = [emit_enum(e) for e in enums]
    parts += [emit_object(o, memberships[o.name]) for o in model.objects]
    parts += [emit_union(u) for u in model.unions]
    return HEADER + "\n" + "\n".join(parts)


def collect_enums(model: Model) -> list[Enum]:
    found: list[Enum] = []

    def walk(type_: Type) -> None:
        if isinstance(type_, Enum):
            found.append(type_)
        elif isinstance(type_, Array):
            walk(type_.item)

    for obj in model.objects:
        for f in obj.fields:
            walk(f.type)
    return found


def variant_name(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^0-9A-Za-z]+", value) if part)


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
    names = [enum.name + variant_name(v) for v in enum.values]
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
    consts = [f for f in obj.fields if isinstance(f.type, Const)]
    typed = [f for f in obj.fields if not isinstance(f.type, Const)]
    decls = []
    for f in typed:
        t = go_type(f.type)
        decls.append(f"\t{pascal(f.name)} {t if f.required or not is_plain(f.type) else '*' + t}")
    reads = []
    inits = []
    for i, f in enumerate(typed):
        if f.required:
            call = "required"
        elif is_plain(f.type):
            call = "optional"
        else:
            call = "optionalNil"
        reads.append(
            f'\tv{i}, err := {call}(obj, "{f.name}", {parser(f.type)})\n\tif err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}'
        )
        inits.append(f"{pascal(f.name)}: v{i}")
    checks = "".join(
        f'\tif _, err := required(obj, "{f.name}", {parser(f.type)}); err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}\n'
        for f in consts
    )
    if obj.exactly_one:
        keys = ", ".join(f'"{k}"' for k in obj.exactly_one)
        checks += f"\tif err := exactlyOne(obj, {keys}); err != nil {{\n\t\treturn {obj.name}{{}}, err\n\t}}\n"
    writes = []
    for f in typed:
        field = f"v.{pascal(f.name)}"
        is_number = f.type == "number" or (isinstance(f.type, Constrained) and f.type.kind == "number")
        if f.required:
            writes.append(
                f'\tputNumber(out, "{f.name}", {field})' if is_number else f'\tout["{f.name}"] = {dump(f.type, field)}'
            )
        else:
            absent = f'\n\t}} else {{\n\t\tdelete(out, "{f.name}")\n\t}}'
            if is_plain(f.type):
                put = f'putNumber(out, "{f.name}", *{field})' if is_number else f'out["{f.name}"] = {dump(f.type, "(*" + field + ")")}'
            else:
                put = f'out["{f.name}"] = {dump(f.type, field)}'
            writes.append(f"\tif {field} != nil {{\n\t\t{put}{absent}")
    writes += [f'\tout["{f.name}"] = "{f.type.value}"' for f in consts]
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
