"""Tests for the Aster local distribution profile, with independent expectations."""

import copy
import errno
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_distribution import check_distribution

SCRIPT = SCRIPTS / "check_distribution.py"


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-distribution-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.plugin = self.repo / "plugins/Sample"
        self.manifest = self.plugin / ".claude-plugin/plugin.json"
        self.skill = self.plugin / "skills/sample-skill/SKILL.md"
        self.codex = self.repo / ".agents/plugins/marketplace.json"
        self.claude = self.repo / ".claude-plugin/marketplace.json"
        self.expected = self.root / "expectations.json"
        self.manifest_data = dict(name="sample", version="0.1.0", skills="./skills/")
        self.codex_data = dict(name="sample-market", plugins=[dict(
            name="sample", source=dict(source="local", path="./plugins/Sample"),
            policy=dict(installation="AVAILABLE", authentication="ON_INSTALL"), category="Productivity")])
        self.claude_data = dict(name="sample-market", owner=dict(name="Owner"),
                                plugins=[dict(name="sample", source="./plugins/Sample")])
        self.expected_data = dict(plugin_name="sample", manifest=".claude-plugin/plugin.json",
                                  files=[".claude-plugin/plugin.json", "skills/sample-skill/SKILL.md"])
        self.save(self.manifest, self.manifest_data)
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text('---\nname: sample-skill\ndescription: sample\n---\n')
        self.save(self.codex, self.codex_data)
        self.save(self.claude, self.claude_data)
        self.save(self.expected, self.expected_data)

    def save(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def check(self):
        return check_distribution(self.plugin, self.repo, self.expected)

    def assert_issue(self, result, check_id, status="FAIL"):
        self.assertTrue(any(c["id"] == check_id and c["status"] == status for c in result["checks"]), result)

    def cli(self, *extra, no_site=False):
        return subprocess.run([sys.executable, "-B", *(["-S"] if no_site else []), str(SCRIPT),
                               str(self.plugin), "--repository-root", str(self.repo),
                               "--expected-files", str(self.expected), *extra],
                              cwd=self.root, capture_output=True, text=True, timeout=15)

    def test_valid_two_catalog_configuration(self):
        result = self.check()
        self.assertEqual((result["status"], result["exit_code"]), ("PASS", 0), result)
        self.assertEqual(result["expected_files"], result["actual_files"])

    def test_optional_version_description_and_skills_can_be_omitted(self):
        self.save(self.manifest, {"name": "sample"})
        self.assertEqual(self.check()["exit_code"], 0)

    def test_optional_string_fields_are_not_required_to_be_nonempty(self):
        self.save(self.manifest, dict(name="sample", description=""))
        self.assertEqual(self.check()["exit_code"], 0)

    def test_manifest_wrong_field_types(self):
        for field, value in (("name", 1), ("name", " "), ("version", []),
                             ("description", False), ("skills", 1), ("skills", ["./skills", None])):
            with self.subTest(field=field, value=value):
                data = dict(self.manifest_data, **{field: value})
                self.save(self.manifest, data)
                self.assertEqual(self.check()["exit_code"], 1)

    def test_manifest_name_must_match_independent_expectation(self):
        self.save(self.manifest, dict(self.manifest_data, name="other"))
        self.assert_issue(self.check(), "manifest.name")

    def test_missing_and_extra_package_files(self):
        self.skill.unlink()
        self.assert_issue(self.check(), "inventory.missing")
        self.skill.write_text("restored")
        (self.plugin / "work-notes.md").write_text("not in approved inventory")
        self.assert_issue(self.check(), "inventory.extra")

    def test_hidden_extra_files_are_not_ignored(self):
        (self.plugin / ".extra").write_text("extra")
        self.assert_issue(self.check(), "inventory.extra")

    def test_json_syntax_duplicate_keys_constants_and_nonobjects(self):
        for text in ('{"name":', '{"name":"bad","name":"sample"}',
                     '{"name":"sample","version":NaN}', '{"name":"sample","version":Infinity}', '[]'):
            with self.subTest(text=text):
                self.manifest.write_text(text)
                self.assert_issue(self.check(), "json.format")

    def test_missing_manifest_and_catalog(self):
        self.manifest.unlink()
        self.assert_issue(self.check(), "json.file")
        self.save(self.manifest, self.manifest_data)
        self.claude.unlink()
        self.assert_issue(self.check(), "json.file")

    def test_invalid_expected_input_is_execution_error(self):
        mutations = [dict(self.expected_data, files=[]),
                     dict(self.expected_data, files=["../outside"]),
                     dict(self.expected_data, files=["/absolute"]),
                     dict(self.expected_data, files=[None]),
                     dict(self.expected_data, files=self.expected_data["files"] * 2),
                     dict(self.expected_data, files=["skills/sample-skill/SKILL.md"]),
                     dict(self.expected_data, plugin_name=1),
                     dict(self.expected_data, unexpected=True)]
        for data in mutations:
            with self.subTest(data=data):
                self.save(self.expected, data)
                self.assert_issue(self.check(), "input.expectations", "ERROR")
                self.assertEqual(self.check()["exit_code"], 2)

    def test_bad_expectations_json_and_missing_file(self):
        self.expected.write_text("[broken")
        self.assert_issue(self.check(), "json.format", "ERROR")
        self.expected.unlink()
        self.assertEqual(self.check()["exit_code"], 2)

    def test_missing_or_duplicate_registration_in_either_catalog(self):
        for path, initial in ((self.codex, self.codex_data), (self.claude, self.claude_data)):
            for entries in ([], initial["plugins"] * 2):
                with self.subTest(path=path, entries=entries):
                    self.save(path, dict(initial, plugins=entries))
                    self.assert_issue(self.check(), "catalog.registration")
            self.save(path, initial)

    def test_registration_resolves_from_repository_not_catalog_parent(self):
        # The valid fixture exists only under repo/plugins, not under .agents/plugins/plugins.
        self.assertEqual(self.check()["exit_code"], 0)
        data = copy.deepcopy(self.codex_data)
        data["plugins"][0]["source"]["path"] = "./does-not-exist"
        self.save(self.codex, data)
        self.assert_issue(self.check(), "catalog.source")

    def test_two_catalogs_must_point_to_requested_plugin(self):
        (self.repo / "plugins/Other").mkdir()
        data = copy.deepcopy(self.claude_data)
        data["plugins"][0]["source"] = "./plugins/Other"
        self.save(self.claude, data)
        self.assert_issue(self.check(), "catalog.target")

    def test_codex_accepts_documented_local_string_source(self):
        data = copy.deepcopy(self.codex_data)
        data["plugins"][0]["source"] = "./plugins/Sample"
        self.save(self.codex, data)
        self.assertEqual(self.check()["exit_code"], 0)

    def test_remote_source_is_explicitly_unchecked(self):
        data = copy.deepcopy(self.claude_data)
        data["plugins"][0]["source"] = {"source": "github", "repo": "owner/example"}
        self.save(self.claude, data)
        result = self.check()
        self.assert_issue(result, "catalog.source", "UNCHECKED")
        self.assertEqual(result["exit_code"], 2)

    def test_other_plugin_paths_are_not_read(self):
        data = copy.deepcopy(self.claude_data)
        data["plugins"].append({"name": "unrelated", "source": "./unavailable-here"})
        self.save(self.claude, data)
        self.assertEqual(self.check()["exit_code"], 0)

    def test_required_catalog_shapes_and_codex_policy(self):
        for field in ("owner", "plugins", "name"):
            with self.subTest(field=field):
                self.save(self.claude, dict(self.claude_data, **{field: None}))
                self.assertEqual(self.check()["exit_code"], 1)
        self.save(self.claude, self.claude_data)
        for field in ("policy", "category"):
            data = copy.deepcopy(self.codex_data)
            data["plugins"][0].pop(field)
            self.save(self.codex, data)
            self.assertEqual(self.check()["exit_code"], 1)

    def test_bad_source_paths_are_not_resolved(self):
        for value in ("plugins/Sample", "./../outside", "/absolute", "./plugins\\Sample", None):
            with self.subTest(value=value):
                data = copy.deepcopy(self.claude_data)
                data["plugins"][0]["source"] = value
                self.save(self.claude, data)
                self.assert_issue(self.check(), "catalog.source")

    def test_skills_path_array_and_root_path(self):
        for paths in (["./skills"], ".", "./"):
            with self.subTest(paths=paths):
                self.save(self.manifest, dict(self.manifest_data, skills=paths))
                self.assertEqual(self.check()["exit_code"], 0)

    def test_invalid_skills_directory(self):
        for value in ("./missing", "./../outside", "skills", "./.claude-plugin/plugin.json"):
            with self.subTest(value=value):
                self.save(self.manifest, dict(self.manifest_data, skills=value))
                self.assert_issue(self.check(), "manifest.skills")

    def test_extra_manifest_field_is_not_claimed_validated(self):
        self.save(self.manifest, dict(self.manifest_data, author={"name": "Owner"}))
        result = self.check()
        self.assert_issue(result, "manifest.optional", "UNCHECKED")
        self.assertEqual(result["exit_code"], 2)

    def test_outside_file_symlink_is_a_boundary_failure(self):
        outside = self.root / "outside.md"
        outside.write_text("outside")
        self.skill.unlink()
        self.skill.symlink_to(outside)
        self.assert_issue(self.check(), "inventory.boundary")

    def test_internal_file_symlink_is_allowed_when_inventory_matches(self):
        original = self.skill.parent / "original.md"
        original.write_text("original")
        self.skill.unlink()
        self.skill.symlink_to("original.md")
        data = copy.deepcopy(self.expected_data)
        data["files"].append("skills/sample-skill/original.md")
        self.save(self.expected, data)
        self.assertEqual(self.check()["exit_code"], 0)

    def test_directory_symlink_is_not_a_complete_inventory(self):
        (self.plugin / "loop").symlink_to(self.plugin, target_is_directory=True)
        result = self.check()
        self.assert_issue(result, "inventory.symlink", "UNCHECKED")
        self.assert_issue(result, "inventory.compare", "UNCHECKED")

    def test_broken_symlink_and_outside_catalog_target(self):
        self.skill.unlink()
        self.skill.symlink_to("missing.md")
        self.assert_issue(self.check(), "inventory.file")
        outside = self.root / "outside"
        outside.mkdir()
        (self.repo / "plugins/Alias").symlink_to(outside, target_is_directory=True)
        data = copy.deepcopy(self.claude_data)
        data["plugins"][0]["source"] = "./plugins/Alias"
        self.save(self.claude, data)
        self.assert_issue(self.check(), "catalog.source")

    def test_directory_enumeration_errors_prevent_complete_inventory(self):
        denied = PermissionError(errno.EACCES, "denied", str(self.plugin))
        with patch("os.scandir", side_effect=denied):
            result = self.check()
        self.assert_issue(result, "inventory.read", "ERROR")
        self.assert_issue(result, "inventory.compare", "UNCHECKED")

    def test_unreadable_inputs_and_missing_repository(self):
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            self.assert_issue(self.check(), "json.read", "ERROR")
        self.assertEqual(check_distribution(self.plugin, self.root / "absent", self.expected)["exit_code"], 2)

    def test_directory_metadata_error_prevents_complete_inventory(self):
        with patch.object(Path, "is_symlink", side_effect=PermissionError("denied")):
            result = self.check()
        self.assert_issue(result, "inventory.read", "ERROR")
        self.assert_issue(result, "inventory.compare", "UNCHECKED")

    def test_cli_json_no_dependencies_and_no_mutation(self):
        def snapshot():
            return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.repo.rglob('*') if p.is_file()}
        before = snapshot()
        run = self.cli("--json", no_site=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "PASS")
        self.assertEqual(before, snapshot())

    def test_cli_failure_incomplete_text_and_help(self):
        self.skill.unlink()
        self.assertEqual(self.cli("--json").returncode, 1)
        self.expected.unlink()
        self.assertEqual(self.cli("--json").returncode, 2)
        self.assertIn("INCOMPLETE", self.cli().stdout)
        run = subprocess.run([sys.executable,"-B",str(SCRIPT),"--help"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)


if __name__ == "__main__":
    unittest.main()
