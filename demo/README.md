# EyePop SDK demos

A small app per language that runs three real pops against a real EyePop environment and prints what came back. Each demo is meant to be read and copied: a scenario is one self-contained block holding its pop and the few SDK calls that run it.

| Language | Directory | Status |
|----------|-----------|--------|
| C# | [cs/](cs/) | available |

The demos for Python, Go, Rust and Node follow the same behavior; see [Porting to another language](#porting-to-another-language).

## Run the C# demo

You need the [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) and an EyePop API key (create one in the dashboard at https://dashboard.eyepop.ai). Devbox is not needed.

```sh
export EYEPOP_API_KEY=...
dotnet run --project demo/cs                 # the objects scenario on the bundled sample image, from any directory
dotnet run --project demo/cs -- list         # the scenario names
dotnet run --project demo/cs -- keypoints --file ./team.jpg
dotnet run --project demo/cs -- all          # every scenario in turn
```

Inside the repo with Devbox: `devbox run -- task demo:cs -- keypoints`.

Output of `all` on the sample image, from a live run:

```
prediction objects=9 [person]
PASS objects
prediction objects=9 [person] keypoints=9
PASS keypoints
prediction caption="A group of nine people stands in a row, each holding a white card with a black question mark over their face, creating an anonymous and inquisitive visual."
PASS caption
```

## Scenarios

All three run on the bundled `demo/media/people-1.jpg`, which shows nine people.

| Scenario | Pop | Prints |
|----------|-----|--------|
| `objects` (default) | `eyepop.person:latest` | object count and labels |
| `keypoints` | person, then `eyepop.person.2d-body-points:latest` on each person crop | the objects, and the number of key point sets |
| `caption` | `eyepop.vlm.image:latest` with the prompt "Describe the scene in one sentence." | the caption |

The `caption` pop passes the prompt as `params.prompt`, a string; the pipeline ignores a `params.prompts` list for this ability. The caption wording varies from run to run.

Verified live: on 2026-11-25 all three scenarios passed against the staging environment, including from a different working directory. The caption is read from `texts[]`, else from `tokens.text` (the protocol's own example uses it); both print correctly.

## Options

| Option | Meaning |
|--------|---------|
| `list` | Print the scenario names and exit. |
| `<scenario>` | Run one scenario. With no command, objects runs. |
| `all` | Run every scenario in turn. |
| `--file <path>` | Process this file instead of the sample. |
| `--url <url>` | Process this URL instead of the sample. Not with --file. |
| `--pop <file.json>` | Run the pop in this JSON file instead of a scenario. |
| `--json` | Print each prediction as raw JSON instead of the summary line. |
| `--timeout <seconds>` | Give up on a scenario after this long. Default 60. |
| `--help`, `-h` | Print this text and exit. |

`--pop` takes the same `{"components": [...]}` JSON as the scenario blocks. A flag needs a value that does not start with `--`, and a flag given twice is a usage error. `--help` prints the same table.

| Environment variable | Meaning |
|----------------------|---------|
| `EYEPOP_API_KEY` | Required for `production` and `staging`. Leave it unset with `EYEPOP_ENV=local`, which runs without auth. |
| `EYEPOP_ENV` | `production` (default), `staging` or `local`. |
| `EYEPOP_URL`, `EYEPOP_AUTH_URL` | Override the pipeline and auth URLs of the environment. |
| `EYEPOP_ACCOUNT_UUID` | Run as this account, when the key belongs to more than one. |

Exit codes: `0` every scenario passed, `1` a scenario failed, `2` the command line or environment is wrong (a missing `EYEPOP_API_KEY`, an unknown scenario, a bad flag).

## Tests

The argument parsing and the summary lines have unit tests that call no network:

```sh
devbox run -- task demo:cs:check
```

CI runs the same task. Running a scenario needs a real environment and is not part of CI.

## Porting to another language

Copy the structure, not the code. A port keeps this behavior exactly, so the demos can be compared and scripted the same way.

- **Layout.** `demo/<lang>/` holds one scenario per block, each with its pop written out in full and the same four steps: connect with the pop, set the source, read the job's messages, report each one. Repeat the steps in every block; do not abstract them. Media is shared: `demo/media/`.
- **Scenarios, commands, options, environment.** As in the tables above, same names, same pops. A bare run is `objects` on the sample image, which the demo finds next to its own executable so the working directory does not matter. The environment comes from the SDK's own config loading.
- **Output, to stdout, one line each:**
  - Per prediction, `prediction` followed by the fields that are present, in this order and form:
    `objects=N [label, ...]`, `keypoints=N`, `caption="..."`.
    Labels are distinct, in first-seen order. `keypoints` counts the key point sets on the objects, however deep they nest. The caption is the first `texts[].text`, else `tokens.text`. A prediction with none of them is `prediction empty`.
  - `--json` replaces that line with the prediction's JSON on one line.
  - `reconnecting (attempt N): <reason>` before each reconnect attempt and `reconnected` after it.
  - The last line of each scenario: `PASS <scenario>` or `FAIL <scenario>: <reason>`. `<scenario>` is `pop` for `--pop`.
- **Failures.** The reason is one short sentence with the fix, never a stack trace. Map the SDK's error kinds: rejected key (exchange failure), refused connection, rejected request, closed connection, file not found. An unreachable network is not an error kind: the SDK retries until the deadline, so it surfaces as the timeout, `timed out after N seconds; check your network, or raise it with --timeout` when no prediction arrived, and `timed out after N seconds; raise it with --timeout` otherwise. (A `reconnecting` line may carry a "cannot reach EyePop" reason.) A job that ends with error, or is preempted (`job was preempted`), fails the scenario.
- **Usage errors** (including `pop` as a command, a missing key when the environment needs one, a flag with no value, a repeated flag) print one line to stderr and exit `2`, before any network call.
- **Exit codes** are `0`, `1` and `2` as above.
- **Tests** cover the pure logic only: argument parsing and the summary lines, with no network.
