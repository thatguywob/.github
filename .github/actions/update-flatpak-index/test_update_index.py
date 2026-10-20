#!/usr/bin/env python3
"""Unit and fixture tests for the update-flatpak-index action script."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("update-index.py")
_SPEC = importlib.util.spec_from_file_location("update_index", SCRIPT)
update_index = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(update_index)


REQUIRED_LABELS = {
    "org.flatpak.ref": "app/org.example.App/x86_64/stable",
    "org.flatpak.metadata": "metadata",
}
APPSTREAM_LABELS = {
    "org.freedesktop.appstream.appdata": "appdata",
    "org.freedesktop.appstream.icon-64": "icon-64",
    "org.freedesktop.appstream.icon-128": "icon-128",
}


class UpdateIndexTests(unittest.TestCase):
    def write_oci_layout(self, root, labels=None, architecture="x86_64"):
        labels = labels if labels is not None else {**REQUIRED_LABELS, **APPSTREAM_LABELS}
        oci_dir = Path(root) / "oci"
        blobs = oci_dir / "blobs" / "sha256"
        blobs.mkdir(parents=True)

        manifest_digest = "sha256:" + "1" * 64
        config_digest = "sha256:" + "2" * 64
        (oci_dir / "index.json").write_text(
            json.dumps({"manifests": [{"digest": manifest_digest}]}), encoding="utf-8"
        )
        (blobs / manifest_digest.split(":", 1)[1]).write_text(
            json.dumps({"config": {"digest": config_digest}}), encoding="utf-8"
        )
        (blobs / config_digest.split(":", 1)[1]).write_text(
            json.dumps(
                {
                    "architecture": architecture,
                    "config": {"Labels": labels},
                }
            ),
            encoding="utf-8",
        )
        return oci_dir, manifest_digest

    def test_read_oci_layout_resolves_manifest_and_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            oci_dir, manifest_digest = self.write_oci_layout(temp_dir)

            actual_digest, config = update_index.read_oci_layout(oci_dir)

        self.assertEqual(actual_digest, manifest_digest)
        self.assertEqual(config["architecture"], "x86_64")
        self.assertEqual(
            config["config"]["Labels"],
            {**REQUIRED_LABELS, **APPSTREAM_LABELS},
        )

    def test_read_oci_layout_rejects_missing_or_empty_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(FileNotFoundError, "index.json not found"):
                update_index.read_oci_layout(Path(temp_dir) / "missing")

            oci_dir = Path(temp_dir) / "empty"
            oci_dir.mkdir()
            (oci_dir / "index.json").write_text(
                json.dumps({"manifests": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "No manifests listed"):
                update_index.read_oci_layout(oci_dir)

    def test_filter_labels_keeps_flatpak_and_appstream_contract(self):
        labels = {
            **REQUIRED_LABELS,
            **APPSTREAM_LABELS,
            "com.example.internal": "drop-me",
        }

        self.assertEqual(
            update_index.filter_labels(labels),
            {**REQUIRED_LABELS, **APPSTREAM_LABELS},
        )
        self.assertEqual(update_index.filter_labels(None), {})

    def test_build_image_entry_requires_flatpak_labels(self):
        with self.assertRaisesRegex(ValueError, "org.flatpak.metadata"):
            update_index.build_image_entry(
                "sha256:" + "1" * 64,
                {"config": {"Labels": {"org.flatpak.ref": "app/example"}}},
                ["latest"],
                False,
            )

    def test_build_image_entry_warns_for_optional_appstream_metadata(self):
        labels = dict(REQUIRED_LABELS)
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            entry = update_index.build_image_entry(
                "sha256:" + "1" * 64,
                {"config": {"Labels": labels}},
                ["latest"],
                False,
            )

        self.assertIn("No AppStream metadata", stderr.getvalue())
        self.assertEqual(entry["Architecture"], "amd64")
        self.assertEqual(entry["OS"], "linux")
        self.assertEqual(entry["Labels"], labels)

    def test_build_image_entry_can_require_appstream_metadata(self):
        with self.assertRaisesRegex(ValueError, "No AppStream metadata"):
            update_index.build_image_entry(
                "sha256:" + "1" * 64,
                {"config": {"Labels": dict(REQUIRED_LABELS)}},
                ["latest"],
                True,
            )

    def test_merge_entry_replaces_same_architecture_and_application_only(self):
        old_app = {
            "Architecture": "x86_64",
            "Labels": {"org.flatpak.ref": "app/old"},
            "Digest": "old",
        }
        other_arch = {
            "Architecture": "aarch64",
            "Labels": {"org.flatpak.ref": "app/old"},
            "Digest": "arm",
        }
        other_app = {
            "Architecture": "x86_64",
            "Labels": {"org.flatpak.ref": "app/other"},
            "Digest": "other",
        }
        index = {
            "Results": [
                {
                    "Name": "tuna-os/example",
                    "Images": [old_app, other_arch, other_app],
                }
            ]
        }
        replacement = {
            "Architecture": "x86_64",
            "Labels": {"org.flatpak.ref": "app/old"},
            "Digest": "new",
        }

        update_index.merge_entry(index, "tuna-os/example", replacement)

        images = index["Results"][0]["Images"]
        self.assertEqual([image["Digest"] for image in images], ["arm", "other", "new"])

    def test_merge_entry_adds_and_sorts_new_repository(self):
        index = {"Results": [{"Name": "z-repo", "Images": []}]}
        image = {
            "Architecture": "x86_64",
            "Labels": {"org.flatpak.ref": "app/example"},
            "Digest": "digest",
        }

        update_index.merge_entry(index, "a-repo", image)

        self.assertEqual(
            [result["Name"] for result in index["Results"]],
            ["a-repo", "z-repo"],
        )
        self.assertEqual(index["Results"][0]["Images"], [image])

    def test_main_creates_index_with_registry_and_persisted_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            oci_dir, manifest_digest = self.write_oci_layout(temp_dir)
            index_file = Path(temp_dir) / "index" / "static"
            argv = [
                "update-index.py",
                "--oci-dir",
                str(oci_dir),
                "--index-file",
                str(index_file),
                "--repo-name",
                "tuna-os/example",
                "--registry",
                "registry.example",
                "--tags",
                "latest",
                "stable",
            ]

            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                update_index.main()

            index = json.loads(index_file.read_text(encoding="utf-8"))

        self.assertEqual(index["Registry"], "https://registry.example")
        self.assertEqual(index["Results"][0]["Name"], "tuna-os/example")
        image = index["Results"][0]["Images"][0]
        self.assertEqual(image["Digest"], manifest_digest)
        self.assertEqual(image["Tags"], ["latest", "stable"])
        self.assertEqual(image["Labels"], {**REQUIRED_LABELS, **APPSTREAM_LABELS})


if __name__ == "__main__":
    unittest.main(verbosity=2)
