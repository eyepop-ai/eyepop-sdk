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



@dataclass(frozen=True)
class Ability:
    ability: str | None = None
    abilityUuid: str | None = None
    params: Mapping[str, Any] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Ability:
        obj = _object(value)
        return Ability(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), params=_optional(obj, 'params', _free), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        if self.params is not None:
            out['params'] = _dump(self.params)
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
        return CameraIntrinsics(fx=_required(obj, 'fx', _number), fy=_required(obj, 'fy', _number), cx=_required(obj, 'cx', _number), cy=_required(obj, 'cy', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['fx'] = _dump(self.fx)
        out['fy'] = _dump(self.fy)
        out['cx'] = _dump(self.cx)
        out['cy'] = _dump(self.cy)
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
        return CameraDistortion(k1=_optional(obj, 'k1', _number), k2=_optional(obj, 'k2', _number), p1=_optional(obj, 'p1', _number), p2=_optional(obj, 'p2', _number), k3=_optional(obj, 'k3', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.k1 is not None:
            out['k1'] = _dump(self.k1)
        if self.k2 is not None:
            out['k2'] = _dump(self.k2)
        if self.p1 is not None:
            out['p1'] = _dump(self.p1)
        if self.p2 is not None:
            out['p2'] = _dump(self.p2)
        if self.k3 is not None:
            out['k3'] = _dump(self.k3)
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
        return CameraExtrinsicsRotation(w=_required(obj, 'w', _number), x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), z=_required(obj, 'z', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['w'] = _dump(self.w)
        out['x'] = _dump(self.x)
        out['y'] = _dump(self.y)
        out['z'] = _dump(self.z)
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
        return CameraExtrinsicsTranslation(x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), z=_required(obj, 'z', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['x'] = _dump(self.x)
        out['y'] = _dump(self.y)
        out['z'] = _dump(self.z)
        return out



@dataclass(frozen=True)
class CameraExtrinsics:
    rotation: CameraExtrinsicsRotation | None = None
    translation: CameraExtrinsicsTranslation | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> CameraExtrinsics:
        obj = _object(value)
        return CameraExtrinsics(rotation=_optional(obj, 'rotation', CameraExtrinsicsRotation.from_json), translation=_optional(obj, 'translation', CameraExtrinsicsTranslation.from_json), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.rotation is not None:
            out['rotation'] = _dump(self.rotation)
        if self.translation is not None:
            out['translation'] = _dump(self.translation)
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
        return Camera(intrinsics=_optional(obj, 'intrinsics', CameraIntrinsics.from_json), hfovDegrees=_optional(obj, 'hfovDegrees', _number), distortion=_optional(obj, 'distortion', CameraDistortion.from_json), extrinsics=_optional(obj, 'extrinsics', CameraExtrinsics.from_json), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.intrinsics is not None:
            out['intrinsics'] = _dump(self.intrinsics)
        if self.hfovDegrees is not None:
            out['hfovDegrees'] = _dump(self.hfovDegrees)
        if self.distortion is not None:
            out['distortion'] = _dump(self.distortion)
        if self.extrinsics is not None:
            out['extrinsics'] = _dump(self.extrinsics)
        return out



@dataclass(frozen=True)
class ComponentParams:
    componentId: int
    values: Mapping[str, Any]
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> ComponentParams:
        obj = _object(value)
        return ComponentParams(componentId=_required(obj, 'componentId', _integer), values=_required(obj, 'values', _free), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['componentId'] = _dump(self.componentId)
        out['values'] = _dump(self.values)
        return out



@dataclass(frozen=True)
class Credit:
    type: Literal['credit']
    id: str
    bytes: int
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Credit:
        obj = _object(value)
        return Credit(type=_required(obj, 'type', _const('credit')), id=_required(obj, 'id', _string), bytes=_required(obj, 'bytes', _integer), member=_optional(obj, 'member', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['bytes'] = _dump(self.bytes)
        if self.member is not None:
            out['member'] = _dump(self.member)
        return out



@dataclass(frozen=True)
class Done:
    type: Literal['done']
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Done:
        obj = _object(value)
        return Done(type=_required(obj, 'type', _const('done')), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        return out



@dataclass(frozen=True)
class Dropped:
    type: Literal['dropped']
    id: str
    count: int
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Dropped:
        obj = _object(value)
        return Dropped(type=_required(obj, 'type', _const('dropped')), id=_required(obj, 'id', _string), count=_required(obj, 'count', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['count'] = _dump(self.count)
        return out



@dataclass(frozen=True)
class End:
    type: Literal['end']
    id: str
    reason: Literal['eos', 'error', 'preempted', 'stopped']
    message: str | None = None
    milliComputeUnits: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> End:
        obj = _object(value)
        return End(type=_required(obj, 'type', _const('end')), id=_required(obj, 'id', _string), reason=_required(obj, 'reason', _enum(('eos', 'error', 'preempted', 'stopped'))), message=_optional(obj, 'message', _string), milliComputeUnits=_optional(obj, 'milliComputeUnits', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['reason'] = _dump(self.reason)
        if self.message is not None:
            out['message'] = _dump(self.message)
        if self.milliComputeUnits is not None:
            out['milliComputeUnits'] = _dump(self.milliComputeUnits)
        return out



@dataclass(frozen=True)
class Error:
    type: Literal['error']
    error: str
    message: str
    id: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Error:
        obj = _object(value)
        return Error(type=_required(obj, 'type', _const('error')), id=_optional(obj, 'id', _string), error=_required(obj, 'error', _string), message=_required(obj, 'message', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        if self.id is not None:
            out['id'] = _dump(self.id)
        out['error'] = _dump(self.error)
        out['message'] = _dump(self.message)
        return out



@dataclass(frozen=True)
class GetGraph:
    type: Literal['getGraph']
    id: str
    format: Literal['dot', 'png', 'pdf']
    verbose: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GetGraph:
        obj = _object(value)
        return GetGraph(type=_required(obj, 'type', _const('getGraph')), id=_required(obj, 'id', _string), format=_required(obj, 'format', _enum(('dot', 'png', 'pdf'))), verbose=_optional(obj, 'verbose', _boolean), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['format'] = _dump(self.format)
        if self.verbose is not None:
            out['verbose'] = _dump(self.verbose)
        return out



@dataclass(frozen=True)
class InferenceComponent:
    type: Literal['inference']
    ability: str | None = None
    abilityUuid: str | None = None
    params: Mapping[str, Any] | None = None
    id: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> InferenceComponent:
        obj = _object(value)
        return InferenceComponent(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), params=_optional(obj, 'params', _free), type=_required(obj, 'type', _const('inference')), id=_optional(obj, 'id', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        if self.params is not None:
            out['params'] = _dump(self.params)
        out['type'] = _dump(self.type)
        if self.id is not None:
            out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class Ping:
    type: Literal['ping']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Ping:
        obj = _object(value)
        return Ping(type=_required(obj, 'type', _const('ping')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class Pong:
    type: Literal['pong']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Pong:
        obj = _object(value)
        return Pong(type=_required(obj, 'type', _const('pong')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
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
        return Pop(components=_required(obj, 'components', _array(decode_popcomponent)), postTransform=_optional(obj, 'postTransform', _string), defaults=_optional(obj, 'defaults', SourceDefaults.from_json), depthMap=_optional(obj, 'depthMap', PopDepthMap.from_json), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['components'] = _dump(self.components)
        if self.postTransform is not None:
            out['postTransform'] = _dump(self.postTransform)
        if self.defaults is not None:
            out['defaults'] = _dump(self.defaults)
        if self.depthMap is not None:
            out['depthMap'] = _dump(self.depthMap)
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
        return PopDepthMap(ability=_optional(obj, 'ability', _string), abilityUuid=_optional(obj, 'abilityUuid', _string), toWorld=_optional(obj, 'toWorld', _boolean), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.ability is not None:
            out['ability'] = _dump(self.ability)
        if self.abilityUuid is not None:
            out['abilityUuid'] = _dump(self.abilityUuid)
        if self.toWorld is not None:
            out['toWorld'] = _dump(self.toWorld)
        return out



@dataclass(frozen=True)
class Prediction:
    type: Literal['prediction']
    id: str
    prediction: Mapping[str, Any]
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Prediction:
        obj = _object(value)
        return Prediction(type=_required(obj, 'type', _const('prediction')), id=_required(obj, 'id', _string), prediction=_required(obj, 'prediction', _free), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['prediction'] = _dump(self.prediction)
        return out



@dataclass(frozen=True)
class Quit:
    type: Literal['quit']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Quit:
        obj = _object(value)
        return Quit(type=_required(obj, 'type', _const('quit')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class RawComponent:
    type: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RawComponent:
        obj = _object(value)
        return RawComponent(type=_required(obj, 'type', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        return out



@dataclass(frozen=True)
class Result:
    type: Literal['result']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Result:
        obj = _object(value)
        return Result(type=_required(obj, 'type', _const('result')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class Send:
    type: Literal['send']
    id: str
    credit: int
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Send:
        obj = _object(value)
        return Send(type=_required(obj, 'type', _const('send')), id=_required(obj, 'id', _string), credit=_required(obj, 'credit', _integer), member=_optional(obj, 'member', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['credit'] = _dump(self.credit)
        if self.member is not None:
            out['member'] = _dump(self.member)
        return out



@dataclass(frozen=True)
class SetPop:
    type: Literal['setPop']
    id: str
    pop: Pop
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SetPop:
        obj = _object(value)
        return SetPop(type=_required(obj, 'type', _const('setPop')), id=_required(obj, 'id', _string), pop=_required(obj, 'pop', Pop.from_json), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['pop'] = _dump(self.pop)
        return out



@dataclass(frozen=True)
class SetSourceUpload:
    contentType: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> SetSourceUpload:
        obj = _object(value)
        return SetSourceUpload(contentType=_required(obj, 'contentType', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['contentType'] = _dump(self.contentType)
        return out



@dataclass(frozen=True)
class SetSource:
    type: Literal['setSource']
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
        return SetSource(type=_required(obj, 'type', _const('setSource')), id=_required(obj, 'id', _string), url=_optional(obj, 'url', _string), assetUuid=_optional(obj, 'assetUuid', _string), upload=_optional(obj, 'upload', SetSourceUpload.from_json), group=_optional(obj, 'group', _array(decode_groupmember)), params=_optional(obj, 'params', _array(ComponentParams.from_json)), fps=_optional(obj, 'fps', _string), roi=_optional(obj, 'roi', decode_roi), camera=_optional(obj, 'camera', Camera.from_json), live=_optional(obj, 'live', _boolean), mode=_optional(obj, 'mode', _enum(('queue', 'preempt'))), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        if self.url is not None:
            out['url'] = _dump(self.url)
        if self.assetUuid is not None:
            out['assetUuid'] = _dump(self.assetUuid)
        if self.upload is not None:
            out['upload'] = _dump(self.upload)
        if self.group is not None:
            out['group'] = _dump(self.group)
        if self.params is not None:
            out['params'] = _dump(self.params)
        if self.fps is not None:
            out['fps'] = _dump(self.fps)
        if self.roi is not None:
            out['roi'] = _dump(self.roi)
        if self.camera is not None:
            out['camera'] = _dump(self.camera)
        if self.live is not None:
            out['live'] = _dump(self.live)
        if self.mode is not None:
            out['mode'] = _dump(self.mode)
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
        return SourceDefaults(camera=_optional(obj, 'camera', Camera.from_json), fps=_optional(obj, 'fps', _string), roi=_optional(obj, 'roi', decode_roi), motionDetect=_optional(obj, 'motionDetect', _boolean), motionSensitivity=_optional(obj, 'motionSensitivity', _number), motionThreshold=_optional(obj, 'motionThreshold', _number), motionGap=_optional(obj, 'motionGap', _integer), motionGridX=_optional(obj, 'motionGridX', _integer), motionGridY=_optional(obj, 'motionGridY', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        if self.camera is not None:
            out['camera'] = _dump(self.camera)
        if self.fps is not None:
            out['fps'] = _dump(self.fps)
        if self.roi is not None:
            out['roi'] = _dump(self.roi)
        if self.motionDetect is not None:
            out['motionDetect'] = _dump(self.motionDetect)
        if self.motionSensitivity is not None:
            out['motionSensitivity'] = _dump(self.motionSensitivity)
        if self.motionThreshold is not None:
            out['motionThreshold'] = _dump(self.motionThreshold)
        if self.motionGap is not None:
            out['motionGap'] = _dump(self.motionGap)
        if self.motionGridX is not None:
            out['motionGridX'] = _dump(self.motionGridX)
        if self.motionGridY is not None:
            out['motionGridY'] = _dump(self.motionGridY)
        return out



@dataclass(frozen=True)
class Start:
    type: Literal['start']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Start:
        obj = _object(value)
        return Start(type=_required(obj, 'type', _const('start')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class StopSource:
    type: Literal['stopSource']
    id: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> StopSource:
        obj = _object(value)
        return StopSource(type=_required(obj, 'type', _const('stopSource')), id=_required(obj, 'id', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        return out



@dataclass(frozen=True)
class Uploaded:
    type: Literal['uploaded']
    id: str
    member: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Uploaded:
        obj = _object(value)
        return Uploaded(type=_required(obj, 'type', _const('uploaded')), id=_required(obj, 'id', _string), member=_optional(obj, 'member', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        if self.member is not None:
            out['member'] = _dump(self.member)
        return out



@dataclass(frozen=True)
class Usage:
    type: Literal['usage']
    id: str
    milliComputeUnits: int
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> Usage:
        obj = _object(value)
        return Usage(type=_required(obj, 'type', _const('usage')), id=_required(obj, 'id', _string), milliComputeUnits=_required(obj, 'milliComputeUnits', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['id'] = _dump(self.id)
        out['milliComputeUnits'] = _dump(self.milliComputeUnits)
        return out



@dataclass(frozen=True)
class GroupMemberUrl:
    url: str
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GroupMemberUrl:
        obj = _object(value)
        return GroupMemberUrl(url=_required(obj, 'url', _string), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
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
        return GroupMemberUploadUpload(contentType=_required(obj, 'contentType', _string), bytes=_optional(obj, 'bytes', _integer), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['contentType'] = _dump(self.contentType)
        if self.bytes is not None:
            out['bytes'] = _dump(self.bytes)
        return out



@dataclass(frozen=True)
class GroupMemberUpload:
    upload: GroupMemberUploadUpload
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> GroupMemberUpload:
        obj = _object(value)
        return GroupMemberUpload(upload=_required(obj, 'upload', GroupMemberUploadUpload.from_json), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['upload'] = _dump(self.upload)
        return out



@dataclass(frozen=True)
class RoiRectangle:
    type: Literal['rectangle']
    x: float
    y: float
    width: float
    height: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiRectangle:
        obj = _object(value)
        return RoiRectangle(type=_required(obj, 'type', _const('rectangle')), x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), width=_required(obj, 'width', _number), height=_required(obj, 'height', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['x'] = _dump(self.x)
        out['y'] = _dump(self.y)
        out['width'] = _dump(self.width)
        out['height'] = _dump(self.height)
        return out



@dataclass(frozen=True)
class RoiContourPoint:
    x: float
    y: float
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiContourPoint:
        obj = _object(value)
        return RoiContourPoint(x=_required(obj, 'x', _number), y=_required(obj, 'y', _number), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['x'] = _dump(self.x)
        out['y'] = _dump(self.y)
        return out



@dataclass(frozen=True)
class RoiContour:
    type: Literal['contour']
    points: list[RoiContourPoint]
    raw: Mapping[str, Any] = field(default_factory=dict[str, Any], compare=False, repr=False)

    @staticmethod
    def from_json(value: Any) -> RoiContour:
        obj = _object(value)
        return RoiContour(type=_required(obj, 'type', _const('contour')), points=_required(obj, 'points', _array(RoiContourPoint.from_json)), raw=obj)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.raw)
        out['type'] = _dump(self.type)
        out['points'] = _dump(self.points)
        return out



@dataclass(frozen=True)
class UnknownCommand:
    raw: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)


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
    try:
        return _dispatch(value, _COMMAND_VARIANTS)
    except ValueError:
        return UnknownCommand(cast(dict[str, Any], value) if isinstance(value, dict) else {})



_GROUPMEMBER_VARIANTS: _Variants = [
    (_key('url'), GroupMemberUrl.from_json),
    (_key('upload'), GroupMemberUpload.from_json),
]

GroupMember = GroupMemberUrl | GroupMemberUpload


def decode_groupmember(value: Any) -> GroupMember:
    return _dispatch(value, _GROUPMEMBER_VARIANTS)



@dataclass(frozen=True)
class UnknownMessage:
    raw: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return dict(self.raw)


_MESSAGE_VARIANTS: _Variants = [
    (_tag('result'), Result.from_json),
    (_tag('send'), Send.from_json),
    (_tag('credit'), Credit.from_json),
    (_tag('start'), Start.from_json),
    (_tag('prediction'), Prediction.from_json),
    (_tag('dropped'), Dropped.from_json),
    (_tag('usage'), Usage.from_json),
    (_tag('end'), End.from_json),
    (_tag('done'), Done.from_json),
    (_tag('pong'), Pong.from_json),
    (_tag('error'), Error.from_json),
]

Message = Result | Send | Credit | Start | Prediction | Dropped | Usage | End | Done | Pong | Error | UnknownMessage


def decode_message(value: Any) -> Message:
    try:
        return _dispatch(value, _MESSAGE_VARIANTS)
    except ValueError:
        return UnknownMessage(cast(dict[str, Any], value) if isinstance(value, dict) else {})



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

