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
