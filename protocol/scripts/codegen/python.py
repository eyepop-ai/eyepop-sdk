from .model import Always, Array, Const, Constrained, Enum, Field, Free, Key, Model, Object, Ref, Tag, Type, Union, Variant, Wire

HEADER = '''# Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.
from __future__ import annotations

import copy
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from decimal import Decimal
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
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        raise ValueError(f"expected an integer, got {type(value).__name__}")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError(f"{value} is not finite")
    if not _INTEGER_MINIMUM <= value <= _INTEGER_MAXIMUM or int(value) != value:
        raise ValueError(f"{value} is not an integer from {_INTEGER_MINIMUM} to {_INTEGER_MAXIMUM}")
    return int(value)


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        raise ValueError(f"expected a number, got {type(value).__name__}")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ValueError(f"{value} is not a finite double")
    return value if isinstance(value, int) else number


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"expected a boolean, got {type(value).__name__}")
    return value


def _free(value: Any) -> dict[str, Any]:
    return copy.deepcopy(_object(value))


def _limit(
    parse: Callable[[Any], Any],
    minimum: float | None = None,
    exclusive_minimum: float | None = None,
    exclusive_maximum: float | None = None,
    min_length: int | None = None,
) -> Callable[[Any], Any]:
    def checked(value: Any) -> Any:
        parsed = parse(value)
        if minimum is not None and parsed < minimum:
            raise ValueError(f"{parsed} is below {minimum}")
        if exclusive_minimum is not None and parsed <= exclusive_minimum:
            raise ValueError(f"{parsed} is not above {exclusive_minimum}")
        if exclusive_maximum is not None and parsed >= exclusive_maximum:
            raise ValueError(f"{parsed} is not below {exclusive_maximum}")
        if min_length is not None and _LENGTH(parsed) < min_length:
            raise ValueError(f"shorter than {min_length}")
        return parsed

    return checked


def _exactly_one(obj: dict[str, Any], keys: Sequence[str]) -> None:
    present = [key for key in keys if key in obj]
    if len(present) != 1:
        raise ValueError(f"expected exactly one of {list(keys)}, got {present}")


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


def _within(value: Any, levels: int) -> bool:
    children: Iterable[Any]
    if isinstance(value, dict):
        children = cast(dict[str, Any], value).values()
    elif isinstance(value, list):
        children = cast(list[Any], value)
    else:
        return True
    return levels > 0 and all(_within(child, levels - 1) for child in children)


def _unicode(value: Any) -> bool:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True
    if isinstance(value, dict):
        return all(_unicode(key) and _unicode(item) for key, item in cast(dict[str, Any], value).items())
    if isinstance(value, list):
        return all(_unicode(item) for item in cast(list[Any], value))
    return True


def _put_number(out: dict[str, Any], key: str, number: float) -> None:
    current = out.get(key)
    if isinstance(current, int | float | Decimal) and not isinstance(current, bool):
        try:
            if float(current) == number:
                return
        except (OverflowError, ValueError):
            pass
    out[key] = number


def _dispatch(value: Any, variants: _Variants) -> Any:
    obj = _object(value)
    for matches, parse in variants:
        if matches(obj):
            return parse(obj)
    raise ValueError("no variant matches")


def _dump(value: Any) -> Any:
    if hasattr(value, "to_json"):
        return value.to_json()
    if isinstance(value, dict):
        return copy.deepcopy(cast(dict[str, Any], value))
    if isinstance(value, list):
        return [_dump(element) for element in cast(list[Any], value)]
    return value

'''

PY_TYPES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
LENGTHS = {"code point": "len"}


def emit(model: Model) -> str:
    unions = frozenset(u.name for u in model.unions)
    parts = [emit_object(obj, unions) for obj in model.objects] + [emit_union(u) for u in model.unions]
    return HEADER + "\n" + constants(model.wire) + "\n" + "\n\n".join(parts) + "\n"


def constants(wire: Wire) -> str:
    return (
        f"_INTEGER_MINIMUM = {wire.integer_minimum}\n_INTEGER_MAXIMUM = {wire.integer_maximum}\n"
        f"_MAX_DEPTH = {wire.max_depth}\n_LENGTH = {LENGTHS[wire.length_unit]}\n"
    )


def annotation(type_: Type) -> str:
    match type_:
        case Constrained(kind):
            return PY_TYPES[kind]
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
        case Constrained(kind, minimum, exclusive_minimum, exclusive_maximum, min_length):
            limits = {
                "minimum": minimum,
                "exclusive_minimum": exclusive_minimum,
                "exclusive_maximum": exclusive_maximum,
                "min_length": min_length,
            }
            args = "".join(f", {name}={value!r}" for name, value in limits.items() if value is not None)
            return f"_limit(_{kind}{args})"
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
    number = f.type == "number" or (isinstance(f.type, Constrained) and f.type.kind == "number")
    put = f"_put_number(out, {f.name!r}, self.{f.name})" if number else f"out[{f.name!r}] = _dump(self.{f.name})"
    if f.required:
        return f"        {put}"
    return (
        f"        if self.{f.name} is not None:\n            {put}\n"
        f"        else:\n            out.pop({f.name!r}, None)"
    )


def emit_object(obj: Object, unions: frozenset[str] = frozenset()) -> str:
    consts = [f for f in obj.fields if isinstance(f.type, Const)]
    typed = sorted((f for f in obj.fields if not isinstance(f.type, Const)), key=lambda f: not f.required)
    fields = "\n".join(declaration(f) for f in typed)
    checks = "".join(f"        _required(obj, {f.name!r}, {parser(f.type, unions)})\n" for f in consts)
    if obj.exactly_one:
        checks += f"        _exactly_one(obj, {obj.exactly_one!r})\n"
    reads = ", ".join(
        [
            f"{f.name}={'_required' if f.required else '_optional'}(obj, {f.name!r}, {parser(f.type, unions)})"
            for f in typed
        ]
        + ["raw=copy.deepcopy(obj)"]
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
        out = copy.deepcopy(dict(self.raw))
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
        return copy.deepcopy(dict(self.raw))


{table}: _Variants = [
{cases}
]

{union.name} = {" | ".join(members + [unknown])}


def decode_{union.name.lower()}(value: Any) -> {union.name}:
    if not _within(value, _MAX_DEPTH):
        return {unknown}({{}})
    try:
        if not _unicode(value):
            raise ValueError("a string holds a lone surrogate")
        return _dispatch(value, {table})
    except ValueError:
        return {unknown}(copy.deepcopy(cast(dict[str, Any], value)) if isinstance(value, dict) else {{}})
"""
