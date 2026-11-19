from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn


@dataclass(frozen=True)
class Const:
    value: str


@dataclass(frozen=True)
class Enum:
    values: tuple[str, ...]
    name: str


@dataclass(frozen=True)
class Free:
    pass


@dataclass(frozen=True)
class Array:
    item: "Type"


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class Constrained:
    kind: str
    minimum: float | None = None
    exclusive_minimum: float | None = None
    exclusive_maximum: float | None = None
    min_length: int | None = None


Type = str | Constrained | Const | Enum | Free | Array | Ref


@dataclass(frozen=True)
class Field:
    name: str
    type: Type
    required: bool


@dataclass(frozen=True)
class Object:
    name: str
    fields: tuple[Field, ...]
    exactly_one: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tag:
    value: str


@dataclass(frozen=True)
class Key:
    name: str


@dataclass(frozen=True)
class Always:
    pass


Match = Tag | Key | Always


@dataclass(frozen=True)
class Variant:
    name: str
    match: Match


@dataclass(frozen=True)
class Union:
    name: str
    variants: tuple[Variant, ...]
    open: bool


@dataclass(frozen=True)
class Model:
    objects: tuple[Object, ...]
    unions: tuple[Union, ...]


def pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def singular(name: str) -> str:
    return name.removesuffix("s")


def ref_name(node: dict) -> str:
    return node["$ref"].removesuffix(".json")


NUMBER_LIMITS = ("minimum", "exclusiveMinimum", "exclusiveMaximum")
LIMITS = (*NUMBER_LIMITS, "minLength")
SCALARS = {"string": ("minLength",), "integer": NUMBER_LIMITS, "number": NUMBER_LIMITS, "boolean": ()}
ANNOTATIONS = ("$schema", "$id", "title")
IGNORED = {
    "additionalProperties": "decoders are tolerant readers: they accept and keep fields the schema does not name",
    "not": "a union matches variants by their type tag before the variant with an open type, so the dispatch does what not says",
}


def selector(body: dict) -> tuple[str, ...]:
    entries = body.get("oneOf", ())
    keys = [e["required"][0] for e in entries if set(e) == {"required"} and len(e["required"]) == 1]
    return tuple(keys) if entries and len(keys) == len(entries) else ()


def kind(body: dict) -> str:
    if "properties" in body:
        return "object"
    if "oneOf" in body:
        return "union"
    return "scalar"


def property_names(schemas: Mapping[str, dict], body: dict) -> set[str]:
    bases = (schemas.get(ref_name(part), {}) for part in body.get("allOf", ()))
    return set(body.get("properties", {})).union(*(property_names(schemas, base) for base in bases))


def check(schemas: Mapping[str, dict], name: str) -> None:
    def fail(path: list[str], message: str) -> NoReturn:
        raise ValueError(f"{name}.json#{''.join('/' + p for p in path)}: {message}")

    def allow(node: dict, path: list[str], keywords: set[str]) -> None:
        for key in node:
            if key not in keywords and key not in ANNOTATIONS and key not in IGNORED:
                fail(path, f"`{key}` is not supported here")

    def target(node: dict, path: list[str]) -> dict:
        allow(node, path, {"$ref"})
        if not node["$ref"].endswith(".json") or ref_name(node) not in schemas:
            fail(path, f"`$ref` {node['$ref']!r} does not name a schema file")
        return schemas[ref_name(node)]

    def object_(node: dict, path: list[str]) -> None:
        allow(node, path, {"type", "properties", "required", "allOf", "oneOf"})
        if node.get("type", "object") != "object":
            fail(path, "`type` beside `properties` must be 'object'")
        for i, part in enumerate(node.get("allOf", ())):
            if kind(target(part, path + ["allOf", str(i)])) != "object":
                fail(path + ["allOf", str(i)], "`allOf` must reference an object schema")
        for i, entry in enumerate(node.get("oneOf", ())):
            if set(entry) != {"required"} or len(entry["required"]) != 1:
                fail(path + ["oneOf", str(i)], "`oneOf` beside `properties` must list one `required` key per entry")
        required = set(node.get("required", ())) | {entry["required"][0] for entry in node.get("oneOf", ())}
        missing = sorted(required - property_names(schemas, node))
        if missing:
            fail(path, f"`required` names {', '.join(missing)}, which is not a property")
        for key, prop in node["properties"].items():
            value(prop, path + ["properties", key])

    def value(node: dict, path: list[str]) -> None:
        if "$ref" in node:
            target(node, path)
        elif "const" in node:
            allow(node, path, {"const"})
            if not isinstance(node["const"], str):
                fail(path, "`const` must be a string")
        elif "enum" in node:
            allow(node, path, {"enum"})
            if not all(isinstance(v, str) for v in node["enum"]):
                fail(path, "`enum` must list strings")
        elif node.get("type") == "array":
            allow(node, path, {"type", "items"})
            if "items" not in node:
                fail(path, "an array needs `items`")
            value(node["items"], path + ["items"])
        elif node.get("type") == "object" and "properties" in node:
            object_(node, path)
        elif node.get("type") == "object":
            allow(node, path, {"type"})
        elif isinstance(node.get("type"), str) and node["type"] in SCALARS:
            allow(node, path, {"type", *SCALARS[node["type"]]})
        else:
            if "type" not in node:
                allow(node, path, set())
            fail(path, f"`type` must be one of object, array, {', '.join(SCALARS)}, not {node.get('type')!r}")

    def union(node: dict, path: list[str]) -> None:
        allow(node, path, {"oneOf"})
        for i, item in enumerate(node["oneOf"]):
            at = path + ["oneOf", str(i)]
            if "$ref" in item:
                if kind(target(item, at)) != "object":
                    fail(at, "a union variant must reference an object schema")
            elif "properties" in item:
                object_(item, at)
                if not item["properties"].get("type", {}).get("const") and not item.get("required"):
                    fail(at, "an inline union variant needs a `type` const or a `required` key to name it")
            else:
                fail(at, "a union variant must be a `$ref` or an object with `properties`")

    body = schemas[name]
    {"object": object_, "union": union, "scalar": value}[kind(body)](body, [])


def parse(schemas: Mapping[str, dict], roots: Sequence[str]) -> Model:
    for name in schemas:
        check(schemas, name)
    objects: dict[str, Object] = {}

    def flatten(body: dict) -> tuple[dict, set, tuple[str, ...]]:
        properties: dict = {}
        required: set = set()
        exactly_one = selector(body)
        for part in body.get("allOf", ()):
            base_properties, base_required, base_selector = flatten(schemas[ref_name(part)])
            properties |= base_properties
            required |= base_required
            exactly_one = exactly_one or base_selector
        return properties | body.get("properties", {}), required | set(body.get("required", ())), exactly_one

    def add_object(name: str, body: dict) -> str:
        properties, required, exactly_one = flatten(body)
        fields = tuple(Field(key, type_of(prop, name + pascal(key)), key in required) for key, prop in properties.items())
        if name in objects:
            raise ValueError(f"two object types are named {name}")
        objects[name] = Object(name, fields, exactly_one)
        return name

    def type_of(prop: dict, hint: str) -> Type:
        if "$ref" in prop:
            target = schemas[ref_name(prop)]
            return type_of(target, hint) if kind(target) == "scalar" else Ref(pascal(ref_name(prop)))
        if "const" in prop:
            return Const(prop["const"])
        if "enum" in prop:
            return Enum(tuple(prop["enum"]), hint)
        if prop["type"] == "array":
            return Array(type_of(prop["items"], singular(hint)))
        if prop["type"] == "object":
            return Ref(add_object(hint, prop)) if "properties" in prop else Free()
        if any(key in prop for key in LIMITS):
            return Constrained(
                prop["type"], prop.get("minimum"), prop.get("exclusiveMinimum"), prop.get("exclusiveMaximum"), prop.get("minLength")
            )
        return prop["type"]

    def variant_names(name: str, body: dict) -> list[str]:
        return [
            pascal(ref_name(item)) if "$ref" in item else add_object(pascal(name) + variant_suffix(item), item)
            for item in body["oneOf"]
        ]

    for name, body in schemas.items():
        if kind(body) == "object":
            add_object(pascal(name), body)

    unions = tuple(
        Union(pascal(name), variants_of(name, [objects[n] for n in variant_names(name, body)]), name in roots)
        for name, body in schemas.items()
        if kind(body) == "union"
    )
    missing = [root for root in roots if pascal(root) not in {u.name for u in unions}]
    if missing:
        raise ValueError(f"requested roots that are not unions: {', '.join(missing)}")
    return Model(tuple(objects.values()), unions)


def variant_suffix(item: dict) -> str:
    tag = item.get("properties", {}).get("type", {}).get("const")
    return pascal(tag if tag else item["required"][0])


def tag_of(obj: Object) -> str | None:
    for f in obj.fields:
        if f.name == "type" and isinstance(f.type, Const):
            return f.type.value
    return None


def variants_of(name: str, objects: list[Object]) -> tuple[Variant, ...]:
    required = {o.name: {f.name for f in o.fields if f.required} for o in objects}
    variants = []
    for obj in objects:
        tag = tag_of(obj)
        if tag is not None:
            match: Match = Tag(tag)
        elif any(f.name == "type" for f in obj.fields):
            match = Always()
        else:
            others = set().union(*(required[o.name] for o in objects if o is not obj))
            own = sorted(required[obj.name] - others)
            if not own:
                raise ValueError(f"{name}.json#/oneOf: variant {obj.name} has no `type` const and no required key the other variants lack")
            match = Key(own[0])
        variants.append(Variant(obj.name, match))
    return tuple(sorted(variants, key=lambda v: isinstance(v.match, Always)))
