import json
from pathlib import Path

import pytest

from codegen import ROOTS
from generate import TARGETS

ROOT = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"
CASES = json.loads((EXAMPLES / "decoding.json").read_text())
FILE_CASES = [case for case in CASES if "file" in case]


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
    assert case["union"] in ROOTS
    assert isinstance(case["unchanged"], bool)
    assert set(case.get("diverges", {})) <= set(TARGETS)


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
