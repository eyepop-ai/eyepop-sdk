import json
from pathlib import Path

import pytest

from codegen import generate, load_schemas
from conftest import load_python

ROOT = Path(__file__).parent.parent
CASES = json.loads((ROOT / "examples" / "decoding.json").read_text())


@pytest.fixture(scope="module")
def protocol():
    return load_python(generate(load_schemas(ROOT / "schema"), ("command", "message"))["python"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_a_decoding_case_is_known_or_unknown_and_keeps_exact_numbers(protocol, case):
    decode = getattr(protocol, f"decode_{case['union']}")

    value = decode(json.loads(case["text"]))

    assert (not type(value).__name__.startswith("Unknown")) == case["known"]
    if "keeps" in case:
        assert case["keeps"] in json.dumps(value.to_json())
