import re

import pytest

from codegen import generate
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
        ("toJSON", "go", "ToJSON"),
        ("toString", "csharp", "ToString"),
        ("wire", "csharp", "Wire"),
    ],
)
def test_a_property_that_becomes_a_generated_member_is_rejected(property, language, name):
    rejects(thing(**{property: text()}), f"property {property!r} of Thing becomes the {language} name {name}, which the generated code already uses")


def test_a_csharp_property_named_like_a_type_another_field_reads_is_rejected():
    schemas = {"camera": schema("camera", {"type": "object", "properties": {"x": text()}})} | thing(Camera=text(), lens={"$ref": "camera.json"})

    rejects(schemas, "property 'Camera' of Thing becomes the csharp name Camera")


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
