import re
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn


@dataclass(frozen=True)
class Const:
    value: str


@dataclass(frozen=True)
class Enum:
    values: tuple[str, ...]
    name: str

    @property
    def value_names(self) -> tuple[str, ...]:
        return tuple(value_name(v) for v in self.values)


def value_name(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^0-9A-Za-z]+", value) if part)


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


def is_number(type_: Type) -> bool:
    return type_ == "number" or (isinstance(type_, Constrained) and type_.kind == "number")


@dataclass(frozen=True)
class Field:
    name: str
    type: Type
    required: bool
    excluded: str | None = None


@dataclass(frozen=True)
class Object:
    name: str
    fields: tuple[Field, ...]
    exactly_one: tuple[str, ...] = ()
    closed: bool = False

    @property
    def consts(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if isinstance(f.type, Const))

    @property
    def typed(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if not isinstance(f.type, Const))


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
    selectors: tuple[str, ...]


@dataclass(frozen=True)
class Wire:
    integer_minimum: int
    integer_maximum: int
    length_unit: str
    max_depth: int

    @property
    def integer_digits(self) -> int:
        return max(len(str(abs(self.integer_minimum))), len(str(abs(self.integer_maximum))))


WIRE = Wire(integer_minimum=-(2**63), integer_maximum=2**63 - 1, length_unit="code point", max_depth=64)

WIRE_RULES = {
    "integer": (
        f"An integer is a JSON number whose exact decimal value is whole and lies from {WIRE.integer_minimum} to {WIRE.integer_maximum}"
        " (int64), however the token is written (1.0, 1e3 and 10e-1 are integers; 1.5, 1.00000000000000001 and 1e-1000000 are not)."
        " A decoder that reads the token as text normalises it to a sign, significant digits without leading or trailing zeros"
        " and a base-ten exponent; it rejects a negative exponent, more digits plus exponent than the bounds have digits,"
        " or a value outside the bounds. A decoder that reads a binary double checks that double's exact value the same way."
    ),
    "number": "A number is a JSON number whose value as a double is finite; one that overflows a double (1e400) is rejected.",
    "length": f"`minLength` counts Unicode {WIRE.length_unit}s: a character outside the Basic Multilingual Plane counts once.",
    "exactly one": "Exactly one of the listed keys is present in the object; a key whose value is null counts as present.",
    "depth": (
        f"A value nests at most {WIRE.max_depth} levels: an object or array is one level deeper than the value holding it,"
        " and the message object is level 1. A union decoder handed a deeper value returns Unknown with no fields and does"
        " not read below that level."
    ),
    "duplicate keys": "When an object repeats a key, the last value wins.",
    "unicode": "A string or key is valid Unicode: one holding a lone surrogate makes a union decoder return Unknown keeping every field.",
}


@dataclass(frozen=True)
class Model:
    objects: tuple[Object, ...]
    unions: tuple[Union, ...]
    wire: Wire = WIRE

    @property
    def enums(self) -> tuple[Enum, ...]:
        found: list[Enum] = []

        def walk(type_: Type) -> None:
            if isinstance(type_, Enum):
                found.append(type_)
            elif isinstance(type_, Array):
                walk(type_.item)

        for obj in self.objects:
            for f in obj.fields:
                walk(f.type)
        return tuple(sorted(found, key=lambda e: e.name))

    def unions_of(self, obj: Object) -> list[str]:
        return [u.name for u in self.unions if any(v.name == obj.name for v in u.variants)]


IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


@dataclass(frozen=True)
class Naming:
    field: Callable[[str, str], str]
    reserved: Callable[[Field, Sequence[Field]], Collection[str]]
    value: Callable[[str], str] | None = None
    values: frozenset[str] = frozenset()


def check_fields(owner: str, where: str, fields: Sequence[Field], places: Mapping[str, str], namings: Mapping[str, Naming]) -> None:
    for f in fields:
        if not IDENTIFIER.fullmatch(f.name):
            raise ValueError(f"{places[f.name]}: property {f.name!r} of {owner} is not an identifier ([A-Za-z][A-Za-z0-9_]*)")
    for language, naming in namings.items():
        taken: dict[str, str] = {}
        for f in fields:
            name = naming.field(owner, f.name)
            if name in naming.reserved(f, fields):
                raise ValueError(f"{places[f.name]}: property {f.name!r} of {owner} becomes the {language} name {name}, which the generated code already uses")
            if name in taken:
                raise ValueError(f"{where}: properties {taken[name]!r} and {f.name!r} of {owner} both become the {language} name {name}")
            taken[name] = f.name


def check_values(enum: Enum, where: str, namings: Mapping[str, Naming]) -> None:
    for v in enum.values:
        if not IDENTIFIER.fullmatch(value_name(v)):
            raise ValueError(f"{where}: enum value {v!r} of {enum.name} does not start with a letter, so it has no identifier")
    for language, naming in namings.items():
        if naming.value is None:
            continue
        taken: dict[str, str] = {}
        for v in enum.values:
            name = naming.value(v)
            if name in naming.values:
                raise ValueError(f"{where}: enum value {v!r} of {enum.name} becomes the {language} name {name}, which the generated code already uses")
            if name in taken:
                raise ValueError(f"{where}: enum values {taken[name]!r} and {v!r} of {enum.name} both become the {language} name {name}")
            taken[name] = v


def pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def singular(name: str) -> str:
    return name.removesuffix("s")


def ref_name(node: dict) -> str:
    return node["$ref"].removesuffix(".json")


NUMBER_LIMITS = ("minimum", "exclusiveMinimum", "exclusiveMaximum")
LIMITS = (*NUMBER_LIMITS, "minLength")
SCALARS = {"string": ("minLength",), "integer": NUMBER_LIMITS, "number": NUMBER_LIMITS, "boolean": ()}
ANNOTATIONS = ("$schema", "$id", "title", "description", "$comment", "examples", "deprecated", "default", "readOnly", "writeOnly")
IGNORED = {
    "additionalProperties": (
        "true or false",
        "decoders are tolerant readers: they accept and keep fields the schema does not name; `false` is read only to check union dispatch",
    ),
    "not": (
        '{"const": <string>} on a string',
        "a union tries its open-`type` variant last, and the model checks that it excludes every tagged sibling; a decoder does not check it",
    ),
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


def refs(schemas: Mapping[str, dict], node: object) -> list[str]:
    if isinstance(node, list):
        return [name for item in node for name in refs(schemas, item)]
    if not isinstance(node, dict):
        return []
    own = node.get("$ref")
    found = [own.removesuffix(".json")] if isinstance(own, str) and isinstance(schemas.get(own.removesuffix(".json")), dict) else []
    return found + [name for key, item in node.items() if key != "$ref" for name in refs(schemas, item)]


def bases(schemas: Mapping[str, dict], body: dict) -> list[str]:
    return refs(schemas, [part for part in body.get("allOf", ()) if isinstance(part, dict) and set(part) == {"$ref"}])


def property_names(schemas: Mapping[str, dict], body: dict) -> set[str]:
    return set(body.get("properties", {})).union(*(property_names(schemas, schemas[base]) for base in bases(schemas, body)))


def check(schemas: Mapping[str, dict], name: str) -> None:
    def fail(path: list[str], message: str) -> NoReturn:
        raise ValueError(f"{name}.json#{''.join('/' + p for p in path)}: {message}")

    def ignored(node: dict, key: str) -> bool:
        if key == "additionalProperties":
            return isinstance(node[key], bool)
        if key == "not":
            excluded = node[key]
            return node.get("type") == "string" and isinstance(excluded, dict) and set(excluded) == {"const"} and isinstance(excluded["const"], str)
        return False

    def allow(node: dict, path: list[str], keywords: set[str]) -> None:
        for key in node:
            if key in keywords or key in ANNOTATIONS or (key in IGNORED and ignored(node, key)):
                continue
            if key in IGNORED:
                fail(path, f"`{key}` is only accepted as {IGNORED[key][0]}")
            fail(path, f"`{key}` is not supported here")

    def a_schema(node: object, path: list[str]) -> None:
        if not isinstance(node, dict):
            fail(path, f"a schema here must be an object, not {node!r}")

    def acyclic(start: str, path: list[str], keyword: str, via: Callable[[str], list[str]], seen: tuple[str, ...] = ()) -> None:
        if start in seen:
            fail(path, f"`{keyword}` cycle: {' -> '.join(seen + (start,))}")
        for following in via(start):
            acyclic(following, path, keyword, via, seen + (start,))

    def target(node: object, path: list[str]) -> dict:
        a_schema(node, path)
        allow(node, path, {"$ref"})
        ref = node.get("$ref")
        if not isinstance(ref, str) or not ref.endswith(".json") or not isinstance(schemas.get(ref_name(node)), dict):
            fail(path, f"`$ref` {ref!r} does not name a schema file")
        return schemas[ref_name(node)]

    def object_(node: object, path: list[str]) -> None:
        a_schema(node, path)
        allow(node, path, {"type", "properties", "required", "allOf", "oneOf"})
        if node.get("type", "object") != "object":
            fail(path, "`type` beside `properties` must be 'object'")
        if not isinstance(node["properties"], dict):
            fail(path + ["properties"], "`properties` must be an object")
        for i, part in enumerate(node.get("allOf", ())):
            if kind(target(part, path + ["allOf", str(i)])) != "object":
                fail(path + ["allOf", str(i)], "`allOf` must reference an object schema")
        for base in bases(schemas, node):
            acyclic(base, path + ["allOf"], "allOf", lambda n: bases(schemas, schemas[n]))
        for i, entry in enumerate(node.get("oneOf", ())):
            if not isinstance(entry, dict) or set(entry) != {"required"} or len(entry["required"]) != 1:
                fail(path + ["oneOf", str(i)], "`oneOf` beside `properties` must list one `required` key per entry")
        required = set(node.get("required", ())) | {entry["required"][0] for entry in node.get("oneOf", ())}
        missing = sorted(required - property_names(schemas, node))
        if missing:
            fail(path, f"`required` names {', '.join(missing)}, which is not a property")
        for key, prop in node["properties"].items():
            value(prop, path + ["properties", key])

    def value(node: object, path: list[str]) -> None:
        a_schema(node, path)
        if "$ref" in node:
            if kind(target(node, path)) == "scalar":
                acyclic(ref_name(node), path, "$ref", lambda n: [r for r in refs(schemas, schemas[n]) if kind(schemas[r]) == "scalar"])
        elif "const" in node:
            allow(node, path, {"const", "type"})
            if not isinstance(node["const"], str) or node.get("type", "string") != "string":
                fail(path, "`const` must be a string")
        elif "enum" in node:
            allow(node, path, {"enum", "type"})
            if not node["enum"] or not all(isinstance(v, str) for v in node["enum"]) or node.get("type", "string") != "string":
                fail(path, "`enum` must list one or more strings")
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
        elif "properties" in node and "type" not in node:
            fail(path, "an object with `properties` needs `\"type\": \"object\"`")
        else:
            if "type" not in node:
                allow(node, path, set())
            fail(path, f"`type` must be one of object, array, {', '.join(SCALARS)}, not {node.get('type')!r}")

    def union(node: dict, path: list[str]) -> None:
        allow(node, path, {"oneOf"})
        for i, item in enumerate(node["oneOf"]):
            at = path + ["oneOf", str(i)]
            a_schema(item, at)
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
    a_schema(body, [])
    {"object": object_, "union": union, "scalar": value}[kind(body)](body, [])


def parse(schemas: Mapping[str, dict], roots: Sequence[str], namings: Mapping[str, Naming] = {}) -> Model:
    for name in schemas:
        check(schemas, name)
    objects: dict[str, Object] = {}
    sources: dict[str, str] = {}
    origin = ""

    def claim(name: str) -> str:
        if name in sources:
            raise ValueError(f"{origin}: two types are named {name}; the other comes from {sources[name]}")
        sources[name] = origin
        return name

    def flatten(body: dict, where: str) -> tuple[dict, set, tuple[str, ...], dict]:
        properties: dict = {}
        required: set = set()
        places: dict = {}
        exactly_one = selector(body)
        for part in body.get("allOf", ()):
            base_properties, base_required, base_selector, base_places = flatten(schemas[ref_name(part)], f"{ref_name(part)}.json#")
            properties |= base_properties
            required |= base_required
            places |= base_places
            exactly_one = exactly_one or base_selector
        own = body.get("properties", {})
        places |= {key: f"{where}/properties/{key}" for key in own}
        return properties | own, required | set(body.get("required", ())), exactly_one, places

    def add_object(name: str, body: dict, where: str) -> str:
        properties, required, exactly_one, places = flatten(body, where)
        fields = tuple(
            Field(key, type_of(prop, name + pascal(key), places[key]), key in required, prop.get("not", {}).get("const"))
            for key, prop in properties.items()
        )
        check_fields(name, where, [f for f in fields if not isinstance(f.type, Const)], places, namings)
        objects[claim(name)] = Object(name, fields, exactly_one, body.get("additionalProperties") is False)
        return name

    def type_of(prop: dict, hint: str, where: str) -> Type:
        if "$ref" in prop:
            target = schemas[ref_name(prop)]
            return type_of(target, hint, f"{ref_name(prop)}.json#") if kind(target) == "scalar" else Ref(pascal(ref_name(prop)))
        if "const" in prop:
            return Const(prop["const"])
        if "enum" in prop:
            enum = Enum(tuple(prop["enum"]), claim(hint))
            check_values(enum, where, namings)
            return enum
        if prop["type"] == "array":
            return Array(type_of(prop["items"], singular(hint), f"{where}/items"))
        if prop["type"] == "object":
            return Ref(add_object(hint, prop, where)) if "properties" in prop else Free()
        if any(key in prop for key in LIMITS):
            return Constrained(
                prop["type"], prop.get("minimum"), prop.get("exclusiveMinimum"), prop.get("exclusiveMaximum"), prop.get("minLength")
            )
        return prop["type"]

    def variant_names(name: str, body: dict) -> list[str]:
        nonlocal origin
        names = []
        for i, item in enumerate(body["oneOf"]):
            origin = f"{name}.json#/oneOf/{i}"
            names.append(pascal(ref_name(item)) if "$ref" in item else add_object(pascal(name) + variant_suffix(item), item, origin))
        return names

    for name, body in schemas.items():
        origin = f"{name}.json#"
        if kind(body) == "union":
            claim(pascal(name))

    for name, body in schemas.items():
        if kind(body) == "object":
            origin = f"{name}.json#"
            add_object(pascal(name), body, origin)

    def union_of(name: str, body: dict) -> Union:
        variants = variants_of(name, [objects[n] for n in variant_names(name, body)])
        return Union(pascal(name), variants, name in roots, tuple(v.match.name for v in variants if isinstance(v.match, Key)))

    unions = tuple(union_of(name, body) for name, body in schemas.items() if kind(body) == "union")
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


def type_field(obj: Object) -> Field | None:
    return next((f for f in obj.fields if f.name == "type"), None)


def open_type(obj: Object) -> bool:
    return tag_of(obj) is None and type_field(obj) is not None


def accepts(field: Field, tag: str) -> bool:
    if isinstance(field.type, Enum):
        return tag in field.type.values
    return tag != field.excluded


def variants_of(name: str, objects: list[Object]) -> tuple[Variant, ...]:
    names = [o.name for o in objects]
    for i, obj in enumerate(objects):
        if obj.name in names[:i]:
            raise ValueError(f"{name}.json#/oneOf/{i}: variant {obj.name} is listed twice")
    variants = []
    for i, obj in enumerate(objects):
        def fail(message: str) -> NoReturn:
            raise ValueError(f"{name}.json#/oneOf/{i}: {message}")

        others = objects[:i] + objects[i + 1 :]
        tag = tag_of(obj)
        if tag is not None:
            twin = next((o for o in objects[:i] if tag_of(o) == tag), None)
            if twin:
                fail(f"variants {twin.name} and {obj.name} both have the `type` const {tag!r}")
            if not type_field(obj).required:
                fail(f"variant {obj.name} has the `type` const {tag!r} but does not require `type`")
            match: Match = Tag(tag)
        elif open_type(obj):
            twin = next((o for o in objects[:i] if open_type(o)), None)
            if twin:
                fail(f"variants {twin.name} and {obj.name} both have an open `type`")
            taken = next((o for o in others if tag_of(o) is not None and accepts(type_field(obj), tag_of(o))), None)
            if taken:
                fail(f"variant {obj.name} has an open `type` that accepts the `type` const {tag_of(taken)!r} of variant {taken.name}")
            match = Always()
        else:
            holders = {f.name: o.name for o in reversed(others) for f in o.fields}
            required = sorted(f.name for f in obj.fields if f.required)
            own = [key for key in required if key not in holders]
            if not required:
                fail(f"variant {obj.name} has no `type` const and no required key")
            if not own:
                taken = ", ".join(f"{key} (a property of {holders[key]})" for key in required)
                fail(f"variant {obj.name} has no `type` const and no required key that is not a property of another variant: {taken}")
            unclosed = next((o for o in objects if not o.closed), None)
            if unclosed:
                fail(f"variant {obj.name} is picked by its key {own[0]}, so every variant must set `additionalProperties: false`, and {unclosed.name} does not")
            match = Key(own[0])
        variants.append(Variant(obj.name, match))
    return tuple(sorted(variants, key=lambda v: isinstance(v.match, Always)))
