# Integration tests run on real staging

Every integration test of the SDKs runs against real staging, through a separate private test repository. Its fixture accounts, media, credential loading and cleanup rules govern each run, and a pipeline-socket suite there drives the SDK. Every run validates the pipeline's messages against `protocol/`. Runs are started by hand on a machine that holds the fixture's API key. No pull request triggers a live run, because secrets do not reach forks and each run bills a fixture account. A manually dispatched CI run is a later addition.

## Considered options

- **Integration tests in this repository against fakes.** They never meet the real pipeline, so the typed `Prediction` would be checked only against samples we wrote.
- **A harness in this repository with its own credential.** The API key would live in one more place, and the fixtures, cleanup rules and billing warnings the test repository already carries would be written again.
- **Recorded transcripts replayed offline by every SDK.** Dropped as more machinery than the SDKs need: recordings carry large values and derivatives of third-party media, and need a policy for when to re-record.

## Consequences

- The pipeline-socket suite does not exist in the test repository yet, so it is built there first.
- Unit tests here keep the rule that they never call a real environment.
