# Registry setup (manual, one-time)

Working assumption: the name `eyepop` (`EyePop` on NuGet) is available or ours everywhere. Each registry needs a trusted publisher (OIDC) pointing at the `eyepop-ai/eyepop-sdk` repo and `.github/workflows/release.yml`.

| Registry | Name | Status / do |
|---|---|---|
| npm | `@eyepop.ai/pipeline` (later `@eyepop.ai/dataset`) | Org owned (`@eyepop.ai`, shared with the old 3.x packages); add trusted publisher |
| PyPI | `eyepop` (existing project) | Org owned. Add trusted publisher for this repo alongside the old one |
| crates.io | `eyepop` | Reserve (first publish claims it); add trusted publisher |
| NuGet | `EyePop` | Not started, see below |
| Go | `github.com/eyepop-ai/eyepop-sdk/go` | No registry. Repo must be public; CI pushes the `go/vX.Y.Z` tag |

## NuGet (nuget.org)

- Packages are claimed by first publish: the ID `EyePop` is yours once you push it. There is no separate reserve step. Optionally request an ID prefix reservation (`EyePop.*`) from nuget.org so others can't publish look-alikes.
- Sign in at nuget.org with a Microsoft account, ideally one shared by the team, or create an organization that owns the package.
- Publishing from CI: nuget.org supports Trusted Publishing for GitHub Actions (a policy tied to the nuget.org account, repo and workflow). Verify whether a policy can be created before the package exists. If not, the first alpha is pushed with a scoped API key, then switched to trusted publishing.

## C# dev environment (macOS)

- Install: `brew install --cask dotnet-sdk`, then `dotnet --version`.
- Scaffold check: `dotnet new sln`, `dotnet new classlib`, `dotnet test`, `dotnet pack`.
- The editor is optional. VS Code with the C# Dev Kit, or JetBrains Rider.

## Prereleases

`v4.0.0-alpha.1` maps to `4.0.0a1` on PyPI and the `next` dist-tag on npm. A published version is never deleted; cut the next alpha instead.
