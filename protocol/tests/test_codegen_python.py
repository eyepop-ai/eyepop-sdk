import dataclasses

import pytest

from conftest import load_python, ping, schema
from codegen import generate


def python(schemas, roots=()):
    return load_python(generate(schemas, roots, None)["python"])


def test_a_closed_object_round_trips():
    protocol = python({"ping": ping()})

    value = protocol.Ping.from_json({"type": "ping", "id": "p1"})

    assert value.id == "p1"
    assert value.to_json() == {"type": "ping", "id": "p1"}


def note():
    return schema(
        "note",
        {
            "type": "object",
            "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["id"],
        },
    )


def test_an_absent_optional_field_is_none_and_stays_absent_on_output():
    protocol = python({"note": note()})

    value = protocol.Note.from_json({"id": "n1"})

    assert value.text is None
    assert value.to_json() == {"id": "n1"}


def test_unknown_fields_survive_a_round_trip():
    protocol = python({"note": note()})

    value = protocol.Note.from_json({"id": "n1", "future": {"a": [1]}})

    assert value.to_json() == {"id": "n1", "future": {"a": [1]}}


@pytest.mark.parametrize(
    "bad",
    ["ping", {}, {"type": "ping"}, {"type": "ping", "id": 1}, {"type": "pong", "id": "p1"}],
    ids=["not-an-object", "empty", "missing-id", "id-not-a-string", "wrong-type-tag"],
)
def test_malformed_input_raises_value_error(bad):
    protocol = python({"ping": ping()})

    with pytest.raises(ValueError):
        protocol.Ping.from_json(bad)


def pong():
    return schema(
        "pong",
        {"type": "object", "properties": {"type": {"const": "pong"}}, "required": ["type"]},
    )


def messages():
    return {
        "message": schema("message", {"oneOf": [{"$ref": "ping.json"}, {"$ref": "pong.json"}]}),
        "ping": ping(),
        "pong": pong(),
    }


def test_a_union_decodes_to_the_variant_named_by_its_type_tag():
    protocol = python(messages(), roots=("message",))

    assert isinstance(protocol.decode_message({"type": "pong"}), protocol.Pong)
    assert protocol.decode_message({"type": "ping", "id": "p1"}) == protocol.Ping(id="p1")


def test_an_unknown_type_decodes_to_the_unknown_variant_keeping_its_json():
    protocol = python(messages(), roots=("message",))

    value = protocol.decode_message({"type": "future", "x": 1})

    assert isinstance(value, protocol.UnknownMessage)
    assert value.to_json() == {"type": "future", "x": 1}


def test_a_known_type_that_does_not_parse_decodes_to_the_unknown_variant():
    protocol = python(messages(), roots=("message",))

    assert isinstance(protocol.decode_message({"type": "ping"}), protocol.UnknownMessage)


def test_decoded_json_is_a_snapshot_of_the_input():
    protocol = python({"note": note()})
    data = {"id": "n1", "future": {"a": 1}}

    value = protocol.Note.from_json(data)
    data["future"]["a"] = 2

    assert value.to_json()["future"] == {"a": 1}


def test_encoded_json_does_not_alias_the_value():
    protocol = python({"note": note()})
    value = protocol.Note.from_json({"id": "n1", "future": {"a": 1}})

    value.to_json()["future"]["a"] = 3

    assert value.to_json()["future"] == {"a": 1}


def test_a_field_set_to_none_is_removed_from_the_retained_json():
    protocol = python({"note": note()})
    value = protocol.Note.from_json({"id": "n1", "text": "x"})

    assert dataclasses.replace(value, text=None).to_json() == {"id": "n1"}


def test_a_requested_root_that_is_not_a_union_is_rejected():
    with pytest.raises(ValueError, match="message"):
        generate({"ping": ping()}, ("message",), None)
