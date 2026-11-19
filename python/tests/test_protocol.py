import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from eyepop.protocol import UnknownCommand, UnknownMessage, decode_command, decode_message

EXAMPLES = Path(__file__).resolve().parents[2] / "protocol" / "examples"
CASES: list[dict[str, Any]] = json.loads((EXAMPLES / "decoding.json").read_text())


def case_id(case: dict[str, Any]) -> str:
    return case.get("file") or case["name"]


def exact(text: str) -> Any:
    return json.loads(text, parse_float=Decimal)


def dumps(value: Any) -> str:
    if isinstance(value, dict):
        obj = cast(dict[str, Any], value)
        return "{" + ",".join(f"{json.dumps(key)}:{dumps(item)}" for key, item in obj.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(dumps(item) for item in cast(list[Any], value)) + "]"
    if isinstance(value, Decimal):
        return str(value)
    return json.dumps(value, allow_nan=False)


def same(a: Any, b: Any) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        x, y = cast(dict[str, Any], a), cast(dict[str, Any], b)
        return x.keys() == y.keys() and all(same(x[key], y[key]) for key in x)
    if isinstance(a, list) and isinstance(b, list):
        x, y = cast(list[Any], a), cast(list[Any], b)
        return len(x) == len(y) and all(same(i, j) for i, j in zip(x, y, strict=True))
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    return a == b


def problem(case: dict[str, Any]) -> str | None:
    text = (EXAMPLES / case["file"]).read_text() if "file" in case else case["text"]
    decode = decode_command if case["union"] == "command" else decode_message
    value = decode(exact(text))
    encoded = dumps(value.to_json())
    unknown = isinstance(value, UnknownCommand | UnknownMessage)
    variant = "Unknown" if unknown else value.to_json()["type"]
    if variant != case["variant"]:
        return f"decoded to {variant}, want {case['variant']}"
    if same(exact(encoded), exact(text)) != case["unchanged"]:
        return f"encoded {encoded}, want unchanged = {case['unchanged']}"
    if case.get("keeps", "") not in encoded:
        return f"encoded {encoded}, want it to contain {case['keeps']}"
    return None


def test_the_decoding_cases_are_found():
    assert len(CASES) > 60


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_a_decoding_case_has_its_stated_outcome(case: dict[str, Any]):
    try:
        found = problem(case)
    except Exception as error:
        found = repr(error)

    reason = case.get("diverges", {}).get("python")
    if reason is not None:
        assert found is not None, f"passes but is a known Python divergence ({reason}); remove it"
    else:
        assert found is None, found
