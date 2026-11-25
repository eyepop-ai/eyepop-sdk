# The Pipeline supervises its socket

A Pipeline outlives its socket. When a socket fails for a reason a retry can fix, the Pipeline opens a new one, sets its pop again, resends every source that has not ended, and its Jobs carry on. The caller sees `reconnecting` and `reconnected` messages, not errors, and receives an error only when a retry would fail the same way. This supersedes the "no reconnect supervision in v1" part of [ADR 0002](0002-one-pipeline-socket-interface-for-every-language-sdk.md).

## Context

The pipeline API keeps nothing for a client between sockets. A pipeline lives for one socket and stops when it closes. Pipelines start and stop freely and may start on any node, so a reconnect is always a new socket running a new pipeline. There is nothing to resume and no socket id to reattach to.

ADR 0002 left reconnecting to the caller. In practice every caller would write the same loop: back off, exchange the key again, reopen, set the pop, resend what was running. Pods restart, networks drop, tokens expire, and streams run for days, so failures are routine and the SDK must absorb them.

## Decisions

- **Live sources never give up; finite sources give up after 15 minutes.** While a live source is open, the Pipeline reconnects for as long as it is open, and the caller bounds it with cancellation or `close()`. When the Pipeline has failed to reconnect for 15 minutes, the Job of every finite source ends with the last Error. A Pipeline with no live source left then stops reconnecting and goes idle. The 15 minutes is a setting with that default.
- **Only `close()` ends a Pipeline.** A failure the Pipeline does not retry ends the Jobs it affects and reaches the caller, but the Pipeline stays usable. An idle Pipeline has no socket, and its next command opens one.
- **A failed pop fails its `setPop`, not the Pipeline.** A pop that does not resolve is a refused `setPop`. A pop that fails to apply closes the socket with `1011 pipeline_stopped` while the `setPop` is pending. Either way that `setPop` fails, is not retried, and the Pipeline keeps the last pop that applied. If the socket closed, the Pipeline reconnects with that pop and resends its unended sources, as after any other drop. The caller can send another `setPop` at any time.
- **When the pop a reconnect sends fails, the Pipeline waits for a new one.** Every open Job ends with the error and the Pipeline goes idle. A `setPop` with a pop that works brings it back. Any other command fails the same way while the pop still fails.
- **A reconnect replays the Pipeline's state.** The Pipeline closes the old socket fully, opens a new one, sends `setPop` with the current pop, then sends `setSource` for every source whose `end` has not arrived, in their original order and with their original ids. No message from the old socket is delivered once the new one is open.
- **Backoff is exponential with jitter.** It starts at about 1 s, is capped at about 60 s, and resets after the Pipeline has been healthy for about 30 s. A `Retry-After` is a floor, capped at the backoff cap so a mistaken or hostile header cannot stall a Pipeline. Jitter keeps many Pipelines that fail in one outage from reconnecting at the same moment. The three values are settings with these defaults.
- **A series of failures** is what backoff and the give-up limit count. It begins with a failure after a healthy period (30 s on one socket, or since a resend went out) and ends only when the socket stays healthy for 30 s again; a socket that opens and fails within that time continues it. A reconnect at once (`credential_expired`, the first `401` on an upgrade) is for the first failure of a series. The give-up limit runs from the series start, so a finite source added during an outage of 15 minutes or more ends with the next failure.
- **The token is exchanged again** on `1008 credential_expired`, and before any reconnect when it has less than 60 s left. After `credential_expired` the first reopen has no backoff.
- **Recoverable and terminal failures are a fixed table** (in [`sdk-interface.md`](../sdk-interface.md), "Supervision"), keyed on HTTP status, close code and reason, and error code. Until the pipeline API marks its errors as retryable, the table is the only source of that decision.
- **A live source that ends is sent again.** An `end` with reason `eos` or `error` on a live source means the camera or the stream stopped, so it is resent with backoff. A finite source's `end` is final, whatever its reason.
- **A resent source may repeat predictions.** A `Url` or `Asset` source starts again at its first frame, and its Job delivers those frames' predictions again. The SDK does not filter them.
- **Upload content can always be read again.** It is bytes, or a function that opens a new stream. A stream that can be read only once is not accepted.
- **The Pipeline has an id.** The SDK makes it when the Pipeline opens. It stays the same across reconnects and appears in the SDK's logs and in `status()`.
- **Job ids are chosen by the SDK.** They are numbered per Pipeline and stay unique for its life, across reconnects. A caller never passes one.

## Considered options

- **Leave reconnecting to the caller (ADR 0002).** Every caller would write the same loop, and many would get the token, the resend or the backoff wrong.
- **Reattach to the same pipeline after a drop.** The pipeline API keeps no state between sockets.
- **Give up after a number of attempts.** An outage longer than the count would end a stream that should have recovered. A time limit on finite sources says what a caller waiting on a batch needs to know.
- **Never give up on finite sources either.** A batch caller would wait forever on an outage with no error to act on.
- **Skip repeated predictions by frame time.** It needs a frame time on every prediction and a rule for selected predictions. A start offset on `setSource` (below) removes the repeats at their source.
- **Buffer one-shot upload streams in memory to resend them.** An upload has no size limit, so the buffer would have none either.

## Consequences

- The pure core's state also holds the current pop, each unended source with its Source, and when reconnecting began. Backoff is a pure function of the attempt number and a random value passed in.
- `Pipeline.expiresAt` is removed: the SDK handles expiry. `Pipeline.status()` and the `reconnecting` and `reconnected` messages take its place.
- After a reconnect, the old and the new pipeline may both process a live source for a moment. Only the new socket's messages are delivered.
- Asks of the pipeline API, each of which would let the SDK drop a workaround:
  - mark an error or a close as retryable, with a delay, so the table is no longer the SDK's guess;
  - accept a start offset on `setSource`, so a resent source does not process its frames again;
  - close with a reason of its own when a pop fails to apply, so the SDK does not have to infer it from a pending `setPop`;
  - log a pipeline id sent by the client, so the sockets of one Pipeline can be traced together.
