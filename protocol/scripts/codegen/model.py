from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Const:
    value: str


@dataclass(frozen=True)
class Enum:
    values: tuple[str, ...]


@dataclass(frozen=True)
class Free:
    pass


@dataclass(frozen=True)
class Array:
    item: "Type"


@dataclass(frozen=True)
class Ref:
    name: str


Type = str | Const | Enum | Free | Array | Ref


@dataclass(frozen=True)
class Field:
    name: str
    type: Type
    required: bool


@dataclass(frozen=True)
class Object:
    name: str
    fields: tuple[Field, ...]


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


def kind(body: dict) -> str:
    if "properties" in body:
        return "object"
    if "oneOf" in body:
        return "union"
    return "scalar"


def parse(schemas: Mapping[str, dict], roots: Sequence[str]) -> Model:
    objects: dict[str, Object] = {}

    def flatten(body: dict) -> tuple[dict, set]:
        properties: dict = {}
        required: set = set()
        for part in body.get("allOf", ()):
            base_properties, base_required = flatten(schemas[ref_name(part)])
            properties |= base_properties
            required |= base_required
        return properties | body.get("properties", {}), required | set(body.get("required", ()))

    def add_object(name: str, body: dict) -> str:
        properties, required = flatten(body)
        fields = tuple(Field(key, type_of(prop, name + pascal(key)), key in required) for key, prop in properties.items())
        objects[name] = Object(name, fields)
        return name

    def type_of(prop: dict, hint: str) -> Type:
        if "$ref" in prop:
            target = schemas[ref_name(prop)]
            return type_of(target, hint) if kind(target) == "scalar" else Ref(pascal(ref_name(prop)))
        if "const" in prop:
            return Const(prop["const"])
        if "enum" in prop:
            return Enum(tuple(prop["enum"]))
        if prop["type"] == "array":
            return Array(type_of(prop["items"], singular(hint)))
        if prop["type"] == "object":
            return Ref(add_object(hint, prop)) if "properties" in prop else Free()
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
        Union(pascal(name), variants_of([objects[n] for n in variant_names(name, body)]), name in roots)
        for name, body in schemas.items()
        if kind(body) == "union"
    )
    return Model(tuple(objects.values()), unions)


def variant_suffix(item: dict) -> str:
    tag = item.get("properties", {}).get("type", {}).get("const")
    return pascal(tag if tag else item["required"][0])


def tag_of(obj: Object) -> str | None:
    for f in obj.fields:
        if f.name == "type" and isinstance(f.type, Const):
            return f.type.value
    return None


def variants_of(objects: list[Object]) -> tuple[Variant, ...]:
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
            match = Key(sorted(required[obj.name] - others)[0])
        variants.append(Variant(obj.name, match))
    return tuple(sorted(variants, key=lambda v: isinstance(v.match, Always)))
