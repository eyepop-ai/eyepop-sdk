# Generated from protocol/schema by protocol/scripts/generate.py. Do not edit.
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


def _key(name: str, selectors: Sequence[str]) -> Callable[[dict[str, Any]], bool]:
    def matches(obj: dict[str, Any]) -> bool:
        if name in obj:
            _exactly_one(obj, selectors)
        return name in obj

    return matches


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


_INTEGER_MINIMUM = -9223372036854775808
_INTEGER_MAXIMUM = 9223372036854775807
_MAX_DEPTH = 64
_LENGTH = len


@dataclass(frozen=True)
class Ability:
    ability: str | None = None
    abilityUuid: str | None = None
    params: Mapping[str, Any] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Ability:
        obj = _object(value)
        _exactly_one(obj, ('ability', 'abilityUuid'))
        return Ability(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), params=_optional(obj, 'params', _free), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        else:
            out.pop('ability', None)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        else:
            out.pop('abilityUuid', None)
        if self.params is not None:
            out['params'] = _dump(self.params)
        else:
            out.pop('params', None)
        return out



@dataclass(frozen=True)
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraIntrinsics:
        obj = _object(value)
        return CameraIntrinsics(fx=_required(obj, 'fx', _number), fy=_required(obj, 'fy', _number), cx=_required(obj, 'cx', _number), cy=_required(obj, 'cy', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        _put_number(out, 'fx', self.fx)
        _put_number(out, 'fy', self.fy)
        _put_number(out, 'cx', self.cx)
        _put_number(out, 'cy', self.cy)
        return out



@dataclass(frozen=True)
class CameraDistortion:
    k1: float | None = None
    k2: float | None = None
    p1: float | None = None
    p2: float | None = None
    k3: float | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraDistortion:
        obj = _object(value)
        return CameraDistortion(k1=_optional(obj, 'k1', _number), k2=_optional(obj, 'k2', _number), p1=_optional(obj, 'p1', _number), p2=_optional(obj, 'p2', _number), k3=_optional(obj, 'k3', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.k1 is not None:
            _put_number(out, 'k1', self.k1)
        else:
            out.pop('k1', None)
        if self.k2 is not None:
            _put_number(out, 'k2', self.k2)
        else:
            out.pop('k2', None)
        if self.p1 is not None:
            _put_number(out, 'p1', self.p1)
        else:
            out.pop('p1', None)
        if self.p2 is not None:
            _put_number(out, 'p2', self.p2)
        else:
            out.pop('p2', None)
        if self.k3 is not None:
            _put_number(out, 'k3', self.k3)
        else:
            out.pop('k3', None)
        return out



@dataclass(frozen=True)
class CameraExtrinsicsRotation:
    w: float
    x: float
    y: float
    z: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraExtrinsicsRotation:
        obj = _object(value)
        return CameraExtrinsicsRotation(w=_required(obj, 'w', _number), x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), z=_required(obj, 'z', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        _put_number(out, 'w', self.w)
        _put_number(out, 'x', self.x)
        _put_number(out, 'y', self.y)
        _put_number(out, 'z', self.z)
        return out



@dataclass(frozen=True)
class CameraExtrinsicsTranslation:
    x: float
    y: float
    z: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraExtrinsicsTranslation:
        obj = _object(value)
        return CameraExtrinsicsTranslation(x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), z=_required(obj, 'z', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        _put_number(out, 'x', self.x)
        _put_number(out, 'y', self.y)
        _put_number(out, 'z', self.z)
        return out



@dataclass(frozen=True)
class CameraExtrinsics:
    rotation: CameraExtrinsicsRotation | None = None
    translation: CameraExtrinsicsTranslation | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraExtrinsics:
        obj = _object(value)
        return CameraExtrinsics(rotation=_optional(obj, 'rotation', CameraExtrinsicsRotation.from_json), translation=_optional(obj, 'translation', CameraExtrinsicsTranslation.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.rotation is not None:
            out['rotation'] = _dump(self.rotation)
        else:
            out.pop('rotation', None)
        if self.translation is not None:
            out['translation'] = _dump(self.translation)
        else:
            out.pop('translation', None)
        return out



@dataclass(frozen=True)
class Camera:
    intrinsics: CameraIntrinsics | None = None
    hfovDegrees: float | None = None
    distortion: CameraDistortion | None = None
    extrinsics: CameraExtrinsics | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Camera:
        obj = _object(value)
        _exactly_one(obj, ('intrinsics', 'hfovDegrees'))
        return Camera(intrinsics=_optional(obj, 'intrinsics', CameraIntrinsics.from_json), hfovDegrees=_optional(obj, 'hfovDegrees', _limit(_number, exclusive_minimum=0, exclusive_maximum=180)), distortion=_optional(obj, 'distortion', CameraDistortion.from_json), extrinsics=_optional(obj, 'extrinsics', CameraExtrinsics.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.intrinsics is not None:
            out['intrinsics'] = _dump(self.intrinsics)
        else:
            out.pop('intrinsics', None)
        if self.hfovDegrees is not None:
            _put_number(out, 'hfovDegrees', self.hfovDegrees)
        else:
            out.pop('hfovDegrees', None)
        if self.distortion is not None:
            out['distortion'] = _dump(self.distortion)
        else:
            out.pop('distortion', None)
        if self.extrinsics is not None:
            out['extrinsics'] = _dump(self.extrinsics)
        else:
            out.pop('extrinsics', None)
        return out



@dataclass(frozen=True)
class ComponentParams:
    componentId: int
    values: Mapping[str, Any]
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> ComponentParams:
        obj = _object(value)
        return ComponentParams(componentId=_required(obj, 'componentId', _integer), values=_required(obj, 'values', _free), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['componentId'] = _dump(self.componentId)
        out['values'] = _dump(self.values)
        return out



@dataclass(frozen=True)
class Contour:
    points: list[Point] | None = None
    cutouts: list[list[Point]] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Contour:
        obj = _object(value)
        return Contour(points=_optional(obj, 'points', _array(Point.from_json)), cutouts=_optional(obj, 'cutouts', _array(_array(Point.from_json))), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.points is not None:
            out['points'] = _dump(self.points)
        else:
            out.pop('points', None)
        if self.cutouts is not None:
            out['cutouts'] = _dump(self.cutouts)
        else:
            out.pop('cutouts', None)
        return out



@dataclass(frozen=True)
class Credit:
    id: str
    bytes: int
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Credit:
        obj = _object(value)
        _required(obj, 'type', _const('credit'))
        return Credit(id=_required(obj, 'id', _limit(_string, min_length=1)), bytes=_required(obj, 'bytes', _limit(_integer, minimum=0)), member=_optional(obj, 'member', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['bytes'] = _dump(self.bytes)
        if self.member is not None:
            out['member'] = _dump(self.member)
        else:
            out.pop('member', None)
        out['type'] = 'credit'
        return out



@dataclass(frozen=True)
class Depth:
    width: int | None = None
    height: int | None = None
    semantic: str | None = None
    values: str | None = None
    world: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Depth:
        obj = _object(value)
        return Depth(width=_optional(obj, 'width', _integer), height=_optional(obj, 'height', _integer), semantic=_optional(obj, 'semantic', _string), values=_optional(obj, 'values', _string), world=_optional(obj, 'world', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.width is not None:
            out['width'] = _dump(self.width)
        else:
            out.pop('width', None)
        if self.height is not None:
            out['height'] = _dump(self.height)
        else:
            out.pop('height', None)
        if self.semantic is not None:
            out['semantic'] = _dump(self.semantic)
        else:
            out.pop('semantic', None)
        if self.values is not None:
            out['values'] = _dump(self.values)
        else:
            out.pop('values', None)
        if self.world is not None:
            out['world'] = _dump(self.world)
        else:
            out.pop('world', None)
        return out



@dataclass(frozen=True)
class Done:

    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Done:
        obj = _object(value)
        _required(obj, 'type', _const('done'))
        return Done(raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['type'] = 'done'
        return out



@dataclass(frozen=True)
class Dropped:
    id: str
    count: int
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Dropped:
        obj = _object(value)
        _required(obj, 'type', _const('dropped'))
        return Dropped(id=_required(obj, 'id', _limit(_string, min_length=1)), count=_required(obj, 'count', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['count'] = _dump(self.count)
        out['type'] = 'dropped'
        return out



@dataclass(frozen=True)
class End:
    id: str
    reason: Literal['eos', 'error', 'preempted', 'stopped']
    message: str | None = None
    milliComputeUnits: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> End:
        obj = _object(value)
        _required(obj, 'type', _const('end'))
        return End(id=_required(obj, 'id', _limit(_string, min_length=1)), reason=_required(obj, 'reason', _enum(('eos', 'error', 'preempted', 'stopped'))), message=_optional(obj, 'message', _string), milliComputeUnits=_optional(obj, 'milliComputeUnits', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['reason'] = _dump(self.reason)
        if self.message is not None:
            out['message'] = _dump(self.message)
        else:
            out.pop('message', None)
        if self.milliComputeUnits is not None:
            out['milliComputeUnits'] = _dump(self.milliComputeUnits)
        else:
            out.pop('milliComputeUnits', None)
        out['type'] = 'end'
        return out



@dataclass(frozen=True)
class ErrorMessage:
    error: str
    message: str
    id: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> ErrorMessage:
        obj = _object(value)
        _required(obj, 'type', _const('error'))
        return ErrorMessage(error=_required(obj, 'error', _limit(_string, min_length=1)), message=_required(obj, 'message', _string), id=_optional(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['error'] = _dump(self.error)
        out['message'] = _dump(self.message)
        if self.id is not None:
            out['id'] = _dump(self.id)
        else:
            out.pop('id', None)
        out['type'] = 'error'
        return out



@dataclass(frozen=True)
class GetGraph:
    id: str
    format: Literal['dot', 'png', 'pdf']
    verbose: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GetGraph:
        obj = _object(value)
        _required(obj, 'type', _const('getGraph'))
        return GetGraph(id=_required(obj, 'id', _limit(_string, min_length=1)), format=_required(obj, 'format', _enum(('dot', 'png', 'pdf'))), verbose=_optional(obj, 'verbose', _boolean), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['format'] = _dump(self.format)
        if self.verbose is not None:
            out['verbose'] = _dump(self.verbose)
        else:
            out.pop('verbose', None)
        out['type'] = 'getGraph'
        return out



@dataclass(frozen=True)
class InferenceComponent:
    ability: str | None = None
    abilityUuid: str | None = None
    params: Mapping[str, Any] | None = None
    id: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> InferenceComponent:
        obj = _object(value)
        _required(obj, 'type', _const('inference'))
        _exactly_one(obj, ('ability', 'abilityUuid'))
        return InferenceComponent(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), params=_optional(obj, 'params', _free), id=_optional(obj, 'id', _integer), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        else:
            out.pop('ability', None)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        else:
            out.pop('abilityUuid', None)
        if self.params is not None:
            out['params'] = _dump(self.params)
        else:
            out.pop('params', None)
        if self.id is not None:
            out['id'] = _dump(self.id)
        else:
            out.pop('id', None)
        out['type'] = 'inference'
        return out



@dataclass(frozen=True)
class Mask:
    width: int | None = None
    height: int | None = None
    stride: int | None = None
    bitmap: str | None = None
    world: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Mask:
        obj = _object(value)
        return Mask(width=_optional(obj, 'width', _integer), height=_optional(obj, 'height', _integer), stride=_optional(obj, 'stride', _integer), bitmap=_optional(obj, 'bitmap', _string), world=_optional(obj, 'world', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.width is not None:
            out['width'] = _dump(self.width)
        else:
            out.pop('width', None)
        if self.height is not None:
            out['height'] = _dump(self.height)
        else:
            out.pop('height', None)
        if self.stride is not None:
            out['stride'] = _dump(self.stride)
        else:
            out.pop('stride', None)
        if self.bitmap is not None:
            out['bitmap'] = _dump(self.bitmap)
        else:
            out.pop('bitmap', None)
        if self.world is not None:
            out['world'] = _dump(self.world)
        else:
            out.pop('world', None)
        return out



@dataclass(frozen=True)
class Ping:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Ping:
        obj = _object(value)
        _required(obj, 'type', _const('ping'))
        return Ping(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'ping'
        return out



@dataclass(frozen=True)
class Point:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    worldX: float | None = None
    worldY: float | None = None
    worldZ: float | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Point:
        obj = _object(value)
        return Point(x=_optional(obj, 'x', _number), y=_optional(obj, 'y', _number), z=_optional(obj, 'z', _number), worldX=_optional(obj, 'worldX', _number), worldY=_optional(obj, 'worldY', _number), worldZ=_optional(obj, 'worldZ', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.x is not None:
            _put_number(out, 'x', self.x)
        else:
            out.pop('x', None)
        if self.y is not None:
            _put_number(out, 'y', self.y)
        else:
            out.pop('y', None)
        if self.z is not None:
            _put_number(out, 'z', self.z)
        else:
            out.pop('z', None)
        if self.worldX is not None:
            _put_number(out, 'worldX', self.worldX)
        else:
            out.pop('worldX', None)
        if self.worldY is not None:
            _put_number(out, 'worldY', self.worldY)
        else:
            out.pop('worldY', None)
        if self.worldZ is not None:
            _put_number(out, 'worldZ', self.worldZ)
        else:
            out.pop('worldZ', None)
        return out



@dataclass(frozen=True)
class Pong:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Pong:
        obj = _object(value)
        _required(obj, 'type', _const('pong'))
        return Pong(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'pong'
        return out



@dataclass(frozen=True)
class Pop:
    components: list[PopComponent]
    postTransform: str | None = None
    defaults: SourceDefaults | None = None
    depthMap: PopDepthMap | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Pop:
        obj = _object(value)
        return Pop(components=_required(obj, 'components', _array(decode_popcomponent)), postTransform=_optional(obj, 'postTransform', _string), defaults=_optional(obj, 'defaults', SourceDefaults.from_json), depthMap=_optional(obj, 'depthMap', PopDepthMap.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['components'] = _dump(self.components)
        if self.postTransform is not None:
            out['postTransform'] = _dump(self.postTransform)
        else:
            out.pop('postTransform', None)
        if self.defaults is not None:
            out['defaults'] = _dump(self.defaults)
        else:
            out.pop('defaults', None)
        if self.depthMap is not None:
            out['depthMap'] = _dump(self.depthMap)
        else:
            out.pop('depthMap', None)
        return out



@dataclass(frozen=True)
class PopDepthMap:
    ability: str | None = None
    abilityUuid: str | None = None
    toWorld: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PopDepthMap:
        obj = _object(value)
        _exactly_one(obj, ('ability', 'abilityUuid'))
        return PopDepthMap(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), toWorld=_optional(obj, 'toWorld', _boolean), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        else:
            out.pop('ability', None)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        else:
            out.pop('abilityUuid', None)
        if self.toWorld is not None:
            out['toWorld'] = _dump(self.toWorld)
        else:
            out.pop('toWorld', None)
        return out



@dataclass(frozen=True)
class PredictedClass:
    classLabel: str | None = None
    confidence: float | None = None
    category: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedClass:
        obj = _object(value)
        return PredictedClass(classLabel=_optional(obj, 'classLabel', _string), confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.classLabel is not None:
            out['classLabel'] = _dump(self.classLabel)
        else:
            out.pop('classLabel', None)
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        return out



@dataclass(frozen=True)
class PredictedKeyPoint:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    worldX: float | None = None
    worldY: float | None = None
    worldZ: float | None = None
    classLabel: str | None = None
    confidence: float | None = None
    category: str | None = None
    visible: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedKeyPoint:
        obj = _object(value)
        return PredictedKeyPoint(x=_optional(obj, 'x', _number), y=_optional(obj, 'y', _number), z=_optional(obj, 'z', _number), worldX=_optional(obj, 'worldX', _number), worldY=_optional(obj, 'worldY', _number), worldZ=_optional(obj, 'worldZ', _number), classLabel=_optional(obj, 'classLabel', _string), confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), visible=_optional(obj, 'visible', _boolean), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.x is not None:
            _put_number(out, 'x', self.x)
        else:
            out.pop('x', None)
        if self.y is not None:
            _put_number(out, 'y', self.y)
        else:
            out.pop('y', None)
        if self.z is not None:
            _put_number(out, 'z', self.z)
        else:
            out.pop('z', None)
        if self.worldX is not None:
            _put_number(out, 'worldX', self.worldX)
        else:
            out.pop('worldX', None)
        if self.worldY is not None:
            _put_number(out, 'worldY', self.worldY)
        else:
            out.pop('worldY', None)
        if self.worldZ is not None:
            _put_number(out, 'worldZ', self.worldZ)
        else:
            out.pop('worldZ', None)
        if self.classLabel is not None:
            out['classLabel'] = _dump(self.classLabel)
        else:
            out.pop('classLabel', None)
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        if self.visible is not None:
            out['visible'] = _dump(self.visible)
        else:
            out.pop('visible', None)
        return out



@dataclass(frozen=True)
class PredictedKeyPoints:
    confidence: float | None = None
    category: str | None = None
    points: list[PredictedKeyPoint] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedKeyPoints:
        obj = _object(value)
        return PredictedKeyPoints(confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), points=_optional(obj, 'points', _array(PredictedKeyPoint.from_json)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        if self.points is not None:
            out['points'] = _dump(self.points)
        else:
            out.pop('points', None)
        return out



@dataclass(frozen=True)
class PredictedMesh:
    confidence: float | None = None
    category: str | None = None
    points: list[Point] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedMesh:
        obj = _object(value)
        return PredictedMesh(confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), points=_optional(obj, 'points', _array(Point.from_json)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        if self.points is not None:
            out['points'] = _dump(self.points)
        else:
            out.pop('points', None)
        return out



@dataclass(frozen=True)
class PredictedObject:
    classLabel: str | None = None
    confidence: float | None = None
    category: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    orientation: float | None = None
    trackId: int | None = None
    globalObjectId: int | None = None
    outline: list[Point] | None = None
    contours: list[Contour] | None = None
    mask: Mask | None = None
    objects: list[PredictedObject] | None = None
    classes: list[PredictedClass] | None = None
    texts: list[PredictedText] | None = None
    keyPoints: list[PredictedKeyPoints] | None = None
    meshes: list[PredictedMesh] | None = None
    details: list[Mapping[str, Any]] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedObject:
        obj = _object(value)
        return PredictedObject(classLabel=_optional(obj, 'classLabel', _string), confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), x=_optional(obj, 'x', _number), y=_optional(obj, 'y', _number), width=_optional(obj, 'width', _number), height=_optional(obj, 'height', _number), orientation=_optional(obj, 'orientation', _number), trackId=_optional(obj, 'trackId', _integer), globalObjectId=_optional(obj, 'globalObjectId', _integer), outline=_optional(obj, 'outline', _array(Point.from_json)), contours=_optional(obj, 'contours', _array(Contour.from_json)), mask=_optional(obj, 'mask', Mask.from_json), objects=_optional(obj, 'objects', _array(PredictedObject.from_json)), classes=_optional(obj, 'classes', _array(PredictedClass.from_json)), texts=_optional(obj, 'texts', _array(PredictedText.from_json)), keyPoints=_optional(obj, 'keyPoints', _array(PredictedKeyPoints.from_json)), meshes=_optional(obj, 'meshes', _array(PredictedMesh.from_json)), details=_optional(obj, 'details', _array(_free)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.classLabel is not None:
            out['classLabel'] = _dump(self.classLabel)
        else:
            out.pop('classLabel', None)
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        if self.x is not None:
            _put_number(out, 'x', self.x)
        else:
            out.pop('x', None)
        if self.y is not None:
            _put_number(out, 'y', self.y)
        else:
            out.pop('y', None)
        if self.width is not None:
            _put_number(out, 'width', self.width)
        else:
            out.pop('width', None)
        if self.height is not None:
            _put_number(out, 'height', self.height)
        else:
            out.pop('height', None)
        if self.orientation is not None:
            _put_number(out, 'orientation', self.orientation)
        else:
            out.pop('orientation', None)
        if self.trackId is not None:
            out['trackId'] = _dump(self.trackId)
        else:
            out.pop('trackId', None)
        if self.globalObjectId is not None:
            out['globalObjectId'] = _dump(self.globalObjectId)
        else:
            out.pop('globalObjectId', None)
        if self.outline is not None:
            out['outline'] = _dump(self.outline)
        else:
            out.pop('outline', None)
        if self.contours is not None:
            out['contours'] = _dump(self.contours)
        else:
            out.pop('contours', None)
        if self.mask is not None:
            out['mask'] = _dump(self.mask)
        else:
            out.pop('mask', None)
        if self.objects is not None:
            out['objects'] = _dump(self.objects)
        else:
            out.pop('objects', None)
        if self.classes is not None:
            out['classes'] = _dump(self.classes)
        else:
            out.pop('classes', None)
        if self.texts is not None:
            out['texts'] = _dump(self.texts)
        else:
            out.pop('texts', None)
        if self.keyPoints is not None:
            out['keyPoints'] = _dump(self.keyPoints)
        else:
            out.pop('keyPoints', None)
        if self.meshes is not None:
            out['meshes'] = _dump(self.meshes)
        else:
            out.pop('meshes', None)
        if self.details is not None:
            out['details'] = _dump(self.details)
        else:
            out.pop('details', None)
        return out



@dataclass(frozen=True)
class PredictedText:
    text: str | None = None
    confidence: float | None = None
    category: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictedText:
        obj = _object(value)
        return PredictedText(text=_optional(obj, 'text', _string), confidence=_optional(obj, 'confidence', _number), category=_optional(obj, 'category', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.text is not None:
            out['text'] = _dump(self.text)
        else:
            out.pop('text', None)
        if self.confidence is not None:
            _put_number(out, 'confidence', self.confidence)
        else:
            out.pop('confidence', None)
        if self.category is not None:
            out['category'] = _dump(self.category)
        else:
            out.pop('category', None)
        return out



@dataclass(frozen=True)
class Prediction:
    timestamp: int | None = None
    seconds: float | None = None
    offset: int | None = None
    duration: int | None = None
    captured_at: int | None = None
    source_id: str | None = None
    source_width: int | None = None
    source_height: int | None = None
    compute_units: float | None = None
    milli_compute_units: int | None = None
    selected: bool | None = None
    objects: list[PredictedObject] | None = None
    classes: list[PredictedClass] | None = None
    texts: list[PredictedText] | None = None
    keyPoints: list[PredictedKeyPoints] | None = None
    meshes: list[PredictedMesh] | None = None
    depth: Depth | None = None
    tokens: Mapping[str, Any] | None = None
    details: list[Mapping[str, Any]] | None = None
    track_events: list[TrackEvent] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Prediction:
        obj = _object(value)
        return Prediction(timestamp=_optional(obj, 'timestamp', _integer), seconds=_optional(obj, 'seconds', _number), offset=_optional(obj, 'offset', _integer), duration=_optional(obj, 'duration', _integer), captured_at=_optional(obj, 'captured_at', _integer), source_id=_optional(obj, 'source_id', _string), source_width=_optional(obj, 'source_width', _integer), source_height=_optional(obj, 'source_height', _integer), compute_units=_optional(obj, 'compute_units', _number), milli_compute_units=_optional(obj, 'milli_compute_units', _integer), selected=_optional(obj, 'selected', _boolean), objects=_optional(obj, 'objects', _array(PredictedObject.from_json)), classes=_optional(obj, 'classes', _array(PredictedClass.from_json)), texts=_optional(obj, 'texts', _array(PredictedText.from_json)), keyPoints=_optional(obj, 'keyPoints', _array(PredictedKeyPoints.from_json)), meshes=_optional(obj, 'meshes', _array(PredictedMesh.from_json)), depth=_optional(obj, 'depth', Depth.from_json), tokens=_optional(obj, 'tokens', _free), details=_optional(obj, 'details', _array(_free)), track_events=_optional(obj, 'track_events', _array(TrackEvent.from_json)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.timestamp is not None:
            out['timestamp'] = _dump(self.timestamp)
        else:
            out.pop('timestamp', None)
        if self.seconds is not None:
            _put_number(out, 'seconds', self.seconds)
        else:
            out.pop('seconds', None)
        if self.offset is not None:
            out['offset'] = _dump(self.offset)
        else:
            out.pop('offset', None)
        if self.duration is not None:
            out['duration'] = _dump(self.duration)
        else:
            out.pop('duration', None)
        if self.captured_at is not None:
            out['captured_at'] = _dump(self.captured_at)
        else:
            out.pop('captured_at', None)
        if self.source_id is not None:
            out['source_id'] = _dump(self.source_id)
        else:
            out.pop('source_id', None)
        if self.source_width is not None:
            out['source_width'] = _dump(self.source_width)
        else:
            out.pop('source_width', None)
        if self.source_height is not None:
            out['source_height'] = _dump(self.source_height)
        else:
            out.pop('source_height', None)
        if self.compute_units is not None:
            _put_number(out, 'compute_units', self.compute_units)
        else:
            out.pop('compute_units', None)
        if self.milli_compute_units is not None:
            out['milli_compute_units'] = _dump(self.milli_compute_units)
        else:
            out.pop('milli_compute_units', None)
        if self.selected is not None:
            out['selected'] = _dump(self.selected)
        else:
            out.pop('selected', None)
        if self.objects is not None:
            out['objects'] = _dump(self.objects)
        else:
            out.pop('objects', None)
        if self.classes is not None:
            out['classes'] = _dump(self.classes)
        else:
            out.pop('classes', None)
        if self.texts is not None:
            out['texts'] = _dump(self.texts)
        else:
            out.pop('texts', None)
        if self.keyPoints is not None:
            out['keyPoints'] = _dump(self.keyPoints)
        else:
            out.pop('keyPoints', None)
        if self.meshes is not None:
            out['meshes'] = _dump(self.meshes)
        else:
            out.pop('meshes', None)
        if self.depth is not None:
            out['depth'] = _dump(self.depth)
        else:
            out.pop('depth', None)
        if self.tokens is not None:
            out['tokens'] = _dump(self.tokens)
        else:
            out.pop('tokens', None)
        if self.details is not None:
            out['details'] = _dump(self.details)
        else:
            out.pop('details', None)
        if self.track_events is not None:
            out['track_events'] = _dump(self.track_events)
        else:
            out.pop('track_events', None)
        return out



@dataclass(frozen=True)
class PredictionMessage:
    id: str
    prediction: Prediction
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> PredictionMessage:
        obj = _object(value)
        _required(obj, 'type', _const('prediction'))
        return PredictionMessage(id=_required(obj, 'id', _limit(_string, min_length=1)), prediction=_required(obj, 'prediction', Prediction.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['prediction'] = _dump(self.prediction)
        out['type'] = 'prediction'
        return out



@dataclass(frozen=True)
class Quit:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Quit:
        obj = _object(value)
        _required(obj, 'type', _const('quit'))
        return Quit(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'quit'
        return out



@dataclass(frozen=True)
class RawComponent:
    type: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RawComponent:
        obj = _object(value)
        return RawComponent(type=_required(obj, 'type', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['type'] = _dump(self.type)
        return out



@dataclass(frozen=True)
class Result:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Result:
        obj = _object(value)
        _required(obj, 'type', _const('result'))
        return Result(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'result'
        return out



@dataclass(frozen=True)
class Send:
    id: str
    credit: int
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Send:
        obj = _object(value)
        _required(obj, 'type', _const('send'))
        return Send(id=_required(obj, 'id', _limit(_string, min_length=1)), credit=_required(obj, 'credit', _limit(_integer, minimum=0)), member=_optional(obj, 'member', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['credit'] = _dump(self.credit)
        if self.member is not None:
            out['member'] = _dump(self.member)
        else:
            out.pop('member', None)
        out['type'] = 'send'
        return out



@dataclass(frozen=True)
class SetPop:
    id: str
    pop: Pop
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SetPop:
        obj = _object(value)
        _required(obj, 'type', _const('setPop'))
        return SetPop(id=_required(obj, 'id', _limit(_string, min_length=1)), pop=_required(obj, 'pop', Pop.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['pop'] = _dump(self.pop)
        out['type'] = 'setPop'
        return out



@dataclass(frozen=True)
class SetSourceUpload:
    contentType: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SetSourceUpload:
        obj = _object(value)
        return SetSourceUpload(contentType=_required(obj, 'contentType', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['contentType'] = _dump(self.contentType)
        return out



@dataclass(frozen=True)
class SetSource:
    id: str
    url: str | None = None
    assetUuid: str | None = None
    upload: SetSourceUpload | None = None
    group: list[GroupMember] | None = None
    params: list[ComponentParams] | None = None
    fps: str | None = None
    roi: Roi | None = None
    camera: Camera | None = None
    live: bool | None = None
    mode: Literal['queue', 'preempt'] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SetSource:
        obj = _object(value)
        _required(obj, 'type', _const('setSource'))
        _exactly_one(obj, ('url', 'assetUuid', 'upload', 'group'))
        return SetSource(id=_required(obj, 'id', _limit(_string, min_length=1)), url=_optional(obj, 'url', _string), assetUuid=_optional(obj, 'assetUuid', _string), upload=_optional(obj, 'upload', SetSourceUpload.from_json), group=_optional(obj, 'group', _array(decode_groupmember)), params=_optional(obj, 'params', _array(ComponentParams.from_json)), fps=_optional(obj, 'fps', _string), roi=_optional(obj, 'roi', decode_roi), camera=_optional(obj, 'camera', Camera.from_json), live=_optional(obj, 'live', _boolean), mode=_optional(obj, 'mode', _enum(('queue', 'preempt'))), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        if self.url is not None:
            out['url'] = _dump(self.url)
        else:
            out.pop('url', None)
        if self.assetUuid is not None:
            out['assetUuid'] = _dump(self.assetUuid)
        else:
            out.pop('assetUuid', None)
        if self.upload is not None:
            out['upload'] = _dump(self.upload)
        else:
            out.pop('upload', None)
        if self.group is not None:
            out['group'] = _dump(self.group)
        else:
            out.pop('group', None)
        if self.params is not None:
            out['params'] = _dump(self.params)
        else:
            out.pop('params', None)
        if self.fps is not None:
            out['fps'] = _dump(self.fps)
        else:
            out.pop('fps', None)
        if self.roi is not None:
            out['roi'] = _dump(self.roi)
        else:
            out.pop('roi', None)
        if self.camera is not None:
            out['camera'] = _dump(self.camera)
        else:
            out.pop('camera', None)
        if self.live is not None:
            out['live'] = _dump(self.live)
        else:
            out.pop('live', None)
        if self.mode is not None:
            out['mode'] = _dump(self.mode)
        else:
            out.pop('mode', None)
        out['type'] = 'setSource'
        return out



@dataclass(frozen=True)
class SourceDefaults:
    camera: Camera | None = None
    fps: str | None = None
    roi: Roi | None = None
    motionDetect: bool | None = None
    motionSensitivity: float | None = None
    motionThreshold: float | None = None
    motionGap: int | None = None
    motionGridX: int | None = None
    motionGridY: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SourceDefaults:
        obj = _object(value)
        return SourceDefaults(camera=_optional(obj, 'camera', Camera.from_json), fps=_optional(obj, 'fps', _string), roi=_optional(obj, 'roi', decode_roi), motionDetect=_optional(obj, 'motionDetect', _boolean), motionSensitivity=_optional(obj, 'motionSensitivity', _number), motionThreshold=_optional(obj, 'motionThreshold', _number), motionGap=_optional(obj, 'motionGap', _integer), motionGridX=_optional(obj, 'motionGridX', _integer), motionGridY=_optional(obj, 'motionGridY', _integer), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.camera is not None:
            out['camera'] = _dump(self.camera)
        else:
            out.pop('camera', None)
        if self.fps is not None:
            out['fps'] = _dump(self.fps)
        else:
            out.pop('fps', None)
        if self.roi is not None:
            out['roi'] = _dump(self.roi)
        else:
            out.pop('roi', None)
        if self.motionDetect is not None:
            out['motionDetect'] = _dump(self.motionDetect)
        else:
            out.pop('motionDetect', None)
        if self.motionSensitivity is not None:
            _put_number(out, 'motionSensitivity', self.motionSensitivity)
        else:
            out.pop('motionSensitivity', None)
        if self.motionThreshold is not None:
            _put_number(out, 'motionThreshold', self.motionThreshold)
        else:
            out.pop('motionThreshold', None)
        if self.motionGap is not None:
            out['motionGap'] = _dump(self.motionGap)
        else:
            out.pop('motionGap', None)
        if self.motionGridX is not None:
            out['motionGridX'] = _dump(self.motionGridX)
        else:
            out.pop('motionGridX', None)
        if self.motionGridY is not None:
            out['motionGridY'] = _dump(self.motionGridY)
        else:
            out.pop('motionGridY', None)
        return out



@dataclass(frozen=True)
class Start:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Start:
        obj = _object(value)
        _required(obj, 'type', _const('start'))
        return Start(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'start'
        return out



@dataclass(frozen=True)
class StopSource:
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> StopSource:
        obj = _object(value)
        _required(obj, 'type', _const('stopSource'))
        return StopSource(id=_required(obj, 'id', _limit(_string, min_length=1)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['type'] = 'stopSource'
        return out



@dataclass(frozen=True)
class TrackEvent:
    track_id: int | None = None
    is_ended: bool | None = None
    started_at: int | None = None
    ended_at: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> TrackEvent:
        obj = _object(value)
        return TrackEvent(track_id=_optional(obj, 'track_id', _integer), is_ended=_optional(obj, 'is_ended', _boolean), started_at=_optional(obj, 'started_at', _integer), ended_at=_optional(obj, 'ended_at', _integer), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        if self.track_id is not None:
            out['track_id'] = _dump(self.track_id)
        else:
            out.pop('track_id', None)
        if self.is_ended is not None:
            out['is_ended'] = _dump(self.is_ended)
        else:
            out.pop('is_ended', None)
        if self.started_at is not None:
            out['started_at'] = _dump(self.started_at)
        else:
            out.pop('started_at', None)
        if self.ended_at is not None:
            out['ended_at'] = _dump(self.ended_at)
        else:
            out.pop('ended_at', None)
        return out



@dataclass(frozen=True)
class Uploaded:
    id: str
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Uploaded:
        obj = _object(value)
        _required(obj, 'type', _const('uploaded'))
        return Uploaded(id=_required(obj, 'id', _limit(_string, min_length=1)), member=_optional(obj, 'member', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        if self.member is not None:
            out['member'] = _dump(self.member)
        else:
            out.pop('member', None)
        out['type'] = 'uploaded'
        return out



@dataclass(frozen=True)
class Usage:
    id: str
    milliComputeUnits: int
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Usage:
        obj = _object(value)
        _required(obj, 'type', _const('usage'))
        return Usage(id=_required(obj, 'id', _limit(_string, min_length=1)), milliComputeUnits=_required(obj, 'milliComputeUnits', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['id'] = _dump(self.id)
        out['milliComputeUnits'] = _dump(self.milliComputeUnits)
        out['type'] = 'usage'
        return out



@dataclass(frozen=True)
class GroupMemberUrl:
    url: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GroupMemberUrl:
        obj = _object(value)
        return GroupMemberUrl(url=_required(obj, 'url', _string), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['url'] = _dump(self.url)
        return out



@dataclass(frozen=True)
class GroupMemberUploadUpload:
    contentType: str
    bytes: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GroupMemberUploadUpload:
        obj = _object(value)
        return GroupMemberUploadUpload(contentType=_required(obj, 'contentType', _string), bytes=_optional(obj, 'bytes', _limit(_integer, minimum=0)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['contentType'] = _dump(self.contentType)
        if self.bytes is not None:
            out['bytes'] = _dump(self.bytes)
        else:
            out.pop('bytes', None)
        return out



@dataclass(frozen=True)
class GroupMemberUpload:
    upload: GroupMemberUploadUpload
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GroupMemberUpload:
        obj = _object(value)
        return GroupMemberUpload(upload=_required(obj, 'upload', GroupMemberUploadUpload.from_json), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['upload'] = _dump(self.upload)
        return out



@dataclass(frozen=True)
class RoiRectangle:
    x: float
    y: float
    width: float
    height: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiRectangle:
        obj = _object(value)
        _required(obj, 'type', _const('rectangle'))
        return RoiRectangle(x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), width=_required(obj, 'width', _number), height=_required(obj, 'height', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        _put_number(out, 'x', self.x)
        _put_number(out, 'y', self.y)
        _put_number(out, 'width', self.width)
        _put_number(out, 'height', self.height)
        out['type'] = 'rectangle'
        return out



@dataclass(frozen=True)
class RoiContourPoint:
    x: float
    y: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiContourPoint:
        obj = _object(value)
        return RoiContourPoint(x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        _put_number(out, 'x', self.x)
        _put_number(out, 'y', self.y)
        return out



@dataclass(frozen=True)
class RoiContour:
    points: list[RoiContourPoint]
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiContour:
        obj = _object(value)
        _required(obj, 'type', _const('contour'))
        return RoiContour(points=_required(obj, 'points', _array(RoiContourPoint.from_json)), raw=copy.deepcopy(obj))

    def to_json(self) -> dict[str, Any]:
        out = copy.deepcopy(dict(self.raw))
        out['points'] = _dump(self.points)
        out['type'] = 'contour'
        return out



@dataclass(frozen=True)
class UnknownCommand:
    raw: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.raw))


_COMMAND_VARIANTS: _Variants = [
    (_tag('setPop'), SetPop.from_json),
    (_tag('ping'), Ping.from_json),
    (_tag('setSource'), SetSource.from_json),
    (_tag('uploaded'), Uploaded.from_json),
    (_tag('stopSource'), StopSource.from_json),
    (_tag('getGraph'), GetGraph.from_json),
    (_tag('quit'), Quit.from_json),
]

Command = SetPop | Ping | SetSource | Uploaded | StopSource | GetGraph | Quit | UnknownCommand


def decode_command(value: Any) -> Command:
    if not _within(value, _MAX_DEPTH):
        return UnknownCommand({})
    try:
        if not _unicode(value):
            raise ValueError("a string holds a lone surrogate")
        return _dispatch(value, _COMMAND_VARIANTS)
    except ValueError:
        return UnknownCommand(copy.deepcopy(cast(dict[str, Any], value)) if isinstance(value, dict) else {})



_GROUPMEMBER_VARIANTS: _Variants = [
    (_key('url', ('url', 'upload')), GroupMemberUrl.from_json),
    (_key('upload', ('url', 'upload')), GroupMemberUpload.from_json),
]

GroupMember = GroupMemberUrl | GroupMemberUpload


def decode_groupmember(value: Any) -> GroupMember:
    return _dispatch(value, _GROUPMEMBER_VARIANTS)



_JOBMESSAGE_VARIANTS: _Variants = [
    (_tag('start'), Start.from_json),
    (_tag('prediction'), PredictionMessage.from_json),
    (_tag('dropped'), Dropped.from_json),
    (_tag('usage'), Usage.from_json),
    (_tag('end'), End.from_json),
]

JobMessage = Start | PredictionMessage | Dropped | Usage | End


def decode_jobmessage(value: Any) -> JobMessage:
    return _dispatch(value, _JOBMESSAGE_VARIANTS)



@dataclass(frozen=True)
class UnknownMessage:
    raw: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return copy.deepcopy(dict(self.raw))


_MESSAGE_VARIANTS: _Variants = [
    (_tag('result'), Result.from_json),
    (_tag('send'), Send.from_json),
    (_tag('credit'), Credit.from_json),
    (_tag('start'), Start.from_json),
    (_tag('prediction'), PredictionMessage.from_json),
    (_tag('dropped'), Dropped.from_json),
    (_tag('usage'), Usage.from_json),
    (_tag('end'), End.from_json),
    (_tag('done'), Done.from_json),
    (_tag('pong'), Pong.from_json),
    (_tag('error'), ErrorMessage.from_json),
]

Message = Result | Send | Credit | Start | PredictionMessage | Dropped | Usage | End | Done | Pong | ErrorMessage | UnknownMessage


def decode_message(value: Any) -> Message:
    if not _within(value, _MAX_DEPTH):
        return UnknownMessage({})
    try:
        if not _unicode(value):
            raise ValueError("a string holds a lone surrogate")
        return _dispatch(value, _MESSAGE_VARIANTS)
    except ValueError:
        return UnknownMessage(copy.deepcopy(cast(dict[str, Any], value)) if isinstance(value, dict) else {})



_POPCOMPONENT_VARIANTS: _Variants = [
    (_tag('inference'), InferenceComponent.from_json),
    (_always, RawComponent.from_json),
]

PopComponent = InferenceComponent | RawComponent


def decode_popcomponent(value: Any) -> PopComponent:
    return _dispatch(value, _POPCOMPONENT_VARIANTS)



_ROI_VARIANTS: _Variants = [
    (_tag('rectangle'), RoiRectangle.from_json),
    (_tag('contour'), RoiContour.from_json),
]

Roi = RoiRectangle | RoiContour


def decode_roi(value: Any) -> Roi:
    return _dispatch(value, _ROI_VARIANTS)

