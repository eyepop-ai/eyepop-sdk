import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

BASE = "https://schemas.example/v1/"


def schema(name: str, body: dict) -> dict:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{BASE}{name}.json", **body}


PING = schema(
    "ping",
    {
        "type": "object",
        "properties": {"type": {"const": "ping"}, "id": {"type": "string"}},
        "required": ["type", "id"],
        "additionalProperties": False,
    },
)
COMMAND = schema("command", {"oneOf": [{"$ref": "ping.json"}]})
MESSAGE = schema("message", {"oneOf": []})


@pytest.fixture
def make_root(tmp_path):
    def build(schemas=None, valid=None, invalid=None, expected=None) -> Path:
        files = {"command": COMMAND, "message": MESSAGE, "ping": PING, **(schemas or {})}
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
