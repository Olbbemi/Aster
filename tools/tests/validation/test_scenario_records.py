"""Scenario record correspondence, independent fixtures and read-only CLI behavior."""

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
from check_scenario_records import check_scenario_records

REQUIREMENTS = """<!-- lifecycle-check:requirements -->
| 요건 ID | 필수 여부 | 범위 | 사유 |
| --- | --- | --- | --- |
| R1 | 필수 | 대상 | |
| R2 | 선택 | 제외 | 이번 범위 밖 |
"""
PLAN = """<!-- lifecycle-check:scenarios -->
| 사례 ID | 대응 요건 | 필수 여부 | 범위 | 기대 결과 | 사유 |
| --- | --- | --- | --- | --- | --- |
| S1 | R1 | 필수 | 대상 | 예상 반환값 | |
| S2 | R2 | 선택 | 보류 | 다른 환경의 반환값 | 환경 대기 |
"""
RESULTS = """<!-- lifecycle-check:results -->
| 사례 ID | 상태 | 근거/사유 |
| --- | --- | --- |
| S1 | 통과 | 실제 반환값 확인 |
| S2 | 미실행 | 환경 대기 |
"""
DOCUMENT = "# 시험 기록\n\n" + REQUIREMENTS + "\n" + PLAN + "\n" + RESULTS


class ScenarioRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-scenario-records-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "records.md"
        self.path.write_text(DOCUMENT, encoding="utf-8")

    def check(self, text=None, phase="results", paths=None):
        if text is not None:
            self.path.write_text(text, encoding="utf-8")
        return check_scenario_records(paths or [self.path], phase=phase)

    def issue(self, report, identifier, status="FAIL"):
        self.assertTrue(any(item["id"] == identifier and item["status"] == status
                            for item in report["checks"]), report)

    def snapshot(self):
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.iterdir() if path.is_file()}

    def cli(self, *args, no_site=False):
        return subprocess.run([sys.executable, "-B", *(["-S"] if no_site else []),
                               str(SCRIPTS / "check_scenario_records.py"), *map(str, args)],
                              cwd=self.root, capture_output=True, text=True, timeout=15)

    def test_valid_results_and_separate_execution_summary(self):
        report = self.check()
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(report["execution"]["counts"], {"통과": 1, "미실행": 1})
        self.assertEqual(report["execution"]["required_cases_not_passed"], [])

    def test_plan_mode_ignores_result_content(self):
        for results in ("", RESULTS.replace("통과", "아직 미정"), RESULTS + "\n" + RESULTS):
            report = self.check(REQUIREMENTS + "\n" + PLAN + "\n" + results, phase="plan")
            self.assertEqual(report["exit_code"], 0, report)
            self.assertEqual(report["execution"], {"checked": False})

    def test_failed_unexecuted_and_unjudged_cases_are_not_record_failures(self):
        for state in ("실패", "미실행", "미판정"):
            with self.subTest(state=state):
                report = self.check(DOCUMENT.replace("| S1 | 통과 |", f"| S1 | {state} |"))
                self.assertEqual(report["exit_code"], 0, report)
                self.assertEqual(report["execution"]["required_cases_not_passed"], ["S1"])

    def test_scope_exclusion_preserves_failure_without_requiring_pass(self):
        source = DOCUMENT.replace("| S1 | R1 | 필수 | 대상 | 예상 반환값 | |",
                                  "| S1 | R1 | 필수 | 제외 | 예상 반환값 | 범위 변경 |")
        source = source.replace("| R1 | 필수 | 대상 | |", "| R1 | 필수 | 제외 | 범위 변경 |")
        source = source.replace("| S1 | 통과 |", "| S1 | 실패 |")
        report = self.check(source)
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(report["execution"]["counts"]["실패"], 1)
        self.assertEqual(report["execution"]["required_cases_not_passed"], [])

    def test_missing_duplicate_and_unregistered_result_ids(self):
        self.issue(self.check(DOCUMENT.replace("| S1 | 통과 | 실제 반환값 확인 |\n", "")), "result.missing")
        self.issue(self.check(DOCUMENT + "| S1 | 통과 | 재시험 |\n"), "record.duplicate")
        self.issue(self.check(DOCUMENT + "| S9 | 통과 | 임의 결과 |\n"), "result.unregistered")

    def test_duplicate_requirement_and_scenario_ids(self):
        for original, addition in ((REQUIREMENTS, "| R1 | 필수 | 대상 | |\n"),
                                   (PLAN, "| S1 | R1 | 필수 | 대상 | 중복 | |\n")):
            self.issue(self.check(DOCUMENT.replace(original, original + addition)), "record.duplicate")

    def test_id_syntax_and_case_sensitive_mapping(self):
        for bad in ("", "한글", "S 1", "_S1"):
            self.issue(self.check(DOCUMENT.replace("| S1 | 통과", f"| {bad} | 통과")), "record.id")
        self.issue(self.check(DOCUMENT.replace("| S1 | 통과", "| s1 | 통과")), "result.unregistered")
        self.assertEqual(self.check(DOCUMENT.replace("S1", "S1.cli_v2-a"))["exit_code"], 0)

    def test_unknown_empty_and_duplicate_requirement_references(self):
        for value in ("", "R1, R1", "R1,"):
            self.issue(self.check(DOCUMENT.replace("| S1 | R1 |", f"| S1 | {value} |")),
                       "scenario.requirements")
        self.issue(self.check(DOCUMENT.replace("| S1 | R1 |", "| S1 | R9 |")),
                   "scenario.unknown-requirement")
        self.assertEqual(self.check(DOCUMENT.replace("| S1 | R1 |", "| S1 | R1, R2 |"))["exit_code"], 0)

    def test_active_requirements_need_active_scenario_coverage(self):
        source = DOCUMENT.replace("| R2 | 선택 | 제외 |", "| R2 | 선택 | 대상 |")
        self.issue(self.check(source), "requirement.uncovered")
        source = source.replace("| S2 | R2 | 선택 | 보류 |", "| S2 | R2 | 선택 | 대상 |")
        self.assertEqual(self.check(source)["exit_code"], 0)

    def test_scope_required_flag_expected_result_and_reason(self):
        self.issue(self.check(DOCUMENT.replace("| R1 | 필수", "| R1 | unknown")), "record.required")
        self.issue(self.check(DOCUMENT.replace("| R1 | 필수 | 대상", "| R1 | 필수 | 통과")), "record.scope")
        for old in ("이번 범위 밖", "환경 대기"):
            self.issue(self.check(DOCUMENT.replace(old, "")), "record.reason")
        self.issue(self.check(DOCUMENT.replace("예상 반환값", "")), "scenario.expected")
        self.issue(self.check(DOCUMENT.replace("실제 반환값 확인", "")), "result.evidence")
        self.issue(self.check(DOCUMENT.replace("| S1 | 통과", "| S1 | 제외")), "result.state")

    def test_missing_duplicate_empty_and_misplaced_tables(self):
        self.issue(self.check(DOCUMENT.replace(REQUIREMENTS, "")), "table.required")
        self.issue(self.check(DOCUMENT + "\n" + PLAN), "table.required")
        source = DOCUMENT.replace("| R1 | 필수 | 대상 | |\n", "").replace("| R2 | 선택 | 제외 | 이번 범위 밖 |\n", "")
        self.issue(self.check(source), "table.empty")
        self.issue(self.check(DOCUMENT.replace("<!-- lifecycle-check:scenarios -->",
                                               "<!-- lifecycle-check:scenarios -->\n\n중간 문단\n")), "table.marker")
        self.issue(self.check(DOCUMENT.replace("lifecycle-check:scenarios", "lifecycle-check:unknown")), "table.marker")

    def test_markers_inside_code_quotes_and_lists_are_not_actual_records(self):
        for replacement in ("```markdown\n" + REQUIREMENTS + "```\n",
                            "\n".join("> " + line for line in REQUIREMENTS.splitlines()) + "\n",
                            "- 예시\n\n" + "\n".join("  " + line for line in REQUIREMENTS.splitlines()) + "\n"):
            self.issue(self.check(DOCUMENT.replace(REQUIREMENTS, replacement)), "table.required")

    def test_reordered_and_additional_columns_and_formatted_ids(self):
        source = DOCUMENT.replace(RESULTS, """<!-- lifecycle-check:results -->
| 설명 | 상태 | 근거/사유 | 사례 ID |
| --- | --- | --- | --- |
| 보충 | 통과 | [근거](not-read.md) | **S1** |
| 보충 | 미실행 | 환경 대기 | `S2` |
""")
        self.assertEqual(self.check(source)["exit_code"], 0)

    def test_header_and_raw_row_column_errors(self):
        for replacement in ("판정", "사례 ID"):
            self.issue(self.check(DOCUMENT.replace("| 상태 |", f"| {replacement} |")), "table.headers")
        for replacement in ("| S1 | 통과 | 실제 반환값 확인 | 초과 |", "| S1 | 통과 |"):
            self.issue(self.check(DOCUMENT.replace("| S1 | 통과 | 실제 반환값 확인 |", replacement)), "table.columns")
        self.assertEqual(self.check(DOCUMENT.replace("예상 반환값", r"왼쪽 \| 오른쪽"))["exit_code"], 0)

    def test_separate_files_and_repeated_input_do_not_duplicate_records(self):
        self.path.write_text(REQUIREMENTS + "\n" + PLAN)
        results = self.root / "results.md"
        results.write_text(RESULTS)
        report = self.check(paths=[self.path, results, self.path])
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(len(report["files"]), 2)

    def test_frontmatter_bom_crlf_and_unmarked_tables(self):
        self.path.write_bytes(b"\xef\xbb\xbf" + ("---\nname: sample\n---\n" + DOCUMENT).replace("\n", "\r\n").encode())
        self.assertEqual(self.check()["exit_code"], 0)
        self.issue(self.check("# no records\n\n| 임의 표 |\n| --- |\n| 값 |\n"), "table.required")

    def test_documented_minimal_format_is_a_valid_unexecuted_plan(self):
        from markdown_it import MarkdownIt
        standard = SCRIPTS.parents[2] / "standards/skills/scenario-records.md"
        examples = [token.content for token in MarkdownIt("commonmark").parse(standard.read_text())
                    if token.type == "fence" and token.info == "markdown"]
        self.assertEqual(len(examples), 1)
        self.assertEqual(self.check(examples[0], phase="plan")["exit_code"], 0)
        report = self.check(examples[0])
        self.assertEqual(report["exit_code"], 0, report)
        self.assertEqual(report["execution"]["required_cases_not_passed"], ["S1"])

    def test_fifo_is_rejected_without_opening(self):
        import os
        fifo = self.root / "pipe.md"
        os.mkfifo(fifo)
        self.issue(self.check(paths=[fifo]), "document.read", "ERROR")

    def test_read_errors_are_not_passes_and_input_is_unchanged(self):
        for path in (self.root / "missing.md", self.root):
            self.issue(self.check(paths=[path]), "document.read", "ERROR")
        self.path.write_bytes(b"\xff")
        self.issue(self.check(), "document.read", "ERROR")
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            self.issue(self.check(), "document.read", "ERROR")
        self.issue(check_scenario_records([], phase="plan"), "input", "ERROR")
        self.issue(check_scenario_records([self.path], phase="wrong"), "input", "ERROR")

    def test_cli_json_text_failures_and_dependency_are_read_only(self):
        before = self.snapshot()
        for phase in ("plan", "results"):
            run = self.cli("records.md", "--phase", phase, "--json")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(json.loads(run.stdout)["phase"], phase)
        run = self.cli("records.md", "--phase", "results")
        self.assertIn("실제 시험 상태", run.stdout)
        self.assertEqual(self.cli("records.md").returncode, 2)
        self.assertEqual(self.cli("--help").returncode, 0)
        run = self.cli("records.md", "--phase", "results", "--json", no_site=True)
        self.assertEqual(run.returncode, 2)
        self.issue(json.loads(run.stdout), "dependency", "ERROR")
        self.assertEqual(self.snapshot(), before)
        self.path.write_text(DOCUMENT.replace("실제 반환값 확인", ""))
        before = self.snapshot()
        run = self.cli("records.md", "--phase", "results", "--json")
        self.assertEqual(run.returncode, 1)
        self.issue(json.loads(run.stdout), "result.evidence")
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
