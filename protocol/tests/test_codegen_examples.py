import json
from pathlib import Path

import pytest

from codegen import generate, load_schemas
from conftest import load_python

ROOT = Path(__file__).parent.parent
EXAMPLES = sorted((ROOT / "examples" / "valid").glob("*.json"))


@pytest.fixture(scope="module")
def protocol():
    schemas = load_schemas(ROOT / "schema")
    return load_python(generate(schemas, ("command", "message"))["python"])


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_a_valid_example_decodes_to_a_known_variant_and_encodes_back_unchanged(protocol, example):
    data = json.loads(example.read_text())
    decode = getattr(protocol, f"decode_{example.name.split('-')[0]}")

    value = decode(data)

    assert not type(value).__name__.startswith("Unknown")
    assert value.to_json() == data
