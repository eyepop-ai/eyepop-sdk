from conftest import missing_id, schema, valid_ping
from validate import Failure, check


def test_an_invalid_example_rejected_for_another_rule_fails(make_root):
    root = make_root(
        valid=valid_ping(),
        invalid=missing_id(),
        expected={"command-ping-missing-id.json": {"path": "", "keyword": "enum"}},
    )

    assert check(root) == [Failure("invalid/command-ping-missing-id.json", "wrong_rule")]


def test_an_invalid_example_rejected_for_its_expected_rule_passes(make_root):
    root = make_root(
        valid=valid_ping(),
        invalid=missing_id(),
        expected={"command-ping-missing-id.json": {"path": "", "keyword": "required"}},
    )

    assert check(root) == []


def test_an_invalid_example_with_no_expected_rule_fails(make_root):
    root = make_root(valid=valid_ping(), invalid=missing_id(), expected={})

    assert check(root) == [Failure("invalid/command-ping-missing-id.json", "no_expectation")]


def test_an_expected_rule_for_a_missing_example_fails(make_root):
    root = make_root(
        valid=valid_ping(),
        invalid=missing_id(),
        expected={
            "command-ping-missing-id.json": {"path": "", "keyword": "required"},
            "command-ping-gone.json": {"path": "", "keyword": "required"},
        },
    )

    assert check(root) == [Failure("invalid/command-ping-gone.json", "stale_expectation")]


def test_an_invalid_example_is_checked_against_the_variant_its_tag_names_whatever_the_file_is_called(make_root):
    root = make_root(
        schemas={
            "ping": schema("ping", {"type": "object"}),
            "pingMessage": schema("pingMessage", {"type": "object", "properties": {"type": {"const": "ping"}, "id": {"type": "string"}}, "required": ["type", "id"]}),
            "command": schema("command", {"oneOf": [{"$ref": "pingMessage.json"}]}),
        },
        valid=valid_ping(),
        invalid=missing_id(),
        expected={"command-ping-missing-id.json": {"path": "", "keyword": "required"}},
    )

    assert check(root) == []


def test_a_variant_missing_from_its_union_fails(make_root):
    root = make_root(
        schemas={"pong": schema("pong", {"type": "object", "properties": {"type": {"const": "pong"}}, "required": ["type"]})},
        valid=valid_ping(),
    )

    assert check(root) == [Failure("schema/pong.json", "unreachable")]


def test_a_typed_schema_reached_through_another_schema_passes(make_root):
    root = make_root(
        schemas={
            "wrapper": schema("wrapper", {"type": "object", "properties": {"inner": {"$ref": "inner.json"}}}),
            "inner": schema("inner", {"type": "object", "properties": {"type": {"const": "inner"}}}),
            "ping": schema(
                "ping",
                {
                    "type": "object",
                    "properties": {"type": {"const": "ping"}, "id": {"type": "string"}, "w": {"$ref": "wrapper.json"}},
                    "required": ["type", "id"],
                },
            ),
        },
        valid=valid_ping(),
    )

    assert check(root) == []


def test_a_union_member_with_no_schema_file_fails(make_root):
    root = make_root(
        schemas={"command": schema("command", {"oneOf": [{"$ref": "ping.json"}, {"$ref": "ghost.json"}]})},
        valid=valid_ping(),
    )

    assert check(root) == [Failure("schema/ghost.json", "missing_variant")]


def test_a_variant_in_both_unions_fails(make_root):
    root = make_root(schemas={"message": schema("message", {"oneOf": [{"$ref": "ping.json"}]})}, valid=valid_ping())

    assert check(root) == [Failure("schema/ping.json", "in_two_unions")]


def test_an_invalid_example_the_variant_accepts_but_the_union_rejects_is_attributed_to_the_union(make_root):
    root = make_root(
        schemas={
            "loose": schema("loose", {"type": "object"}),
            "command": schema("command", {"oneOf": [{"$ref": "ping.json"}, {"$ref": "loose.json"}]}),
        },
        valid={},
        invalid={"command-ping-overlap.json": {"type": "ping", "id": "p1"}},
        expected={"command-ping-overlap.json": {"path": "", "keyword": "oneOf"}},
    )

    assert check(root) == []


def test_a_schema_that_breaks_the_metaschema_fails(make_root):
    root = make_root(schemas={"bad": schema("bad", {"type": 5})}, valid=valid_ping())

    assert check(root) == [Failure("schema/bad.json", "invalid_schema")]
