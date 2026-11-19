import dataclasses

import pytest

from codegen import csharp, go, python, rust
from codegen.model import WIRE, WIRE_RULES, parse
from conftest import load_python, ping, schema

EMITTERS = {"python": python.emit, "rust": rust.emit, "go": go.emit, "csharp": csharp.emit}


def schemas() -> dict:
    thing = schema(
        "thing",
        {
            "type": "object",
            "properties": {
                "type": {"const": "thing"},
                "id": {"type": "string", "minLength": 2},
                "count": {"type": "integer"},
                "extra": {"type": "object"},
            },
            "required": ["type", "id"],
        },
    )
    return {"message": schema("message", {"oneOf": [{"$ref": "thing.json"}, {"$ref": "ping.json"}]}), "thing": thing, "ping": ping()}


def protocol(**wire):
    model = parse(schemas(), ("message",))
    return load_python(python.emit(dataclasses.replace(model, wire=dataclasses.replace(model.wire, **wire))))


def test_the_wire_rules_are_data_on_the_model():
    model = parse(schemas(), ("message",))

    assert model.wire == WIRE
    assert (WIRE.integer_minimum, WIRE.integer_maximum, WIRE.length_unit, WIRE.max_depth) == (-(2**63), 2**63 - 1, "code point", 64)
    assert set(WIRE_RULES) == {"integer", "number", "length", "exactly one", "depth", "duplicate keys", "unicode"}


def test_the_integer_bounds_come_from_the_model():
    generated = protocol(integer_minimum=-5, integer_maximum=100)

    decoded = [type(generated.decode_message({"type": "thing", "id": "t1", "count": n})).__name__ for n in (-6, -5, 100, 101, 100.0)]

    assert decoded == ["UnknownMessage", "Thing", "Thing", "UnknownMessage", "Thing"]


def test_the_depth_limit_comes_from_the_model():
    generated = protocol(max_depth=3)

    two = generated.decode_message({"type": "thing", "id": "t1", "extra": {"a": []}})
    four = generated.decode_message({"type": "thing", "id": "t1", "extra": {"a": [[]]}})

    assert type(two).__name__ == "Thing"
    assert type(four).__name__ == "UnknownMessage"
    assert four.to_json() == {}


def test_a_string_length_counts_code_points():
    generated = protocol()

    assert type(generated.decode_message({"type": "thing", "id": "\U0001f600"})).__name__ == "UnknownMessage"
    assert type(generated.decode_message({"type": "thing", "id": "\U0001f600\U0001f600"})).__name__ == "Thing"


@pytest.mark.parametrize("language", EMITTERS)
def test_every_emitter_takes_the_bounds_from_the_model(language):
    model = parse(schemas(), ("message",))
    changed = dataclasses.replace(model, wire=dataclasses.replace(model.wire, integer_minimum=-12345, integer_maximum=6789, max_depth=97))

    default, mutated = EMITTERS[language](model), EMITTERS[language](changed)

    assert all(literal in default for literal in ("9223372036854775807", "-9223372036854775808"))
    assert all(literal not in mutated for literal in ("9223372036854775807", "9223372036854775808", "9.2e18", "19"))
    assert all(literal in mutated for literal in ("-12345", "6789", "97"))


@pytest.mark.parametrize("language", EMITTERS)
def test_a_length_unit_an_emitter_cannot_adapt_fails_generation(language):
    model = parse(schemas(), ("message",))

    with pytest.raises(KeyError, match="byte"):
        EMITTERS[language](dataclasses.replace(model, wire=dataclasses.replace(model.wire, length_unit="byte")))
