# Lockstep, tag-driven releases for every Language SDK

One git tag `vX.Y.Z` is the only source of truth for a version, and every Language SDK is published at that version on every release, even if nothing in it changed. We chose this over independent per-language versions for simpler CI and a single "which version do I use" answer, accepting churny no-change releases (a node-only change republishes go and rust).
