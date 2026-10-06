"""Marked flow character checks, fence boundaries and read-only CLI behavior."""

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
from check_ascii_flows import check_ascii_flows

FLOW = "```text ascii-flow\n[start] -> [end]\n```\n"


class AsciiFlowsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-ascii-flows-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "flow.md"
        self.path.write_text(FLOW, encoding="utf-8")

    def check(self, text=None, paths=None):
        if text is not None:
            self.path.write_bytes(text.encode("utf-8"))
        return check_ascii_flows(paths or [self.path])

    def issue(self, report, identifier, status="FAIL"):
        self.assertTrue(any(item["id"] == identifier and item["status"] == status
                            for item in report["checks"]), report)

    def cli(self, *args, no_site=False):
        return subprocess.run([sys.executable, "-B", *(["-S"] if no_site else []),
                               str(SCRIPTS / "check_ascii_flows.py"), *map(str, args)],
                              cwd=self.root, capture_output=True, text=True, timeout=15)

    def test_ascii_korean_and_long_lines_are_allowed(self):
        report = self.check(FLOW.replace("[start] -> [end]", "[시작] -> [종료]\n" + "A" * 300))
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(report["diagrams_checked"], 1)

    def test_controls_non_ascii_spaces_and_connector_glyphs_fail(self):
        characters = ["\t", "\x00", "\x1b", "\x7f", "\r", "\x85", "\u200b", "\u202e", "\ue000",
                      "\u00a0", "\u3000", "\u2028", "\u2029", "\u2500", "\u2588", "\u25a0",
                      "\u2192", "\u279c", "\u2013", "\u2014", "\uff0b", "\uff0d", "\uff5c", "\uff1c", "\uff1e"]
        for char in characters:
            with self.subTest(code=ord(char)):
                report = self.check(FLOW.replace("[start] -> [end]", "A" + char + "B"))
                self.assertEqual(report["exit_code"], 1, report)
                self.issue(report, "diagram.character")
                problem = next(item for item in report["checks"] if item["id"] == "diagram.character")
                self.assertEqual((problem["line"], problem["column"]), (2, 2))

    def test_unclosed_wrong_short_or_overindented_closers_fail(self):
        for text in ("```text ascii-flow\n[A]\n", "```text ascii-flow\n[A]\n~~~\n",
                     "````text ascii-flow\n[A]\n```\n", "```text ascii-flow\n[A]\n    ```\n",
                     "```text ascii-flow\n[A]\n``` trailing text\n", "```text ascii-flow"):
            with self.subTest(text=text):
                self.issue(self.check(text), "diagram.fence")

    def test_valid_tilde_longer_closer_empty_and_no_final_newline(self):
        for text in ("~~~text ascii-flow\n[A]\n~~~~\n", "````text ascii-flow\n[A]\n`````",
                     "```text ascii-flow\n```", FLOW.rstrip("\n")):
            with self.subTest(text=text):
                self.assertEqual(self.check(text)["exit_code"], 0)

    def test_nested_quote_and_list_flows_use_original_line_positions(self):
        quote = "\n".join("> " + line for line in FLOW.splitlines()) + "\n"
        nested = "- 흐름\n\n" + "\n".join("  " + line for line in FLOW.splitlines()) + "\n"
        for text in (quote, nested):
            with self.subTest(text=text):
                self.assertEqual(self.check(text)["exit_code"], 0)
                self.issue(self.check(text.replace("[start]", "[\tstart]")), "diagram.character")
        self.issue(self.check("> ```text ascii-flow\n> [A]\n\n다른 문단\n"), "diagram.fence")

    def test_only_explicit_marked_fences_are_checked(self):
        for text in ("일반 설명 \t \u2192", FLOW.replace("text ascii-flow", "text").replace("->", "\u2192"),
                     "````markdown\n" + FLOW.replace("->", "\u2192") + "````\n",
                     "<!--\n" + FLOW.replace("->", "\u2192") + "-->\n"):
            with self.subTest(text=text):
                report = self.check(text)
                self.assertEqual(report["exit_code"], 0)
                self.assertEqual(report["diagrams_checked"], 0)
                self.issue(report, "diagram.none", "SKIP")

    def test_multiple_files_diagrams_and_repeated_inputs(self):
        other = self.root / "other.md"
        other.write_text(FLOW + "\n" + FLOW)
        report = self.check(paths=[self.path, other, self.path])
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["diagrams_checked"], 3)
        self.assertEqual(len(report["files"]), 2)

    def test_bom_crlf_frontmatter_and_character_lines(self):
        text = "---\nname: test\n---\n\n" + FLOW
        self.path.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode())
        self.assertEqual(self.check()["exit_code"], 0)
        report = self.check(text.replace("[start]", "\t[start]"))
        problem = next(item for item in report["checks"] if item["id"] == "diagram.character")
        self.assertEqual(problem["line"], 6)

    def test_invalid_utf8_missing_files_and_permissions_are_errors(self):
        self.path.write_bytes(b"\xff")
        self.issue(self.check(), "document.read", "ERROR")
        for path in (self.root / "missing.md", self.root):
            self.issue(self.check(paths=[path]), "document.read", "ERROR")
        with patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            self.issue(self.check(), "document.read", "ERROR")
        self.issue(check_ascii_flows([]), "input", "ERROR")

    def test_errors_do_not_hide_other_document_failures(self):
        self.path.write_text(FLOW.replace("->", "\u2192"))
        report = self.check(paths=[self.path, self.root / "missing.md"])
        self.assertEqual(report["exit_code"], 2)
        self.issue(report, "diagram.character")
        self.issue(report, "document.read", "ERROR")

    def test_fifo_is_rejected_without_opening(self):
        import os
        fifo = self.root / "pipe.md"
        os.mkfifo(fifo)
        self.issue(self.check(paths=[fifo]), "document.read", "ERROR")

    def test_cli_json_text_help_dependency_and_failure_are_read_only(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        run = self.cli("flow.md", "--json")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["diagrams_checked"], 1)
        self.assertIn("도식 1개", self.cli("flow.md").stdout)
        self.assertEqual(self.cli("--help").returncode, 0)
        self.assertEqual(self.cli().returncode, 2)
        run = self.cli("flow.md", "--json", no_site=True)
        self.assertEqual(run.returncode, 2)
        self.issue(json.loads(run.stdout), "dependency", "ERROR")
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)
        self.path.write_text(FLOW.replace("->", "\u2192"))
        before = self.path.read_bytes()
        run = self.cli("flow.md", "--json")
        self.assertEqual(run.returncode, 1)
        self.issue(json.loads(run.stdout), "diagram.character")
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
