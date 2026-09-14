"""Reference checker tests against real temporary trees and Markdown syntax."""

import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_references import check_references

SCRIPT = SCRIPTS / "check_references.py"


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-reference-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "sample-skill"
        self.skill.mkdir()
        self.source = self.skill / "SKILL.md"

    def write(self, text, name="SKILL.md"):
        path = self.skill / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_check(self, text):
        self.write(text)
        return check_references(self.skill)

    def assert_check(self, result, check_id, status):
        self.assertTrue(any(c["id"] == check_id and c["status"] == status
                            for c in result["checks"]), result)

    def cli(self, *args, no_site=False):
        return subprocess.run([sys.executable, "-B", *(["-S"] if no_site else []),
                               str(SCRIPT), *map(str, args)], cwd=self.root,
                              text=True, capture_output=True, timeout=15)

    def test_existing_files_directories_and_missing_targets(self):
        self.write("# guide", "references/guide.md")
        result = self.run_check("[file](references/guide.md) [dir](references/) [bad](missing.md)")
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["counts"]["PASS"], 2)
        self.assertEqual(result["counts"]["FAIL"], 1)
        self.assert_check(result, "reference.exists", "FAIL")

    def test_scan_all_markdown_including_hidden_and_uppercase(self):
        self.write("[self](SKILL.md)")
        self.write("[root](../SKILL.md)", "references/GUIDE.MD")
        self.write("[root](../SKILL.md)", ".hidden/notes.md")
        self.write("[missing](absent.md)", "ignored.txt")
        result = check_references(self.skill)
        self.assertEqual(len(result["documents"]), 3)
        self.assertEqual(result["links_extracted"], 3)
        self.assertEqual(result["exit_code"], 0)

    def test_relative_paths_are_based_on_each_document(self):
        self.write("[child](refs/guide.md)")
        self.write("[sibling](data.txt) [parent](../SKILL.md)", "refs/guide.md")
        self.write("data", "refs/data.txt")
        result = check_references(self.skill)
        self.assertEqual(result["counts"]["PASS"], 3)

    def test_link_target_documents_are_not_recursively_scanned(self):
        external = self.root / "outside.md"
        external.write_text("[bad](missing.md)")
        result = self.run_check("[existing](../outside.md)")
        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(result["exit_code"], 0)

    def test_unicode_space_parenthesis_title_and_percent_encoding(self):
        for name in ("한글 문서.md", "guide(v2).md", "percent%20.md", "hash#name.md", "a&b.md"):
            self.write("body", name)
        result = self.run_check(
            '[space](<한글 문서.md> "title")\n'
            '[paren](guide(v2).md) [escaped](guide\\(v2\\).md)\n'
            '[percent](percent%2520.md) [hash](hash%23name.md) [entity](a&amp;b.md)\n')
        self.assertEqual(result["links_extracted"], 6)
        self.assertEqual(result["counts"]["PASS"], 6, result)

    def test_reference_links_images_and_table_links(self):
        self.write("image bytes", "image.png")
        result = self.run_check(
            '[direct](image.png) [reference][asset] [asset][] [asset]\n\n'
            '[asset]: image.png "title"\n\n'
            '[![image](image.png)](image.png)\n\n'
            '| Asset |\n| --- |\n| [table](image.png) |\n')
        self.assertEqual(result["links_extracted"], 7, result)
        self.assertEqual(result["counts"]["PASS"], 7)
        self.assertTrue(all(c["block_line"] is not None for c in result["checks"]))

    def test_each_occurrence_is_reported(self):
        result = self.run_check("[one](SKILL.md)\n\n[two](SKILL.md)")
        self.assertEqual(result["links_extracted"], 2)
        self.assertEqual([c["block_line"] for c in result["checks"]], [1, 3])

    def test_frontmatter_is_masked_without_changing_positions(self):
        result = self.run_check('---\nname: sample-skill\ndescription: "[not a link](missing.md)"\n---\n\n[real](SKILL.md)\n')
        self.assertEqual(result["links_extracted"], 1)
        self.assertEqual(result["checks"][0]["block_line"], 6)

    def test_yaml_literal_separator_does_not_end_frontmatter(self):
        result = self.run_check('---\ndescription: |\n  ---\n  [not a link](missing.md)\n---\n[real](SKILL.md)')
        self.assertEqual(result["counts"]["PASS"], 1)

    def test_missing_frontmatter_end_is_not_a_successful_scan(self):
        result = self.run_check('---\nname: sample-skill\n')
        self.assertEqual(result["exit_code"], 2)
        self.assert_check(result, "document.read", "ERROR")

    def test_code_html_and_plain_path_mentions_are_not_links(self):
        result = self.run_check(
            '`[inline](missing.md)`\n\n'
            '```markdown\n[fenced](missing.md)\n```\n\n'
            '    [indented](missing.md)\n\n'
            '<!-- [comment](missing.md) -->\n\n'
            '<a href="missing.md">HTML</a>\n\n'
            'Plain missing.md and \\[escaped](missing.md)\n\n'
            '[existing](SKILL.md)\n')
        self.assertEqual(result["links_extracted"], 1, result)
        self.assertEqual(result["exit_code"], 0)

    def test_image_alt_text_is_not_scanned_for_extra_links(self):
        self.write("image", "image.png")
        result = self.run_check('![caption [text](missing.md)](image.png)')
        self.assertEqual(result["links_extracted"], 1)
        self.assertEqual(result["exit_code"], 0)

    def test_external_urls_and_nonpath_schemes_are_explicitly_skipped(self):
        result = self.run_check(
            '[web](https://example.invalid/nope) [mail](mailto:test@example.invalid) '
            '[network](//example.invalid/path) [file](file:///missing.md) '
            '[custom](custom:whatever) <https://example.invalid>')
        self.assertEqual(result["counts"]["SKIP"], 6, result)
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(all(c["target"] is None for c in result["checks"]))

    def test_fragments_and_queries_do_not_become_filename_characters(self):
        result = self.run_check('[file](SKILL.md#no-such-heading) [self](#no-such-heading) [query](SKILL.md?view=1#top)')
        self.assertEqual(result["counts"]["PASS"], 2)
        self.assertEqual(result["counts"]["SKIP"], 1)
        self.assertTrue(all(not c["fragment_checked"] for c in result["checks"]))

    def test_missing_file_with_fragment_still_fails(self):
        result = self.run_check('[bad](absent.md#heading)')
        self.assertEqual(result["exit_code"], 1)

    def test_empty_link_destination_points_to_same_document(self):
        result = self.run_check('[self]()')
        self.assertEqual(result["counts"]["PASS"], 1)
        self.assertEqual(result["checks"][0]["resolved_target"], str(self.source))

    def test_absolute_local_paths(self):
        asset = self.root / "asset.txt"
        asset.write_text("asset")
        result = self.run_check(f'[absolute]({asset})')
        self.assertEqual(result["exit_code"], 0)

    def test_generated_looking_link_is_not_inferred_as_excluded(self):
        result = self.run_check('[future](report-001.md)')
        self.assertEqual(result["exit_code"], 1)

    def test_bad_encoded_paths(self):
        result = self.run_check('[nul](bad%00.md) [encoding](bad%FF.md)')
        self.assertEqual(result["counts"]["FAIL"], 2)
        self.assertTrue(all(c["id"] == "reference.path" for c in result["checks"]))

    def test_symlink_targets_and_broken_links(self):
        self.write("asset", "asset.txt")
        (self.skill / "valid.txt").symlink_to("asset.txt")
        (self.skill / "broken.txt").symlink_to("missing.txt")
        result = self.run_check('[ok](valid.txt) [bad](broken.txt)')
        self.assertEqual(result["counts"]["PASS"], 1)
        self.assertEqual(result["counts"]["FAIL"], 1)

    def test_symlink_then_parent_is_resolved_by_filesystem_not_lexically(self):
        external = self.root / "external"
        (external / "child").mkdir(parents=True)
        (external / "asset.txt").write_text("asset")
        (self.skill / "alias").symlink_to(external / "child", target_is_directory=True)
        result = self.run_check('[asset](alias/../asset.txt)')
        link = next(c for c in result["checks"] if "destination" in c)
        self.assertEqual(link["status"], "PASS", result)
        self.assertEqual(link["resolved_target"], str(external / "asset.txt"))
        self.assert_check(result, "scan.symlink", "UNCHECKED")

    def test_directory_symlink_cycle_is_reported_not_followed(self):
        (self.skill / "loop").symlink_to(self.skill, target_is_directory=True)
        result = self.run_check('[self](SKILL.md)')
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(len(result["documents"]), 1)

    def test_symlinked_markdown_uses_location_of_reference_document(self):
        external = self.root / "external.md"
        external.write_text('[near](asset.txt)')
        self.source.symlink_to(external)
        self.write("asset", "asset.txt")
        result = check_references(self.skill)
        self.assertEqual(result["exit_code"], 0)

    def test_input_root_preserves_symlink_then_parent_semantics(self):
        external = self.root / "external"
        (external / "child").mkdir(parents=True)
        (external / "sample-skill").mkdir()
        (external / "sample-skill" / "SKILL.md").write_text('[self](SKILL.md)')
        alias = self.root / "alias"
        alias.symlink_to(external / "child", target_is_directory=True)
        result = check_references(alias / ".." / "sample-skill")
        self.assertEqual(result["counts"]["PASS"], 1, result)
        self.assertEqual(result["exit_code"], 0)

    def test_no_documents_is_error_but_no_links_is_zero_count(self):
        self.assertEqual(check_references(self.skill)["exit_code"], 2)
        result = self.run_check('Text only and [unresolved][missing-label].')
        self.assertEqual(result["links_extracted"], 0)
        self.assertEqual(result["exit_code"], 0)

    def test_missing_target_directory(self):
        self.assertEqual(check_references(self.root / "absent")["exit_code"], 2)

    def test_read_errors_are_not_silently_ignored(self):
        self.write('[self](SKILL.md)')
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            result = check_references(self.skill)
        self.assertEqual(result["exit_code"], 2)
        self.assertFalse(result["documents"][0]["parsed"])
        self.source.write_bytes(b'\xff\xfe')
        self.assertEqual(check_references(self.skill)["exit_code"], 2)

    def test_directory_scan_errors_are_reported(self):
        self.write('[self](SKILL.md)')
        denied = PermissionError(errno.EACCES, "denied", str(self.skill))
        with patch("os.scandir", side_effect=denied):
            result = check_references(self.skill)
        self.assert_check(result, "scan.read", "ERROR")
        self.assertEqual(result["exit_code"], 2)

    def test_non_regular_markdown_and_link_targets_do_not_block(self):
        os.mkfifo(self.skill / "pipe.md")
        result = self.run_check('[pipe](pipe.md)')
        self.assert_check(result, "document.file", "ERROR")
        self.assert_check(result, "reference.kind", "FAIL")

    def test_cli_json_from_another_cwd_and_files_unchanged(self):
        self.write('[self](SKILL.md)')
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        run = self.cli("sample-skill", "--json")
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result["links_extracted"], 1)
        self.assertEqual(result["counts"]["PASS"], 1)
        self.assertEqual(before, hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(list(self.skill.iterdir()), [self.source])

    def test_cli_exit_codes_failure_and_missing_dependency(self):
        self.write('[missing](absent.md)')
        run = self.cli(self.skill, "--json")
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["status"], "FAIL")
        run = self.cli(self.skill, "--json", no_site=True)
        self.assertEqual(run.returncode, 2)
        self.assert_check(json.loads(run.stdout), "dependency.markdown", "ERROR")

    def test_cli_text_help_and_bad_arguments(self):
        self.write('[self](SKILL.md)')
        run = self.cli(self.skill)
        self.assertEqual(run.returncode, 0)
        self.assertIn("PASS", run.stdout)
        self.assertIn("추출 링크 1개", run.stdout)
        self.assertEqual(self.cli("--help").returncode, 0)
        self.assertEqual(self.cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()
