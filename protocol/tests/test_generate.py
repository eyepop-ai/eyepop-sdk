import generate
import pytest
from codegen import SchemaError, load_schemas
from conftest import ping


def test_a_schema_the_generator_rejects_fails_with_one_error_line(monkeypatch, capsys):
    body = ping()
    body["patternProperties"] = {"^x": {}}
    monkeypatch.setattr(generate, "load_schemas", lambda path: {"ping": body})

    assert generate.main(["--check"]) == 1

    assert capsys.readouterr().err == "error: ping.json#: `patternProperties` is not supported here\n"


def test_a_schema_file_that_is_not_json_is_named_in_the_error(tmp_path):
    (tmp_path / "broken.json").write_text('{"title": ')

    with pytest.raises(SchemaError, match="^broken.json: Expecting value"):
        load_schemas(tmp_path)


def test_an_error_that_is_not_about_a_schema_keeps_its_traceback(monkeypatch):
    def fail(schemas, roots, public):
        raise ValueError("emitter bug")

    monkeypatch.setattr(generate, "generate", fail)

    with pytest.raises(ValueError, match="emitter bug"):
        generate.main(["--check"])
