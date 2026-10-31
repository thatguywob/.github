#!/usr/bin/env python3
"""Offline conformance and rejection tests for the enrollment prototype."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "enrollment_report", ROOT / "scripts/enrollment-report.py"
)
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)
SCHEMA = report.read_json(ROOT / "organization/enrollment.schema.json")
VALID = {
    "schema_version": 1,
    "repositories": [{"name": "app", "profiles": ["workflow-permissions"]}],
}
INVENTORY = (
    "| Repo | Default branch | ROADMAP.md? |\n|---|---|---|\n"
    "| app | main | ✅ |\n| image | dev | ❌ (note) |\n| infra | main | ✅ |\n\n"
)


class DeclarationTests(unittest.TestCase):
    def test_example_valid_against_committed_inventory(self):
        data = report.read_json(ROOT / "organization/enrollment.example.json")
        report.validate_declaration(data, SCHEMA, report.inventory_names(ROOT / "ROADMAP-INDEX.md"))

    def test_valid_and_rejection_fixtures(self):
        report.validate_declaration(VALID, SCHEMA, {"app"})
        fixtures = [
            ({**VALID, "schema_version": 2}, "/schema_version"),
            ({**VALID, "schema_version": True}, "/schema_version"),
            ({**VALID, "unexpected": 1}, "/:"),
            (
                {**VALID, "repositories": [{"name": "missing", "profiles": ["ci-contract"]}]},
                "/repositories/0/name: unknown",
            ),
            (
                {**VALID, "repositories": [{"name": "app", "profiles": ["unknown"]}]},
                "/repositories/0/profiles/0",
            ),
            (
                {**VALID, "repositories": [{"name": "app", "profiles": []}]},
                "/repositories/0/profiles",
            ),
            (
                {
                    **VALID,
                    "repositories": [{"name": "app", "profiles": ["ci-contract", "ci-contract"]}],
                },
                "/repositories/0/profiles",
            ),
            (
                {**VALID, "repositories": [VALID["repositories"][0], VALID["repositories"][0]]},
                "/repositories/1/name: duplicate",
            ),
            (
                {**VALID, "repositories": [{"name": "../app", "profiles": ["ci-contract"]}]},
                "/repositories/0/name",
            ),
            (
                {
                    **VALID,
                    "repositories": [{"name": "app", "profiles": ["ci-contract"], "owner": "x"}],
                },
                "/repositories/0",
            ),
        ]
        for data, diagnostic in fixtures:
            with self.subTest(data=data), self.assertRaises(report.DeclarationError) as err:
                report.validate_declaration(copy.deepcopy(data), SCHEMA, {"app"})
            self.assertIn(diagnostic, str(err.exception))

    def test_strict_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "declaration.json"
            for content, diagnostic in [
                (b'{"x":1,"x":2}', "duplicate key"),
                (b'{"x":NaN}', "invalid JSON constant"),
                (b"{", "declaration.json"),
                (b"\xff", "declaration.json"),
                (b" " * (report.MAX_BYTES + 1), "exceeds"),
            ]:
                path.write_bytes(content)
                with (
                    self.subTest(content=content[:20]),
                    self.assertRaises(report.DeclarationError) as err,
                ):
                    report.read_json(path)
                self.assertIn(diagnostic, str(err.exception))

    def test_inventory_rejects_ambiguous_or_malformed_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            path.write_text(INVENTORY, encoding="utf-8")
            self.assertEqual(report.inventory_names(path), {"app", "image", "infra"})
            for content in [
                "missing",
                INVENTORY + INVENTORY,
                INVENTORY.replace("| image |", "| app |"),
                INVENTORY.replace("| image | dev | ❌ (note) |", "| bad | row |"),
            ]:
                path.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(report.DeclarationError):
                    report.inventory_names(path)


class ReportTests(unittest.TestCase):
    def test_cli_three_repositories_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "index.md"
            index.write_text(INVENTORY, encoding="utf-8")
            declaration = root / "declaration.json"
            declaration.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repositories": [
                            {"name": "app", "profiles": ["workflow-permissions"]},
                            {"name": "image", "profiles": ["workflow-permissions", "ci-contract"]},
                            {"name": "infra", "profiles": ["workflow-permissions"]},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            for name in ("app", "image", "infra"):
                workflows = root / name / ".github/workflows"
                workflows.mkdir(parents=True)
                (workflows / "test.yml").write_text(
                    "on: push\npermissions:\n  contents: read\njobs:\n  build:\n"
                    "    steps:\n      - name: Check\n        run: echo ok\n",
                    encoding="utf-8",
                )
            criteria = root / "image/.github/green-criteria.yml"
            criteria.write_text(
                "criteria:\n  - id: build\n    freshness_sla_days: 1\n    asserted_by: test.yml\n"
                "    gates:\n      - workflow: test.yml\n        jobs:\n          build: Check\n",
                encoding="utf-8",
            )
            before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            command = [
                sys.executable,
                str(ROOT / "scripts/enrollment-report.py"),
                "--workspace",
                str(root),
                "--inventory",
                str(index),
                "--declaration",
                str(declaration),
            ]
            run = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            self.assertEqual([r["status"] for r in json.loads(run.stdout)["results"]], ["pass"] * 4)
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob("*") if p.is_file()})
            (root / "app/.github/workflows/test.yml").write_text("on: push\n", encoding="utf-8")
            criteria.unlink()
            (root / "infra/.github/workflows/test.yml").unlink()
            run = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 1)
            results = json.loads(run.stdout)["results"]
            self.assertEqual([r["status"] for r in results], ["fail", "pass", "fail", "fail"])
            self.assertIn("missing", results[2]["diagnostics"][0])
            self.assertIn("no workflow", results[3]["diagnostics"][0])
            declaration.write_text('{"schema_version":2,"repositories":[]}', encoding="utf-8")
            run = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, "")
            self.assertIn("declaration error", run.stderr)

    def test_ci_contract_violations_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "build.yml").write_text("on: push\njobs: {}\n", encoding="utf-8")
            (root / ".github/green-criteria.yml").write_text(
                "criteria:\n  - id: build\n    freshness_sla_days: 1\n"
                "    asserted_by: build.yml\n    gates:\n      - workflow: build.yml\n"
                "        jobs:\n          missing: Check\n",
                encoding="utf-8",
            )
            status, diagnostics = report.check_profile(root, "ci-contract")
            self.assertEqual(status, "fail")
            self.assertIn("has no job 'missing'", diagnostics[0])

    def test_missing_checkout_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, diagnostics = report.check_profile(
                Path(tmp) / "missing", "workflow-permissions"
            )
            self.assertEqual(status, "unavailable")
            self.assertIn("checkout missing", diagnostics[0])

    def test_empty_or_bad_ci_criteria_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github/workflows").mkdir(parents=True)
            criteria = root / ".github/green-criteria.yml"
            for content in [
                "",
                "criteria: []",
                "criteria: [null]",
                "criteria: [",
                "criteria: [{id: x}]",
            ]:
                criteria.write_text(content, encoding="utf-8")
                with self.subTest(content=content):
                    self.assertEqual(report.check_profile(root, "ci-contract")[0], "fail")


if __name__ == "__main__":
    unittest.main()
