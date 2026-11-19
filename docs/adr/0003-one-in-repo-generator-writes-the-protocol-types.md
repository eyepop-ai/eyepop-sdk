# One in-repo generator writes the protocol types for every Language SDK

The types for the pipeline socket are generated from `protocol/schema` by one script, `protocol/scripts/generate.py`, with one emitter per language: Python, Rust, Go and C#. The generated files are committed. This settles the spike ADR 0002 asked for.

## Decision

- **One model, four emitters.** `protocol/scripts/codegen` reads the schemas into a small model (objects, unions, enums, arrays, free JSON), and each emitter writes one file in its language's idiom. Output is deterministic.
- **Same behavior everywhere.** Every type has a decode and an encode (`from_json`/`to_json`, `FromJSON`/`ToJSON`). A value keeps its original JSON, and unknown fields survive a round trip. A constant such as `"type": "ping"` is checked on decode and written on encode, and is not a field. `Message` and `Command` decode by their `type` tag, and a known tag that does not parse, or an unknown one, decodes to an `Unknown` variant that keeps its JSON. Decoding the two unions never fails.
- **Only the standard library**, plus `serde_json` in Rust. The Python SDK has no dependencies, so the generated Python uses dataclasses.
- **Generated files are committed and never edited.** `task protocol:generate` rewrites them; `task protocol:generate:check` fails when they differ from what the schemas produce, and runs in the protocol gate. Hand-written code sits beside them.
- **Each SDK replays one conformance set.** Every language's own test suite decodes each case in `protocol/examples/decoding.json` (every valid and invalid example, plus edge-case JSON text) through its generated decoder, and checks the variant it decodes to and whether it encodes back unchanged. A case one SDK gets wrong carries a known-divergence marker for that language, and the replay fails once the marker is no longer needed. A Language SDK's CI also runs when `protocol/**` changes.

## Considered and rejected

The spike ran each tool on the bundled schemas.

| Tool | Result |
|---|---|
| datamodel-code-generator (Python) | Good structs and real unions, but needs pydantic, and drops the raw JSON. |
| typify (Rust) | Good structs, `#[serde(untagged)]` unions, panics on the `not` keyword, drops the raw JSON. |
| go-jsonschema (Go) | Unions and the `type` constant become `interface{}`. |
| quicktype (all four) | Flattens every variant of a union into one struct with all fields optional. |
| NSwag / NJsonSchema (C#) | Fails on `$defs` references, and then on the root schema. |

Using the tools for structs and a script for the unions would leave four different pipelines, none of which keeps the raw JSON. One generator, with the behavior above written once, is smaller than that.

## Consequences

- A schema construct the generator does not know fails the generate task. Before any emitter runs, the model checks each schema file. A keyword must be modelled, an annotation (`$schema`, `$id`, `title`, `description`, `$comment`, `examples`, `deprecated`, `default`, `readOnly`, `writeOnly`), or one of two ignored forms, each with its reason recorded in the model:
  - `additionalProperties: true` or `false`, because decoders are tolerant readers that keep unknown fields.
  - `not: {"const": "<string>"}` on a string property, as in `rawComponent`. A union tries its tagged variants first, so through the union a value with the excluded tag never reaches that variant.

  Any other keyword or form, or a shape the model cannot express (a `type` array, an inline `oneOf` on a property, a boolean schema, an empty `enum`, a `$ref` or `allOf` cycle), fails with the schema file, the path inside it and the keyword. Two generated types with the same name (objects, enums and unions) fail with both sources. A new construct needs a change to the model and each emitter, with a test.
- The check assumes the schemas already pass the JSON Schema meta-schema check that `validate.py` runs in `task protocol:check`; a malformed keyword value can still crash the generator. It does not yet check that names are valid identifiers in each language, or that two names stay distinct after a language's casing rules.
- Decoders accept more than the schema allows. They keep fields a closed object does not name, and a variant decoded on its own does not check `not`. The schema and `task protocol:validate` stay the strict contract.
- Adding a language is one emitter, a round-trip test and a target in `generate.py`.
- Schema changes show up as diffs in four generated files, reviewed with the schema change.
