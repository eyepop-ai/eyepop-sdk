import re

import pytest

from codegen import csharp, generate, go, python, rust
from codegen.model import parse
from conftest import load_python, schema

RUST_KEYWORDS = (
    *("as", "break", "const", "continue", "crate", "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let"),
    *("loop", "match", "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct", "super", "trait"),
    *("true", "type", "unsafe", "use", "where", "while", "async", "await", "dyn", "abstract", "become", "box", "do"),
    *("final", "macro", "override", "priv", "typeof", "unsized", "virtual", "yield", "try", "gen"),
)


def thing(**properties) -> dict:
    return {"thing": schema("thing", {"type": "object", "properties": properties})}


def text() -> dict:
    return {"type": "string"}


def rejects(schemas: dict, *parts: str) -> None:
    with pytest.raises(ValueError, match=".*".join(re.escape(part) for part in parts)):
        generate(schemas, ())


@pytest.mark.parametrize("name", ["foo-bar", "foo bar", "1st", "_id", "café"])
def test_a_property_that_is_not_a_plain_identifier_is_rejected(name):
    rejects(thing(**{name: text()}), f"thing.json#/properties/{name}: property {name!r} of Thing is not an identifier")


@pytest.mark.parametrize(
    "first, second, language, name",
    [("fooBar", "FooBar", "go", "FooBar"), ("from", "from_", "python", "from_"), ("self", "self_", "rust", "self_")],
)
def test_two_properties_that_become_one_identifier_in_a_language_are_rejected(first, second, language, name):
    rejects(thing(**{first: text(), second: text()}), f"thing.json#: properties {first!r} and {second!r} of Thing both become the {language} name {name}")


@pytest.mark.parametrize(
    "property, language, name",
    [
        ("raw", "python", "raw"),
        ("to_json", "python", "to_json"),
        ("staticmethod", "python", "staticmethod"),
        ("field", "python", "field"),
        ("dict", "python", "dict"),
        ("toJSON", "go", "ToJSON"),
        ("toString", "csharp", "ToString"),
        ("wire", "csharp", "Wire"),
    ],
)
def test_a_property_that_becomes_a_generated_member_is_rejected(property, language, name):
    rejects(thing(**{property: text()}), f"property {property!r} of Thing becomes the {language} name {name}, which the generated code already uses")


@pytest.mark.parametrize(
    "emitter, property, name",
    [(rust, "raw", "raw"), (go, "raw", "Raw"), (csharp, "raw", "Raw"), (csharp, "clone", "Clone"), (csharp, "decode", "Decode")],
)
def test_each_language_rejects_its_own_generated_members(emitter, property, name):
    language = emitter.__name__.rsplit(".", 1)[1]

    with pytest.raises(ValueError, match=re.escape(f"property {property!r} of Thing becomes the {language} name {name}")):
        parse(thing(**{property: text()}), (), {language: emitter.NAMING})


def test_a_csharp_variant_property_named_like_the_open_union_decoder_is_rejected():
    other = {"type": {"type": "string", "not": {"const": "ping"}}, "decode": text()}
    schemas = {
        "command": schema("command", {"oneOf": [{"$ref": "ping.json"}, {"$ref": "other.json"}]}),
        "ping": schema("ping", {"type": "object", "properties": {"type": {"const": "ping"}}, "required": ["type"], "additionalProperties": False}),
        "other": schema("other", {"type": "object", "properties": other, "required": ["type"], "additionalProperties": False}),
    }

    with pytest.raises(ValueError, match=re.escape("other.json#/properties/decode: property 'decode' of Other becomes the csharp name Decode")):
        generate(schemas, ("command",))


def test_a_csharp_property_named_like_the_owner_gets_a_value_suffix():
    assert "string? ThingValue = null" in generate(thing(thing=text()), ())["csharp"]


def test_a_csharp_property_named_like_a_type_another_field_reads_is_rejected():
    schemas = {"camera": schema("camera", {"type": "object", "properties": {"x": text()}})} | thing(Camera=text(), lens={"$ref": "camera.json"})

    rejects(schemas, "property 'Camera' of Thing becomes the csharp name Camera")


def test_a_csharp_property_named_like_a_type_an_array_field_reads_is_rejected():
    schemas = {"camera": schema("camera", {"type": "object", "properties": {"x": text()}})}
    schemas |= thing(Camera=text(), lenses={"type": "array", "items": {"$ref": "camera.json"}})

    rejects(schemas, "property 'Camera' of Thing becomes the csharp name Camera")


def test_a_csharp_property_named_like_an_enum_decoder_is_rejected():
    rejects(thing(mode={"enum": ["on"]}, thingModeWire=text()), "property 'thingModeWire' of Thing becomes the csharp name ThingModeWire")


def test_a_property_from_an_all_of_base_is_reported_at_the_base():
    schemas = {"camera": schema("camera", {"type": "object", "properties": {"x": text()}})}
    schemas["base"] = schema("base", {"type": "object", "properties": {"Camera": text()}})
    schemas["thing"] = schema("thing", {"type": "object", "properties": {"lens": {"$ref": "camera.json"}}, "allOf": [{"$ref": "base.json"}]})

    rejects(schemas, "base.json#/properties/Camera: property 'Camera' of Thing becomes the csharp name Camera")


def test_an_enum_in_array_items_is_reported_at_the_items():
    rejects(thing(modes={"type": "array", "items": {"enum": ["1x"]}}), "thing.json#/properties/modes/items: enum value '1x' of ThingMode")


def test_a_csharp_property_named_like_its_own_type_is_accepted():
    schemas = {"camera": schema("camera", {"type": "object", "properties": {"x": text()}})}
    schemas |= thing(camera={"$ref": "camera.json"}, cameras={"type": "array", "items": {"$ref": "camera.json"}})

    assert "csharp" in generate(schemas, ())


@pytest.mark.parametrize("value", ["1x", "-", ""])
def test_an_enum_value_whose_name_does_not_start_with_a_letter_is_rejected(value):
    rejects(thing(mode={"enum": ["on", value]}), f"thing.json#/properties/mode: enum value {value!r} of ThingMode does not start with a letter")


@pytest.mark.parametrize("values", [["a-b", "a_b"], ["A", "a"]])
def test_two_enum_values_that_become_one_identifier_are_rejected(values):
    rejects(thing(mode={"enum": values}), f"enum values {values[0]!r} and {values[1]!r} of ThingMode both become the rust name")


def test_two_enum_values_that_become_one_escaped_rust_name_are_reported_with_that_name():
    rejects(thing(mode={"enum": ["self", "Self"]}), "enum values 'self' and 'Self' of ThingMode both become the rust name Self_")


UNWRITABLE = ["a\\tb", 'a"b', "a'b", "a\tb", "a\nb"]


@pytest.mark.parametrize("value", UNWRITABLE)
def test_an_enum_value_a_string_literal_cannot_hold_is_rejected(value):
    rejects(thing(mode={"enum": [value]}), f"thing.json#/properties/mode: enum value {value!r} of ThingMode holds a quote, a backslash")


@pytest.mark.parametrize("value", UNWRITABLE)
def test_a_const_value_a_string_literal_cannot_hold_is_rejected(value):
    rejects(thing(kind={"const": value}), f"thing.json#/properties/kind: const value {value!r} holds a quote, a backslash")


@pytest.mark.parametrize("key", UNWRITABLE)
def test_a_const_property_key_a_string_literal_cannot_hold_is_rejected(key):
    rejects(thing(**{key: {"const": "v"}}), f"const property key {key!r} of Thing holds a quote, a backslash")


def test_const_property_keys_need_not_be_identifiers():
    generated = generate(thing(**{"x-kind": {"const": "v"}, "_tag": {"const": "w"}, "1st": {"const": "z"}}), ())

    assert 'out["x-kind"] = "v"' in generated["go"]


def test_an_inline_variant_tag_that_cannot_form_a_type_name_is_rejected():
    variant = {"type": "object", "properties": {"type": {"const": "get-graph"}}, "required": ["type"]}

    rejects({"command": schema("command", {"oneOf": [variant]})}, "command.json#/oneOf/0: the inline variant's type name CommandGet-graph is not an identifier")


def test_an_enum_value_that_becomes_a_generated_name_is_rejected():
    rejects(thing(mode={"enum": ["fromJSON"]}), "enum value 'fromJSON' of ThingMode becomes the go name FromJSON")


def test_a_python_keyword_property_is_renamed_and_keeps_its_wire_key():
    protocol = load_python(generate(thing(**{"from": text(), "class": text(), "None": text()}), ())["python"])
    wire = {"from": "a", "class": "b", "None": "c", "extra": 1}

    value = protocol.Thing.from_json(wire)

    assert (value.from_, value.class_, value.None_) == ("a", "b", "c")
    assert value.to_json() == wire


@pytest.mark.parametrize("keyword", RUST_KEYWORDS)
def test_a_rust_keyword_property_is_escaped_and_keeps_its_wire_key(keyword):
    rust = generate(thing(**{keyword: text()}), ())["rust"]

    escaped = f"{keyword}_" if keyword in ("crate", "self", "Self", "super") else f"r#{keyword}"
    assert f"    pub {escaped}: Option<String>," in rust
    assert f'optional(obj, "{keyword}", parse_string)' in rust


def test_a_rust_enum_value_named_self_is_escaped():
    rust = generate(thing(mode={"enum": ["self"]}), ())["rust"]

    assert '            Some("self") => Ok(ThingMode::Self_),' in rust
