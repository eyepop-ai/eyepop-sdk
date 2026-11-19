from .model import Always, Array, Const, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant

HEADER = '''# Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, cast

_Variants = Sequence[tuple[Callable[[dict[str, Any]], bool], Callable[[Any], Any]]]


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"expected an object, got {type(value).__name__}")
    return cast(dict[str, Any], value)


def _required(obj: dict[str, Any], key: str, parse: Callable[[Any], Any]) -> Any:
    if key not in obj:
        raise ValueError(f"missing {key}")
    return parse(obj[key])


def _optional(obj: dict[str, Any], key: str, parse: Callable[[Any], Any]) -> Any:
    return parse(obj[key]) if key in obj else None


def _string(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"expected a string, got {type(value).__name__}")
    return value


def _integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"expected an integer, got {type(value).__name__}")
    return value


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected a number, got {type(value).__name__}")
    return value


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"expected a boolean, got {type(value).__name__}")
    return value


def _free(value: Any) -> dict[str, Any]:
    return _object(value)


def _const(expected: str) -> Callable[[Any], str]:
    def parse(value: Any) -> str:
        if value != expected:
            raise ValueError(f"expected {expected!r}, got {value!r}")
        return expected

    return parse


def _enum(allowed: Sequence[str]) -> Callable[[Any], str]:
    def parse(value: Any) -> str:
        if value not in allowed:
            raise ValueError(f"expected one of {list(allowed)}, got {value!r}")
        return value

    return parse


def _array(item: Callable[[Any], Any]) -> Callable[[Any], list[Any]]:
    def parse(value: Any) -> list[Any]:
        if not isinstance(value, list):
            raise ValueError(f"expected an array, got {type(value).__name__}")
        return [item(element) for element in cast(list[Any], value)]

    return parse


def _tag(expected: str) -> Callable[[dict[str, Any]], bool]:
    return lambda obj: obj.get("type") == expected


def _key(name: str) -> Callable[[dict[str, Any]], bool]:
    return lambda obj: name in obj


def _always(obj: dict[str, Any]) -> bool:
    return True


def _dispatch(value: Any, variants: _Variants) -> Any:
    obj = _object(value)
    for matches, parse in variants:
        if matches(obj):
            return parse(obj)
    raise ValueError("no variant matches")


def _dump(value: Any) -> Any:
    if hasattr(value, "to_json"):
        return value.to_json()
    if isinstance(value, list):
        return [_dump(element) for element in cast(list[Any], value)]
    return value

'''

PY_TYPES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}


def emit(model: Model) -> str:
    unions = frozenset(u.name for u in model.unions)
    parts = [emit_object(obj, unions) for obj in model.objects] + [emit_union(u) for u in model.unions]
    return HEADER + "\n" + "\n\n".join(parts) + "\n"


def annotation(type_: Type) -> str:
    match type_:
        case Const(value):
            return f"Literal[{value!r}]"
        case Enum(values, _):
            return f"Literal[{', '.join(repr(v) for v in values)}]"
        case Free():
            return "Mapping[str, Any]"
        case Array(item):
            return f"list[{annotation(item)}]"
        case Ref(name):
            return name
        case _:
            return PY_TYPES[type_]


def parser(type_: Type, unions: frozenset[str]) -> str:
    match type_:
        case Const(value):
            return f"_const({value!r})"
        case Enum(values, _):
            return f"_enum({values!r})"
        case Free():
            return "_free"
        case Array(item):
            return f"_array({parser(item, unions)})"
        case Ref(name):
            return f"decode_{name.lower()}" if name in unions else f"{name}.from_json"
        case _:
            return f"_{type_}"


def declaration(f: Field) -> str:
    return f"    {f.name}: {annotation(f.type)}" if f.required else f"    {f.name}: {annotation(f.type)} | None = None"


def write(f: Field) -> str:
    if f.required:
        return f"        out[{f.name!r}] = _dump(self.{f.name})"
    return f"        if self.{f.name} is not None:\n            out[{f.name!r}] = _dump(self.{f.name})"


def emit_object(obj: Object, unions: frozenset[str] = frozenset()) -> str:
    consts = [f for f in obj.fields if isinstance(f.type, Const)]
    typed = sorted((f for f in obj.fields if not isinstance(f.type, Const)), key=lambda f: not f.required)
    fields = "\n".join(declaration(f) for f in typed)
    checks = "".join(f"        _required(obj, {f.name!r}, {parser(f.type, unions)})\n" for f in consts)
    reads = ", ".join(
        [
            f"{f.name}={'_required' if f.required else '_optional'}(obj, {f.name!r}, {parser(f.type, unions)})"
            for f in typed
        ]
        + ["raw=obj"]
    )
    writes = "\n".join([write(f) for f in typed] + [f"        out[{f.name!r}] = {f.type.value!r}" for f in consts])
    return f"""
@dataclass(frozen=True)
class {obj.name}:
{fields}
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> {obj.name}:
        obj = _object(value)
{checks}        return {obj.name}({reads})

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
{writes}
        return out
"""


def predicate(variant: Variant) -> str:
    match variant.match:
        case Tag(value):
            return f"_tag({value!r})"
        case Key(name):
            return f"_key({name!r})"
        case Always():
            return "_always"


def emit_union(union: Union) -> str:
    table = f"_{union.name.upper()}_VARIANTS"
    cases = "\n".join(f"    ({predicate(v)}, {v.name}.from_json)," for v in union.variants)
    members = [v.name for v in union.variants]
    if not union.open:
        return f"""
{table}: _Variants = [
{cases}
]

{union.name} = {" | ".join(members)}


def decode_{union.name.lower()}(value: Any) -> {union.name}:
    return _dispatch(value, {table})
"""
    unknown = f"Unknown{union.name}"
    return f"""
@dataclass(frozen=True)
class {unknown}:
    raw: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)


{table}: _Variants = [
{cases}
]

{union.name} = {" | ".join(members + [unknown])}


def decode_{union.name.lower()}(value: Any) -> {union.name}:
    try:
        return _dispatch(value, {table})
    except ValueError:
        return {unknown}(cast(dict[str, Any], value) if isinstance(value, dict) else {{}})
"""
