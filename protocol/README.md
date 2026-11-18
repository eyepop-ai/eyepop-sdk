# Pipeline socket protocol

JSON Schema (draft 2020-12) for the messages on the pipeline socket: `GET /api/v1/pipeline`, subprotocol `eyepop.v1`. Every Language SDK generates its wire types from these files.

Property names are the wire names. Languages rename them when they generate code, not here.

## Layout

| Path | What |
|---|---|
| `schema/command.json` | Every client text message. A `oneOf` of one schema per command. |
| `schema/message.json` | Every server text message. A `oneOf` of one schema per message. |
| `schema/<name>.json` | One file per type, named by its wire name (`setSource.json`, `pong.json`) or its value name (`pop.json`, `camera.json`). Each has a stable `$id` under `https://schemas.eyepop.ai/pipeline-socket/v1/`; `$ref`s are relative to it. |
| `examples/valid/` | Documents every schema must accept. |
| `examples/invalid/` | Documents every schema must reject, one per rule worth guarding. |

Every command and message variant pins `type` with `const`, so a generator can build a tagged union. Every command has a non-empty string `id`, chosen by the client; a server message echoes it.

An example file is named `command-<what>.json` or `message-<what>.json`. The prefix says which union it is checked against.

## Validate

```sh
devbox run -- task protocol:validate
```

```sh
devbox run -- task protocol:check   # test, then validate: the CI gate
```

`validate` runs `scripts/validate.py` with `uv`. It fails when:

- a valid example is rejected, or an invalid one is accepted;
- an invalid example is rejected at another place or by another keyword than `examples/invalid/expected.json` says (file name to `{path, keyword}`, checked against the variant its `type` names), has no entry there, or an entry names no example;
- a union member has no schema file, is in both unions, or has a `type` const that differs from its file name;
- a schema with a `type` const is not reachable by `$ref` from `command.json` or `message.json`.

`test` runs `tests/` against throwaway fixture schemas, so each check above is proven able to fail.

## Open and closed

- Commands are closed (`additionalProperties: false`): the SDK sends only what is defined.
- The `Pop` envelope, `SourceDefaults`, `Camera` and the `roi` shapes are closed.
- Pop components are open. An `inference` component is typed by `ability.json` (exactly one of `ability` or `abilityUuid`, plus `params`). Any other `type` (`forward`, `tracking`, `contour_finder`, `component_finder`, ...) is a raw object and passes through unchanged.
- Server messages are open: a field added by the server must not break a client.
- `prediction` in a `prediction` message is an open object. Its fields are defined in a later change.

## Binary frames

JSON Schema cannot describe these, so they are documented here. Every binary message starts with one kind byte.

| Kind | Layout | Use |
|---|---|---|
| `0x01` chunk | `[0x01][media bytes]` | Part of a chunked upload. |
| `0x02` combined | `[0x02][header length: 4 bytes, big endian][header: a setSource command, UTF-8 JSON][media bytes]` | A whole upload in one message. |

The header of a combined upload is a `setSource` command and validates against `schema/setSource.json`. Each upload member of a combined group carries `bytes`, its length.

## Error codes

The `error` field of an `error` message is an open string. Clients must accept a code not listed here. Known codes:

`invalid_request`, `subprotocol_required`, `unexpected_bytes`, `unknown_command`, `duplicate_id`, `live_source_open`, `queue_full`, `credit_exceeded`, `whip_unavailable`, `shutting_down`, `upload_stalled`, `no_caller`, `origin_not_allowed`, `too_large`, `unsupported_media_type`, `upgrade_required`, `invalid_pop`, `unsupported_pop`, `ability_unavailable`, `source_failed`, `not_a_single_image`, `overloaded`, `pipeline_start_failed`, `pipeline_stopped`, `source_timeout`, `internal_error`.

## Out of scope

Prediction (its own schema), WHIP commands and messages, and the one-image POST.
