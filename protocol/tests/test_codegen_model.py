import re

import pytest

from codegen import generate
from codegen.model import Always, Key, Tag, Variant, is_number, parse
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


def test_a_ref_that_does_not_end_in_json_is_rejected():
    rejects({"thing": thing(other={"$ref": "thing"})}, "thing.json#/properties/other: `$ref` 'thing' does not name a schema file")


def test_a_type_other_than_object_beside_properties_is_rejected():
    body = thing()
    body["type"] = "string"

    rejects({"thing": body}, "thing.json#: `type` beside `properties` must be 'object'")


def test_properties_that_are_not_an_object_are_rejected():
    rejects({"thing": schema("thing", {"type": "object", "properties": []})}, "thing.json#/properties: `properties` must be an object")


def test_a_one_of_selector_key_that_is_not_a_property_is_rejected():
    body = thing()
    body["oneOf"] = [{"required": ["id"]}, {"required": ["url"]}]

    rejects({"thing": body}, "thing.json#: `required` names url")


def test_a_ref_to_a_missing_schema_is_rejected():
    rejects({"thing": thing(other={"$ref": "missing.json"})}, "thing.json#/properties/other: `$ref` 'missing.json'")


def test_a_const_that_is_not_a_string_is_rejected():
    rejects({"thing": thing(version={"const": 1})}, "thing.json#/properties/version: `const` must be a string")


def test_an_enum_that_is_not_strings_is_rejected():
    rejects({"thing": thing(level={"enum": [1, 2]})}, "thing.json#/properties/level: `enum` must list one or more strings")


def test_an_empty_enum_is_rejected():
    rejects({"thing": thing(level={"enum": []})}, "thing.json#/properties/level: `enum` must list one or more strings")


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


def variant(properties: dict, required: list[str], closed: bool = True) -> dict:
    body = {"type": "object", "properties": {key: {"type": "string"} if prop is None else prop for key, prop in properties.items()}, "required": required}
    return body | {"additionalProperties": False} if closed else body


def either(**variants) -> dict:
    return {"either": schema("either", {"oneOf": [{"$ref": f"{n}.json"} for n in variants]}), **variants}


def dispatch(schemas: dict) -> tuple[Variant, ...]:
    return parse(schemas, ()).unions[0].variants


def raw(excluded: str = "a") -> dict:
    return variant({"type": {"type": "string", "not": {"const": excluded}}}, ["type"])


def test_a_union_tries_tags_and_keys_in_schema_order_and_the_open_type_last():
    a = variant({"type": {"const": "a"}}, ["type"])
    k = variant({"k": None}, ["k"])

    assert dispatch(either(raw=raw(), a=a, k=k)) == (Variant("A", Tag("a")), Variant("K", Key("k")), Variant("Raw", Always()))


def test_two_variants_with_one_tag_are_rejected():
    a = variant({"type": {"const": "x"}}, ["type"])
    b = variant({"type": {"const": "x"}, "q": None}, ["type", "q"])

    rejects(either(a=a, b=b), "either.json#/oneOf/1: variants A and B both have the `type` const 'x'")


def test_a_tag_that_is_not_required_is_rejected():
    a = variant({"type": {"const": "a"}, "x": None}, ["x"])
    b = variant({"type": {"const": "b"}}, ["type"])

    rejects(either(a=a, b=b), "either.json#/oneOf/0: variant A has the `type` const 'a' but does not require `type`")


def test_two_variants_with_an_open_type_are_rejected():
    rejects(either(a=raw("x"), b=raw("y")), "either.json#/oneOf/1: variants A and B both have an open `type`")


@pytest.mark.parametrize(
    "type_, tag",
    [({"type": "string"}, "a"), ({"type": "string", "not": {"const": "a"}}, "b"), ({"enum": ["a", "c"]}, "a")],
    ids=["no-not", "not-one-of-two-tags", "enum-with-a-tag"],
)
def test_an_open_type_that_accepts_a_sibling_tag_is_rejected(type_, tag):
    a = variant({"type": {"const": "a"}, "x": None}, ["type", "x"])
    b = variant({"type": {"const": "b"}}, ["type"])

    rejects(either(a=a, b=b, raw=variant({"type": type_}, ["type"])), f"either.json#/oneOf/2: variant Raw has an open `type` that accepts the `type` const {tag!r} of variant")


def test_an_open_type_listed_before_a_tag_it_accepts_is_rejected():
    o = variant({"type": {"type": "string"}}, ["type"])
    a = variant({"type": {"const": "a"}}, ["type"])

    rejects(either(o=o, a=a), "either.json#/oneOf/0: variant O has an open `type` that accepts the `type` const 'a' of variant A")


def test_an_enum_type_without_a_sibling_tag_is_the_open_type():
    a = variant({"type": {"const": "a"}}, ["type"])

    assert dispatch(either(a=a, raw=variant({"type": {"enum": ["b", "c"]}}, ["type"]))) == (Variant("A", Tag("a")), Variant("Raw", Always()))


def test_a_variant_listed_twice_is_rejected():
    union = schema("either", {"oneOf": [{"$ref": "k.json"}, {"$ref": "k.json"}]})

    rejects({"either": union, "k": variant({"k": None}, ["k"])}, "either.json#/oneOf/1: variant K is listed twice")


def test_a_key_required_by_another_variant_is_not_a_selector():
    rejects(either(a=variant({"id": None}, ["id"]), b=variant({"id": None}, ["id"])), "either.json#/oneOf/0: variant A has no `type` const")


def test_a_key_that_is_only_a_property_of_another_variant_is_not_a_selector():
    a = variant({"x": None}, ["x"])
    b = variant({"x": None, "y": None}, ["y"])

    rejects(
        either(a=a, b=b),
        "either.json#/oneOf/0: variant A has no `type` const and no required key that is not a property of another variant: x (a property of B)",
    )


def test_a_variant_with_no_required_key_is_rejected():
    union = either(a=variant({"x": None}, []), b=variant({"y": None}, ["y"]))

    with pytest.raises(ValueError, match=re.escape("either.json#/oneOf/0: variant A has no `type` const and no required key") + "$"):
        parse(union, ())


def test_the_selector_is_the_first_required_key_by_name_that_no_other_variant_has():
    a = variant({"c": None, "f": None, "d": None}, ["f", "d", "c"])
    b = variant({"c": None, "y": None}, ["y"])

    assert dispatch(either(a=a, b=b)) == (Variant("A", Key("d")), Variant("B", Key("y")))


def test_a_union_lists_the_selectors_of_its_keyed_variants_in_schema_order():
    t = variant({"type": {"const": "t"}}, ["type"])
    k = variant({"k": None}, ["k"])
    j = variant({"j": None}, ["j"])

    assert parse(either(k=k, t=t, j=j), ()).unions[0].selectors == ("k", "j")


@pytest.mark.parametrize(
    "others, unclosed",
    [
        ({"k2": variant({"k2": None}, ["k2"], closed=False)}, "K2"),
        ({"t": variant({"type": {"const": "t"}}, ["type"], closed=False)}, "T"),
        ({"raw": variant({"type": None}, ["type"], closed=False)}, "Raw"),
    ],
    ids=["key", "tag", "open-type"],
)
def test_a_key_selector_needs_every_other_variant_closed(others, unclosed):
    k1 = variant({"k1": None, "z": None}, ["k1", "z"])

    rejects(either(k1=k1, **others), f"variant K1 is picked by its key k1, so every variant must set `additionalProperties: false`, and {unclosed} does not")


def test_a_key_selector_needs_its_own_variant_closed():
    t = variant({"type": {"const": "t"}}, ["type"])
    k = variant({"k": None}, ["k"], closed=False)

    rejects(either(t=t, k=k), "either.json#/oneOf/1: variant K is picked by its key k, so every variant must set `additionalProperties: false`, and K does not")


def test_two_object_types_with_one_name_are_rejected():
    body = thing(detail={"type": "object", "properties": {"x": {"type": "number"}}})
    detail = schema("thingDetail", {"type": "object", "properties": {"y": {"type": "number"}}})

    rejects({"thing": body, "thingDetail": detail}, "thingDetail.json#: two types are named ThingDetail; the other comes from thing.json#")


def test_two_enums_with_one_name_are_rejected():
    body = thing(level={"enum": ["a"]}, levels={"type": "array", "items": {"enum": ["b"]}})

    rejects({"thing": body}, "thing.json#: two types are named ThingLevel; the other comes from thing.json#")


def test_an_object_named_like_a_union_is_rejected():
    body = thing(either={"type": "object", "properties": {"x": {"type": "number"}}})
    union = schema("thingEither", {"oneOf": [{"$ref": "other.json"}]})
    other = schema("other", {"type": "object", "properties": {"type": {"const": "other"}}})

    rejects({"thing": body, "thingEither": union, "other": other}, "thing.json#: two types are named ThingEither; the other comes from thingEither.json#")


def test_an_enum_named_like_an_object_is_rejected():
    level = schema("thingLevel", {"type": "object", "properties": {"x": {"type": "number"}}})

    rejects({"thing": thing(level={"enum": ["a"]}), "thingLevel": level}, "thingLevel.json#: two types are named ThingLevel; the other comes from thing.json#")


def test_an_inline_union_variant_named_like_another_object_is_rejected():
    union = schema("either", {"oneOf": [{"type": "object", "properties": {"type": {"const": "thing"}}}]})
    clash = schema("eitherThing", {"type": "object", "properties": {"y": {"type": "number"}}})

    rejects({"either": union, "eitherThing": clash}, "either.json#/oneOf/0: two types are named EitherThing")


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
        ("additionalProperties", True, "object"),
        ("title", "a thing", "value"),
        ("description", "a thing", "value"),
        ("$comment", "a note", "object"),
        ("examples", ["a"], "value"),
        ("deprecated", True, "value"),
        ("default", "a", "value"),
        ("readOnly", True, "value"),
        ("writeOnly", True, "value"),
    ],
)
def test_ignored_keywords_and_annotations_are_accepted_and_change_nothing(keyword, value, at):
    plain = thing(name={"type": "string"})
    marked = thing(name={"type": "string"})
    (marked if at == "object" else marked["properties"]["name"])[keyword] = value

    assert parse({"thing": marked}, ()) == parse({"thing": plain}, ())


def test_additional_properties_false_and_an_excluded_const_are_kept_in_the_model_and_change_no_output():
    marked = thing(name={"type": "string", "not": {"const": "x"}}) | {"additionalProperties": False}
    plain = thing(name={"type": "string"})

    (obj,) = parse({"thing": marked}, ()).objects
    assert obj.closed and obj.fields[1].excluded == "x"
    assert generate({"thing": marked}, ()) == generate({"thing": plain}, ())


def test_the_model_lists_every_enum_sorted_by_name_including_array_items():
    other = schema("other", {"type": "object", "properties": {"mode": {"enum": ["on", "off"]}}})
    things = thing(level={"enum": ["low"]}, tags={"type": "array", "items": {"enum": ["a"]}}, name={"type": "string"})

    assert [e.name for e in parse({"thing": things, "other": other}, ()).enums] == ["OtherMode", "ThingLevel", "ThingTag"]


def test_an_enum_value_is_named_by_its_alphanumeric_parts_each_capitalised():
    (enum,) = parse({"thing": thing(level={"enum": ["low-power", "high_speed", "x2", "--odd", "Max"]})}, ()).enums

    assert enum.value_names == ("LowPower", "HighSpeed", "X2", "Odd", "Max")


def test_a_number_field_with_or_without_limits_is_a_number_and_an_integer_is_not():
    schemas = {
        "thing": thing(
            ratio={"type": "number"},
            share={"type": "number", "exclusiveMinimum": 0},
            count={"type": "integer"},
            size={"type": "integer", "minimum": 0},
        )
    }

    (obj,) = parse(schemas, ()).objects
    assert {f.name: is_number(f.type) for f in obj.fields} == {"id": False, "ratio": True, "share": True, "count": False, "size": False}


def test_an_object_splits_its_const_fields_from_its_typed_fields_in_schema_order():
    (obj,) = parse({"thing": thing(kind={"const": "thing"}, size={"type": "integer"}, mode={"const": "x"})}, ()).objects

    assert [f.name for f in obj.consts] == ["kind", "mode"]
    assert [f.name for f in obj.typed] == ["id", "size"]


def test_an_object_knows_every_union_that_lists_it_in_schema_order():
    a = variant({"type": {"const": "a"}}, ["type"])
    b = variant({"type": {"const": "b"}}, ["type"])
    schemas = {
        "first": schema("first", {"oneOf": [{"$ref": "a.json"}, {"$ref": "b.json"}]}),
        "second": schema("second", {"oneOf": [{"$ref": "a.json"}]}),
        "a": a,
        "b": b,
        "c": thing(),
    }

    model = parse(schemas, ())
    assert {o.name: model.unions_of(o) for o in model.objects} == {"A": ["First", "Second"], "B": ["First"], "C": []}
