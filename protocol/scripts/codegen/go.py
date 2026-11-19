import re

from .model import Always, Array, Const, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant, pascal

HEADER = """// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.

package eyepop

import (
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

func parseInteger(value any) (int64, error) {
	number, ok := value.(float64)
	if !ok || number != math.Trunc(number) {
		return 0, fmt.Errorf("expected an integer, got %v", value)
	}
	return int64(number), nil
}

func parseNumber(value any) (float64, error) {
	number, ok := value.(float64)
	if !ok {
		return 0, fmt.Errorf("expected a number, got %v", value)
	}
	return number, nil
}

func parseBoolean(value any) (bool, error) {
	flag, ok := value.(bool)
	if !ok {
		return false, fmt.Errorf("expected a boolean, got %v", value)
	}
	return flag, nil
}

func parseFree(value any) (map[string]any, error) {
	return parseObject(value)
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

func copyMap(source map[string]any) map[string]any {
	out := make(map[string]any, len(source))
	for key, value := range source {
		out[key] = value
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


def parser(type_: Type) -> str:
    match type_:
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
        case Array(item) if isinstance(item, (Ref, Enum, Array)):
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
    writes = []
    for f in typed:
        field = f"v.{pascal(f.name)}"
        if f.required:
            writes.append(f'\tout["{f.name}"] = {dump(f.type, field)}')
        elif is_plain(f.type):
            writes.append(f'\tif {field} != nil {{\n\t\tout["{f.name}"] = {dump(f.type, "(*" + field + ")")}\n\t}}')
        else:
            writes.append(f'\tif {field} != nil {{\n\t\tout["{f.name}"] = {dump(f.type, field)}\n\t}}')
    writes += [f'\tout["{f.name}"] = "{f.type.value}"' for f in consts]
    inits.append("Raw: obj")
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
		return Unknown{name}{{Raw: raw}}
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
