import re

import pytest

from codegen import generate
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


@pytest.mark.parametrize(
    "prop",
    [
        {"const": "a", "minItems": 1},
        {"enum": ["a"], "minItems": 1},
        {"type": "array", "items": {"type": "string"}, "minItems": 1},
        {"type": "object", "properties": {"x": {"type": "number"}}, "minItems": 1},
    ],
    ids=["const", "enum", "array", "inline-object"],
)
def test_a_stray_keyword_beside_each_value_form_is_rejected(prop):
    rejects({"thing": thing(other=prop)}, "thing.json#/properties/other: `minItems`")


def test_a_keyword_beside_a_ref_is_rejected():
    rejects({"thing": thing(other={"$ref": "thing.json", "minimum": 1})}, "thing.json#/properties/other: `minimum`")


def test_a_type_array_is_rejected():
    rejects({"thing": thing(count={"type": ["integer", "null"]})}, "thing.json#/properties/count: `type` must be one of")


def test_an_inline_one_of_on_a_property_is_rejected():
    count = {"oneOf": [{"type": "integer"}, {"type": "string"}]}

    rejects({"thing": thing(count=count)}, "thing.json#/properties/count: `oneOf`")


def test_a_value_without_a_type_is_rejected():
    rejects({"thing": thing(count={})}, "thing.json#/properties/count: `type` must be one of")


def test_an_inline_object_without_a_type_is_rejected():
    rejects({"thing": thing(detail={"properties": {"x": {"type": "number"}}})}, 'thing.json#/properties/detail: an object with `properties` needs `"type": "object"`')


@pytest.mark.parametrize(
    "prop, where",
    [
        (True, "thing.json#/properties/other: a schema here must be an object"),
        ({"type": "array", "items": True}, "thing.json#/properties/other/items: a schema here must be an object"),
        ({"type": "array", "items": [{"type": "string"}]}, "thing.json#/properties/other/items: a schema here must be an object"),
    ],
    ids=["boolean-property", "boolean-items", "tuple-items"],
)
def test_a_schema_that_is_not_an_object_is_rejected(prop, where):
    rejects({"thing": thing(other=prop)}, where)


def test_all_of_without_a_ref_is_rejected():
    body = thing()
    body["allOf"] = [{}]

    rejects({"thing": body}, "thing.json#/allOf/0: `$ref` None")


def test_an_all_of_cycle_is_rejected():
    body = thing()
    body["allOf"] = [{"$ref": "base.json"}]
    base = schema("base", {"type": "object", "properties": {"x": {"type": "number"}}, "allOf": [{"$ref": "thing.json"}]})

    rejects({"thing": body, "base": base}, "thing.json#/allOf: `allOf` cycle: base -> thing -> base")


def test_a_ref_cycle_used_from_a_property_is_rejected():
    tree = schema("tree", {"type": "array", "items": {"$ref": "tree.json"}})

    rejects({"thing": thing(tree={"$ref": "tree.json"}), "tree": tree}, "thing.json#/properties/tree: `$ref` cycle: tree -> tree")


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

    rejects({"thing": body, "thingDetail": detail}, "thingDetail.json#: two object types are named ThingDetail; the other comes from thing.json#")


def test_an_inline_union_variant_named_like_another_object_is_rejected():
    union = schema("either", {"oneOf": [{"type": "object", "properties": {"type": {"const": "thing"}}}]})
    clash = schema("eitherThing", {"type": "object", "properties": {"y": {"type": "number"}}})

    rejects({"either": union, "eitherThing": clash}, "either.json#/oneOf/0: two object types are named EitherThing")


@pytest.mark.parametrize(
    "prop, where",
    [
        ({"type": "object", "additionalProperties": {"type": "integer"}}, "`additionalProperties` is only accepted as true or false"),
        ({"type": "integer", "not": {"const": "x"}}, "`not` is only accepted as"),
        ({"type": "string", "not": {"enum": ["x"]}}, "`not` is only accepted as"),
        ({"type": "string", "not": {"const": 1}}, "`not` is only accepted as"),
    ],
    ids=["typed-map", "not-on-integer", "not-enum", "not-const-number"],
)
def test_an_ignored_keyword_in_another_form_is_rejected(prop, where):
    rejects({"thing": thing(other=prop)}, f"thing.json#/properties/other: {where}")


def test_not_beside_properties_is_rejected():
    body = thing()
    body["not"] = {"const": "x"}

    rejects({"thing": body}, "thing.json#: `not` is only accepted as")


@pytest.mark.parametrize("keyword", ["const", "enum"])
def test_a_string_type_beside_const_or_enum_is_accepted_and_changes_nothing(keyword):
    plain = {"const": "a"} if keyword == "const" else {"enum": ["a"]}

    assert parse({"thing": thing(level={"type": "string", **plain})}, ()) == parse({"thing": thing(level=plain)}, ())


def test_a_description_leaves_the_generated_output_unchanged():
    described = thing(name={"type": "string", "description": "what it is called"})

    assert generate({"thing": described}, ()) == generate({"thing": thing(name={"type": "string"})}, ())


@pytest.mark.parametrize(
    "keyword, value, at",
    [
        ("additionalProperties", False, "object"),
        ("additionalProperties", True, "object"),
        ("not", {"const": "x"}, "value"),
        ("title", "a thing", "value"),
        ("description", "a thing", "value"),
        ("$comment", "a note", "object"),
        ("examples", ["a"], "value"),
        ("deprecated", True, "value"),
    ],
)
def test_ignored_keywords_and_annotations_are_accepted_and_change_nothing(keyword, value, at):
    plain = thing(name={"type": "string"})
    marked = thing(name={"type": "string"})
    (marked if at == "object" else marked["properties"]["name"])[keyword] = value

    assert parse({"thing": marked}, ()) == parse({"thing": plain}, ())
