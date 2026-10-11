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

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts/validation"
sys.path.insert(0, str(SCRIPTS))

from check_distribution import check_distribution
from check_distribution import DistributionCheck

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

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), "-c", "user.name=Distribution Test",
             "-c", "user.email=distribution@example.invalid", *args], stderr=subprocess.PIPE).decode().strip()

    def remote_fixture(self):
        self.source = dict(source="git-subdir", url=self.repo.as_uri(),
                           path="plugins/Sample", ref="integrate/sample")
        self.expected_data["source"] = self.source.copy()
        self.save(self.expected, self.expected_data)
        for path, data in ((self.codex, self.codex_data), (self.claude, self.claude_data)):
            data["plugins"][0]["source"] = self.source.copy()
            self.save(path, data)
        self.git("init", "-b", "integrate/sample")
        self.git("add", ".")
        self.git("commit", "-m", "Initial plugin fixture")
        return self.git("rev-parse", "HEAD")

    def remote_check(self, **kwargs):
        return check_distribution(self.plugin, self.repo, self.expected, verify_remote=True, **kwargs)

    def test_remote_branch_snapshot_and_cli(self):
        commit = self.remote_fixture()
        result = self.remote_check()
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(result["remote_commit"], commit)
        self.assertEqual(self.cli("--verify-remote", "--json").returncode, 0)

    def test_remote_verification_is_explicit_and_read_only(self):
        self.remote_fixture()
        with patch.object(DistributionCheck, "git", side_effect=AssertionError("unexpected Git call")):
            self.assert_issue(self.check(), "source.remote", "UNCHECKED")
        before = self.git("status", "--porcelain=v1", "--untracked-files=all")
        self.assertEqual(self.remote_check()["exit_code"], 0)
        self.assertEqual(self.git("status", "--porcelain=v1", "--untracked-files=all"), before)

    def test_remote_source_needs_independent_expectation(self):
        self.remote_fixture()
        self.expected_data.pop("source")
        self.save(self.expected, self.expected_data)
        self.assert_issue(self.remote_check(), "catalog.source", "UNCHECKED")

    def test_remote_wrong_ref_url_or_path_in_either_catalog(self):
        self.remote_fixture()
        for path, data in ((self.codex, self.codex_data), (self.claude, self.claude_data)):
            for field, value in (("ref", "integrate/other"), ("path", "plugins/Other"),
                                 ("url", "https://example.invalid/other.git")):
                with self.subTest(path=path, field=field):
                    changed = copy.deepcopy(data)
                    changed["plugins"][0]["source"][field] = value
                    self.save(path, changed)
                    self.assert_issue(self.remote_check(), "catalog.target")
            self.save(path, data)

    def test_remote_source_cannot_fall_back_to_local_checkout(self):
        self.remote_fixture()
        self.codex_data["plugins"][0]["source"] = "./plugins/Sample"
        self.save(self.codex, self.codex_data)
        self.assert_issue(self.remote_check(), "catalog.source")

    def test_invalid_remote_expectations_and_unsupported_fields(self):
        self.remote_fixture()
        for source in ({**self.source, "sha": "a" * 40}, {**self.source, "ref": "bad*ref"},
                       {**self.source, "path": "../outside"}, {**self.source, "url": "ext::command"},
                       {**self.source, "ref": "branch/../other"}, {**self.source, "url": 123}):
            with self.subTest(source=source):
                self.save(self.expected, {**self.expected_data, "source": source})
                self.assert_issue(self.remote_check(), "input.expectations", "ERROR")

    def test_remote_checkout_content_mode_and_inventory_must_match(self):
        self.remote_fixture()
        original = self.skill.read_bytes()
        self.skill.write_text("unpublished content")
        self.assert_issue(self.remote_check(), "source.file")
        self.skill.write_bytes(original)
        self.skill.chmod(0o755)
        self.assert_issue(self.remote_check(), "source.file")
        self.skill.chmod(0o644)
        # Even a forged local expectation must not hide an extra remote file.
        extra = self.plugin / "extra.md"
        extra.write_text("published extra")
        self.git("add", ".")
        self.git("commit", "-m", "Add remote file")
        extra.unlink()
        self.assert_issue(self.remote_check(), "source.inventory")

    def test_remote_lookup_and_missing_git_objects_are_incomplete(self):
        self.remote_fixture()
        with patch.object(DistributionCheck, "git", side_effect=OSError("network unavailable")):
            self.assert_issue(self.remote_check(), "source.remote", "ERROR")
        empty = self.root / "empty"
        empty.mkdir()
        subprocess.run(["git", "init", str(empty)], capture_output=True, check=True)
        self.assert_issue(self.remote_check(source_repository=empty), "source.remote", "ERROR")

    def test_missing_remote_branch_is_not_a_local_success(self):
        self.remote_fixture()
        self.git("branch", "-m", "renamed")
        self.assert_issue(self.remote_check(), "source.remote", "ERROR")

    def test_remote_snapshot_can_be_outside_catalog_repository(self):
        self.remote_fixture()
        import shutil
        snapshot = self.root / "snapshot"
        shutil.copytree(self.plugin, snapshot)
        result = check_distribution(snapshot, self.repo, self.expected, verify_remote=True)
        self.assertEqual(result["exit_code"], 0, result)
        self.expected_data.pop("source")
        self.save(self.expected, self.expected_data)
        result = check_distribution(snapshot, self.repo, self.expected)
        self.assertEqual(result["exit_code"], 2)

    def test_same_repository_branches_resolve_independently(self):
        first = self.remote_fixture()
        original = self.skill.read_bytes()
        self.git("checkout", "-b", "integrate/other")
        self.skill.write_text("different branch content")
        self.git("add", ".")
        self.git("commit", "-m", "Update other branch only")
        second = self.git("rev-parse", "HEAD")
        self.git("checkout", "integrate/sample")
        self.assertEqual(self.remote_check()["remote_commit"], first)
        self.assertEqual(self.skill.read_bytes(), original)
        self.source["ref"] = "integrate/other"
        self.expected_data["source"] = self.source.copy()
        self.save(self.expected, self.expected_data)
        for path, data in ((self.codex, self.codex_data), (self.claude, self.claude_data)):
            data["plugins"][0]["source"] = self.source.copy()
            self.save(path, data)
        result = self.remote_check()
        self.assertEqual(result["remote_commit"], second)
        self.assert_issue(result, "source.file")
        self.skill.write_text("different branch content")
        self.assertEqual(self.remote_check()["exit_code"], 0)
        self.assertEqual(self.git("rev-parse", "integrate/sample"), first)

    def test_remote_links_and_submodules_are_not_claimed_verified(self):
        self.remote_fixture()
        self.skill.unlink()
        self.skill.symlink_to("../../.claude-plugin/plugin.json")
        self.git("add", ".")
        self.git("commit", "-m", "Replace skill with link")
        self.assert_issue(self.remote_check(), "source.kind", "UNCHECKED")


if __name__ == "__main__":
    unittest.main()
