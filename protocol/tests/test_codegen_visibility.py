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
    "hidden": obj("hidden"),
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
    assert "public sealed record Start(string Id, JsonObject? Raw = null) : JobMessage" in source


def test_an_internal_union_that_holds_public_variants_is_not_their_base_type():
    source = csharp(["start", "jobMessage"])

    assert "internal static class Message" in source
    assert "public static object Decode(JsonNode? value)" in source
    assert "internal sealed record UnknownMessage(" in source
    assert "internal sealed record Pong(string Id, JsonObject? Raw = null)\n{" in source


def test_without_a_list_every_type_stays_public():
    assert "internal sealed record" not in csharp(None)
