# /// script
# requires-python = ">=3.12"
# dependencies = ["jsonschema>=4.23", "referencing>=0.35"]
# ///
import json
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, NamedTuple

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parent.parent
UNIONS = MappingProxyType({"command": "command.json", "message": "message.json"})
EXPECTED = "expected.json"


class Failure(NamedTuple):
    example: str
    kind: str


def load_registry(root: Path) -> Registry:
    registry = Registry()
    for path in sorted((root / "schema").glob("*.json")):
        document = json.loads(path.read_text())
        registry = registry.with_resource(document["$id"], Resource.from_contents(document, DRAFT202012))
    return registry


def schema_for(example: Path, unions: Mapping[str, str]) -> str:
    kind = example.name.split("-", 1)[0]
    if kind not in unions:
        raise SystemExit(f"{example.name}: file name must start with one of {sorted(unions)} followed by '-'")
    return unions[kind]


def validator(root: Path, registry: Registry, schema_file: str) -> Draft202012Validator:
    path = root / "schema" / schema_file
    if not path.exists():
        raise SystemExit(f"missing schema/{schema_file}")
    return Draft202012Validator(json.loads(path.read_text()), registry=registry)


def rejection(root: Path, registry: Registry, union: str, instance: object) -> tuple[str, str]:
    variant = f"{instance.get('type')}.json" if isinstance(instance, dict) else None
    schema_file = variant if variant and (root / "schema" / variant).exists() else union
    error = best_match(validator(root, registry, schema_file).iter_errors(instance))
    if error is None:
        error = best_match(validator(root, registry, union).iter_errors(instance))
    path = "".join(f"/{part}" for part in error.absolute_path)
    return path, error.validator


def members(root: Path, union: str) -> list[str]:
    document = json.loads((root / "schema" / union).read_text())
    return [Path(branch["$ref"]).stem for branch in document.get("oneOf", [])]


def const_type(root: Path, name: str) -> str | None:
    path = root / "schema" / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text()).get("properties", {}).get("type", {}).get("const")


def refs(node: object) -> list[str]:
    if isinstance(node, dict):
        own = [Path(node["$ref"]).stem] if isinstance(node.get("$ref"), str) else []
        return own + [name for child in node.values() for name in refs(child)]
    if isinstance(node, list):
        return [name for child in node for name in refs(child)]
    return []


def reachable(root: Path, unions: Mapping[str, str]) -> set[str]:
    seen: set[str] = set()
    pending = [Path(union).stem for union in unions.values()]
    while pending:
        name = pending.pop()
        path = root / "schema" / f"{name}.json"
        if name in seen or not path.exists():
            continue
        seen.add(name)
        pending.extend(refs(json.loads(path.read_text())))
    return seen


def is_schema(path: Path) -> bool:
    try:
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    except SchemaError:
        return False
    return True


def check(root: Path, unions: Mapping[str, str] = UNIONS) -> list[Failure]:
    listed = [name for union in unions.values() for name in members(root, union)]
    missing = [name for name in listed if not (root / "schema" / f"{name}.json").exists()]
    if missing:
        return [Failure(f"schema/{name}.json", "missing_variant") for name in missing]
    broken = [path.stem for path in sorted((root / "schema").glob("*.json")) if not is_schema(path)]
    if broken:
        return [Failure(f"schema/{name}.json", "invalid_schema") for name in broken]
    registry = load_registry(root)
    manifest = root / "examples" / "invalid" / EXPECTED
    expected = json.loads(manifest.read_text()) if manifest.exists() else {}
    failures = [
        Failure(f"schema/{name}.json", "in_two_unions") for name in sorted(set(listed)) if listed.count(name) > 1
    ]
    failures += [
        Failure(f"schema/{name}.json", "type_mismatch")
        for union in unions.values()
        for name in members(root, union)
        if const_type(root, name) not in (None, name)
    ]
    seen = reachable(root, unions)
    failures += [
        Failure(f"schema/{path.stem}.json", "unreachable")
        for path in sorted((root / "schema").glob("*.json"))
        if const_type(root, path.stem) is not None and path.stem not in seen
    ]
    count = 0
    for accepted, folder in ((True, "valid"), (False, "invalid")):
        for example in sorted((root / "examples" / folder).glob("*.json")):
            if example.name == EXPECTED:
                continue
            count += 1
            union = schema_for(example, unions)
            instance = json.loads(example.read_text())
            name = f"{folder}/{example.name}"
            if validator(root, registry, union).is_valid(instance) != accepted:
                failures.append(Failure(name, "rejected" if accepted else "accepted"))
            elif not accepted and example.name not in expected:
                failures.append(Failure(name, "no_expectation"))
            elif not accepted:
                path, keyword = rejection(root, registry, union, instance)
                if expected[example.name] != {"path": path, "keyword": keyword}:
                    failures.append(Failure(name, "wrong_rule"))
    for name in sorted(expected):
        if not (root / "examples" / "invalid" / name).exists():
            failures.append(Failure(f"invalid/{name}", "stale_expectation"))
    if count == 0:
        failures.append(Failure("", "no_examples"))
    return failures


def main() -> int:
    failures = check(ROOT, UNIONS)
    for failure in failures:
        print(f"{failure.example}: {failure.kind}", file=sys.stderr)
    print(f"{'FAILED' if failures else 'ok'}: {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
