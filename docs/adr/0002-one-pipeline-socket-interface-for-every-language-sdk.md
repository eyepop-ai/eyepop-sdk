# One pipeline socket interface for every Language SDK

Every Language SDK exposes the same public interface for the pipeline API, over its WebSocket only. The interface is written once, in language-neutral form, in [`docs/sdk-interface.md`](../sdk-interface.md). The wire protocol is defined once as JSON Schema in `protocol/`, and shared conformance transcripts in `conformance/` are replayed by every SDK's tests. A language differs from another in casing and in how it reports failure, nothing else. The C# SDK is built first and proves the contract.

This is a clean break from the old Python and Node SDKs (`WorkerEndpoint`, sessions, `predict()` loops, ~15 environment variables). No code is carried over and no old variable keeps its meaning.

## Decisions

- **Only the pipeline socket.** `GET /api/v1/pipeline` and its commands. No `POST /api/v1/pipeline` (a single image goes up as a combined upload), no Data API, no compute sessions, no WHIP and no reconnect supervision in v1. Each can come back as its own contract.
- **Values, a pure core and a thin shell.** Immutable values; a pure core (`encode`, `decode`, `step`) that does no IO; a shell that owns the socket and the one HTTP call. This is what makes five SDKs testable the same way, with no sockets in unit tests.
- **A Job per Source.** `setSource` returns a Job, because both old SDKs showed users think per source. A Job is a pure demux of the Session's one ordered message stream, which stays public.
- **One Session is one socket and one pipeline.** The server gives each socket a pipeline of its own (spec 019). Pooling sockets, as the old SDKs did with four, is an optimization to discuss later, not part of v1.
- **The pop is fixed when the Session opens.** The old SDKs kept it as mutable endpoint-wide state. Different pops are different Sessions; `setPop` exists because the wire has it and applies to the whole socket.
- **Ability and Pop are typed, first-class and contain each other.** The server has no machine-readable schema for them (its Go code parses components by hand), so we author it. Kinds we have not typed pass through as raw JSON, and every typed value keeps its raw JSON.
- **Predictions are typed, with nothing dropped.** The model is generated from the schema with every field optional, and the original JSON stays reachable.
- **The API key is always exchanged.** The pipeline API takes only a JWT and refuses to start with any credential of its own. `Config` holds an `Auth` that is either an exchange (an auth URL and an API key) or anonymous, which exists only where there is no auth URL, such as `local`. There is no access-token credential. The token is a short-lived value that is never cached or shared between Sessions.
- **Environments are a lookup table, and the environment is an argument.** `EYEPOP_ENV` selects a row of pipeline URL and auth URL; `EYEPOP_URL` and `EYEPOP_AUTH_URL` override each; `EYEPOP_API_KEY` is the only credential variable. Reading is a pure function over a map the caller passes in. Nothing in the core reads the process environment. No YAML or other file loading in v1.
- **Backpressure is real.** The pump reads the socket only while a consumer pulls, with a bounded buffer per Job, so pressure reaches the server, which already handles slow clients per its contract.
- **Names are the wire names.** `setPop`, `setSource`, `stopSource`, `getGraph`, `ping`; `result`, `send`, `credit`, `start`, `prediction`, `dropped`, `usage`, `end`, `done`, `pong`, `error`. A change to the socket contract maps mechanically into every SDK.
- **Errors share a taxonomy, not a mechanism.** The same kinds and fields everywhere, reported as exceptions in C#, Python and Node, `Result` in Rust and `(value, error)` in Go. `decode` never throws.

## Why

Both old SDKs drifted apart (different result readers, error names, environment variables and exports) and both carry a deprecated session flow. A predictable cross-language interface needs one written contract and tests that every language must pass, not five SDKs designed independently.

## Considered and rejected

- **Port the old interface per language.** It is built around sessions and an endpoint-wide mutable pop, and it differs between Python and Node.
- **A class-based `EyePopClient` as in the pipeline API's spec 012 contract.** It predates the command socket (spec 019) and reads no environment variable; this decision replaces it for the SDKs. The contract lives in `eyepop-instance`, so that repository should note the change.
- **Generate everything with an off-the-shelf tool.** Generators flatten discriminated unions: Modelina merges the branches, and typify emits untagged unions unless every branch pins a `const` tag. We generate the structs with a tool and expect to generate the two unions (`Message`, `Command`) with a small script. A spike on C# plus one more language decides this before the generator is committed to.
- **Unbounded per-job buffers.** They hide a slow consumer from the server and grow without limit, which is what the old Node SDK did.

## Consequences

- The Python and Node scaffolds in this repository follow the same contract. Nothing in the old SDKs is a constraint.
- `protocol/` and `conformance/` become shared assets that every SDK's CI runs against. The schema is authored here first and proposed to `eyepop-instance` to own afterwards.
- `EYEPOP_URL` meant the compute URL in the old SDKs and now means the pipeline URL. A leftover value would point the socket at the wrong service, so the release notes say so.
