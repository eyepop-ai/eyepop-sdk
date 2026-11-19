# Pipeline socket protocol

JSON Schema (draft 2020-12) for the messages on the pipeline socket: `GET /api/v1/pipeline`, subprotocol `eyepop.v1`. Every Language SDK generates its wire types from it.

- Property and type names are the wire names. Languages rename them when they generate code.
- Every command and message pins `type` with `const`, so a generator can build a tagged union. `command.json` and `message.json` are the two unions.
- Every command has a non-empty string `id` chosen by the client. A server message echoes it.
- Commands and the `Pop`, `SourceDefaults`, `Camera` and `roi` values are closed. Server messages are open, so a field the server adds does not break a client.
- An `inference` component is typed (one of `ability` or `abilityUuid`, plus `params`). Any other component kind passes through as raw JSON.
- The `error` code is an open string. Clients accept codes they do not know.
- An `integer` is an int64 on the wire. A decoder rejects a value outside that range even where the schema alone accepts it, because the schemas say only `integer` and a `maximum` is not modelled.

## Examples

`examples/valid` must pass and `examples/invalid` must fail. A file name starts with `command-` or `message-`, which picks the union it is checked against. `examples/invalid/expected.json` names where and by which keyword each invalid example fails.

`examples/decoding.json` is the conformance set every Language SDK replays through its generated decoder. It has one case per example file (`file`) plus edge cases written as JSON text (`name` and `text`). Each case names its `union`, the `variant` it decodes to (a `type` tag, or `Unknown`), whether it encodes back `unchanged` (numbers compared by exact value), and optionally a number token the output `keeps`. A case whose decoder outcome differs from the schema states the `reason`: an invalid example decoders accept, or a schema-valid text case they reject, such as an integer beyond int64. `diverges` maps a language (`python`, `rust`, `go`, `csharp`) to why that SDK gets the case wrong today; that SDK's replay fails if the case starts passing, so whoever fixes it removes the marker.

```sh
devbox run -- task protocol:check
```

## Generated types

`task protocol:generate` writes the types into each Language SDK from these schemas, and `task protocol:generate:check` fails when a generated file is stale. Run the first after any schema change and commit the result. Never edit a generated file. A keyword or shape the generator cannot express, or two generated types with one name, fails generation with the file, the path and the keyword. So does a union whose variants cannot be told apart: two variants with one `type` const, two with an open `type`, or a variant with neither whose every required key is a property of another variant. A variant with no `type` const or open `type` is picked by the first key, by name, that it requires and no other variant has as a property. This assumes the schemas pass the meta-schema check in `task protocol:validate`. Names that are not identifiers in a language, or that collide only after its casing rules, are not checked yet. It ignores `additionalProperties: true|false` and a `not: {"const": ...}` on a string, so decoders accept more than the schema allows: they keep unknown fields even on a closed object. [ADR 0003](../docs/adr/0003-one-in-repo-generator-writes-the-protocol-types.md) has the rules.

## Binary frames

JSON Schema cannot describe these. Every binary message starts with one kind byte.

| Kind | Layout |
|---|---|
| `0x01` chunk | `[0x01][media bytes]` |
| `0x02` combined | `[0x02][header length: 4 bytes, big endian][header: a setSource command, UTF-8 JSON][media bytes]` |

## Out of scope

Prediction, WHIP, and the one-image POST.
