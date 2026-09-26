"""Test the todo hook with disposable homes and local Git checkouts."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[2] / "scripts/git/post-checkout"


class TodoHookTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="aster-todo-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.share = self.home / ".local/share"
        self.aster = self.share / "aster"
        self.todo = self.aster / "todo"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")

    def run_hook(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-I", "-B", str(HOOK), *args],
                                env=self.env, cwd=self.root, text=True,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def prepare(self, expected=0):
        return self.run_hook("HEAD", "HEAD", "1", expected=expected)

    def test_creates_path_and_preserves_existing_data_on_repeat(self):
        self.prepare()
        self.assertTrue(self.todo.is_dir())
        record = self.todo / "existing.md"
        record.write_text("keep\n")
        readme = self.aster / "README.md"
        readme.write_text("shared data\n")
        self.prepare()
        self.assertEqual(record.read_text(), "keep\n")
        self.assertEqual(readme.read_text(), "shared data\n")
        self.assertFalse(self.aster.is_symlink())

    def test_preserves_existing_shared_data_link(self):
        target = self.root / "shared data"
        target.mkdir()
        (target / "cargo").mkdir()
        self.share.mkdir(parents=True)
        self.aster.symlink_to(target, target_is_directory=True)
        self.prepare()
        self.assertEqual(self.aster.readlink(), target)
        self.assertTrue((target / "todo").is_dir())
        self.assertTrue((target / "cargo").is_dir())

    def test_preserves_existing_todo_link(self):
        target = self.root / "existing todo"
        target.mkdir()
        self.aster.mkdir(parents=True)
        self.todo.symlink_to(target, target_is_directory=True)
        self.prepare()
        self.assertEqual(self.todo.readlink(), target)

    def test_file_conflicts_are_preserved(self):
        for conflict in (self.home / ".local", self.share, self.aster, self.todo):
            with self.subTest(path=conflict):
                conflict.parent.mkdir(parents=True, exist_ok=True)
                conflict.write_text("keep\n")
                result = self.prepare(expected=1)
                self.assertIn("Aster post-checkout:", result.stderr)
                self.assertEqual(conflict.read_text(), "keep\n")
                conflict.unlink()

    def test_broken_links_are_preserved_without_creating_targets(self):
        for conflict in (self.home / ".local", self.share, self.aster, self.todo):
            with self.subTest(path=conflict):
                conflict.parent.mkdir(parents=True, exist_ok=True)
                target = self.root / "missing"
                conflict.symlink_to(target, target_is_directory=True)
                self.prepare(expected=1)
                self.assertEqual(conflict.readlink(), target)
                self.assertFalse(target.exists())
                conflict.unlink()

    def test_file_checkout_does_not_create_path(self):
        self.run_hook("HEAD", "HEAD", "0")
        self.assertFalse(self.aster.exists())

    def test_invalid_arguments_do_not_create_path(self):
        for args in ((), ("HEAD", "HEAD"), ("HEAD", "HEAD", "2"),
                     ("HEAD", "HEAD", "1", "extra")):
            with self.subTest(args=args):
                self.run_hook(*args, expected=1)
                self.assertFalse(self.aster.exists())

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], env=self.env,
                              text=True, capture_output=True, check=True, timeout=15)

    def test_clone_checkout_and_worktree_use_one_project_path(self):
        source = self.root / "source"
        source.mkdir()
        self.git(source, "init", "--template=", "--initial-branch=main")
        self.git(source, "config", "user.name", "Test User")
        self.git(source, "config", "user.email", "test@example.invalid")
        project_hook = source / "tools/scripts/git/post-checkout"
        project_hook.parent.mkdir(parents=True)
        shutil.copy2(HOOK, project_hook)
        self.assertTrue(os.access(project_hook, os.X_OK))
        self.git(source, "add", ".")
        self.git(source, "commit", "-m", "Add todo hook")
        template = self.root / "template"
        common = template / "hooks/post-checkout"
        common.parent.mkdir(parents=True)
        # Exercise the Hortulanus caller contract; installation is tested there.
        common.write_text('#!/bin/sh\nset -eu\n'
                          'cd "$(git rev-parse --show-toplevel)"\n'
                          'exec ./tools/scripts/git/post-checkout "$@"\n')
        common.chmod(0o755)
        clone = self.root / "arbitrary clone name"
        self.git(self.root, "clone", f"--template={template}", str(source), str(clone))
        self.assertTrue(self.todo.is_dir())
        self.todo.rmdir()
        self.git(clone, "switch", "-c", "another-branch")
        self.assertTrue(self.todo.is_dir())
        self.todo.rmdir()
        worktree = self.root / "arbitrary worktree name"
        self.git(clone, "worktree", "add", "-b", "linked", str(worktree))
        self.assertTrue(self.todo.is_dir())
        self.assertEqual(sorted(p.name for p in self.share.iterdir()), ["aster"])
        self.assertEqual(self.git(clone, "status", "--porcelain").stdout, "")
        self.assertEqual(self.git(worktree, "status", "--porcelain").stdout, "")


if __name__ == "__main__":
    unittest.main()
