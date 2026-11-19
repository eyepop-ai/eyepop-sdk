# /// script
# requires-python = ">=3.12"
# ///
import sys
from pathlib import Path

from codegen import generate, load_schemas

ROOT = Path(__file__).resolve().parent.parent
ROOTS = ("command", "message")
TARGETS = {"python": ROOT.parent / "python" / "src" / "eyepop" / "protocol.py"}


def main(argv: list[str]) -> int:
    outputs = generate(load_schemas(ROOT / "schema"), ROOTS)
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
