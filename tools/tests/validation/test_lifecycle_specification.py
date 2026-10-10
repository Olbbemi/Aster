"""Lifecycle format behavior, independent fixtures and real read-only CLI calls."""

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
from check_lifecycle_specification import check_lifecycle_specification, DEFAULT_LIFECYCLE

SCRIPT = SCRIPTS / "check_lifecycle_specification.py"
ORDER = """# 생명 주기

## 생명 주기 순서

1. `problem-definition` (문제 정의)
2. `completed` (완료)

## 기타

1. 이 목록은 단계가 아니다.
"""
BODY = """# 샘플 작업

## problem-definition (문제 정의)

### 진입 조건 확인

### 문제

### 완료 조건 확인

### 단계 이동 기록

## completed (완료)

### 진입 조건 확인

### 판단

### 완료 조건 확인

### 단계 이동 기록
"""
META = """---
name: sample-skill
target_path: .agents/skills/sample-skill
operation: create
current_stage: problem-definition
in_review: false
---
"""


class LifecycleSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-lifecycle-format-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rules = self.root / "skill-lifecycle"
        (self.rules / "references/stages").mkdir(parents=True)
        (self.rules / "assets").mkdir()
        (self.rules / "references/lifecycle.md").write_text(ORDER, encoding="utf-8")
        for stage, record in (("problem-definition", "문제"), ("completed", "판단")):
            (self.rules / f"references/stages/{stage}.md").write_text(
                f"# 단계\n\n## 단계 운영 규칙\n\n### 검사 대상 아님\n\n"
                f"## 명세서 기록 항목\n\n### {record}\n", encoding="utf-8")
        self.template = self.rules / "assets/lifecycle-template.md"
        self.template.write_text(META.replace("operation: create", "operation: '<선택>'") + BODY)
        self.spec = self.root / "specification.md"
        self.spec.write_text(META + BODY, encoding="utf-8")

    def check(self, text=None, **kwargs):
        if text is not None:
            self.spec.write_text(text, encoding="utf-8")
        return check_lifecycle_specification(self.spec, lifecycle_directory=self.rules, **kwargs)

    def issue(self, result, identifier, status="FAIL"):
        self.assertTrue(any(item["id"] == identifier and item["status"] == status
                            for item in result["checks"]), result)

    def cli(self, *args, no_site=False):
        return subprocess.run(
            [sys.executable, "-B", *(["-S"] if no_site else []), str(SCRIPT), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, timeout=15)

    def snapshot(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def test_valid_standard_specification(self):
        self.assertEqual(self.check()["exit_code"], 0)

    def test_initial_null_and_all_operations(self):
        for operation in ("create", "update", "integrate", "deprecate"):
            with self.subTest(operation=operation):
                text = META.replace("name: sample-skill", "name: null")
                text = text.replace("target_path: .agents/skills/sample-skill", "target_path: null")
                text = text.replace("operation: create", "operation: " + operation)
                self.assertEqual(self.check(text + BODY)["exit_code"], 0)

    def test_review_boolean_and_invalid_types(self):
        for value in ("true", "false"):
            with self.subTest(value=value):
                result = self.check(META.replace("in_review: false", "in_review: " + value) + BODY)
                self.assertEqual(result["exit_code"], 0)
        for value in ('"true"', '"false"', "0", "1", "null", "[]", "{}", '""'):
            with self.subTest(value=value):
                self.issue(self.check(META.replace("in_review: false", "in_review: " + value) + BODY),
                           "in_review.type")
        self.issue(self.check(META.replace("in_review: false", "in_review: true\nin_review: false") + BODY),
                   "frontmatter.yaml")

    def test_legacy_missing_review_is_reported_without_rewrite(self):
        self.spec.write_text(META.replace("in_review: false\n", "") + BODY, encoding="utf-8")
        before = self.snapshot()
        result = self.cli(self.spec, "--lifecycle-directory", self.rules, "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.issue(json.loads(result.stdout), "frontmatter.fields")
        self.assertEqual(self.snapshot(), before)

    def test_format_pass_does_not_establish_approval_or_completion(self):
        text = (META.replace("current_stage: problem-definition", "current_stage: completed")
                .replace("name: sample-skill", "name: null") + BODY)
        result = self.check(text + "\n승인 미확인. 필수 조건 미충족.\n")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(any("실제 완료" in limit for limit in result["limits"]))

    def test_missing_extra_or_nonstring_fields(self):
        for line in META.splitlines()[1:-1]:
            with self.subTest(line=line):
                self.issue(self.check((META + BODY).replace(line + "\n", "")), "frontmatter.fields")
        self.issue(self.check(META.replace("operation: create", "operation: create\nstatus: done") + BODY),
                   "frontmatter.fields")
        self.issue(self.check(META.replace("operation: create", "operation: create\n1: value") + BODY),
                   "frontmatter.mapping")

    def test_types_and_empty_values(self):
        values = {"name": "sample-skill", "target_path": ".agents/skills/sample-skill",
                  "operation": "create", "current_stage": "problem-definition"}
        for field, original in values.items():
            for invalid in ('""', '"   "', "42", "false", "[text]", "{key: value}"):
                with self.subTest(field=field, invalid=invalid):
                    self.issue(self.check(META.replace(f"{field}: {original}", f"{field}: {invalid}") + BODY),
                               f"{field}.type")
        for field in ("operation", "current_stage"):
            self.issue(self.check(META.replace(f"{field}: {values[field]}", f"{field}: null") + BODY),
                       f"{field}.type")

    def test_invalid_enums_and_duplicate_yaml_keys(self):
        for field, old in (("operation", "create"), ("current_stage", "problem-definition")):
            self.issue(self.check(META.replace(f"{field}: {old}", f"{field}: invalid") + BODY),
                       f"{field}.value")
        self.issue(self.check(META.replace("name: sample-skill", "name: wrong\nname: sample-skill") + BODY),
                   "frontmatter.yaml")

    def test_bad_yaml_mapping_and_delimiters(self):
        for front in ("[]", "null", "text", "{1: value}"):
            self.issue(self.check(f"---\n{front}\n---\n" + BODY), "frontmatter.mapping")
        for front in ("name: [unterminated", "name:\n\tbad", "!!python/object/apply:os.system ['false']"):
            self.issue(self.check(f"---\n{front}\n---\n" + BODY), "frontmatter.yaml")
        for text in ("", BODY, "\n" + META + BODY, "---\nname: sample-skill\n"):
            self.issue(self.check(text), "frontmatter.delimiters")

    def test_crlf_bom_and_quoted_yaml_values(self):
        self.spec.write_bytes(b"\xef\xbb\xbf" + (META + BODY).replace("\n", "\r\n").encode())
        self.assertEqual(self.check()["exit_code"], 0)
        self.assertEqual(self.check(META.replace("name: sample-skill", 'name: "yes"') + BODY)["exit_code"], 0)

    def test_missing_reordered_duplicate_or_wrong_language_stage(self):
        first, last = BODY.split("## completed (완료)")
        reordered = "# 샘플 작업\n\n## completed (완료)" + last + first.split("# 샘플 작업\n", 1)[1]
        for body in (first, reordered, BODY + "\n## completed (완료)\n",
                     BODY.replace("## completed (완료)", "## completed (완료됨)")):
            with self.subTest(body=body):
                self.issue(self.check(META + body), "stages.order")

    def test_missing_or_duplicate_required_records(self):
        for heading in ("진입 조건 확인", "완료 조건 확인", "단계 이동 기록", "문제"):
            with self.subTest(heading=heading):
                self.issue(self.check(META + BODY.replace(f"### {heading}\n", "", 1)), "stage.headings")
                self.issue(self.check(META + BODY.replace(f"### {heading}\n", f"### {heading}\n\n### {heading}\n", 1)),
                           "stage.headings")

    def test_wrong_heading_depth_does_not_satisfy_required_record(self):
        self.issue(self.check(META + BODY.replace("### 문제", "#### 문제")), "stage.headings")

    def test_examples_comments_and_quoted_headings_are_not_records(self):
        for fake in ("```markdown\n### 문제\n```", "<!--\n### 문제\n-->", "> ### 문제"):
            self.issue(self.check(META + BODY.replace("### 문제", fake)), "stage.headings")
        extra = "\n```markdown\n## completed (완료)\n### 판단\n```\n<!--\n## completed (완료)\n-->\n> ## completed (완료)\n"
        self.assertEqual(self.check(META + BODY + extra)["exit_code"], 0)

    def test_additional_headings_and_reference_content_are_allowed(self):
        body = BODY.replace("### 문제\n", "### 문제\n\n[근거](missing.md)\n\n### 추가 설명\n\n#### 상세\n")
        self.assertEqual(self.check(META + body + "\n## 관련 자료\n")["exit_code"], 0)

    def test_rendered_headings_and_setext_document_title(self):
        body = BODY.replace("# 샘플 작업", "샘플 작업\n==========")
        body = body.replace("## completed (완료)", "## `completed` (완료)").replace("### 판단", "### **판단**")
        self.assertEqual(self.check(META + body)["exit_code"], 0)

    def test_missing_late_and_duplicate_document_title(self):
        for body in (BODY.replace("# 샘플 작업\n", "", 1), BODY + "\n# 추가 문서\n",
                     BODY.replace("# 샘플 작업\n", "", 1) + "\n# 늦은 제목\n"):
            self.issue(self.check(META + body), "document.title")

    def test_template_mode_does_not_treat_placeholder_as_specification(self):
        result = check_lifecycle_specification(check_template=True, lifecycle_directory=self.rules)
        self.assertEqual(result["exit_code"], 0)
        result = check_lifecycle_specification(self.template, lifecycle_directory=self.rules)
        self.issue(result, "operation.value")

    def test_template_title_changes_and_order_mismatch_are_detected(self):
        for body in (BODY.replace("### 문제", "### 다른 제목"),
                     BODY.replace("### 진입 조건 확인\n\n### 문제", "### 문제\n\n### 진입 조건 확인"),
                     BODY.replace("### 문제", "### 추가 제목\n\n### 문제")):
            self.template.write_text(META + body)
            result = check_lifecycle_specification(check_template=True, lifecycle_directory=self.rules)
            self.issue(result, "template.headings")

    def test_stage_document_is_source_for_required_records(self):
        path = self.rules / "references/stages/completed.md"
        path.write_text(path.read_text() + "\n### 새 기록\n")
        self.issue(self.check(), "stage.headings")
        self.issue(check_lifecycle_specification(check_template=True, lifecycle_directory=self.rules),
                   "template.headings")

    def test_template_extra_stage_is_not_ignored_as_supplementary_content(self):
        self.template.write_text(META + BODY + "\n## unknown-stage (추가 단계)\n")
        result = check_lifecycle_specification(check_template=True, lifecycle_directory=self.rules)
        self.issue(result, "stages.order")

    def test_unreadable_target_invalid_utf8_and_missing_rules_are_errors(self):
        self.spec.unlink()
        self.issue(self.check(), "specification.read", "ERROR")
        self.spec.write_bytes(b"\xff\xfe")
        self.issue(self.check(), "specification.read", "ERROR")
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            self.issue(self.check(), "rules.read", "ERROR")
        (self.rules / "references/lifecycle.md").unlink()
        self.issue(self.check(), "rules.read", "ERROR")

    def test_malformed_rule_list_or_record_sections_are_errors(self):
        order_path = self.rules / "references/lifecycle.md"
        for value in ("# no list", ORDER.replace("2. `completed` (완료)", "2. not a stage"),
                      ORDER.replace("2. `completed` (완료)", "2. `problem-definition` (문제 정의)")):
            order_path.write_text(value)
            self.issue(self.check(), "rules.read", "ERROR")
        order_path.write_text(ORDER)
        path = self.rules / "references/stages/completed.md"
        path.write_text("# completed\n\n## 명세서 기록 항목\n\n### 판단\n\n### 판단\n")
        self.issue(self.check(), "rules.read", "ERROR")

    def test_error_does_not_hide_other_failure_in_combined_modes(self):
        self.template.unlink()
        result = self.check(META.replace("operation: create", "operation: invalid") + BODY,
                            check_template=True)
        self.assertEqual(result["exit_code"], 2)
        self.issue(result, "template.read", "ERROR")
        self.issue(result, "operation.value")

    def test_cli_json_from_other_cwd_and_no_file_changes(self):
        before = self.snapshot()
        run = self.cli("specification.md", "--check-template", "--lifecycle-directory", self.rules, "--json")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "PASS")
        self.assertEqual(self.snapshot(), before)

    def test_cli_failure_error_text_help_and_dependency(self):
        self.spec.write_text(META.replace("operation: create", "operation: invalid") + BODY)
        before = self.snapshot()
        run = self.cli(self.spec, "--lifecycle-directory", self.rules, "--json")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["exit_code"], 1)
        run = self.cli(self.root / "missing.md", "--lifecycle-directory", self.rules, "--json")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["exit_code"], 2)
        run = self.cli("--check-template", "--lifecycle-directory", self.rules)
        self.assertEqual(run.returncode, 0)
        self.assertIn("lifecycle-format", run.stdout)
        self.assertEqual(self.cli("--help").returncode, 0)
        self.assertEqual(self.cli().returncode, 2)
        run = self.cli(self.spec, "--json", no_site=True)
        self.assertEqual(run.returncode, 2)
        self.issue(json.loads(run.stdout), "dependency", "ERROR")
        self.assertEqual(self.snapshot(), before)

    def test_current_repository_template_correspondence(self):
        result = check_lifecycle_specification(check_template=True)
        self.assertEqual(result["exit_code"], 0, result)
        # A fresh standard document exercises all current stages without creating a real work record.
        source = (DEFAULT_LIFECYCLE / "assets/lifecycle-template.md").read_text()
        source = source.replace('operation: "<create|update|integrate|deprecate>"', 'operation: create')
        source = source.replace("# <작업 주제>", "# 시험")
        self.spec.write_text(source)
        self.assertEqual(check_lifecycle_specification(self.spec)["exit_code"], 0)


STAGE_RULES = ORDER + """
## 단계 정의 공통 항목

- 진입 조건
- 수행 작업
- 완료 조건
- 허용 전이
- 산출물

다음 목록은 운영 항목이 아니다.

- 추가 설명
"""
STAGE_BODY = """
## 단계 운영 규칙

### 진입 조건

### 수행 작업

### 완료 조건

### 허용 전이

### 산출물

## 명세서 기록 항목

"""


class LifecycleStageDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aster-lifecycle-stages-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rules = self.root / "skill-lifecycle"
        self.stage_dir = self.rules / "references/stages"
        self.stage_dir.mkdir(parents=True)
        self.policy = self.rules / "references/lifecycle.md"
        self.policy.write_text(STAGE_RULES, encoding="utf-8")
        for stage, title, record in (("problem-definition", "문제 정의", "문제"),
                                     ("completed", "완료", "판단")):
            (self.stage_dir / f"{stage}.md").write_text(
                f"# {stage} ({title})\n" + STAGE_BODY + f"### {record}\n", encoding="utf-8")
        self.path = self.stage_dir / "completed.md"
        self.source = self.path.read_text(encoding="utf-8")
        (self.rules / "assets").mkdir()
        self.template = self.rules / "assets/lifecycle-template.md"
        self.template.write_text(META + BODY, encoding="utf-8")
        self.spec = self.root / "specification.md"
        self.spec.write_text(META + BODY, encoding="utf-8")

    def check(self, source=None, **kwargs):
        if source is not None:
            self.path.write_text(source, encoding="utf-8")
        return check_lifecycle_specification(check_stages=True, lifecycle_directory=self.rules, **kwargs)

    def issue(self, report, identifier, status="FAIL"):
        self.assertTrue(any(item["id"] == identifier and item["status"] == status
                            for item in report["checks"]), report)

    def snapshot(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def cli(self, *args, no_site=False):
        return subprocess.run(
            [sys.executable, "-B", *(["-S"] if no_site else []), str(SCRIPT), "--check-stages",
             "--lifecycle-directory", str(self.rules), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, timeout=15)

    def test_standalone_does_not_require_template_or_work_specification(self):
        self.template.unlink()
        self.spec.unlink()
        report = self.check()
        self.assertEqual(report["exit_code"], 0, report)
        self.assertTrue(report["check_stages"])
        self.assertFalse(report["check_template"])
        self.assertTrue(all(item["id"].startswith("stage-documents.") for item in report["checks"]))

    def test_missing_and_unregistered_stage_files(self):
        self.path.rename(self.stage_dir / "unknown.md")
        report = self.check()
        self.assertEqual(report["exit_code"], 1)
        self.issue(report, "stage-documents.files")
        self.issue(report, "stage-documents.read")
        inventory = next(item for item in report["checks"] if item["id"] == "stage-documents.files")
        self.assertIn("completed.md", inventory["message"])
        self.assertIn("unknown.md", inventory["message"])

    def test_markdown_extension_case_and_non_markdown_supplements(self):
        extra = self.stage_dir / "completed.MD"
        extra.write_text(self.source)
        self.issue(self.check(), "stage-documents.files")
        extra.unlink()
        (self.stage_dir / "diagram.txt").write_text("supplement")
        self.assertEqual(self.check()["exit_code"], 0)

    def test_missing_stage_directory_is_failure(self):
        self.stage_dir.rename(self.stage_dir.with_name("moved"))
        report = self.check()
        self.assertEqual(report["exit_code"], 1)
        self.issue(report, "stage-documents.files")

    def test_stage_titles_must_match_once_and_precede_sections(self):
        title = "# completed (완료)\n"
        for source in (self.source.replace(title, "# completed (다른 제목)\n"),
                       self.source.replace(title, "# other (완료)\n"),
                       self.source.replace(title, ""), self.source + "\n" + title,
                       self.source.replace(title, "## completed (완료)\n"),
                       self.source.replace(title, "") + "\n" + title):
            with self.subTest(source=source):
                self.issue(self.check(source), "stage-documents.title")

    def test_common_sections_missing_duplicate_reordered_or_wrong_depth(self):
        for title in ("단계 운영 규칙", "명세서 기록 항목"):
            for replacement in ("", f"## {title}\n\n## {title}\n", f"### {title}\n"):
                with self.subTest(title=title, replacement=replacement):
                    self.issue(self.check(self.source.replace(f"## {title}\n", replacement)),
                               "stage-documents.sections")
        source = self.source.replace("## 단계 운영 규칙", "## placeholder")
        source = source.replace("## 명세서 기록 항목", "## 단계 운영 규칙")
        self.issue(self.check(source.replace("## placeholder", "## 명세서 기록 항목")),
                   "stage-documents.sections")
        self.issue(self.check(self.source + "\n## 추가 구역\n"), "stage-documents.sections")

    def test_operation_headings_missing_duplicate_reordered_or_wrong_depth(self):
        for title in ("진입 조건", "수행 작업", "완료 조건", "허용 전이", "산출물"):
            for replacement in ("", f"### {title}\n\n### {title}\n", f"#### {title}\n"):
                with self.subTest(title=title, replacement=replacement):
                    self.issue(self.check(self.source.replace(f"### {title}\n", replacement)),
                               "stage-documents.operations")
        reversed_pair = self.source.replace("### 진입 조건\n\n### 수행 작업",
                                            "### 수행 작업\n\n### 진입 조건")
        self.issue(self.check(reversed_pair), "stage-documents.operations")
        self.issue(self.check(self.source.replace("### 수행 작업", "### 추가 항목\n\n### 수행 작업")),
                   "stage-documents.operations")

    def test_operation_heading_in_record_section_does_not_satisfy_requirement(self):
        source = self.source.replace("### 완료 조건\n", "") + "\n### 완료 조건\n"
        self.issue(self.check(source), "stage-documents.operations")

    def test_additional_nested_headings_and_examples_are_allowed(self):
        extra = """
#### 세부 설명

##### 예외

###### 근거

```markdown
# 잘못된 제목
## 단계 운영 규칙
### 수행 작업
```

<!--
## 명세서 기록 항목
### 수행 작업
-->

> ## 단계 운영 규칙
> ### 수행 작업

- 인용한 예

  ### 수행 작업
"""
        report = self.check(self.source.replace("### 수행 작업\n", "### 수행 작업\n" + extra))
        self.assertEqual(report["exit_code"], 0, report)

    def test_example_headings_do_not_replace_required_headings(self):
        for heading, identifier in (("# completed (완료)", "title"),
                                    ("## 명세서 기록 항목", "sections"),
                                    ("### 완료 조건", "operations")):
            for fake in (f"```markdown\n{heading}\n```", f"<!--\n{heading}\n-->", f"> {heading}"):
                with self.subTest(heading=heading, fake=fake):
                    self.issue(self.check(self.source.replace(heading, fake)),
                               "stage-documents." + identifier)

    def test_rendered_headings_bom_and_crlf_are_supported(self):
        source = self.source.replace("# completed (완료)", "`completed` (완료)\n==================")
        source = source.replace("### 수행 작업", "### **수행 작업**")
        self.path.write_bytes(b"\xef\xbb\xbf" + source.replace("\n", "\r\n").encode())
        self.assertEqual(self.check()["exit_code"], 0)

    def test_operation_titles_come_from_policy_document(self):
        self.policy.write_text(STAGE_RULES.replace("- 수행 작업", "- 실행 항목"))
        self.issue(self.check(), "stage-documents.operations")
        for path in self.stage_dir.glob("*.md"):
            path.write_text(path.read_text().replace("### 수행 작업", "### 실행 항목"))
        self.assertEqual(self.check()["exit_code"], 0)

    def test_stage_inventory_and_titles_come_from_policy_document(self):
        self.policy.write_text(STAGE_RULES.replace("2. `completed` (완료)", "2. `finished` (끝)"))
        self.issue(self.check(), "stage-documents.files")
        self.path.rename(self.stage_dir / "finished.md")
        path = self.stage_dir / "finished.md"
        self.issue(self.check(), "stage-documents.title")
        path.write_text(self.source.replace("completed (완료)", "finished (끝)"))
        self.assertEqual(self.check()["exit_code"], 0)

    def test_missing_ambiguous_or_invalid_policy_is_error(self):
        for policy in (ORDER, STAGE_RULES.replace("- 진입 조건", "- 수행 작업"),
                       STAGE_RULES.replace("2. `completed` (완료)", "2. not a stage"),
                       STAGE_RULES.replace("2. `completed` (완료)", "2. `problem-definition` (문제 정의)"),
                       STAGE_RULES + "\n## 생명 주기 순서\n",
                       STAGE_RULES + "\n## 단계 정의 공통 항목\n",
                       ORDER + "\n## 단계 정의 공통 항목\n본문만 있음\n"):
            with self.subTest(policy=policy):
                self.policy.write_text(policy)
                self.issue(self.check(), "stage-documents.rules", "ERROR")
        self.policy.unlink()
        self.issue(self.check(), "stage-documents.rules", "ERROR")

    def test_read_failure_is_error_and_other_stages_are_still_checked(self):
        self.path.write_bytes(b"\xff\xfe")
        report = self.check()
        self.assertEqual(report["exit_code"], 2)
        self.issue(report, "stage-documents.read", "ERROR")
        self.assertTrue(any(item["target"].endswith("problem-definition.md")
                            and item["status"] == "PASS" for item in report["checks"]))
        original = Path.read_text

        def read(path, *args, **kwargs):
            if path == self.path:
                raise PermissionError("denied")
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", read):
            self.issue(self.check(), "stage-documents.read", "ERROR")
        with patch.object(Path, "iterdir", side_effect=PermissionError("denied")):
            self.issue(self.check(), "stage-documents.directory", "ERROR")

    def test_combined_modes_collect_stage_failures_and_other_errors(self):
        self.template.unlink()
        self.spec.write_text(META.replace("operation: create", "operation: invalid") + BODY)
        report = self.check(self.source.replace("### 수행 작업", "### 다른 제목"),
                            specification=self.spec, check_template=True)
        self.assertEqual(report["exit_code"], 2)
        self.issue(report, "stage-documents.operations")
        self.issue(report, "template.read", "ERROR")
        self.issue(report, "operation.value")

    def test_combined_missing_stage_reports_failure_and_unreadable_record_rules(self):
        self.path.unlink()
        report = self.check(check_template=True)
        self.assertEqual(report["exit_code"], 2)
        self.issue(report, "stage-documents.files")
        self.issue(report, "rules.read", "ERROR")

    def test_stage_mode_is_opt_in_and_does_not_validate_record_content(self):
        self.path.write_text(self.source.replace("### 수행 작업", "### 다른 제목"))
        report = check_lifecycle_specification(self.spec, check_template=True, lifecycle_directory=self.rules)
        self.assertEqual(report["exit_code"], 0, report)
        self.assertFalse(report["check_stages"])
        report = self.check(self.source + "\n전이 조건은 미확인. 승인 없음.\n")
        self.assertEqual(report["exit_code"], 0, report)

    def test_cli_combined_json_and_text_are_read_only_from_other_directory(self):
        before = self.snapshot()
        run = self.cli(self.spec, "--check-template", "--json")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        report = json.loads(run.stdout)
        self.assertTrue(report["check_stages"])
        self.assertTrue(report["check_template"])
        self.issue(report, "stage-documents.operations", "PASS")
        self.issue(report, "template.headings", "PASS")
        self.issue(report, "operation.value", "PASS")
        run = self.cli()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("stage-documents.operations", run.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_cli_failure_and_dependency_error_are_read_only(self):
        self.path.write_text(self.source.replace("### 수행 작업", "### 다른 제목"))
        before = self.snapshot()
        run = self.cli("--json")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.issue(json.loads(run.stdout), "stage-documents.operations")
        run = self.cli("--json", no_site=True)
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.issue(json.loads(run.stdout), "dependency", "ERROR")
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
