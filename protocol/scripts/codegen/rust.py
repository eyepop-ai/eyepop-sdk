import re

from .model import Always, Array, Const, Constrained, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant

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
    if let Some(number) = value.as_i64() {
        return Ok(number);
    }
    match value.as_f64() {
        Some(number) if number.fract() == 0.0 && number.abs() < 9.2e18 => Ok(number as i64),
        _ => fail(format!("expected an integer, got {value}")),
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

fn limit<T>(
    parse: impl Fn(&Value) -> std::result::Result<T, DecodeError>,
    measure: impl Fn(&T) -> f64,
    minimum: Option<f64>,
    exclusive_minimum: Option<f64>,
    exclusive_maximum: Option<f64>,
) -> impl Fn(&Value) -> std::result::Result<T, DecodeError> {
    move |value| {
        let parsed = parse(value)?;
        let size = measure(&parsed);
        if minimum.is_some_and(|bound| size < bound)
            || exclusive_minimum.is_some_and(|bound| size <= bound)
            || exclusive_maximum.is_some_and(|bound| size >= bound)
        {
            return fail(format!("{value} is out of range"));
        }
        Ok(parsed)
    }
}

fn exactly_one(obj: &Map<String, Value>, keys: &[&str]) -> std::result::Result<(), DecodeError> {
    let present = keys.iter().filter(|key| obj.contains_key(**key)).count();
    if present == 1 {
        Ok(())
    } else {
        fail(format!("expected exactly one of {keys:?}, got {present}"))
    }
}

fn put_number(out: &mut Map<String, Value>, key: &str, number: f64) {
    if out.get(key).and_then(Value::as_f64) != Some(number) {
        out.insert(key.to_string(), number_to_json(number));
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
        case Constrained(kind):
            return RUST_TYPES[kind]
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


def bound(value: float | None) -> str:
    return "None" if value is None else f"Some({float(value)!r})"


def parser(type_: Type) -> str:
    match type_:
        case Constrained(kind, minimum, exclusive_minimum, exclusive_maximum, min_length):
            measure = "|text: &String| text.chars().count() as f64" if kind == "string" else "|n| *n as f64"
            low = float(min_length) if min_length is not None else minimum
            return f"limit({PARSERS[kind]}, {measure}, {bound(low)}, {bound(exclusive_minimum)}, {bound(exclusive_maximum)})"
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
        case Constrained(kind):
            return dump(kind, ref)
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
    if obj.exactly_one:
        keys = ", ".join(f'"{k}"' for k in obj.exactly_one)
        checks += f"        exactly_one(obj, &[{keys}])?;\n"
    reads = "\n".join(
        f'            {field_name(f.name)}: {"required" if f.required else "optional"}(obj, "{f.name}", {parser(f.type)})?,'
        for f in typed
    )
    writes = []
    for f in typed:
        name = f"self.{field_name(f.name)}"
        is_number = f.type == "number" or (isinstance(f.type, Constrained) and f.type.kind == "number")
        if f.required:
            if is_number:
                writes.append(f'        put_number(&mut out, "{f.name}", {name});')
            else:
                writes.append(f'        out.insert("{f.name}".to_string(), {dump(f.type, f"(&{name})")});')
        else:
            put = (
                f'put_number(&mut out, "{f.name}", *x);'
                if is_number
                else f'out.insert("{f.name}".to_string(), {dump(f.type, "x")});'
            )
            writes.append(
                f'        if let Some(x) = &{name} {{\n            {put}\n        }} else {{\n            out.remove("{f.name}");\n        }}'
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
