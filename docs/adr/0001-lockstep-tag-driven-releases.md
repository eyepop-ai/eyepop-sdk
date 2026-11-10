# Lockstep, tag-driven releases for every Language SDK

One git tag `vX.Y.Z` is the only source of truth for a version, and every Language SDK is published at that version on every release, even if nothing in it changed. We chose this over independent per-language versions for simpler CI and a single "which version do I use" answer, accepting churny no-change releases (a node-only change republishes go and rust).

## Revisited 2026-11-10: kept

We considered independent per-language releases (`<lang>/vX.Y.Z` tags, one release workflow per language) because existing registry histories differ (PyPI `eyepop`, the `@eyepop.ai` npm scope) and a node-only change should not republish the others. We kept lockstep: one version and one tag are much easier to track, and per-language versions would need a pipeline-API compatibility story and a rewrite of the Release tag and Lockstep release terms. The churn cost above stands. Reopen this if a Language SDK needs to ship on its own cadence.
