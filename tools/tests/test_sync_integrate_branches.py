"""Exercise propagation against real, disposable Git remotes."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "sync_integrate_branches.py"


class PropagationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-propagation-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.repo))
        self.git(self.repo, "config", "user.name", "Test User")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        self.base = self.commit("base.txt", "base\n")
        self.git(self.repo, "push", "origin", "main")
        for branch in ("integrate/common", "integrate/camellia", "work/common/example"):
            self.git(self.repo, "push", "origin", f"HEAD:refs/heads/{branch}")

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, path, content):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        self.git(self.repo, "add", path)
        self.git(self.repo, "commit", "-m", f"Update {path}")
        return self.git(self.repo, "rev-parse", "HEAD")

    def main_change(self):
        self.git(self.repo, "switch", "main")
        commit = self.commit("common.txt", "shared change\n")
        self.git(self.repo, "push", "origin", "main")
        return commit

    def remote_head(self, branch):
        return self.git(self.remote, "rev-parse", f"refs/heads/{branch}")

    def run_sync(self, expected_code=0):
        summary = self.root / "summary.md"
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), "--repo", str(self.repo)],
            env=dict(self.env, GITHUB_STEP_SUMMARY=str(summary)),
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(report["main"] or "null", summary.read_text())
        return {item["branch"]: item for item in report["results"]}

    def test_ff_all_integrations_preserves_work_branch_and_dirty_index(self):
        target = self.main_change()
        self.git(self.repo, "push", "origin", f"{self.base}:refs/heads/integrate/new-plugin")
        self.git(self.repo, "switch", "-c", "work/common/local")
        (self.repo / "staged.txt").write_text("staged\n")
        self.git(self.repo, "add", "staged.txt")
        (self.repo / "base.txt").write_text("unstaged\n")
        (self.repo / "untracked.txt").write_text("untracked\n")
        before = self.git(self.repo, "status", "--porcelain=v1")
        index = self.git(self.repo, "write-tree")
        results = self.run_sync()
        self.assertEqual(set(results), {"integrate/common", "integrate/camellia", "integrate/new-plugin"})
        for branch, item in results.items():
            self.assertEqual(item["status"], "success")
            self.assertEqual(item["action"], "fast-forward")
            self.assertEqual(self.remote_head(branch), target)
        self.assertEqual(self.remote_head("work/common/example"), self.base)
        self.assertEqual(self.remote_head("main"), target)
        self.assertEqual(self.git(self.repo, "status", "--porcelain=v1"), before)
        self.assertEqual(self.git(self.repo, "write-tree"), index)
        self.assertEqual(self.git(self.repo, "branch", "--show-current"), "work/common/local")

    def test_divergent_merge_preserves_both_parents_and_changes_and_rerun(self):
        self.git(self.repo, "switch", "-c", "plugin", self.base)
        plugin = self.commit("plugin.txt", "plugin change\n")
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/integrate/camellia")
        target = self.main_change()
        result = self.run_sync()["integrate/camellia"]
        self.assertEqual(result["action"], "merge")
        merged = self.remote_head("integrate/camellia")
        self.assertEqual(self.git(self.remote, "show", "-s", "--format=%P", merged), f"{plugin} {target}")
        self.assertEqual(self.git(self.remote, "show", f"{merged}:plugin.txt"), "plugin change")
        self.assertEqual(self.git(self.remote, "show", f"{merged}:common.txt"), "shared change")
        rerun = self.run_sync()
        self.assertTrue(all(item["action"] == "already-current" for item in rerun.values()))
        self.assertEqual(self.remote_head("integrate/camellia"), merged)

    def test_conflict_leaves_branch_unchanged_and_continues_other_branches(self):
        self.git(self.repo, "switch", "-c", "plugin", self.base)
        plugin = self.commit("base.txt", "plugin version\n")
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/integrate/camellia")
        self.git(self.repo, "switch", "main")
        target = self.commit("base.txt", "main version\n")
        self.git(self.repo, "push", "origin", "main")
        results = self.run_sync(expected_code=1)
        self.assertEqual(results["integrate/camellia"]["status"], "failure")
        self.assertIn("CONFLICT", results["integrate/camellia"]["detail"])
        self.assertEqual(self.remote_head("integrate/camellia"), plugin)
        self.assertEqual(results["integrate/common"]["status"], "success")
        self.assertEqual(self.remote_head("integrate/common"), target)

    def test_push_rejection_is_failure_and_other_branch_still_updates(self):
        target = self.main_change()
        hook = self.remote / "hooks" / "update"
        hook.write_text('#!/bin/sh\nif [ "$1" = "refs/heads/integrate/camellia" ]; then\n'
                        '  echo "Rejected by test policy" >&2\n  exit 1\nfi\n')
        hook.chmod(0o755)
        results = self.run_sync(expected_code=1)
        self.assertEqual(results["integrate/camellia"]["status"], "failure")
        self.assertIn("Rejected by test policy", results["integrate/camellia"]["detail"])
        self.assertEqual(self.remote_head("integrate/camellia"), self.base)
        self.assertEqual(self.remote_head("integrate/common"), target)

    def test_already_ahead_is_not_rewritten(self):
        target = self.main_change()
        ahead = self.commit("plugin.txt", "ahead\n")
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/integrate/camellia")
        result = self.run_sync()["integrate/camellia"]
        self.assertEqual(result["action"], "already-current")
        self.assertEqual(self.remote_head("integrate/camellia"), ahead)
        self.assertEqual(self.remote_head("main"), target)

    def test_remote_deleted_before_run_is_pruned(self):
        self.git(self.repo, "fetch", "origin")
        self.git(self.repo, "push", "origin", "--delete", "integrate/camellia")
        self.main_change()
        results = self.run_sync()
        self.assertEqual(set(results), {"integrate/common"})
        self.assertEqual(self.git(self.remote, "for-each-ref", "--format=%(refname)",
                                  "refs/heads/integrate/camellia"), "")

    def test_concurrent_remote_commit_is_preserved_when_push_is_rejected(self):
        target = self.main_change()
        self.git(self.repo, "switch", "-c", "concurrent", self.base)
        concurrent = self.commit("concurrent.txt", "another writer\n")
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/work/common/race-source")
        hook = self.repo / ".git" / "hooks" / "pre-push"
        hook.write_text(
            '#!/bin/sh\nwhile read local_ref local_sha remote_ref remote_sha; do\n'
            '  if [ "$remote_ref" = "refs/heads/integrate/camellia" ]; then\n'
            f'    git --git-dir={shlex.quote(str(self.remote))} update-ref '
            f'refs/heads/integrate/camellia {concurrent} {self.base}\n'
            '  fi\ndone\n'
        )
        hook.chmod(0o755)
        results = self.run_sync(expected_code=1)
        self.assertEqual(results["integrate/camellia"]["status"], "failure")
        self.assertEqual(self.remote_head("integrate/camellia"), concurrent)
        self.assertEqual(self.remote_head("integrate/common"), target)

    def test_missing_main_fails_before_any_remote_change(self):
        self.git(self.remote, "update-ref", "-d", "refs/heads/main")
        self.assertEqual(self.run_sync(expected_code=1), {})
        self.assertEqual(self.remote_head("integrate/common"), self.base)
        self.assertEqual(self.remote_head("integrate/camellia"), self.base)


if __name__ == "__main__":
    unittest.main()
