"""Check plugin versions and real pre-push rejection using disposable repositories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKS = Path(__file__).resolve().parents[2]
SCRIPT = CHECKS / "scripts/validation/check_plugin_versions.py"
HOOK = CHECKS / "scripts/git/pre-push"


class PluginVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-plugin-versions-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", LC_ALL="C")
        self.git("init", "--bare", "--initial-branch=main", str(self.remote), cwd=self.root)
        self.git("init", "--initial-branch=main", str(self.repo), cwd=self.root)
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", str(self.remote))
        self.manifest("Camellia", "0.1.0")
        self.manifest("Other", "0.2.0")
        self.write("plugins/Camellia/skills/one/SKILL.md", "original\n")
        self.write("plugins/Other/mcp/server.py", "original\n")
        self.write_project_tools()
        self.base = self.commit()
        self.git("push", "origin", "main")

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(["git", "-C", str(cwd or self.repo), *args],
                                env=self.env, capture_output=True, text=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout.strip()
        return result

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def write_project_tools(self):
        self.write("tools/scripts/git/pre-push", HOOK.read_text())
        (self.repo / "tools/scripts/git/pre-push").chmod(0o755)
        self.write("tools/scripts/validation/check_plugin_versions.py", SCRIPT.read_text())

    def manifest(self, name, version):
        self.write(f"plugins/{name}/.claude-plugin/plugin.json",
                   json.dumps({"name": name.lower(), "version": version}) + "\n")

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "--allow-empty", "-m", "Test change")
        return self.git("rev-parse", "HEAD")

    def check_versions(self, expected=0, *options, base=None, target="HEAD", staged=False):
        args = ["check", "--base", base or self.base]
        args += ["--staged"] if staged else ["--target", target]
        result = self.run_script(*args, *options)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def run_script(self, *args, input=None):
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *args],
                              cwd=self.repo, env=self.env, input=input, text=True,
                              capture_output=True, timeout=30)

    def install_hook(self):
        # Test the project hook through the agreed caller contract.
        # Hortulanus owns production installation and its integration tests.
        hook = self.repo / ".git/hooks/pre-push"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text('#!/bin/sh\nset -eu\nrepo_root=$(git rev-parse --show-toplevel)\n'
                        'exec "$repo_root/tools/scripts/git/pre-push" "$@"\n')
        hook.chmod(0o755)

    def remote_head(self, ref="main"):
        return self.git("rev-parse", f"refs/heads/{ref}", cwd=self.remote)

    def test_common_changes_ignore_even_invalid_unchanged_plugin(self):
        self.manifest("Other", "invalid")
        base = self.commit()
        for path in ("AGENTS.md", ".agents/skills/skill-lifecycle/SKILL.md",
                     "tools/scripts/git/shared.py", ".agents/plugins/marketplace.json",
                     "plugins/catalog.txt"):
            self.write(path, "common change\n")
        self.commit()
        output = self.check_versions(base=base)
        self.assertNotIn("FAIL", output)

    def test_only_changed_plugin_is_checked(self):
        self.manifest("Other", "invalid")
        base = self.commit()
        self.manifest("Camellia", "0.1.1")
        self.commit()
        output = self.check_versions(base=base)
        self.assertIn("Camellia", output)
        self.assertNotIn("Other", output)

    def test_changed_skill_without_version_increase_fails(self):
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.commit()
        self.assertIn("Camellia", self.check_versions(1))

    def test_multiple_commits_need_only_final_version_increase(self):
        self.write("plugins/Camellia/skills/one/SKILL.md", "first\n")
        self.commit()
        self.write("plugins/Camellia/mcp/server.py", "second\n")
        self.commit()
        self.manifest("Camellia", "0.1.1")
        self.commit()
        self.check_versions()

    def test_multiple_plugins_are_independent(self):
        self.manifest("Camellia", "0.1.1")
        self.write("plugins/Other/mcp/server.py", "changed\n")
        self.commit()
        output = self.check_versions(1)
        self.assertIn("OK plugins/Camellia", output)
        self.assertIn("FAIL plugins/Other", output)

    def test_uncommitted_version_increase_cannot_fix_committed_target(self):
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.commit()
        self.manifest("Camellia", "0.1.1")
        self.git("add", "plugins/Camellia/.claude-plugin/plugin.json")
        before = self.git("status", "--porcelain")
        self.check_versions(1)
        self.check_versions(staged=True)
        self.assertEqual(before, self.git("status", "--porcelain"))

    def test_unstaged_version_increase_cannot_fix_index(self):
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.git("add", "plugins/Camellia/skills/one/SKILL.md")
        self.manifest("Camellia", "0.1.1")
        self.check_versions(1, staged=True)

    def test_numeric_order_prerelease_and_build_metadata(self):
        for old, new, expected in (("1.9.0", "1.10.0", 0), ("1.10.0", "1.9.0", 1),
                                   ("1.0.0-rc.2", "1.0.0-rc.10", 0),
                                   ("1.0.0-rc.10", "1.0.0", 0),
                                   ("1.0.0", "1.0.0-rc.1", 1),
                                   ("1.0.0+old", "1.0.0+new", 1)):
            with self.subTest(old=old, new=new):
                self.manifest("Camellia", old)
                base = self.commit()
                self.manifest("Camellia", new)
                self.commit()
                self.check_versions(expected, base=base)

    def test_invalid_or_missing_version_is_rejected(self):
        for value in (None, 2, "", "1.2", "v1.2.3", "01.2.3", "1.0.0-01", "1.0.0+"):
            with self.subTest(value=value):
                self.manifest("Camellia", value)
                self.commit()
                self.check_versions(1)

    def test_invalid_json_and_ambiguous_manifests_are_rejected(self):
        path = "plugins/Camellia/.claude-plugin/plugin.json"
        for value in ('{', '[]', '{"version":"0.2.0","version":"0.3.0"}'):
            with self.subTest(value=value):
                self.write(path, value)
                self.commit()
                self.check_versions(1)
        self.manifest("Camellia", "0.2.0")
        self.write("plugins/Camellia/.codex-plugin/plugin.json", '{"version":"0.2.0"}')
        self.commit()
        self.check_versions(1)

    def test_new_plugin_and_complete_deletion(self):
        self.manifest("New", "0.1.0")
        self.commit()
        self.assertIn("NEW", self.check_versions())
        self.git("rm", "-r", "plugins/Camellia")
        self.commit()
        self.assertIn("REMOVED", self.check_versions())

    def test_deleting_only_manifest_is_not_plugin_removal(self):
        self.git("rm", "plugins/Camellia/.claude-plugin/plugin.json")
        self.commit()
        self.check_versions(1)

    def test_file_deletion_rename_and_mode_change_require_version(self):
        path = "plugins/Camellia/skills/one/SKILL.md"
        self.git("mv", path, "plugins/Camellia/skills/one/renamed.md")
        renamed = self.commit()
        self.check_versions(1)
        (self.repo / "plugins/Camellia/skills/one/renamed.md").chmod(0o755)
        self.git("add", "plugins/Camellia/skills/one/renamed.md")
        self.git("commit", "-m", "Change executable bit")
        self.check_versions(1, base=renamed)
        self.git("rm", "plugins/Camellia/skills/one/renamed.md")
        self.commit()
        self.check_versions(1)

    def test_manifest_symlink_is_rejected(self):
        manifest = self.repo / "plugins/Camellia/.claude-plugin/plugin.json"
        manifest.unlink()
        manifest.symlink_to("../../Other/.claude-plugin/plugin.json")
        self.commit()
        self.check_versions(1)

    def test_spaces_and_newlines_in_changed_paths(self):
        self.write("plugins/Camellia/skills/space and\nnewline.md", "new\n")
        self.commit()
        self.check_versions(1)

    def test_real_hook_blocks_and_then_allows_push_without_touching_worktree(self):
        self.install_hook()
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.commit()
        self.manifest("Camellia", "0.1.1")
        before = self.git("status", "--porcelain")
        result = self.git("push", "origin", "main", check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FAIL plugins/Camellia", result.stderr)
        self.assertEqual(self.remote_head(), self.base)
        self.assertEqual(self.git("status", "--porcelain"), before)
        target = self.commit()
        self.git("push", "origin", "main")
        self.assertEqual(self.remote_head(), target)

    def test_hook_uses_sent_ref_not_checked_out_head(self):
        self.install_hook()
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        target = self.commit()
        self.git("switch", "--detach", self.base)
        result = self.git("push", "origin", f"{target}:refs/heads/main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.remote_head(), self.base)

    def test_new_branch_cannot_bypass_version_check(self):
        self.install_hook()
        self.write("plugins/Camellia/mcp/new.py", "changed\n")
        self.commit()
        result = self.git("push", "origin", "HEAD:refs/heads/work/common/test", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL plugins/Camellia", result.stderr)
        self.manifest("Camellia", "0.1.1")
        target = self.commit()
        self.git("push", "origin", "HEAD:refs/heads/work/common/test")
        self.assertEqual(self.remote_head("work/common/test"), target)

    def test_existing_commit_new_branch_and_ref_deletion(self):
        self.install_hook()
        self.git("push", "origin", "HEAD:refs/heads/work/common/test")
        self.assertEqual(self.remote_head("work/common/test"), self.base)
        self.git("push", "origin", ":refs/heads/work/common/test")

    def test_first_push_to_empty_remote(self):
        empty = self.root / "empty.git"
        self.git("init", "--bare", str(empty), cwd=self.root)
        self.install_hook()
        self.git("push", str(empty), "main")
        self.assertEqual(self.git("rev-parse", "main", cwd=empty), self.base)

    def test_same_version_sync_requires_identical_published_plugin(self):
        # Simulate old published history from before the hook was introduced.
        self.write("plugins/Camellia/skills/one/SKILL.md", "published\n")
        published = self.commit()
        self.git("push", "origin", "HEAD:refs/heads/integrate/camellia")
        self.check_versions(1)
        self.check_versions(0, "--remote", "origin")
        self.install_hook()
        self.git("push", "origin", "main")
        self.assertEqual(self.remote_head(), published)
        self.write("plugins/Camellia/skills/one/SKILL.md", "local extra\n")
        self.commit()
        result = self.git("push", "origin", "main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.remote_head(), published)

    def test_published_lower_version_is_not_sync_exception(self):
        self.manifest("Camellia", "0.0.9")
        self.commit()
        self.git("push", "origin", "HEAD:refs/heads/old-version")
        self.check_versions(1, "--remote", "origin")

    def test_missing_remote_objects_and_bad_input_fail_closed(self):
        result = self.run_script("pre-push", "origin", str(self.remote),
                                 input=f"refs/heads/main {self.base} refs/heads/main {'a' * 40}\n")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        result = self.run_script("pre-push", "origin", str(self.remote), input="broken\n")
        self.assertEqual(result.returncode, 2)
        self.check_versions(2, base="missing-ref")

    def test_multiple_ref_push_is_blocked_before_any_ref_updates(self):
        self.install_hook()
        self.write("plugins/Camellia/skills/one/SKILL.md", "bad change\n")
        target = self.commit()
        result = self.git("push", "origin", f"{self.base}:refs/heads/good",
                          f"{target}:refs/heads/main", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.remote_head(), self.base)
        self.assertNotEqual(self.git("rev-parse", "--verify", "refs/heads/good",
                                     cwd=self.remote, check=False).returncode, 0)

    def test_linked_worktree_uses_installed_hook(self):
        self.install_hook()
        worktree = self.root / "linked"
        self.git("worktree", "add", "-b", "linked", str(worktree), self.base)
        (worktree / "plugins/Camellia/skills/one/SKILL.md").write_text("changed\n")
        self.git("add", "--all", cwd=worktree)
        self.git("commit", "-m", "Change in linked worktree", cwd=worktree)
        result = self.git("push", "origin", "HEAD:refs/heads/linked", cwd=worktree, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL plugins/Camellia", result.stderr)

    def test_unrelated_history_and_shallow_history_fail_closed(self):
        self.git("switch", "--orphan", "orphan")
        self.manifest("Camellia", "0.1.0")
        self.write_project_tools()
        self.git("add", "plugins", "tools")
        self.git("commit", "-m", "Unrelated root")
        self.install_hook()
        result = self.git("push", "origin", "HEAD:refs/heads/orphan", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no common history", result.stderr)
        shallow = self.root / "shallow"
        self.git("clone", "--depth=1", self.remote.as_uri(), str(shallow), cwd=self.root)
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "check",
                                 "--base", "HEAD", "--target", "HEAD"], cwd=shallow,
                                env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertIn("shallow", result.stderr)

    def test_missing_remote_history_for_new_ref_requires_fetch(self):
        other = self.root / "other-clone"
        self.git("clone", str(self.remote), str(other), cwd=self.root)
        self.git("config", "user.name", "Other User", cwd=other)
        self.git("config", "user.email", "other@example.invalid", cwd=other)
        (other / "common.txt").write_text("remote change\n")
        self.git("add", "common.txt", cwd=other)
        self.git("commit", "-m", "Remote changed", cwd=other)
        self.git("push", "origin", "main", cwd=other)
        self.install_hook()
        result = self.git("push", "origin", "HEAD:refs/heads/new", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fetch remote history", result.stderr)
        self.git("fetch", "origin")
        self.git("push", "origin", "HEAD:refs/heads/new")

    def test_annotated_tag_is_checked_by_its_commit(self):
        self.install_hook()
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.commit()
        self.git("tag", "-a", "bad", "-m", "Missing version")
        result = self.git("push", "origin", "refs/tags/bad", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL plugins/Camellia", result.stderr)

    def test_remote_unavailable_is_error_not_pass(self):
        self.write("plugins/Camellia/skills/one/SKILL.md", "changed\n")
        self.commit()
        self.check_versions(2, "--remote", str(self.root / "missing.git"))


if __name__ == "__main__":
    unittest.main()
