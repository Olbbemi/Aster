"""Test shared work-data initialization with disposable homes and real Git repos."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[2] / "scripts/git/post-checkout"
OPERATION = HOOK.parent / "operations/prepare_work_data.py"


class WorkDataHookTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="aster-data-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.share = self.home / ".local/share"
        self.public = self.share / "aster"
        self.repo = self.root / "source repo"
        self.repo.mkdir()
        self.data = self.repo / "data"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
        self.git(self.repo, "init", "--template=", "--initial-branch=main")
        self.git(self.repo, "config", "user.name", "Test User")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        hook = self.repo / "tools/scripts/git/post-checkout"
        hook.parent.mkdir(parents=True)
        shutil.copy2(HOOK, hook)
        operation = hook.parent / "operations/prepare_work_data.py"
        operation.parent.mkdir()
        shutil.copy2(OPERATION, operation)
        self.hook = hook
        self.operation = operation
        (self.repo / ".gitignore").write_text("/data/\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "Add data hook")
        self.template = self.root / "template"
        common = self.template / "hooks/post-checkout"
        common.parent.mkdir(parents=True)
        common.write_text('#!/bin/sh\nset -eu\n'
                          'cd "$(git rev-parse --show-toplevel)"\n'
                          'exec ./tools/scripts/git/post-checkout "$@"\n')
        common.chmod(0o755)

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env,
                              text=True, capture_output=True, check=True, timeout=15)

    def run_hook(self, *args, cwd=None, expected=0):
        result = subprocess.run([sys.executable, "-I", "-B", str(self.hook), *args],
                                env=self.env, cwd=cwd or self.repo, text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def initialize(self, **kwargs):
        return self.run_hook("--initialize", **kwargs)

    def run_operation(self, *args, cwd=None, expected=0):
        result = subprocess.run([sys.executable, "-I", "-B", str(self.operation), *args],
                                env=self.env, cwd=cwd or self.repo, text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def clone(self, name="arbitrary clone name"):
        clone = self.root / name
        self.git(self.root, "clone", f"--template={self.template}", str(self.repo), str(clone))
        return clone

    def test_explicit_initialization_and_repeat_preserve_data(self):
        self.initialize()
        self.assertEqual(self.public.readlink(), self.data)
        self.assertFalse(self.data.is_symlink())
        self.assertTrue((self.data / "cargo").is_dir())
        record = self.public / "todo/existing.md"
        record.write_text("keep\n")
        self.initialize()
        self.assertEqual(record.read_text(), "keep\n")
        self.assertEqual(self.git(self.repo, "status", "--porcelain").stdout, "")

    def test_manual_operation_and_hook_share_existing_data(self):
        self.run_operation("--initialize")
        self.assertEqual(self.public.readlink(), self.data)
        record = self.public / "todo/existing.md"
        record.write_text("keep\n")
        self.initialize()
        self.run_operation("--initialize")
        self.assertEqual(record.read_text(), "keep\n")
        self.assertEqual(self.git(self.repo, "status", "--porcelain").stdout, "")

    def test_manual_operation_rejects_linked_worktree_without_creating_paths(self):
        worktree = self.root / "linked worktree"
        self.git(self.repo, "worktree", "add", "-b", "linked", str(worktree))
        self.run_operation("--initialize", cwd=worktree, expected=1)
        self.run_operation("--checkout", cwd=worktree)
        self.assertFalse(self.public.exists())
        self.assertFalse((worktree / "data").exists())

    def test_invalid_operation_arguments_do_not_prepare_paths(self):
        for args in ((), ("--initialize", "extra"), ("--checkout", "extra"),
                     ("--initialize", "--checkout")):
            self.run_operation(*args, expected=1)
            self.assertFalse(self.public.exists())

    def test_initial_clone_creates_real_data_and_shared_alias(self):
        clone = self.clone()
        self.assertEqual(self.public.readlink(), clone / "data")
        self.assertTrue((clone / "data/todo").is_dir())
        self.assertTrue((clone / "data/cargo").is_dir())
        self.assertFalse((clone / "data").is_symlink())
        self.assertEqual(self.git(clone, "status", "--porcelain").stdout, "")

    def test_second_clone_preserves_first_owner(self):
        first = self.clone("first")
        record = self.public / "todo/existing.md"
        record.write_text("keep\n")
        second = self.clone("second")
        self.assertEqual(self.public.readlink(), first / "data")
        self.assertFalse((second / "data").exists())
        self.assertEqual(record.read_text(), "keep\n")

    def test_checkout_and_worktree_do_not_prepare_missing_alias(self):
        clone = self.clone()
        self.public.unlink()
        self.git(clone, "switch", "-c", "another-branch")
        self.assertFalse(self.public.exists())
        worktree = self.root / "linked worktree"
        self.git(clone, "worktree", "add", "-b", "linked", str(worktree))
        self.assertFalse(self.public.exists())
        self.assertFalse((worktree / "data").exists())
        self.initialize(cwd=worktree, expected=1)
        self.assertFalse(self.public.exists())

    def test_worktree_preserves_existing_owner(self):
        clone = self.clone()
        record = self.public / "todo/existing.md"
        record.write_text("keep\n")
        worktree = self.root / "linked worktree"
        self.git(clone, "worktree", "add", "-b", "linked", str(worktree))
        self.assertEqual(self.public.readlink(), clone / "data")
        self.assertEqual(record.read_text(), "keep\n")
        self.assertFalse((worktree / "data").exists())

    def test_existing_healthy_legacy_alias_is_preserved(self):
        target = self.root / "legacy data"
        target.mkdir()
        self.share.mkdir(parents=True)
        self.public.symlink_to(target, target_is_directory=True)
        self.initialize()
        self.assertEqual(self.public.readlink(), target)
        self.assertTrue((target / "todo").is_dir())
        self.assertTrue((target / "cargo").is_dir())
        self.assertFalse(self.data.exists())

    def test_existing_healthy_child_link_is_preserved(self):
        self.initialize()
        (self.data / "todo").rmdir()
        target = self.root / "old todo"
        target.mkdir()
        (self.data / "todo").symlink_to(target, target_is_directory=True)
        self.initialize()
        self.assertEqual((self.data / "todo").readlink(), target)

    def test_existing_plain_shared_directory_is_rejected(self):
        self.public.mkdir(parents=True)
        record = self.public / "keep.md"
        record.write_text("keep")
        self.initialize(expected=1)
        self.assertEqual(record.read_text(), "keep")
        self.assertFalse(self.data.exists())

    def test_file_conflicts_preserved_before_other_paths_created(self):
        for conflict in (self.home / ".local", self.share, self.public,
                         self.data, self.data / "todo", self.data / "cargo"):
            with self.subTest(path=conflict):
                conflict.parent.mkdir(parents=True, exist_ok=True)
                conflict.write_text("keep\n")
                self.initialize(expected=1)
                self.assertEqual(conflict.read_text(), "keep\n")
                self.assertFalse(self.public.is_symlink())
                conflict.unlink()

    def test_broken_links_preserved_without_creating_targets(self):
        for conflict in (self.home / ".local", self.share, self.public,
                         self.data, self.data / "todo", self.data / "cargo"):
            with self.subTest(path=conflict):
                conflict.parent.mkdir(parents=True, exist_ok=True)
                target = self.root / "missing"
                conflict.symlink_to(target, target_is_directory=True)
                self.initialize(expected=1)
                self.assertEqual(conflict.readlink(), target)
                self.assertFalse(target.exists())
                conflict.unlink()

    def test_new_data_root_must_not_be_symlink(self):
        target = self.root / "other data"
        target.mkdir()
        self.data.symlink_to(target, target_is_directory=True)
        self.initialize(expected=1)
        self.assertEqual(self.data.readlink(), target)
        self.assertFalse(self.public.exists())

    def test_non_initial_checkout_is_noop_even_outside_git(self):
        for args in (("HEAD", "HEAD", "0"), ("HEAD", "HEAD", "1"),
                     ("0" * 40, "HEAD", "0")):
            self.run_hook(*args, cwd=self.home)
            self.assertFalse(self.public.exists())

    def test_initial_checkout_accepts_sha256_null_oid(self):
        self.run_hook("0" * 64, "1" * 64, "1")
        self.assertEqual(self.public.readlink(), self.data)

    def test_invalid_arguments_do_not_prepare_paths(self):
        for args in ((), ("HEAD", "HEAD"), ("HEAD", "HEAD", "2"),
                     ("--initialize", "extra")):
            self.run_hook(*args, expected=1)
            self.assertFalse(self.public.exists())

    def test_explicit_initialization_requires_git_worktree(self):
        self.initialize(cwd=self.home, expected=1)
        self.assertFalse(self.public.exists())


if __name__ == "__main__":
    unittest.main()
