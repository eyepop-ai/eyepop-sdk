import generate
from conftest import ping


def test_a_schema_the_generator_rejects_fails_with_one_error_line(monkeypatch, capsys):
    body = ping()
    body["patternProperties"] = {"^x": {}}
    monkeypatch.setattr(generate, "load_schemas", lambda path: {"ping": body})

    assert generate.main(["--check"]) == 1

    assert capsys.readouterr().err == "error: ping.json#: `patternProperties` is not supported here\n"
