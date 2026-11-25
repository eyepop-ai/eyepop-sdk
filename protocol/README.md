# Pipeline socket protocol

JSON Schema (draft 2020-12) for the messages on the pipeline socket: `GET /api/v1/pipeline`, subprotocol `eyepop.v1`. Every Language SDK generates its wire types from it.

- Property and type names are the wire names. Languages rename them when they generate code.
- Every command and message pins `type` with `const`, so a generator can build a tagged union. `command.json` and `message.json` are the two unions.
- Every command has a non-empty string `id` chosen by the client. A server message echoes it.
- Commands and the `Pop`, `SourceDefaults`, `Camera` and `roi` values are closed. Server messages are open, so a field the server adds does not break a client.
- An `inference` component is typed (one of `ability` or `abilityUuid`, plus `params`). Any other component kind passes through as raw JSON.
- The `error` code is an open string. Clients accept codes they do not know.
- Wire values follow rules the schemas cannot state, defined once in `scripts/codegen/model.py` (`WIRE`, `WIRE_RULES`) and applied by every generated decoder, even where the schema alone would accept the value:
  - An `integer` is an int64: its exact decimal value is whole and lies from -2^63 to 2^63-1, however it is written (`1.0` and `1e3` are integers; `1.00000000000000001` and `1e19` are not). The schemas say only `integer`, and a `maximum` is not modelled.
  - A `number` is finite as a double: `1e400` is rejected.
  - `minLength` counts Unicode code points.
  - A value nests at most 64 levels (the message object is level 1). A union decoder returns `Unknown` with no fields for anything deeper.
  - When an object repeats a key, the last value wins.
  - A string or key holding a lone surrogate is not valid text. A union decoder returns `Unknown` keeping every field.

- `public.json` lists, by schema file name, the types a caller of an SDK may see. Every other type is internal in a language that has the notion; today only the C# generator applies it (`internal`), and the other languages emit everything public. A listed type also makes public the types it holds and the union it belongs to, so a public type never exposes an internal one. A name that is not a schema fails generation. `reconnecting` and `reconnected` are not here: they exist only in the SDKs.
- A variant's schema file need not be named for its `type` tag: `predictionMessage.json` and `errorMessage.json` hold the `prediction` and `error` messages, named so that `Prediction` and `Error` stay free for other types.

## Examples

`examples/valid` must pass and `examples/invalid` must fail. A file name starts with `command-` or `message-`, which picks the union it is checked against. `examples/invalid/expected.json` names where and by which keyword each invalid example fails.

`examples/decoding.json` is the conformance set every Language SDK replays through its generated decoder. It has one case per example file (`file`) plus edge cases written as JSON text (`name` and `text`). Each case names its `union`, the `variant` it decodes to (a `type` tag, or `Unknown`), whether it encodes back `unchanged` (numbers compared by exact value), and optionally a number token the output `keeps`. A case whose decoder outcome differs from the schema states the `reason`: an invalid example decoders accept, or a schema-valid text case they reject, such as an integer beyond int64. `diverges` maps a language (`python`, `rust`, `go`, `csharp`) to why that SDK does not give the stated outcome: a known divergence still to fix, or a documented limit of its host JSON parser (the reason starts with "Documented limit"). That SDK's replay fails if the case starts passing, so whoever fixes it removes the marker.

The edge cases cover integer forms and the int64 bounds (including the maximum written four other ways), a non-finite number, `number` fields holding decimals a double cannot hold, a duplicate key (also beside a U+FFFD or a lone surrogate), a lone surrogate, a character outside the Basic Multilingual Plane, and values nested 64, 65, 601 and 5001 levels deep. The Python replay reads text with `json.loads(text, parse_float=Decimal)`, which its decoders handle exactly; a Python caller also passes a `parse_constant` that raises, because `json.loads` accepts `NaN` and `Infinity`, and treats `ValueError` (also raised for an integer over 4,300 digits), `ArithmeticError` (`decimal.InvalidOperation` on an exponent such as `0e999999999999999999999`) and `RecursionError` (very deep nesting) from `json.loads` as text that is not a message. The cases serde_json rounds or refuses before the Rust decoder sees them, the lone surrogates Go's `encoding/json` replaces with U+FFFD, and the lone surrogates System.Text.Json writes back as U+FFFD, are documented limits; [ADR 0003](../docs/adr/0003-one-in-repo-generator-writes-the-protocol-types.md) lists them.

```sh
devbox run -- task protocol:check
```

## Generated types

`task protocol:generate` writes the types into each Language SDK from these schemas, and `task protocol:generate:check` fails when a generated file is stale. Run the first after any schema change and commit the result. Never edit a generated file. A keyword or shape the generator cannot express, or two generated types with one name, fails generation with the file, the path and the keyword. So does a union whose variants the decoders cannot tell apart. A tagged variant must require its `type` const, and no two may share one. At most one variant may have an open `type`, and it must exclude every sibling's tag (`not: {"const": ...}` on a string, or an `enum` without it). Any other variant is picked by the first key, by name, that it requires and no other variant has as a property, and then every variant in the union must set `additionalProperties: false`. A value holding the selector keys of two keyed variants decodes as `Unknown`. A variant listed twice fails too. Decoders try tagged and keyed variants in schema order, and the open-`type` variant last. This assumes the schemas pass the meta-schema check in `task protocol:validate`. A property name must be a plain identifier (`[A-Za-z][A-Za-z0-9_]*`), and generation fails when two property names, or two enum values, become one identifier in any language after its casing and keyword rules, or when one becomes a name the generated code already uses (such as `raw`). A keyword gets another identifier only in that language (Python `from_`, Rust `r#for` or `self_`) and keeps its wire key. A `const` property key is exempt from the identifier rule (`x-kind` is fine). Instead, a `const` key, a `const` value and an enum value must not hold a quote (`"` or `'`), a backslash or a character that is not printable, because the generated code writes them into string literals as they are. An inline union variant must give a type name that is an identifier (a tag `get-graph` fails). Other type names are not checked yet. Decoders ignore `additionalProperties: true|false` and a `not: {"const": ...}` on a string (the generator reads them only for the union rules), so they accept more than the schema allows: they keep unknown fields even on a closed object. [ADR 0003](../docs/adr/0003-one-in-repo-generator-writes-the-protocol-types.md) has the rules.

## Binary frames

JSON Schema cannot describe these. Every binary message starts with one kind byte.

| Kind | Layout |
|---|---|
| `0x01` chunk | `[0x01][media bytes]` |
| `0x02` combined | `[0x02][header length: 4 bytes, big endian][header: a setSource command, UTF-8 JSON][media bytes]` |

## Out of scope

Prediction, WHIP, and the one-image POST.
