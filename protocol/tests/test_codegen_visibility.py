import pytest

from codegen import generate
from conftest import schema


def obj(name: str, tag: str | None = None, **properties) -> dict:
    props = {"id": {"type": "string"}, **properties}
    if tag:
        props["type"] = {"const": tag}
    return schema(name, {"type": "object", "properties": props, "required": ["id", *(["type"] if tag else [])]})


def union(name: str, *variants: str) -> dict:
    return schema(name, {"oneOf": [{"$ref": f"{variant}.json"} for variant in variants]})


SCHEMAS = {
    "shown": obj("shown", level={"enum": ["low", "high"]}, part={"$ref": "part.json"}),
    "part": obj("part"),
    "hidden": obj("hidden", mode={"enum": ["a", "b"]}),
    "start": obj("start", "start"),
    "pong": obj("pong", "pong"),
    "setPop": obj("setPop", "setPop"),
    "command": union("command", "setPop"),
    "message": union("message", "start", "pong"),
    "jobMessage": union("jobMessage", "start"),
}
ROOTS = ("command", "message")


def csharp(public) -> str:
    return generate(SCHEMAS, ROOTS, public)["csharp"]


def test_a_public_list_names_a_schema_that_does_not_exist():
    with pytest.raises(ValueError, match="public list names 'missing', which is not a schema"):
        csharp(["shown", "missing"])


def test_csharp_marks_what_the_list_does_not_name_internal():
    source = csharp(["shown", "part", "start", "jobMessage"])

    assert "public sealed record Shown(" in source
    assert "internal sealed record Hidden(" in source
    assert "internal sealed record SetPop(" in source


def test_an_enum_is_public_with_the_schema_that_defines_it():
    source = csharp(["shown", "part"])

    assert "public enum ShownLevel" in source
    assert "public static class ShownLevelWire" in source


def test_a_public_type_that_holds_an_internal_one_fails():
    with pytest.raises(ValueError, match="public type Shown holds Part, which is not on the public list"):
        csharp(["shown"])


def test_a_public_union_with_an_internal_variant_fails():
    with pytest.raises(ValueError, match="public type Message has the variant Pong, which is not on the public list"):
        csharp(["start", "message"])


def test_a_variant_of_a_public_union_and_of_an_internal_one_sits_under_the_public_one():
    source = csharp(["start", "jobMessage"])

    assert "public abstract record JobMessage" in source
    assert "public sealed record Start(string Id, JsonObject? Raw = null) : JobMessage, IMessage" in source


def test_an_internal_union_that_holds_public_variants_is_an_interface_not_their_base_type():
    source = csharp(["start", "jobMessage"])

    assert "internal interface IMessage\n{\n    JsonNode ToJson();\n}" in source
    assert "internal static class MessageWire" in source
    assert "public static IMessage Decode(JsonNode? value)" in source
    assert "internal sealed record UnknownMessage(JsonObject Raw) : IMessage" in source
    assert "internal sealed record Pong(string Id, JsonObject? Raw = null) : IMessage" in source
    assert "ToJson(object" not in source


def test_an_enum_of_an_unlisted_schema_is_internal():
    source = csharp(["start", "jobMessage"])

    assert "internal enum HiddenMode" in source
    assert "internal static class HiddenModeWire" in source


def test_a_public_type_holding_a_list_of_an_internal_one_fails():
    bag = obj("bag", parts={"type": "array", "items": {"$ref": "hidden.json"}})

    with pytest.raises(ValueError, match="public type Bag holds Hidden, which is not on the public list"):
        generate({**SCHEMAS, "bag": bag}, ROOTS, ["bag"])


def test_without_a_list_every_type_stays_public():
    assert "internal sealed record" not in csharp(None)


def test_an_empty_public_list_fails():
    with pytest.raises(ValueError, match="the public list is empty"):
        csharp([])


def test_a_listed_schema_that_defines_no_type_fails():
    scalar = schema("code", {"type": "string"})

    with pytest.raises(ValueError, match="public list names 'code', which defines no type"):
        generate({**SCHEMAS, "code": scalar}, ROOTS, ["start", "jobMessage", "code"])
