# Registry setup (manual, one-time)

Working assumption: the name `eyepop` (`EyePop.Sdk` on NuGet) is available or ours everywhere. Each registry needs a trusted publisher (OIDC) pointing at the `eyepop-ai/eyepop-sdk` repo and `.github/workflows/release.yaml`.

| Registry | Name | Status / do |
|---|---|---|
| npm | `@eyepop.ai/pipeline` (later `@eyepop.ai/dataset`) | Org owned (`@eyepop.ai`). Separate from the existing `@eyepop.ai/eyepop`, which this repo never publishes to, so both variants coexist during the transition; add trusted publisher |
| PyPI | `eyepop` (existing project) | Org owned. Add trusted publisher for this repo alongside the old one |
| crates.io | `eyepop` | Reserve (first publish claims it); add trusted publisher |
| NuGet | `EyePop.Sdk` | Not started, see below |
| Go | `github.com/eyepop-ai/eyepop-sdk/go` | No registry. Repo must be public; CI pushes the `go/vX.Y.Z` tag |

## NuGet (nuget.org)

- Packages are claimed by first publish: the ID `EyePop.Sdk` is yours once you push it. There is no separate reserve step. Optionally request an ID prefix reservation (`EyePop.*`) from nuget.org so others can't publish look-alikes.
- The package is owned by the `eyepop-ai` organization on nuget.org.
- Publishing from CI uses Trusted Publishing, no API key. Policy owner `eyepop-ai`, Repository Owner `eyepop-ai`, Repository `eyepop-sdk`, Workflow File `release.yaml` (file name only, no path), scope matching `EyePop.Sdk` and allowed to publish new packages.
- `NUGET_USER` at the top of `_release-cs.yaml` is the nuget.org profile name (not an email address, not a secret). The job gets a 1-hour API key from `NuGet/login` right before the push.
- Unconfirmed until the first real publish: whether nuget.org matches the calling `release.yaml` for a job running in the reusable `_release-cs.yaml`, and whether the policy can publish a package ID that does not exist yet. If it cannot, push the first alpha once with a scoped API key, then switch back.
- To publish only to NuGet, set the repo variable `PUBLISH_TO_REGISTRIES` to `cs`. `true` publishes every registry.

## C# dev environment (macOS)

- Install: `brew install --cask dotnet-sdk`, then `dotnet --version`.
- Scaffold check: `dotnet new sln`, `dotnet new classlib`, `dotnet test`, `dotnet pack`.
- The editor is optional. VS Code with the C# Dev Kit, or JetBrains Rider.

## Prereleases

`v4.0.0-alpha.1` maps to `4.0.0a1` on PyPI and the `next` dist-tag on npm. A published version is never deleted; cut the next alpha instead.
