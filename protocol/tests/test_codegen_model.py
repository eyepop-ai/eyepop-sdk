import re

import pytest

from codegen.model import parse
from conftest import schema


def thing(**properties) -> dict:
    return schema("thing", {"type": "object", "properties": {"id": {"type": "string"}, **properties}, "required": ["id"]})


def rejects(schemas: dict, where: str) -> None:
    with pytest.raises(ValueError, match=re.escape(where)):
        parse(schemas, ())


@pytest.mark.parametrize(
    "keyword, value",
    [("maximum", 10), ("pattern", "^a"), ("maxLength", 3), ("format", "uuid"), ("multipleOf", 2), ("minItems", 1)],
)
def test_an_unknown_keyword_on_a_value_is_rejected(keyword, value):
    rejects({"thing": thing(count={"type": "integer", keyword: value})}, f"thing.json#/properties/count: `{keyword}`")


def test_an_unknown_keyword_on_an_object_is_rejected():
    body = thing()
    body["patternProperties"] = {}

    rejects({"thing": body}, "thing.json#: `patternProperties`")


def test_an_unknown_keyword_on_a_union_is_rejected():
    union = schema("either", {"oneOf": [{"$ref": "thing.json"}], "discriminator": {}})

    rejects({"either": union, "thing": thing()}, "either.json#: `discriminator`")


def test_a_limit_that_does_not_fit_the_type_is_rejected():
    rejects({"thing": thing(count={"type": "integer", "minLength": 1})}, "thing.json#/properties/count: `minLength`")


def test_a_keyword_beside_a_ref_is_rejected():
    rejects({"thing": thing(other={"$ref": "thing.json", "minimum": 1})}, "thing.json#/properties/other: `minimum`")


def test_a_type_array_is_rejected():
    rejects({"thing": thing(count={"type": ["integer", "null"]})}, "thing.json#/properties/count: `type` must be one of")


def test_an_inline_one_of_on_a_property_is_rejected():
    count = {"oneOf": [{"type": "integer"}, {"type": "string"}]}

    rejects({"thing": thing(count=count)}, "thing.json#/properties/count: `oneOf`")


def test_a_value_without_a_type_is_rejected():
    rejects({"thing": thing(count={})}, "thing.json#/properties/count: `type` must be one of")


def test_an_array_without_items_is_rejected():
    rejects({"thing": thing(tags={"type": "array"})}, "thing.json#/properties/tags: an array needs `items`")


def test_a_ref_to_a_missing_schema_is_rejected():
    rejects({"thing": thing(other={"$ref": "missing.json"})}, "thing.json#/properties/other: `$ref` 'missing.json'")


def test_a_const_that_is_not_a_string_is_rejected():
    rejects({"thing": thing(version={"const": 1})}, "thing.json#/properties/version: `const` must be a string")


def test_an_enum_that_is_not_strings_is_rejected():
    rejects({"thing": thing(level={"enum": [1, 2]})}, "thing.json#/properties/level: `enum` must list strings")


def test_a_one_of_beside_properties_that_is_not_a_required_key_selector_is_rejected():
    body = thing()
    body["oneOf"] = [{"required": ["id"]}, {"properties": {"id": {"const": "x"}}}]

    rejects({"thing": body}, "thing.json#/oneOf/1: `oneOf` beside `properties`")


def test_a_required_key_that_is_not_a_property_is_rejected():
    body = thing()
    body["required"] = ["id", "idd"]

    rejects({"thing": body}, "thing.json#: `required` names idd")


def test_all_of_a_schema_that_is_not_an_object_is_rejected():
    body = thing()
    body["allOf"] = [{"$ref": "name.json"}]

    rejects({"thing": body, "name": schema("name", {"type": "string"})}, "thing.json#/allOf/0: `allOf` must reference")


def test_a_union_variant_that_is_not_an_object_is_rejected():
    union = schema("either", {"oneOf": [{"$ref": "name.json"}]})

    rejects({"either": union, "name": schema("name", {"type": "string"})}, "either.json#/oneOf/0: a union variant must")


def test_an_inline_union_variant_without_a_name_is_rejected():
    union = schema("either", {"oneOf": [{"type": "object", "properties": {"x": {"type": "number"}}}]})

    rejects({"either": union}, "either.json#/oneOf/0: an inline union variant needs")


def test_a_union_variant_that_cannot_be_told_apart_is_rejected():
    union = schema("either", {"oneOf": [{"$ref": "thing.json"}, {"$ref": "other.json"}]})
    other = schema("other", {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]})

    rejects({"either": union, "thing": thing(), "other": other}, "either.json#/oneOf: variant Thing has no")


def test_two_object_types_with_one_name_are_rejected():
    body = thing(detail={"type": "object", "properties": {"x": {"type": "number"}}})
    detail = schema("thingDetail", {"type": "object", "properties": {"y": {"type": "number"}}})

    rejects({"thing": body, "thingDetail": detail}, "two object types are named ThingDetail")


@pytest.mark.parametrize(
    "keyword, value, at",
    [("additionalProperties", False, "object"), ("not", {"const": "x"}, "value"), ("title", "a thing", "value")],
)
def test_ignored_keywords_and_annotations_are_accepted_and_change_nothing(keyword, value, at):
    plain = thing(name={"type": "string"})
    marked = thing(name={"type": "string"})
    (marked if at == "object" else marked["properties"]["name"])[keyword] = value

    assert parse({"thing": marked}, ()) == parse({"thing": plain}, ())
