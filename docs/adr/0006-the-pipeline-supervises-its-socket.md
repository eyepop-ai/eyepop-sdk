# The Pipeline supervises its socket

A Pipeline outlives its socket. When a socket fails for a reason a retry can fix, the Pipeline opens a new one, sets its pop again, resends every source that has not ended, and its Jobs carry on. The caller sees `reconnecting` and `reconnected` messages, not errors, and receives an error only when a retry would fail the same way. This supersedes the "no reconnect supervision in v1" part of [ADR 0002](0002-one-pipeline-socket-interface-for-every-language-sdk.md).

## Context

The pipeline API keeps nothing for a client between sockets. A pipeline lives for one socket and stops when it closes. Pipelines start and stop freely and may start on any node, so a reconnect is always a new socket running a new pipeline. There is nothing to resume and no socket id to reattach to.

ADR 0002 left reconnecting to the caller. In practice every caller would write the same loop: back off, exchange the key again, reopen, set the pop, resend what was running. Pods restart, networks drop, tokens expire, and streams run for days, so failures are routine and the SDK must absorb them.

## Decisions

- **The Pipeline reconnects, for as long as it is open.** It has no give-up count, for streams and for finite sources alike. The caller bounds it with cancellation or `close()`.
- **A reconnect replays the Pipeline's state.** The Pipeline closes the old socket fully, opens a new one, sends `setPop` with the current pop, then sends `setSource` for every source whose `end` has not arrived, in their original order and with their original ids. No message from the old socket is delivered once the new one is open.
- **Backoff is exponential with jitter.** It starts at about 1 s, is capped at about 60 s, and resets after the Pipeline has been healthy for about 30 s. A `Retry-After` is a floor. Jitter keeps many Pipelines that fail in one outage from reconnecting at the same moment. The three values are settings with these defaults.
- **The token is exchanged again** on `1008 credential_expired`, and before any reconnect when it has less than 60 s left. After `credential_expired` the first reopen has no backoff.
- **Recoverable and terminal failures are a fixed table** (in [`sdk-interface.md`](../sdk-interface.md), "Supervision"), keyed on HTTP status, close code and reason, and error code. Until the pipeline API marks its errors as retryable, the table is the only source of that decision.
- **A live source that ends is sent again.** An `end` with reason `eos` or `error` on a live source means the camera or the stream stopped, so it is resent with backoff. A finite source's `end` is final, whatever its reason.
- **A resent source does not repeat predictions.** A `Url` or `Asset` source starts again at its first frame. Its Job skips any prediction for a frame at or before the last frame it delivered. A selected prediction is never skipped, because it describes an earlier frame by design.
- **Upload content can always be read again.** It is bytes, or a function that opens a new stream. A stream that can be read only once is not accepted.
- **The Pipeline has an id.** The SDK makes it when the Pipeline opens. It stays the same across reconnects and appears in the SDK's logs and in `status()`.
- **Job ids are chosen by the SDK.** They are numbered per Pipeline and stay unique for its life, across reconnects. A caller never passes one.

## Considered options

- **Leave reconnecting to the caller (ADR 0002).** Every caller would write the same loop, and many would get the token, the resend or the backoff wrong.
- **Reattach to the same pipeline after a drop.** The pipeline API keeps no state between sockets.
- **Give up after a number of attempts.** An outage longer than the count would end a stream that should have recovered. The caller already holds cancellation.
- **Deliver repeated predictions after a resend.** Every caller would have to remove them.
- **Buffer one-shot upload streams in memory to resend them.** An upload has no size limit, so the buffer would have none either.

## Consequences

- The pure core's state also holds the current pop, each unended source with its Source, and the last frame each Job delivered. Backoff is a pure function of the attempt number and a random value passed in.
- `Pipeline.expiresAt` is removed: the SDK handles expiry. `Pipeline.status()` and the `reconnecting` and `reconnected` messages take its place.
- After a reconnect, the old and the new pipeline may both process a live source for a moment. Only the new socket's messages are delivered.
- Asks of the pipeline API, each of which would let the SDK drop a workaround:
  - mark an error or a close as retryable, with a delay, so the table is no longer the SDK's guess;
  - accept a start offset on `setSource`, so a resent source does not process its frames again;
  - log a pipeline id sent by the client, so the sockets of one Pipeline can be traced together.
