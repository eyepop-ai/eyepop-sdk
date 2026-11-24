# EyePop SDK

The monorepo that holds every EyePop client SDK, one per language, and releases them together.

## Language

**Language SDK**:
The EyePop client for one programming language (node, python, go, rust, cs), living in its own top-level directory and published to that language's registry.
_Avoid_: client library, binding, port

**Release tag**:
The single git tag `vX.Y.Z` that defines the version of every Language SDK. It is the only source of truth for a version.
_Avoid_: version bump, release version

**Lockstep release**:
Publishing every Language SDK at the Release tag's version, including those with no changes since the previous release.
_Avoid_: unified release, full release

**Scaffold package**:
A package that exports only a no-op `eyepop` symbol reporting its own version, used to prove the Lockstep release flow before any real SDK code exists.
_Avoid_: stub, placeholder, hello-world package

**Release artifact**:
The file or files a Language SDK's `package` task writes into `OUT` at the Release tag's version, stored as a workflow artifact by every release run. A publish rebuilds from source rather than uploading these files. Packaging leaves the working tree unchanged.
_Avoid_: build output, dist

## Pipeline socket

**Pipeline socket**:
The WebSocket at `GET /api/v1/pipeline`, subprotocol `eyepop.v1`. Each one runs a pipeline of its own and takes commands. It is the only thing the Language SDK interface covers.
_Avoid_: worker, worker endpoint, stream

**Pipeline**:
The SDK object that runs one pop over a Pipeline socket, from `connect` until `close`. When the socket fails, it opens a new one and resends what was running, so one Pipeline can use many sockets in turn. Not a compute session of the old SDKs.
_Avoid_: session, connection, client, endpoint

**Pop**:
What a Pipeline runs: components, where an inference component holds an Ability.
_Avoid_: pipeline definition, graph

**Ability**:
A named model capability, given as an alias such as `eyepop.person:latest` or a uuid, with params.
_Avoid_: model, worker

**Source**:
One input a Pipeline processes: a url, an asset, an upload or a group.
_Avoid_: job, request, item

**Job**:
The handle of one Source on a Pipeline: its id (chosen by the SDK), its messages, and its `cancel`.
_Avoid_: task, stream

**Prediction**:
What the pipeline reports for one processed frame of a Source, as a typed value with the pipeline's own JSON object kept beside it. Every field is optional. A selected prediction describes an earlier frame than the one before it.
_Avoid_: result, frame, detection

**Prediction message**:
The Message that carries one Prediction for a Job. A Job yields a Prediction even when its typed fields cannot be read, with the JSON object alone.
_Avoid_: result message

**Environment**:
A named row (`production`, `staging`, `local`) giving a pipeline URL and an auth URL. Chosen by `EYEPOP_ENV`.
_Avoid_: stage, mode

**Protocol schema**:
The JSON Schema in `protocol/` that defines every command, message and value of the Pipeline socket. SDK types are generated from it.
_Avoid_: spec, API definition
