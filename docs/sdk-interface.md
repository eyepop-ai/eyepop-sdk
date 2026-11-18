# The Language SDK interface: the pipeline socket

The public interface of every Language SDK, written once and without a language. Decisions and their reasons are in [ADR 0002](adr/0002-one-pipeline-socket-interface-for-every-language-sdk.md). Terms are in [`GLOSSARY.md`](../GLOSSARY.md). The wire contract is the pipeline API's socket contract in `eyepop-instance` (`specs/019-pipeline-socket-commands/contracts/socket.md`); the machine-readable form is `protocol/`.

A language renders this with its own casing (`setSource`, `SetSource`, `set_source`) and its own failure idiom. It adds no concept, and it omits none.

## Scope

The pipeline API's WebSocket, `GET /api/v1/pipeline`, and the one HTTP call that gets a token for it. Out of v1: the one-image `POST`, the Data API, WHIP commands, supervised reconnect, socket pooling.

## Values

All values are immutable. A value that holds a raw JSON field exposes it unchanged.

**Config**: what a Session needs, built once and passed in.
- `pipelineUrl`, the pipeline API root.
- `auth`, either `Exchange{authUrl, apiKey}` or `Anonymous`.
- `accountUuid`, optional, sent on the exchange so the token carries the account claim. A token without it runs the socket unbilled.

Construction refuses what cannot work: an `Exchange` without an API key, an API key without an auth URL, plain `http` to a host that is not loopback. Nothing downstream re-checks.

**Environment**: a named row of `{pipelineUrl, authUrl}`.

| name | pipelineUrl | authUrl |
|---|---|---|
| `production` (default) | `https://pipeline.eyepop.ai` | `https://compute.eyepop.ai` |
| `staging` | `https://pipeline.staging.eyepop.xyz` | `https://compute.staging.eyepop.xyz` |
| `local` | `http://127.0.0.1:9002` | none, so `Anonymous` |

**Ability**: a name or alias (`eyepop.person:latest`) or a uuid, plus `params`.

**Pop**: `components`, and optionally `defaults`, `postTransform`, `depthMap`. An inference component holds an Ability. Component kinds not yet typed are raw JSON. `ability(name, params)` builds a Pop of one inference component.

**Source**: one of `Url`, `Asset`, `Upload{contentType, content}`, `Group{members}`, with the options the socket takes: `params`, `roi`, `camera`, `fps`, `live`, `mode` (`queue` or `preempt`). A group member is a `Url` or an `Upload`, in the order the ability sees them. `content` is bytes or a byte stream, with an optional known length.

**Message**: a tagged union of everything the server sends: `result`, `send`, `credit`, `start`, `prediction`, `dropped`, `usage`, `end`, `done`, `pong`, `error`. A source ending with `end` reason `error` is an ordinary message.

**Prediction**: a typed model, every field optional, with the original JSON kept.

**Error**: `kind`, plus `status`, `closeCode`, `error` and `message` where they apply. Kinds: `invalid_config`, `exchange_failed`, `connection_failed`, `upgrade_refused`, `command_rejected`, `closed`. An error never holds the API key or a token.

## Pure core

No IO, no clock, no environment.
- `encode(Command) → Frame`, for `setPop`, `setSource`, `stopSource`, `getGraph`, `ping`, `quit` and the upload frames.
- `decode(Frame) → Message | Malformed`. It never throws.
- `step(State, Input) → (State, Outputs)`, where `State` tracks open sources, upload credit and the current upload, and `Input` is a command from the caller or a decoded message.
- `configFromEnvironment(map) → Config | invalid_config`. Precedence: explicit argument, then `EYEPOP_URL` and `EYEPOP_AUTH_URL`, then the `EYEPOP_ENV` row, then `production`. `EYEPOP_API_KEY` is the only credential variable; `EYEPOP_ACCOUNT_UUID` supplies `accountUuid`.

## Shell

**`connect(config, pop) → Session`**: exchanges the API key for a token when `auth` is `Exchange`, opens the socket with subprotocol `eyepop.v1` and `Authorization: Bearer <token>`, and sets the pop. The token is a value, `{jwt, expiresAt}`, never cached or shared between Sessions.

**Session**: one open socket and its one pipeline.
- `setSource(source) → Job`
- `setPop(pop)`: applies to the whole socket.
- `getGraph(format, verbose?)`
- `ping()`
- `messages()`: one ordered stream of every Message.
- `expiresAt`: the server never refreshes a socket's credential and closes it with `1008 credential_expired`, so a caller that wants no dropped sources reconnects before this time.
- `close()`: sends `quit`.

**Job**: the handle of one Source.
- `id`
- `messages()`: that source's `start`, `prediction`, `dropped`, `usage` and `end`.
- `predictions()`: the predictions alone.
- `cancel()`: sends `stopSource`; the Job ends with `end` reason `stopped`.

A Job is a pure demux of the Session's stream by source `id`. Results are read with the language's native asynchronous iteration. There is no call that returns one result at a time until it returns nothing.

## Uploads

A known length of 8 MiB or less goes as one combined message. Anything else is chunked under the server's credit in 64 KiB frames, one upload at a time, and the SDK sends `uploaded` after the last chunk. The caller never sees `send`, `credit` or `uploaded`. A file path is a per-language helper that builds the stream, not part of this contract.

## Backpressure and closing

The Session reads the socket only while a consumer pulls from a stream. Each Job has a buffer of 256 messages; when one is full the reader waits, so the pressure reaches the server, which drops predictions for live sources and closes with `1008 slow_client` after its write timeout for the others. The SDK drops nothing itself. Consume every Job you open: one stalled Job holds up the others.

A close with `1000` (a `quit`, a client `close`, or `1000 idle`) ends `messages()` normally. Any other close is an error of kind `closed` with its `closeCode` and reason, and every Job in flight receives it. The SDK never reconnects and never resends a source.

## Naming

Names are the wire names (above). A language changes casing only. Types that carry a discriminator are unions in the language's own way: sealed hierarchy or `JsonPolymorphic` in C#, tagged enum in Rust, interface plus concrete types in Go, discriminated union in TypeScript and Python.

## Protocol schema and conformance

- `protocol/` holds JSON Schema 2020-12 for every command, message, `Source`, `Pop`, `Ability`, `Camera` and `Prediction`, with a `const` discriminator on `type`. Types are generated from it; the generation approach is decided by a spike (ADR 0002).
- `conformance/` holds scripted transcripts of a fake pipeline API and a fake auth service. Every SDK's integration suite replays them, and CI validates every transcript message against `protocol/`.
- Unit tests of the pure core use a fake transport. Integration tests run the shell against in-process fakes. The two suites run apart.

## Open details for the build slices

These were not settled in design and are decided while the slice is built, then written back here:
- How a Job's `id` is chosen. Ids are client chosen and must be unique among a socket's open sources.
- Whether `setSource` resolves when the server answers `result`, or earlier.
- Whether `connect` retries an upgrade refused with `503` and `Retry-After` (both old SDKs waited up to 30 s).
- The exact name and set of fields of the typed Prediction.
