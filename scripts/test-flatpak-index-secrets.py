#!/usr/bin/env python3
"""Exercise token selection and preflight without real credentials or network.

Requires PyYAML. Run: python3 scripts/test-flatpak-index-secrets.py
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION = yaml.safe_load((ROOT / ".github/actions/publish-flatpak-index/action.yml").read_text())
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/publish-flatpak.yml").read_text())


class SecretTests(unittest.TestCase):
    def run_shell(self, source, values):
        with tempfile.TemporaryDirectory() as directory:
            # Reject permissions after recording the auth header. No clone or
            # push can occur, and accidental network access fails the test.
            curl = Path(directory) / "curl"
            curl.write_text(
                '#!/bin/bash\nprintf "%s\\n" "$@" > "$AUTH_CAPTURE"\n'
                'printf \'{"permissions":{"push":false}}\\n200\'\n'
            )
            curl.chmod(0o755)
            capture = Path(directory) / "auth"
            env = {
                "PATH": directory + os.pathsep + os.defpath,
                "AUTH_CAPTURE": str(capture),
                "TAGS": "latest",
                "DOCS_REPO": "tuna-os/docs",
                **values,
            }
            result = subprocess.run(
                ["bash", "-c", source], env=env, text=True, capture_output=True, timeout=5
            )
            return result, capture.read_text() if capture.exists() else ""

    def test_missing_action_token_fails_before_api(self):
        result, auth = self.run_shell(ACTION["runs"]["steps"][0]["run"], {})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FLATPAK_INDEX_TOKEN is unavailable", result.stderr)
        self.assertEqual(auth, "")

    def test_environment_and_legacy_input(self):
        for values, expected in [
            ({"FLATPAK_INDEX_TOKEN": "org-fixture"}, "org-fixture"),
            ({"TOKEN_INPUT": "legacy-fixture"}, "legacy-fixture"),
            (
                {"TOKEN_INPUT": "override-fixture", "FLATPAK_INDEX_TOKEN": "org-fixture"},
                "override-fixture",
            ),
            ({"TOKEN_INPUT": "", "FLATPAK_INDEX_TOKEN": "org-fixture"}, "org-fixture"),
        ]:
            with self.subTest(values=values):
                result, auth = self.run_shell(ACTION["runs"]["steps"][0]["run"], values)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Authorization: Bearer " + expected, auth)
                self.assertEqual(result.stdout, "::add-mask::" + expected + "\n")
                self.assertIn("cannot push", result.stderr)
                self.assertNotIn(expected, result.stderr)

    def test_workflow_action_boundary(self):
        step = next(
            step
            for step in WORKFLOW["jobs"]["publish"]["steps"]
            if "publish-flatpak-index@" in step.get("uses", "")
        )
        self.assertEqual(step["env"]["FLATPAK_INDEX_TOKEN"], "${{ secrets.FLATPAK_INDEX_TOKEN }}")
        self.assertNotIn("token", step["with"])
        self.assertFalse(ACTION["inputs"]["token"]["required"])
        action_env = ACTION["runs"]["steps"][0]["env"]
        self.assertNotIn("FLATPAK_INDEX_TOKEN", action_env)
        self.assertEqual(action_env["TOKEN_INPUT"], "${{ inputs.token }}")

    def test_workflow_preflight(self):
        step = WORKFLOW["jobs"]["arch-plan"]["steps"][0]
        self.assertEqual(step["if"], "inputs.publish")
        self.assertEqual(step["env"]["FLATPAK_INDEX_TOKEN"], "${{ secrets.FLATPAK_INDEX_TOKEN }}")
        for token, code in [("", 1), ("org-fixture", 0)]:
            result, auth = self.run_shell(step["run"], {"FLATPAK_INDEX_TOKEN": token})
            self.assertEqual(result.returncode, code)
            self.assertEqual(auth, "")
            self.assertNotIn("org-fixture", result.stdout + result.stderr)
        self.assertIn("arch-plan", WORKFLOW["jobs"]["build-oci"]["needs"])
        # BaseLoader avoids YAML 1.1 interpreting the Actions key `on` as True.
        workflow = yaml.load(
            (ROOT / ".github/workflows/publish-flatpak.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        secret = workflow["on"]["workflow_call"]["secrets"]["FLATPAK_INDEX_TOKEN"]
        self.assertEqual(secret["required"], "false")


if __name__ == "__main__":
    unittest.main()
