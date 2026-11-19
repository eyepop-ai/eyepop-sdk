# Pipeline socket protocol

JSON Schema (draft 2020-12) for the messages on the pipeline socket: `GET /api/v1/pipeline`, subprotocol `eyepop.v1`. Every Language SDK generates its wire types from it.

- Property and type names are the wire names. Languages rename them when they generate code.
- Every command and message pins `type` with `const`, so a generator can build a tagged union. `command.json` and `message.json` are the two unions.
- Every command has a non-empty string `id` chosen by the client. A server message echoes it.
- Commands and the `Pop`, `SourceDefaults`, `Camera` and `roi` values are closed. Server messages are open, so a field the server adds does not break a client.
- An `inference` component is typed (one of `ability` or `abilityUuid`, plus `params`). Any other component kind passes through as raw JSON.
- The `error` code is an open string. Clients accept codes they do not know.

## Examples

`examples/valid` must pass and `examples/invalid` must fail. A file name starts with `command-` or `message-`, which picks the union it is checked against. `examples/invalid/expected.json` names where and by which keyword each invalid example fails.

```sh
devbox run -- task protocol:check
```

## Generated types

`task protocol:generate` writes the types into each Language SDK from these schemas, and `task protocol:generate:check` fails when a generated file is stale. Run the first after any schema change and commit the result. Never edit a generated file. A keyword or shape the generator cannot express fails generation with the file, the path and the keyword. It ignores `additionalProperties` and `not`, so decoders accept more than the schema allows: they keep unknown fields even on a closed object. [ADR 0003](../docs/adr/0003-one-in-repo-generator-writes-the-protocol-types.md) has the rules.

## Binary frames

JSON Schema cannot describe these. Every binary message starts with one kind byte.

| Kind | Layout |
|---|---|
| `0x01` chunk | `[0x01][media bytes]` |
| `0x02` combined | `[0x02][header length: 4 bytes, big endian][header: a setSource command, UTF-8 JSON][media bytes]` |

## Out of scope

Prediction, WHIP, and the one-image POST.
