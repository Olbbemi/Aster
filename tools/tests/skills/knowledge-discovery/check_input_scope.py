#!/usr/bin/env python3
"""Persistent checks for input scope."""

import os
from pathlib import Path
import sys
from unittest.mock import patch

# -I excludes the script directory; only these local check helpers are added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import RuntimeFixture, run_check


class InputScopeChecks(RuntimeFixture):
    """input scope checks."""

    def test_inspect_only_lists_structure_and_never_reads_sources(self):
        with patch.object(self.sources, "regular_bytes", side_effect=AssertionError("source read")):
            result = self.command("inspect", target=[str(self.source)], output_root=str(self.repo))
        self.assertEqual({"mixed.md", "detail.rs"}, {entry["path"] for entry in result["targets"][0]["structure"]})
        self.assertFalse((self.repo / "knowledge-candidate").exists())


    def test_inspect_lists_nested_names_without_traversing_links(self):
        nested = self.source / "nested"
        nested.mkdir()
        (nested / "concept.md").write_text("concept")
        (nested / "outside").symlink_to(self.repo, target_is_directory=True)
        result = self.command("inspect", target=[str(self.source)], output_root=str(self.repo))
        structure = result["targets"][0]["structure"]
        self.assertIn({"path": "nested/outside", "kind": "link"}, structure)
        self.assertNotIn("nested/outside/.git", {item["path"] for item in structure})


    def test_git_root_rejects_subdirectories_bare_and_plain_folders(self):
        sub = self.repo / "sub"
        sub.mkdir()
        bare = self.root / "bare"
        self.git("init", "--bare", "-q", str(bare))
        for path in (sub, bare, self.source, self.root / "missing"):
            with self.subTest(path=path):
                self.assert_error("INVALID_OUTPUT_ROOT", self.sources.output_root, str(path))
        self.assertEqual(self.repo, self.sources.output_root(str(self.repo)))


    def test_git_root_accepts_worktree_git_file(self):
        self.git("-C", str(self.repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-qm", "fixture")
        worktree = self.root / "worktree"
        self.git("-C", str(self.repo), "worktree", "add", "--detach", "-q", str(worktree))
        self.assertTrue((worktree / ".git").is_file())
        self.assertEqual(worktree, self.sources.output_root(str(worktree)))


    def test_scope_and_links_are_not_auto_included(self):
        request = dict(self.request, files=[str(self.other)])
        self.assert_error("SCOPE_VIOLATION", self.begin, request)
        link = self.source / "linked.md"
        link.symlink_to(self.other)
        request["files"] = [str(link)]
        self.assert_error("SCOPE_VIOLATION", self.begin, request)
        run = self.begin()
        self.assert_error("SCOPE_VIOLATION", self.command, "read", run, file=str(self.other))


    def test_invalid_json_keys_types_duplicates_and_no_content(self):
        for change in ({"surprise": True}, {"model": "fake"}, {"scope_confirmation": ""}):
            self.assert_error("INVALID_PAYLOAD", self.begin, dict(self.request, **change))
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"targets": [], "targets": []}')
        self.assert_error("INVALID_PAYLOAD", self.sources.load_json, str(duplicate))


    def test_read_and_save_reject_changed_source(self):
        run = self.approved()
        self.first.write_text("changed", encoding="utf-8")
        self.assert_error("SOURCE_CHANGED", self.command, "read", run, file=str(self.first))
        self.assert_error("SOURCE_CHANGED", self.command, "save-topic", run, self.detail())
        self.assertFalse((self.repo / "knowledge-candidate").exists())


    def test_deleted_source_is_changed_and_non_text_is_an_error(self):
        run = self.begin()
        self.first.unlink()
        self.assert_error("SOURCE_CHANGED", self.command, "read", run, file=str(self.first))
        self.first.write_bytes(b"\xff\xfe")
        self.assert_error("IO_ERROR", self.begin)


    def test_fifo_is_rejected_without_blocking(self):
        fifo = self.source / "pipe"
        os.mkfifo(fifo)
        self.assert_error("INVALID_TARGET", self.sources.targets, [str(fifo)])
        request = dict(self.request, files=[str(fifo)])
        self.assert_error("INVALID_TARGET", self.begin, request)



def main(argv=None):
    return run_check("input-scope", InputScopeChecks, argv)


if __name__ == "__main__":
    sys.exit(main())
