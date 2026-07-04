"""Check pyproject dependency pins and obvious unused runtime packages."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
OS_MARKER_TOKENS = (
    "os_name",
    "platform_machine",
    "platform_release",
    "platform_system",
    "platform_version",
    "sys_platform",
)
NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
EXACT_PIN_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?\s*==\s*[A-Za-z0-9_.!+-]+"
    r"(?:\s*;.*)?$"
)


def read_pyproject() -> dict:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)


def dependency_strings(values: Iterable[object]) -> Iterable[str]:
    for value in values:
        if isinstance(value, str):
            yield value


def all_dependency_specs(config: dict) -> list[tuple[str, str]]:
    project = config.get("project", {})
    specs: list[tuple[str, str]] = []

    for spec in dependency_strings(project.get("dependencies", [])):
        specs.append(("project.dependencies", spec))

    optional = project.get("optional-dependencies", {})
    for group, values in optional.items():
        for spec in dependency_strings(values):
            specs.append((f"project.optional-dependencies.{group}", spec))

    dependency_groups = config.get("dependency-groups", {})
    for group, values in dependency_groups.items():
        for spec in dependency_strings(values):
            specs.append((f"dependency-groups.{group}", spec))

    return specs


def runtime_dependency_specs(config: dict) -> list[str]:
    project = config.get("project", {})
    specs = list(dependency_strings(project.get("dependencies", [])))
    optional = project.get("optional-dependencies", {})
    for values in optional.values():
        specs.extend(dependency_strings(values))
    return specs


def is_exact_pin(spec: str) -> bool:
    return bool(EXACT_PIN_PATTERN.match(spec)) and "*" not in spec


def package_name(spec: str) -> str:
    match = NAME_PATTERN.match(spec)
    if match is None:
        return spec
    return match.group(1).lower().replace("_", "-")


def is_os_specific(spec: str) -> bool:
    marker = spec.split(";", maxsplit=1)[1].lower() if ";" in spec else ""
    return any(token in marker for token in OS_MARKER_TOKENS)


def python_files() -> Iterable[Path]:
    for path in ROOT.rglob("*.py"):
        if EXCLUDED_DIRS.intersection(path.parts):
            continue
        yield path


def imported_modules() -> set[str]:
    imports: set[str] = set()
    for path in python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            raise SystemExit(f"{path}: cannot parse Python source: {error}") from error

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.partition(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.partition(".")[0])
    return imports


def import_names_for_package(config: dict, name: str) -> set[str]:
    configured = config.get("tool", {}).get("seekphony", {}).get("dependency-imports", {})
    value = configured.get(name)
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return {name.replace("-", "_")}


def main() -> int:
    config = read_pyproject()
    errors: list[str] = []

    for location, spec in all_dependency_specs(config):
        if not is_exact_pin(spec):
            errors.append(f"{location}: dependency must be exact-pinned: {spec!r}")

    imports = imported_modules()
    for spec in runtime_dependency_specs(config):
        if is_os_specific(spec):
            continue

        name = package_name(spec)
        expected_imports = import_names_for_package(config, name)
        if imports.isdisjoint(expected_imports):
            expected = ", ".join(sorted(expected_imports))
            errors.append(
                f"project.dependencies: {name!r} is not imported by Python source "
                f"(expected one of: {expected}). Remove it or configure "
                "[tool.seekphony.dependency-imports]."
            )

    if errors:
        print("pyproject.toml dependency checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("pyproject.toml dependencies are exact-pinned and used where checkable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
