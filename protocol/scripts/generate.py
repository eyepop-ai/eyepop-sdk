# /// script
# requires-python = ">=3.12"
# ///
import subprocess
import sys
from pathlib import Path

from codegen import ROOTS, SchemaError, generate, load_schemas

ROOT = Path(__file__).resolve().parent.parent
TARGETS = {
    "python": ROOT.parent / "python" / "src" / "eyepop" / "protocol.py",
    "rust": ROOT.parent / "rust" / "crates" / "eyepop" / "src" / "protocol.rs",
    "go": ROOT.parent / "go" / "protocol.go",
    "csharp": ROOT.parent / "cs" / "src" / "EyePop" / "Protocol.g.cs",
}
FORMATTERS = {"go": ["gofmt"]}


def render(language: str, source: str) -> str:
    if language not in FORMATTERS:
        return source
    return subprocess.run(FORMATTERS[language], input=source, capture_output=True, text=True, check=True).stdout


def main(argv: list[str]) -> int:
    try:
        generated = generate(load_schemas(ROOT / "schema"), ROOTS)
    except SchemaError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    outputs = {language: render(language, source) for language, source in generated.items()}
    if "--check" in argv:
        stale = [path for language, path in TARGETS.items() if not path.exists() or path.read_text() != outputs[language]]
        for path in stale:
            print(f"stale: {path.relative_to(ROOT.parent)}", file=sys.stderr)
        if stale:
            print("run `task protocol:generate` and commit the result", file=sys.stderr)
        return 1 if stale else 0
    for language, path in TARGETS.items():
        path.write_text(outputs[language])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
