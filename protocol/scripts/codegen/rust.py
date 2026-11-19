import re

from .model import Always, Array, Const, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant

HEADER = """// Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.
#![allow(dead_code, non_snake_case, clippy::all)]

use serde_json::{Map, Value};

#[derive(Debug, Clone, PartialEq)]
pub struct DecodeError(pub String);

fn fail<T>(message: String) -> std::result::Result<T, DecodeError> {
    Err(DecodeError(message))
}

fn parse_object(value: &Value) -> std::result::Result<&Map<String, Value>, DecodeError> {
    match value {
        Value::Object(map) => Ok(map),
        _ => fail(format!("expected an object, got {value}")),
    }
}

fn parse_string(value: &Value) -> std::result::Result<String, DecodeError> {
    match value {
        Value::String(text) => Ok(text.clone()),
        _ => fail(format!("expected a string, got {value}")),
    }
}

fn parse_integer(value: &Value) -> std::result::Result<i64, DecodeError> {
    match value.as_i64() {
        Some(number) => Ok(number),
        None => fail(format!("expected an integer, got {value}")),
    }
}

fn parse_number(value: &Value) -> std::result::Result<f64, DecodeError> {
    match value {
        Value::Number(number) => Ok(number.as_f64().unwrap_or(f64::NAN)),
        _ => fail(format!("expected a number, got {value}")),
    }
}

fn parse_boolean(value: &Value) -> std::result::Result<bool, DecodeError> {
    match value {
        Value::Bool(flag) => Ok(*flag),
        _ => fail(format!("expected a boolean, got {value}")),
    }
}

fn parse_free(value: &Value) -> std::result::Result<Map<String, Value>, DecodeError> {
    parse_object(value).cloned()
}

fn parse_const(expected: &'static str) -> impl Fn(&Value) -> std::result::Result<(), DecodeError> {
    move |value| match value {
        Value::String(text) if text == expected => Ok(()),
        _ => fail(format!("expected {expected:?}, got {value}")),
    }
}

fn parse_array<T>(
    item: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> impl Fn(&Value) -> std::result::Result<Vec<T>, DecodeError> {
    move |value| match value {
        Value::Array(elements) => elements.iter().map(&item).collect(),
        _ => fail(format!("expected an array, got {value}")),
    }
}

fn required<T>(
    obj: &Map<String, Value>,
    key: &str,
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> std::result::Result<T, DecodeError> {
    match obj.get(key) {
        Some(value) => parse(value),
        None => fail(format!("missing {key}")),
    }
}

fn optional<T>(
    obj: &Map<String, Value>,
    key: &str,
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
) -> std::result::Result<Option<T>, DecodeError> {
    obj.get(key).map(parse).transpose()
}

fn number_to_json(number: f64) -> Value {
    if number.fract() == 0.0 && number.abs() < 9.0e15 {
        Value::from(number as i64)
    } else {
        Value::from(number)
    }
}
"""

KEYWORDS = {"type", "match", "ref", "in", "mod", "use", "fn", "as", "loop", "move", "impl", "trait", "struct", "enum"}
RUST_TYPES = {"string": "String", "integer": "i64", "number": "f64", "boolean": "bool"}
PARSERS = {"string": "parse_string", "integer": "parse_integer", "number": "parse_number", "boolean": "parse_boolean"}


def emit(model: Model) -> str:
    enums = sorted({e.name: e for e in collect_enums(model)}.values(), key=lambda e: e.name)
    parts = [emit_enum(e) for e in enums]
    parts += [emit_object(o) for o in model.objects]
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


def field_name(name: str) -> str:
    return f"r#{name}" if name in KEYWORDS else name


def rust_type(type_: Type) -> str:
    match type_:
        case Enum(_, name):
            return name
        case Free():
            return "Map<String, Value>"
        case Array(item):
            return f"Vec<{rust_type(item)}>"
        case Ref(name):
            return name
        case _:
            return RUST_TYPES[type_]


def parser(type_: Type) -> str:
    match type_:
        case Const(value):
            return f"parse_const({value!r})".replace("'", '"')
        case Enum(_, name):
            return f"{name}::from_json"
        case Free():
            return "parse_free"
        case Array(item):
            return f"parse_array({parser(item)})"
        case Ref(name):
            return f"{name}::from_json"
        case _:
            return PARSERS[type_]


def dump(type_: Type, ref: str) -> str:
    match type_:
        case Enum() | Ref():
            return f"{ref}.to_json()"
        case Free():
            return f"Value::Object({ref}.clone())"
        case Array(item):
            return f"Value::Array({ref}.iter().map(|x| {dump(item, 'x')}).collect())"
        case "string":
            return f"Value::String({ref}.clone())"
        case "integer":
            return f"Value::from(*{ref})"
        case "number":
            return f"number_to_json(*{ref})"
        case _:
            return f"Value::Bool(*{ref})"


def emit_enum(enum: Enum) -> str:
    names = [variant_name(v) for v in enum.values]
    variants = "\n".join(f"    {n}," for n in names)
    reads = "\n".join(f'            Some("{v}") => Ok({enum.name}::{n}),' for v, n in zip(enum.values, names))
    writes = "\n".join(f'            {enum.name}::{n} => Value::from("{v}"),' for v, n in zip(enum.values, names))
    return f"""
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum {enum.name} {{
{variants}
}}

impl {enum.name} {{
    pub fn from_json(value: &Value) -> std::result::Result<{enum.name}, DecodeError> {{
        match value.as_str() {{
{reads}
            _ => fail(format!("unexpected value {{value}}")),
        }}
    }}

    pub fn to_json(&self) -> Value {{
        match self {{
{writes}
        }}
    }}
}}
"""


def emit_object(obj: Object) -> str:
    consts = [f for f in obj.fields if isinstance(f.type, Const)]
    typed = [f for f in obj.fields if not isinstance(f.type, Const)]
    fields = "\n".join(
        f"    pub {field_name(f.name)}: {rust_type(f.type) if f.required else f'Option<{rust_type(f.type)}>'},"
        for f in typed
    )
    checks = "".join(f'        required(obj, "{f.name}", {parser(f.type)})?;\n' for f in consts)
    reads = "\n".join(
        f'            {field_name(f.name)}: {"required" if f.required else "optional"}(obj, "{f.name}", {parser(f.type)})?,'
        for f in typed
    )
    writes = []
    for f in typed:
        name = f"self.{field_name(f.name)}"
        if f.required:
            writes.append(f'        out.insert("{f.name}".to_string(), {dump(f.type, f"(&{name})")});')
        else:
            writes.append(
                f'        if let Some(x) = &{name} {{\n            out.insert("{f.name}".to_string(), {dump(f.type, "x")});\n        }}'
            )
    writes += [f'        out.insert("{f.name}".to_string(), Value::from("{f.type.value}"));' for f in consts]
    return f"""
#[derive(Debug, Clone, PartialEq)]
pub struct {obj.name} {{
{fields}
    pub raw: Map<String, Value>,
}}

impl {obj.name} {{
    pub fn from_json(value: &Value) -> std::result::Result<{obj.name}, DecodeError> {{
        let obj = parse_object(value)?;
{checks}        Ok({obj.name} {{
{reads}
            raw: obj.clone(),
        }})
    }}

    pub fn to_json(&self) -> Value {{
        let mut out = self.raw.clone();
{chr(10).join(writes)}
        Value::Object(out)
    }}
}}
"""


def condition(variant: Variant) -> str | None:
    match variant.match:
        case Tag(value):
            return f'obj.get("type").and_then(Value::as_str) == Some("{value}")'
        case Key(name):
            return f'obj.contains_key("{name}")'
        case Always():
            return None


def emit_union(union: Union) -> str:
    name = union.name
    members = "\n".join(f"    {v.name}({v.name})," for v in union.variants)
    if union.open:
        members += "\n    Unknown(Map<String, Value>),"
    arms = []
    for v in union.variants:
        branch = f"{name}::{v.name}({v.name}::from_json(value)?)"
        cond = condition(v)
        arms.append(f"        if {cond} {{\n            return Ok({branch});\n        }}" if cond else f"        return Ok({branch});")
    if not any(condition(v) is None for v in union.variants):
        arms.append('        fail("no variant matches".to_string())')
    dumps = "\n".join(f"            {name}::{v.name}(v) => v.to_json()," for v in union.variants)
    decode = ""
    if union.open:
        dumps += f"\n            {name}::Unknown(raw) => Value::Object(raw.clone()),"
        decode = f"""
    pub fn decode(value: &Value) -> {name} {{
        {name}::from_json(value)
            .unwrap_or_else(|_| {name}::Unknown(value.as_object().cloned().unwrap_or_default()))
    }}
"""
    return f"""
#[derive(Debug, Clone, PartialEq)]
pub enum {name} {{
{members}
}}

impl {name} {{
    pub fn from_json(value: &Value) -> std::result::Result<{name}, DecodeError> {{
        let obj = parse_object(value)?;
{chr(10).join(arms)}
    }}
{decode}
    pub fn to_json(&self) -> Value {{
        match self {{
{dumps}
        }}
    }}
}}
"""
