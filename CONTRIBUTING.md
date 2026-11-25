# Contributing

## Toolchain

`devbox.json` pins every toolchain (`dotnet-sdk@8`, node, python, go, rust, `go-task`). Run toolchain commands through it so versions match CI.

```bash
devbox run -- task cs:check        # the C# CI gate: lint, typecheck, test
devbox run -- dotnet <args>        # any one-off dotnet command
devbox shell                       # interactive shell with everything on PATH
```

The first run downloads the packages into the Nix store (a few minutes). Later runs start in seconds. `devbox.lock` pins the exact versions; commit it when `devbox.json` changes.

## C# (`cs/`)

Tasks are defined in `cs/Taskfile.yaml` and run from the repo root as `task cs:<name>`, or inside `cs/` as `task <name>`. Wrap them in `devbox run --`.

| Command | What it does |
|---|---|
| `devbox run -- task cs:build` | Build `cs/EyePop.sln` (Release) |
| `devbox run -- task cs:test` | Run the xUnit tests |
| `devbox run -- task cs:lint` | `dotnet format --verify-no-changes`; fix with `devbox run -- dotnet format cs/EyePop.sln` |
| `devbox run -- task cs:typecheck` | Build with warnings as errors |
| `devbox run -- task cs:check` | The CI gate: lint, typecheck, test. |
| `devbox run -- dotnet test cs/EyePop.sln --filter "FullyQualifiedName~Name"` | One test |

- The target framework (`net8.0`) is set once, in `cs/Directory.Build.props`. `cs/global.json` pins SDK 8.0.100 with `rollForward: latestFeature`; CI installs it from that file with `actions/setup-dotnet`, Devbox from `dotnet-sdk@8`. Moving to a new .NET changes `Directory.Build.props`, `global.json` and the `devbox.json` pin together.
- The version is never in a file. `package`, `publish` and `verify` take `TAG=vX.Y.Z`; do not run them locally except `publish:dry-run`.
- `bin/`, `obj/` and `artifacts/` are ignored. After a failed restore, delete `cs/**/bin` and `cs/**/obj` and rerun.
- The C# demo in `demo/cs/` has its own gate: `devbox run -- task demo:cs:check` (format, build, unit tests; no network). Run it with `devbox run -- task demo:cs -- <args>`. See [demo/README.md](demo/README.md).
- Unit tests must not call a real environment. Integration tests run against staging through a separate private test repository ([ADR 0005](docs/adr/0005-integration-tests-run-on-real-staging.md)).
