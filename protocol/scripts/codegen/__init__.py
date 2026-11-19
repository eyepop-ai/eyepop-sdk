import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from .model import parse
from .python import emit as emit_python
from .rust import emit as emit_rust


def generate(schemas: Mapping[str, dict], roots: Sequence[str]) -> dict[str, str]:
    model = parse(schemas, roots)
    return {"python": emit_python(model), "rust": emit_rust(model)}


def load_schemas(directory: Path) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))}
