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

Construction refuses what cannot work: an `Exchange` without an API key, an API key without an auth URL, plain `http` to a host that is not loopback (`localhost`, `127.0.0.0/8` or `::1`). Nothing downstream re-checks.

**Environment**: a named row of `{pipelineUrl, authUrl}`.

| name | pipelineUrl | authUrl |
|---|---|---|
| `production` (default) | `https://pipeline.eyepop.ai` | `https://compute.eyepop.ai` |
| `staging` | `https://pipeline.staging.eyepop.xyz` | `https://compute.staging.eyepop.xyz` |
| `local` | `http://127.0.0.1:9002` | none, so `Anonymous` |

**Ability**: a name or alias (`eyepop.person:latest`) or a uuid, plus `params`.

**Pop**: `components`, and optionally `defaults`, `postTransform`, `depthMap`. An inference component holds an Ability. Component kinds not yet typed are raw JSON. `ability(name, params)` builds a Pop of one inference component.

**Source**: one of `Url`, `Asset`, `Upload{contentType, content}`, `Group{members}`, with the options the socket takes: `params`, `roi`, `camera`, `fps`, `live`. There is no `mode` option: the SDK never sends one, and the pipeline applies its default (queue). A group member is a `Url` or an `Upload`, in the order the ability sees them. `content` is bytes, or a function that opens a new byte stream, with an optional known length. A stream that can be read only once is not accepted, because a reconnect sends the upload again ([ADR 0006](adr/0006-the-pipeline-supervises-its-socket.md)).

**Message**: a tagged union of what a Job delivers: `start`, `prediction`, `dropped`, `usage`, `end`, and two messages the Pipeline adds and the server never sends, `reconnecting` (with `cause`, an Error, `attempt` and `delay`) and `reconnected`. A source ending with `end` reason `error` is an ordinary message. The server's other messages (`result`, `send`, `credit`, `done`, `pong`, `error`) are internal: the SDK acts on them and the caller never sees them.

**Prediction**: what the pipeline reports for one processed frame, built from the `prediction` object of a `prediction` message. The pipeline sends prediction format v4 on the socket, so the legacy keys of v1 (`classId`, per-object `id`, `traceId`) are not typed. Every field is optional. Nested values are typed: `objects` (which nest), `classes`, `texts`, `keyPoints`, `meshes`, `depth`, `mask`, `track_events`. `tokens`, `raw`, `details` and `features` stay raw JSON, and base64 values (`depth.values`, `depth.world`, `mask.bitmap`, `mask.world`) stay strings. `depth.semantic` is an open string. The original JSON object is kept unchanged beside the typed fields, and the `prediction` message keeps it too. A value the typed fields cannot hold leaves them empty and the JSON object intact. A selected prediction (`selected` is true) describes an earlier frame and arrives after later ones. The schema is `protocol/schema/prediction.json`, shared by every surface that reports a prediction ([ADR 0004](adr/0004-shared-prediction-schema-typed-view-over-raw-object.md)).

**Error**: `kind`, plus `status`, `closeCode`, `error` and `message` where they apply. Kinds: `invalid_config`, `exchange_failed`, `connection_failed`, `upgrade_refused`, `command_rejected`, `closed`. A command the server refuses is `command_rejected`, with the server's code in `error`, for example `queue_full` or `live_source_open`. An error never holds the API key or a token. The caller receives an Error only when a retry would fail the same way. A failure a retry can fix is the `cause` of a `reconnecting` message instead (see "Supervision").

## Pure core

No IO, no clock, no environment.
- `encode(Command) → Frame`, for `setPop`, `setSource`, `stopSource`, `getGraph`, `ping`, `quit` and the upload frames.
- `decode(Frame) → ServerMessage | Malformed`. A `ServerMessage` is any message the server sends. It is internal: the shell passes the ones a Job delivers on as the public `Message`. It never throws. A message whose `type` the SDK does not know decodes as an unknown message, which the shell ignores, so a newer server does not break an older SDK. `Malformed` (not JSON, or a known `type` missing required fields) is skipped by the shell: it is logged and counted in `status()` with the last one seen, and the socket stays open.
- `step(State, Input) → (State, Outputs)`, where `State` tracks the current pop, open sources with their Source, upload credit, the current upload and when reconnecting began, and `Input` is a command from the caller, a decoded message or a reconnect.
- `backoff(attempt, random) → delay`, the jittered delay before a reconnect (see "Supervision").
- `configFromEnvironment(map) → Config | invalid_config`. Precedence: explicit argument, then `EYEPOP_URL` and `EYEPOP_AUTH_URL`, then the `EYEPOP_ENV` row, then `production`. `EYEPOP_API_KEY` is the only credential variable; `EYEPOP_ACCOUNT_UUID` supplies `accountUuid`.

## Shell

**`connect(config, pop) → Pipeline`**: exchanges the API key for a token when `auth` is `Exchange`, opens the socket with subprotocol `eyepop.v1` and `Authorization: Bearer <token>`, and sets the pop. It retries as described in "Supervision", and fails if the pop fails. The token is a value, `{jwt, expiresAt}`, never cached or shared between Pipelines.

**Pipeline**: one pop and its sources, over one socket at a time.
- `id`: made by the SDK when the Pipeline opens. It stays the same across reconnects.
- `setSource(source) → Job`: returns the Job at once, without waiting for the server. The server may answer late, behind its queue or a resolving `setPop`. A refusal such as `queue_full` or `live_source_open` arrives as the Job failing with `command_rejected`, so every outcome of a source goes through its Job.
- `setPop(pop)`: sent in order like any command, and completes when the server answers `result`. It changes the pop in place, under the sources already running or queued. If it fails, the Pipeline keeps the last pop that applied.
- `getGraph(format, verbose?) → graph`: the server's answer, as raw JSON.
- `ping()`: completes when the server answers `pong`.
- `status()`: `state` (`connecting`, `open`, `backingOff`, `idle`, `closed`), the number of reconnects, the last Error, and the number of malformed frames with the last one.
- `close()`: sends `quit` and stops reconnecting.

**Job**: the handle of one Source.
- `id`: chosen by the SDK, numbered per Pipeline, and unique for the Pipeline's life. A caller never passes one.
- `messages()`: that source's `start`, `prediction`, `dropped`, `usage` and `end`, and the Pipeline's `reconnecting` and `reconnected`.
- `predictions()`: every prediction of the source, selected ones included, each as a Prediction. A Prediction whose typed fields could not be read still arrives, with only its JSON object. Skip a selected one when counting frames. It is a filtered view of `messages()`: it ends when the Job ends, and fails after the last prediction when the Job ends with an Error or with `end` reason `error`.

A Job has one reader. The first call of `messages()` or `predictions()` takes it, and any later call of either fails, in the language's own way for a misuse rather than as an Error kind. Two readers of one buffer would each see only part of it.
- `cancel()`: sends `stopSource`; the Job ends with `end` reason `stopped`.

A Job is a pure demux of the socket's messages by source `id`. The Pipeline has no public message stream, so there is no stream a caller can forget to read. A command's answer completes that command, the Pipeline's own events go to `status()` and to every open Job, and an `error` with no `id` goes to `status()`. Results are read with the language's native asynchronous iteration. There is no call that returns one result at a time until it returns nothing.

## Sources and ordering

The SDK sends every command as it is called and keeps no queue and no ordering policy of its own. The pipeline owns the source queue. The SDK remembers only the pop and the sources that have not ended, to send them again after a reconnect.
- Sources run in the order the pipeline queues them. A second `setSource` does not clear the first: both Jobs run. To end one, call `cancel()` on its Job.
- A Pipeline holds at most 256 open sources. The 257th is refused with `queue_full`.
- A live source cannot queue behind another live source of the same socket: it is refused with `live_source_open`. Cancel the first, or open another Pipeline.
- Each answer and message carries the source `id`, so a Job reads only its own. Across Jobs the SDK promises no order beyond the pipeline's queue order; sorting out results across sources is the caller's job.
- `setPop` is sent in order. While it applies, the server holds later `setSource` commands in order and sends them once the pop is in. A pop that fails to resolve is a refused command; a pop that fails to apply closes the socket with `1011 pipeline_stopped`. Either one fails that `setPop` only (see "Supervision").

## Uploads

A known length of 8 MiB or less goes as one combined message. Anything else is chunked under the server's credit in 64 KiB frames, one upload at a time, and the SDK sends `uploaded` after the last chunk. The caller never sees `send`, `credit` or `uploaded`. A file path is a per-language helper that builds the stream, not part of this contract.

## Backpressure and closing

The Pipeline reads the socket only while a consumer pulls from a Job or a command waits for its answer. Each Job has a buffer of 256 messages; when one is full the reader waits, so the pressure reaches the server, which drops predictions for live sources and closes with `1008 slow_client` after its write timeout for the others. The SDK drops nothing itself. Consume every Job you open: one stalled Job holds up the others.

`close()` ends every Job's `messages()` normally, and only `close()` ends a Pipeline. A `1000 idle` close leaves the Pipeline idle: the next command opens a new socket. Every other close goes through "Supervision". A close it cannot retry is an error of kind `closed` with its `closeCode` and reason, and every Job in flight receives it.

## Supervision

A Pipeline outlives its socket ([ADR 0006](adr/0006-the-pipeline-supervises-its-socket.md)). The pipeline API keeps nothing between sockets, so a reconnect is always a new socket running a new pipeline. While a live source is open, the Pipeline reconnects for as long as it is open, and the caller bounds it with cancellation or `close()`. When the Pipeline has failed to reconnect for 15 minutes (a setting), the Job of every finite source ends with the last Error. A Pipeline with no live source left then stops reconnecting and goes idle. A terminal failure ends the Jobs it affects and reaches the caller, but never ends the Pipeline: from idle, the next command opens a new socket.

A reconnect:
1. closes the old socket fully; no message from it is delivered after this;
2. exchanges the key again if the token has less than 60 s left;
3. opens a new socket and sends `setPop` with the current pop;
4. sends `setSource` again for every source whose `end` has not arrived, in the original order and with the original ids.

Every Job in flight receives `reconnecting` before the attempt and `reconnected` after it. A resent `Url` or `Asset` source starts again at its first frame, and its Job delivers those frames' predictions again. The SDK does not filter them.

Backoff is exponential with full jitter. It starts at 1 s, is capped at 60 s, and resets after 30 s without a failure. A `Retry-After` is a floor. All three values are settings with these defaults.

| Failure | What the Pipeline does |
|---|---|
| The exchange cannot connect, times out, or answers `429` or `5xx` | Retries the exchange with backoff |
| The exchange answers `401` or `403` | Terminal `exchange_failed` |
| The upgrade cannot connect, is reset, or times out | Reconnects with backoff |
| The upgrade answers `503` (`overloaded`, `pipeline_start_failed`, `shutting_down`) | Waits at least `Retry-After`, then reconnects |
| The upgrade answers `401` or `403` | Exchanges again and retries once; a second refusal is terminal `upgrade_refused` |
| A refused `setPop`, or close `1011 pipeline_stopped` while a `setPop` is pending | That `setPop` fails with `command_rejected` or `closed` and is not retried. The Pipeline keeps the last pop that applied, and reconnects with it if the socket closed |
| The same failure for the `setPop` a reconnect sends | Every open Job ends with the error and the Pipeline goes idle. A `setPop` with a pop that works brings it back |
| Close `1001`; close `1011` with any other reason or with no `setPop` pending; close `1008` `slow_client` or `client_gone`; a drop with no close frame | Reconnects with backoff |
| Close `1008 credential_expired` | Exchanges again and reconnects at once |
| Close `1008` `unexpected_bytes` or `credit_exceeded` | Terminal `closed`: the SDK broke the upload protocol, and a resend would break it again |
| No message for longer than the liveness window (default 60 s; the server pings every 20 s) | Treats the socket as dead, closes it and reconnects |
| `error` `overloaded` for a `setSource` | Sends that source again with backoff |
| Any other `error` for a command, such as `queue_full` or `live_source_open` | Terminal `command_rejected` for that command; the socket stays open |
| `end` with reason `eos` or `error` on a live source | Sends that source again with backoff |
| `end` on a finite source | The Job ends |

## Naming

Names are the wire names (above). A language changes casing only. Two types are renamed: the `prediction` message is `PredictionMessage` because `Prediction` names the typed value, and the `error` message is `ErrorMessage` because Error names the SDK's own failure. In C# that failure is `EyePopException` with a `Kind`. Types that carry a discriminator are unions in the language's own way: sealed hierarchy or `JsonPolymorphic` in C# for the public unions, tagged enum in Rust, interface plus concrete types in Go, discriminated union in TypeScript and Python.

## Protocol schema and tests

- `protocol/` holds JSON Schema 2020-12 for every command, message, `Source`, `Pop`, `Ability`, `Camera` and `Prediction`, with a `const` discriminator on `type`. Types are generated from it ([ADR 0003](adr/0003-one-in-repo-generator-writes-the-protocol-types.md)).
- One list in `protocol/` names the public types: `Pop`, `Ability`, `Camera`, `Roi`, `ComponentParams`, `Prediction` and the Message types above. Today only the C# generator applies it, marking the rest `internal`; the other generators emit everything public until they do the same (`pub(crate)` in Rust, not exported in TypeScript, a `_` prefix in Python, a lowercase name in Go). Commands, including `setSource` and its `mode`, are internal. The generated public union is `jobMessage` (the five Job messages), the base of the public `Message`, which adds `reconnecting` and `reconnected` by hand. The generated `message`, which holds everything the server sends, is internal and only the decoder uses it (in C#, its variants implement an internal `IMessage`). A public type never holds or has as a variant an internal one, and generation fails if it does.
- The public Source values (`Url`, `Asset`, `Upload`, `Group` and their options) are written by hand over the generated types, not generated from `setSource`.
- Unit tests of the pure core use a fake transport and never call a real environment.
- Integration tests run against real staging through a separate private test repository. Each run validates the pipeline's messages against `protocol/` ([ADR 0005](adr/0005-integration-tests-run-on-real-staging.md)).
