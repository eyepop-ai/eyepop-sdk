import json
from pathlib import Path

import pytest

BASE = "https://schemas.example/v1/"


def schema(name: str, body: dict) -> dict:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}{name}.json", **body}


def ping() -> dict:
    return schema(
        "ping",
        {
            "type": "object",
            "properties": {"type": {"const": "ping"}, "id": {"type": "string"}},
            "required": ["type", "id"],
            "additionalProperties": False,
        },
    )


def valid_ping() -> dict:
    return {"command-ping.json": {"type": "ping", "id": "p1"}}


def missing_id() -> dict:
    return {"command-ping-missing-id.json": {"type": "ping"}}


@pytest.fixture
def make_root(tmp_path):
    def build(schemas=None, valid=None, invalid=None, expected=None) -> Path:
        files = {
            "command": schema("command", {"oneOf": [{"$ref": "ping.json"}]}),
            "message": schema("message", {"type": "object"}),
            "ping": ping(),
            **(schemas or {}),
        }
        for name, body in files.items():
            write(tmp_path / "schema" / f"{name}.json", body)
        for folder, examples in (("valid", valid), ("invalid", invalid)):
            (tmp_path / "examples" / folder).mkdir(parents=True, exist_ok=True)
            for name, body in (examples or {}).items():
                write(tmp_path / "examples" / folder / name, body)
        if expected is not None:
            write(tmp_path / "examples" / "invalid" / "expected.json", expected)
        return tmp_path

    return build


def write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


def load_python(source: str):
    import sys
    import types

    module = types.ModuleType("generated_protocol")
    sys.modules[module.__name__] = module
    exec(compile(source, "generated_protocol.py", "exec"), module.__dict__)
    return module
