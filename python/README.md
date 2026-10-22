# EyePop Python SDK

Scaffold package. The version is the release tag (see the repo's `docs/adr/0001-*.md`);
`eyepop.version()` reports it.

## 4.x is a breaking rewrite

4.x replaces the 3.x `sessions` API (`from eyepop import EyePopSdk`) with the new pipeline-api,
and does not keep the old entry point. Until the rewrite reaches parity every 4.x release is a
prerelease (`4.0.0aN`), which `pip install eyepop` does not pick up by default. The 3.x line
continues from `eyepop-ai/eyepop-sdk-python`.
