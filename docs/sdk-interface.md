# The Language SDK interface: the pipeline socket

The public interface of every Language SDK, written once and without a language. Decisions and their reasons are in [ADR 0002](adr/0002-one-pipeline-socket-interface-for-every-language-sdk.md). Terms are in [`GLOSSARY.md`](../GLOSSARY.md). The wire contract is the pipeline API's socket contract; the machine-readable form is `protocol/`.

A language renders this with its own casing (`setSource`, `SetSource`, `set_source`) and its own failure idiom. It adds no concept, and it omits none.

## Scope

The pipeline API's WebSocket, `GET /api/v1/pipeline`, and the one HTTP call that gets a token for it. Out of v1: the one-image `POST`, the Data API, WHIP commands, socket pooling.

## Values

All values are immutable. A value that holds a raw JSON field exposes it unchanged.

**Config**: what a Pipeline needs, built once and passed in.
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

**Source**: one of `Url`, `Asset`, `Upload{contentType, content}`, `Group{members}`, with the options the socket takes: `params`, `roi`, `camera`, `fps`, `live`. There is no `mode` option: the SDK never sends one, and the pipeline applies its default (queue). A group member is a `Url` or an `Upload`, in the order the ability sees them. `content` is bytes, or a function that opens a new byte stream, with an optional known length. A stream that can be read only once is not accepted, because a reconnect sends the upload again ([ADR 0006](adr/0006-the-pipeline-supervises-its-socket.md)).

**Message**: a tagged union of everything the server sends: `result`, `send`, `credit`, `start`, `prediction`, `dropped`, `usage`, `end`, `done`, `pong`, `error`. A source ending with `end` reason `error` is an ordinary message. The Pipeline adds two messages of its own, which the server never sends: `reconnecting`, with `cause` (an Error), `attempt` and `delay`, and `reconnected`.

**Prediction**: what the pipeline reports for one processed frame, built from the `prediction` object of a `prediction` message. The socket always asks for prediction format v4, so the legacy keys of v1 (`classId`, per-object `id`, `traceId`) are not typed. Every field is optional. Nested values are typed: `objects` (which nest), `classes`, `texts`, `keyPoints`, `meshes`, `depth`, `mask`, `track_events`. `tokens`, `raw`, `details` and `features` stay raw JSON, and base64 values (`depth.values`, `depth.world`, `mask.bitmap`, `mask.world`) stay strings. `depth.semantic` is an open string. The original JSON object is kept unchanged beside the typed fields, and the `prediction` message keeps it too. A value the typed fields cannot hold leaves them empty and the JSON object intact. A selected prediction (`selected` is true) describes an earlier frame and arrives after later ones. The schema is `protocol/schema/prediction.json`, shared by every surface that reports a prediction ([ADR 0004](adr/0004-shared-prediction-schema-typed-view-over-raw-object.md)).

**Error**: `kind`, plus `status`, `closeCode`, `error` and `message` where they apply. Kinds: `invalid_config`, `exchange_failed`, `connection_failed`, `upgrade_refused`, `command_rejected`, `closed`. A command the server refuses is `command_rejected`, with the server's code in `error`, for example `queue_full` or `live_source_open`. An error never holds the API key or a token. The caller receives an Error only when a retry would fail the same way. A failure a retry can fix is the `cause` of a `reconnecting` message instead (see "Supervision").

## Pure core

No IO, no clock, no environment.
- `encode(Command) → Frame`, for `setPop`, `setSource`, `stopSource`, `getGraph`, `ping`, `quit` and the upload frames.
- `decode(Frame) → Message | Malformed`. It never throws.
- `step(State, Input) → (State, Outputs)`, where `State` tracks the current pop, open sources with their Source, upload credit, the current upload and the last frame each Job delivered, and `Input` is a command from the caller, a decoded message or a reconnect.
- `backoff(attempt, random) → delay`, the jittered delay before a reconnect (see "Supervision").
- `configFromEnvironment(map) → Config | invalid_config`. Precedence: explicit argument, then `EYEPOP_URL` and `EYEPOP_AUTH_URL`, then the `EYEPOP_ENV` row, then `production`. `EYEPOP_API_KEY` is the only credential variable; `EYEPOP_ACCOUNT_UUID` supplies `accountUuid`.

## Shell

**`connect(config, pop) → Pipeline`**: exchanges the API key for a token when `auth` is `Exchange`, opens the socket with subprotocol `eyepop.v1` and `Authorization: Bearer <token>`, and sets the pop. It retries as described in "Supervision". The token is a value, `{jwt, expiresAt}`, never cached or shared between Pipelines.

**Pipeline**: one pop and its sources, over one socket at a time.
- `id`: made by the SDK when the Pipeline opens. It stays the same across reconnects.
- `setSource(source) → Job`
- `setPop(pop)`: sent in order like any command. It changes the pop in place, under the sources already running or queued.
- `getGraph(format, verbose?)`
- `ping()`
- `messages()`: one ordered stream of every Message.
- `status()`: `state` (`connecting`, `open`, `backingOff`, `closed`, `failed`), the number of reconnects and the last Error.
- `close()`: sends `quit` and stops reconnecting.

**Job**: the handle of one Source.
- `id`: chosen by the SDK, numbered per Pipeline, and unique for the Pipeline's life. A caller never passes one.
- `messages()`: that source's `start`, `prediction`, `dropped`, `usage` and `end`, and the Pipeline's `reconnecting` and `reconnected`.
- `predictions()`: every prediction of the source, selected ones included, each as a Prediction. A Prediction whose typed fields could not be read still arrives, with only its JSON object. Skip a selected one when counting frames.
- `cancel()`: sends `stopSource`; the Job ends with `end` reason `stopped`.

A Job is a pure demux of the Pipeline's stream by source `id`. Results are read with the language's native asynchronous iteration. There is no call that returns one result at a time until it returns nothing.

## Sources and ordering

The SDK sends every command as it is called and keeps no queue and no ordering policy of its own. The pipeline owns the source queue. The SDK remembers only the pop and the sources that have not ended, to send them again after a reconnect.
- Sources run in the order the pipeline queues them. A second `setSource` does not clear the first: both Jobs run. To end one, call `cancel()` on its Job.
- A Pipeline holds at most 256 open sources. The 257th is refused with `queue_full`.
- A live source cannot queue behind another live source of the same socket: it is refused with `live_source_open`. Cancel the first, or open another Pipeline.
- Each answer and message carries the source `id`, so a Job reads only its own. Across Jobs the SDK promises no order beyond the pipeline's queue order; sorting out results across sources is the caller's job.
- `setPop` is sent in order. While it applies, the server holds later `setSource` commands in order and sends them once the pop is in. A pop that fails to resolve is a refused command and the pipeline keeps its old pop. A pop that fails to apply closes the socket with `1011 pipeline_stopped`.

## Uploads

A known length of 8 MiB or less goes as one combined message. Anything else is chunked under the server's credit in 64 KiB frames, one upload at a time, and the SDK sends `uploaded` after the last chunk. The caller never sees `send`, `credit` or `uploaded`. A file path is a per-language helper that builds the stream, not part of this contract.

## Backpressure and closing

The Pipeline reads the socket only while a consumer pulls from a stream. Each Job has a buffer of 256 messages; when one is full the reader waits, so the pressure reaches the server, which drops predictions for live sources and closes with `1008 slow_client` after its write timeout for the others. The SDK drops nothing itself. Consume every Job you open: one stalled Job holds up the others.

`close()` ends `messages()` normally. A `1000 idle` close keeps the Pipeline: the next command opens a new socket. Every other close goes through "Supervision". A close it cannot retry is an error of kind `closed` with its `closeCode` and reason, and every Job in flight receives it.

## Supervision

A Pipeline outlives its socket ([ADR 0006](adr/0006-the-pipeline-supervises-its-socket.md)). The pipeline API keeps nothing between sockets, so a reconnect is always a new socket running a new pipeline. The Pipeline reconnects for as long as it is open, with no give-up count. The caller bounds it with cancellation or `close()`.

A reconnect:
1. closes the old socket fully; no message from it is delivered after this;
2. exchanges the key again if the token has less than 60 s left;
3. opens a new socket and sends `setPop` with the current pop;
4. sends `setSource` again for every source whose `end` has not arrived, in the original order and with the original ids.

Every Job in flight receives `reconnecting` before the attempt and `reconnected` after it. A resent `Url` or `Asset` source starts again at its first frame. Its Job skips any prediction for a frame at or before the last frame it delivered, but never a selected prediction.

Backoff is exponential with full jitter. It starts at 1 s, is capped at 60 s, and resets after 30 s without a failure. A `Retry-After` is a floor. All three values are settings with these defaults.

| Failure | What the Pipeline does |
|---|---|
| The exchange cannot connect, times out, or answers `429` or `5xx` | Retries the exchange with backoff |
| The exchange answers `401` or `403` | Terminal `exchange_failed` |
| The upgrade cannot connect, is reset, or times out | Reconnects with backoff |
| The upgrade answers `503` (`overloaded`, `pipeline_start_failed`, `shutting_down`) | Waits at least `Retry-After`, then reconnects |
| The upgrade answers `401` or `403` | Exchanges again and retries once; a second refusal is terminal `upgrade_refused` |
| Close `1001`; close `1011` with any reason; close `1008` `slow_client` or `client_gone`; a drop with no close frame | Reconnects with backoff |
| Close `1008 credential_expired` | Exchanges again and reconnects at once |
| Close `1008` `unexpected_bytes` or `credit_exceeded` | Terminal `closed`: the SDK broke the upload protocol, and a resend would break it again |
| No message for longer than the liveness window (default 60 s; the server pings every 20 s) | Treats the socket as dead, closes it and reconnects |
| `error` `overloaded` for a `setSource` | Sends that source again with backoff |
| Any other `error` for a command, such as `queue_full`, `live_source_open` or a pop that does not resolve | Terminal `command_rejected` for that command; the socket stays open |
| `end` with reason `eos` or `error` on a live source | Sends that source again with backoff |
| `end` on a finite source | The Job ends |

## Naming

Names are the wire names (above). A language changes casing only. The one exception is the type of the `prediction` message, which is `PredictionMessage` because `Prediction` names the typed value. Types that carry a discriminator are unions in the language's own way: sealed hierarchy or `JsonPolymorphic` in C#, tagged enum in Rust, interface plus concrete types in Go, discriminated union in TypeScript and Python.

## Protocol schema and tests

- `protocol/` holds JSON Schema 2020-12 for every command, message, `Source`, `Pop`, `Ability`, `Camera` and `Prediction`, with a `const` discriminator on `type`. Types are generated from it ([ADR 0003](adr/0003-one-in-repo-generator-writes-the-protocol-types.md)).
- Unit tests of the pure core use a fake transport and never call a real environment.
- Integration tests run against real staging through a separate private test repository. Each run validates the pipeline's messages against `protocol/` ([ADR 0005](adr/0005-integration-tests-run-on-real-staging.md)).

## Open details for the build slices

These were not settled in design and are decided while the slice is built, then written back here:
- Whether `setSource` resolves when the server answers `result`, or earlier.
