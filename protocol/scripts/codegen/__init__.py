import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .model import SchemaError, parse
from . import csharp, go, python, rust

ROOTS = ("command", "message")


def generate(schemas: Mapping[str, dict], roots: Sequence[str], public: Sequence[str] | None = None) -> dict[str, str]:
    emitters = {"python": python, "rust": rust, "go": go, "csharp": csharp}
    model = parse(schemas, roots, {language: emitter.NAMING for language, emitter in emitters.items()}, public)
    return {language: emitter.emit(model) for language, emitter in emitters.items()}


def load_schemas(directory: Path) -> dict[str, dict]:
    schemas = {}
    for path in sorted(directory.glob("*.json")):
        try:
            schemas[path.stem] = json.loads(path.read_text())
        except ValueError as error:
            raise SchemaError(f"{path.name}: {error}") from error
    return schemas
