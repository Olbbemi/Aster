"""Behavior tests using independent SKILL.md fixtures and actual CLI calls."""

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

from check_structure import check_structure


SCRIPT = SCRIPTS / "check_structure.py"
VALID = "---\nname: sample-skill\ndescription: 샘플 작업에 사용하는 스킬입니다.\n---\n# 지침\n"


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-structure-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "sample-skill"
        self.skill.mkdir()
        self.file = self.skill / "SKILL.md"

    def write(self, text=VALID):
        self.file.write_text(text, encoding="utf-8")
        return check_structure(self.skill)

    def assert_issue(self, result, check_id, status="FAIL"):
        self.assertTrue(any(item["id"] == check_id and item["status"] == status
                            for item in result["checks"]), result)

    def cli(self, *args, no_site=False, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", *(["-S"] if no_site else []), str(SCRIPT), *map(str, args)],
            cwd=cwd or self.root, capture_output=True, text=True, timeout=15,
        )

    def test_minimal_file_without_optional_fields_passes(self):
        result = self.write()
        self.assertEqual((result["status"], result["exit_code"]), ("PASS", 0))

    def test_multiline_description_and_markdown_are_not_parsed_as_metadata(self):
        result = self.write('---\nname: sample-skill\ndescription: |\n  첫 줄\n  둘째 줄\n---\n[not YAML\n')
        self.assertEqual(result["exit_code"], 0)

    def test_crlf_and_utf8_bom_are_readable(self):
        self.file.write_bytes(b"\xef\xbb\xbf" + VALID.replace("\n", "\r\n").encode())
        self.assertEqual(check_structure(self.skill)["exit_code"], 0)

    def test_description_has_no_invented_length_cap(self):
        result = self.write(VALID.replace("샘플 작업에 사용하는 스킬입니다.", "한" * 3000))
        self.assertEqual(result["exit_code"], 0)

    def test_name_has_no_invented_length_cap(self):
        long_skill = self.root / ("a" * 65)
        long_skill.mkdir()
        (long_skill / "SKILL.md").write_text(VALID.replace("sample-skill", "a" * 65))
        self.assertEqual(check_structure(long_skill)["exit_code"], 0)

    def test_quoted_yaml_boolean_word_is_a_valid_name(self):
        directory = self.root / "yes"
        directory.mkdir()
        (directory / "SKILL.md").write_text(VALID.replace("sample-skill", '"yes"'))
        self.assertEqual(check_structure(directory)["exit_code"], 0)

    def test_missing_required_fields(self):
        for field, line in (("name", "name: sample-skill\n"),
                            ("description", "description: 샘플 작업에 사용하는 스킬입니다.\n")):
            with self.subTest(field=field):
                result = self.write(VALID.replace(line, ""))
                self.assert_issue(result, f"{field}.required")
                self.assertEqual(result["exit_code"], 1)

    def test_blank_and_nonstring_required_values(self):
        for field in ("name", "description"):
            for value, issue in [('""', "nonempty"), ('"   "', "nonempty"),
                                 ('"\\n\\t"', "nonempty"), ("null", "type"),
                                 ("42", "type"), ("false", "type"),
                                 ("[text]", "type"), ("{value: text}", "type")]:
                with self.subTest(field=field, value=value):
                    other = "description: text" if field == "name" else "name: sample-skill"
                    result = self.write(f"---\n{other}\n{field}: {value}\n---\n")
                    self.assert_issue(result, f"{field}.{issue}")

    def test_missing_or_late_start_and_missing_end(self):
        for text in ("", "# no frontmatter\n", "\n" + VALID,
                     "# Heading\n" + VALID, "  " + VALID,
                     "---\nname: sample-skill\n"):
            with self.subTest(text=text):
                self.assert_issue(self.write(text), "frontmatter.delimiters")

    def test_indented_dashes_in_multiline_description_are_not_a_delimiter(self):
        result = self.write('---\nname: sample-skill\ndescription: |\n  첫 줄\n  ---\n  둘째 줄\n---\n')
        self.assertEqual(result["exit_code"], 0)

    def test_invalid_yaml_including_unsafe_tags_is_rejected(self):
        for content in ("name: [unterminated", "name:\n\tbad: value",
                        "name: !!python/object/apply:os.system ['false']"):
            with self.subTest(content=content):
                self.assert_issue(self.write(f"---\n{content}\n---\n"), "frontmatter.yaml")

    def test_non_mapping_or_nonstring_keys(self):
        for content in ("[]", "null", "some text", "1: value"):
            with self.subTest(content=content):
                self.assert_issue(self.write(f"---\n{content}\n---\n"), "frontmatter.mapping")

    def test_duplicate_explicit_keys_are_not_silently_overwritten(self):
        result = self.write(VALID.replace("name: sample-skill", "name: wrong\nname: sample-skill"))
        self.assert_issue(result, "frontmatter.yaml")
        failure = next(item for item in result["checks"] if item["status"] == "FAIL")
        self.assertEqual(failure["line"], 3)

    def test_nested_duplicate_keys_are_reported(self):
        result = self.write(VALID.replace("name: sample-skill", "name: sample-skill\nmetadata: {a: 1, a: 2}"))
        self.assert_issue(result, "frontmatter.yaml")

    def test_yaml_merge_override_is_valid(self):
        result = self.write('---\n<<: &defaults {name: other, description: text}\nname: sample-skill\n---\n')
        self.assertEqual(result["exit_code"], 0, result)

    def test_name_mismatch_is_not_fixed_by_trimming(self):
        for name in ("different", '" sample-skill "'):
            with self.subTest(name=name):
                self.assert_issue(self.write(VALID.replace("sample-skill", name)), "name.directory")

    def test_invalid_name_characters(self):
        for name in ("Sample-skill", "sample_skill", "sample.skill", "샘플", '"sample skill"'):
            with self.subTest(name=name):
                self.assert_issue(self.write(VALID.replace("sample-skill", name)), "name.characters")

    def test_missing_wrongcase_or_directory_named_skill_md(self):
        self.assert_issue(check_structure(self.skill), "skill.file")
        (self.skill / "skill.md").write_text(VALID)
        self.assert_issue(check_structure(self.skill), "skill.file")
        self.file.mkdir()
        self.assert_issue(check_structure(self.skill), "skill.file")

    def test_target_must_be_a_directory(self):
        self.write()
        for path in (self.root / "absent", self.file):
            with self.subTest(path=path):
                result = check_structure(path)
                self.assertEqual(result["exit_code"], 2)
                self.assert_issue(result, "target.directory", "ERROR")

    def test_unreadable_and_non_utf8_input_are_execution_errors(self):
        self.write()
        with patch.object(Path, "read_text", side_effect=PermissionError("permission denied")):
            self.assert_issue(check_structure(self.skill), "skill.read", "ERROR")
        self.file.write_bytes(b"\xff\xfe")
        self.assert_issue(check_structure(self.skill), "skill.read", "ERROR")

    def test_optional_field_is_neither_silent_pass_nor_invalid(self):
        result = self.write(VALID.replace("name: sample-skill", "name: sample-skill\nmetadata: {owner: team}"))
        self.assertEqual((result["status"], result["exit_code"]), ("INCOMPLETE", 2))
        self.assert_issue(result, "optional.schema", "UNCHECKED")
        self.assertFalse(any(item["status"] == "FAIL" for item in result["checks"]))

    def test_failures_remain_visible_with_unchecked_fields(self):
        result = self.write(VALID.replace("name: sample-skill", "name: wrong\nunknown: 1"))
        self.assertEqual(result["exit_code"], 2)
        self.assert_issue(result, "name.directory")
        self.assert_issue(result, "optional.schema", "UNCHECKED")

    def test_cli_json_from_another_cwd_and_no_input_changes(self):
        self.write()
        before = hashlib.sha256(self.file.read_bytes()).hexdigest()
        run = self.cli("sample-skill/.", "--json")
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["target"], str(self.file))
        self.assertEqual(before, hashlib.sha256(self.file.read_bytes()).hexdigest())
        self.assertEqual(list(self.skill.iterdir()), [self.file])

    def test_cli_failure_exit_and_result(self):
        self.write(VALID.replace("sample-skill", "wrong"))
        run = self.cli(self.skill, "--json")
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["exit_code"], 1)

    def test_cli_optional_field_exit(self):
        self.write(VALID.replace("name: sample-skill", "name: sample-skill\nunknown: 1"))
        run = self.cli(self.skill, "--json")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["status"], "INCOMPLETE")

    def test_cli_missing_yaml_dependency(self):
        self.write()
        run = self.cli(self.skill, "--json", no_site=True)
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assert_issue(json.loads(run.stdout), "dependency.yaml", "ERROR")

    def test_cli_bad_arguments(self):
        for args in ((), ("--not-an-option",)):
            with self.subTest(args=args):
                run = self.cli(*args)
                self.assertEqual(run.returncode, 2)

    def test_cli_text_and_help(self):
        self.write()
        run = self.cli(self.skill)
        self.assertEqual(run.returncode, 0)
        self.assertIn("PASS", run.stdout)
        self.assertIn("basic-structure", run.stdout)
        self.assertEqual(self.cli("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
