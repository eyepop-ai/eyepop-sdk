import json
from decimal import Decimal
from pathlib import Path

import pytest

from codegen import ROOTS
from generate import TARGETS
from validate import UNIONS, load_registry, validator

ROOT = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"
CASES = json.loads((EXAMPLES / "decoding.json").read_text())
FILE_CASES = [case for case in CASES if "file" in case]
TEXT_CASES = [case for case in CASES if "text" in case]
KEYS = {"name", "file", "union", "text", "variant", "unchanged", "keeps", "reason", "diverges"}


def test_every_example_file_has_exactly_one_decoding_case():
    files = sorted(
        f"{path.parent.name}/{path.name}"
        for folder in ("valid", "invalid")
        for path in (EXAMPLES / folder).glob("*.json")
        if path.name != "expected.json"
    )

    assert sorted(case["file"] for case in FILE_CASES) == files


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.get("file") or c["name"])
def test_a_decoding_case_is_well_formed(case):
    assert ("file" in case) != ("text" in case)
    assert ("file" in case) != ("name" in case)
    assert set(case) <= KEYS
    assert all(isinstance(case[key], str) and case[key] for key in KEYS - {"unchanged", "diverges"} if key in case)
    assert case["union"] in ROOTS
    assert isinstance(case["unchanged"], bool)
    if "diverges" in case:
        diverges = case["diverges"]
        assert isinstance(diverges, dict) and diverges and set(diverges) <= set(TARGETS)
        assert all(isinstance(reason, str) and reason for reason in diverges.values())


@pytest.mark.parametrize("case", FILE_CASES, ids=lambda c: c["file"])
def test_a_file_case_is_checked_against_the_union_its_name_starts_with(case):
    assert Path(case["file"]).name.split("-")[0] == case["union"]


@pytest.mark.parametrize("case", [c for c in FILE_CASES if c["file"].startswith("valid/")], ids=lambda c: c["file"])
def test_a_valid_example_decodes_to_its_variant_and_encodes_back_unchanged(case):
    data = json.loads((EXAMPLES / case["file"]).read_text())

    assert (case["variant"], case["unchanged"]) == (data["type"], True)


@pytest.mark.parametrize("case", [c for c in FILE_CASES if c["file"].startswith("invalid/")], ids=lambda c: c["file"])
def test_an_invalid_example_a_decoder_accepts_says_why(case):
    assert case["variant"] == "Unknown" or case.get("reason")


def exact(token: str):
    value = Decimal(token)
    if value != value.to_integral_value():
        return value
    sign, digits, exponent = value.as_tuple()
    whole = int("".join(map(str, digits)))
    whole = whole * 10**exponent if exponent >= 0 else whole // 10**-exponent
    return -whole if sign else whole


@pytest.mark.parametrize("case", TEXT_CASES, ids=lambda c: c["name"])
def test_a_text_case_matches_the_schema_unless_it_says_why(case):
    instance = json.loads(case["text"], parse_float=exact)

    valid = validator(ROOT, load_registry(ROOT), UNIONS[case["union"]]).is_valid(instance)

    if case["variant"] == "Unknown":
        assert not valid or "reason" in case
    else:
        assert valid or "reason" in case
