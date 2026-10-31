#!/usr/bin/env python3
"""Validate experimental enrollments and report local, read-only policy checks."""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
# Imports of the shared checkers must not create __pycache__ in this checkout.
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / ".github/scripts"))
import ci_contract  # noqa: E402


def load_permissions_checker():
    spec = importlib.util.spec_from_file_location(
        "workflow_permissions", ROOT / "scripts/check-workflow-permissions.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


permissions = load_permissions_checker()
MAX_BYTES = 65536
HEADER = "| Repo | Default branch | ROADMAP.md? |"
NAME = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")


class DeclarationError(ValueError):
    pass


def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DeclarationError(f"{path}: duplicate key {key!r}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise DeclarationError(f"{path}: invalid JSON constant {value}")

    try:
        with path.open("rb") as file:
            data = file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise DeclarationError(f"{path}: exceeds {MAX_BYTES} bytes")
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=invalid_constant
        )
    except DeclarationError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise DeclarationError(f"{path}: {exc}") from exc


def inventory_names(path):
    """Read the generated active-repository table; reject ambiguous inventories."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise DeclarationError(f"{path}: {exc}") from exc
    if lines.count(HEADER) != 1:
        raise DeclarationError(f"{path}: expected exactly one repository table")
    start = lines.index(HEADER)
    if start + 1 >= len(lines) or lines[start + 1] != "|---|---|---|":
        raise DeclarationError(f"{path}: invalid repository table separator")
    names = set()
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3 or not NAME.fullmatch(cells[0]) or not cells[1] or not cells[2]:
            raise DeclarationError(f"{path}: malformed repository row: {line}")
        if cells[0].casefold() in {name.casefold() for name in names}:
            raise DeclarationError(f"{path}: duplicate repository {cells[0]!r}")
        names.add(cells[0])
    if not names:
        raise DeclarationError(f"{path}: repository table is empty")
    return names


def validate_declaration(data, schema, names):
    errors = sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.path)))
    if errors:
        error = errors[0]
        location = "/" + "/".join(map(str, error.absolute_path))
        raise DeclarationError(f"{location}: {error.message}")
    seen = set()
    for i, entry in enumerate(data["repositories"]):
        name = entry["name"]
        if name not in names:
            raise DeclarationError(
                f"/repositories/{i}/name: unknown repository {name!r} in ROADMAP-INDEX.md"
            )
        if name.casefold() in seen:
            raise DeclarationError(f"/repositories/{i}/name: duplicate repository {name!r}")
        seen.add(name.casefold())


def check_profile(repo_path, profile):
    workflows = repo_path / ".github/workflows"
    if not repo_path.is_dir():
        return "unavailable", [f"checkout missing: {repo_path}"]
    if not workflows.is_dir():
        return "fail", [f"{workflows}: workflows directory missing"]
    try:
        if profile == "workflow-permissions":
            files = permissions.find_workflow_files(workflows)
            if not files:
                return "fail", [f"{workflows}: no workflow files"]
            violations = [violation for file in files for violation in permissions.check_file(file)]
        else:
            criteria = repo_path / ".github/green-criteria.yml"
            # The shared validator intentionally skips absent files. Enrollment must not.
            if not criteria.is_file():
                return "fail", [f"{criteria}: enrolled CI contract is missing"]
            parsed = ci_contract.yaml.safe_load(criteria.read_text(encoding="utf-8"))
            criteria_list = parsed.get("criteria") if isinstance(parsed, dict) else None
            if (
                not isinstance(criteria_list, list)
                or not criteria_list
                or not all(isinstance(item, dict) for item in criteria_list)
                or not any(item.get("gates") for item in criteria_list)
            ):
                return "fail", [f"{criteria}: expected nonempty criteria with at least one gate"]
            with contextlib.redirect_stdout(io.StringIO()):
                violations, skipped = ci_contract.validate_ci_contract(
                    str(criteria), str(workflows)
                )
            if skipped:
                return "fail", [f"{criteria}: enrolled CI contract was skipped"]
        return ("fail" if violations else "pass"), violations
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        ci_contract.yaml.YAMLError,
    ) as exc:
        return "fail", [f"{profile}: cannot evaluate: {exc}"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--declaration", type=Path, default=ROOT / "organization/enrollment.example.json"
    )
    parser.add_argument("--inventory", type=Path, default=ROOT / "ROADMAP-INDEX.md")
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="directory containing local checkouts named after repositories",
    )
    args = parser.parse_args(argv)
    try:
        schema = read_json(ROOT / "organization/enrollment.schema.json")
        data = read_json(args.declaration)
        validate_declaration(data, schema, inventory_names(args.inventory))
    except DeclarationError as exc:
        print(f"declaration error: {exc}", file=sys.stderr)
        return 2
    results = []
    for entry in data["repositories"]:
        for profile in entry["profiles"]:
            status, diagnostics = check_profile(args.workspace / entry["name"], profile)
            results.append(
                {
                    "repository": entry["name"],
                    "profile": profile,
                    "status": status,
                    "diagnostics": diagnostics,
                }
            )
    print(json.dumps({"schema_version": 1, "results": results}, indent=2))
    return 1 if any(result["status"] != "pass" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
