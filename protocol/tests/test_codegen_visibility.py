import pytest

from codegen import generate
from conftest import schema


def obj(name: str, tag: str | None = None, **properties) -> dict:
    props = {"id": {"type": "string"}, **properties}
    if tag:
        props["type"] = {"const": tag}
    return schema(name, {"type": "object", "properties": props, "required": ["id", *(["type"] if tag else [])]})


SCHEMAS = {
    "shown": obj("shown", level={"enum": ["low", "high"]}, part={"$ref": "part.json"}),
    "part": obj("part"),
    "hidden": obj("hidden"),
    "start": obj("start", "start"),
    "setPop": obj("setPop", "setPop"),
    "command": schema("command", {"oneOf": [{"$ref": "setPop.json"}]}),
    "message": schema("message", {"oneOf": [{"$ref": "start.json"}]}),
}
ROOTS = ("command", "message")


def csharp(public) -> str:
    return generate(SCHEMAS, ROOTS, public)["csharp"]


def test_a_public_list_names_a_schema_that_does_not_exist():
    with pytest.raises(ValueError, match="public list names 'missing', which is not a schema"):
        csharp(["shown", "missing"])


def test_csharp_marks_what_the_list_does_not_name_internal():
    source = csharp(["shown", "start"])

    assert "public sealed record Shown(" in source
    assert "internal sealed record Hidden(" in source
    assert "internal sealed record SetPop(" in source


def test_a_type_a_public_type_holds_is_public():
    source = csharp(["shown"])

    assert "public sealed record Part(" in source
    assert "public enum ShownLevel" in source
    assert "public static class ShownLevelWire" in source


def test_a_union_is_public_when_one_of_its_variants_is():
    source = csharp(["start"])

    assert "public abstract record Message" in source
    assert "public sealed record UnknownMessage(" in source
    assert "internal abstract record Command" in source
    assert "internal sealed record UnknownCommand(" in source


def test_without_a_list_every_type_stays_public():
    assert "internal sealed record" not in csharp(None)
