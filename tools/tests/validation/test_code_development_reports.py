"""Contract tests for the installed code-development report checker."""

import hashlib
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / 'plugins/Camellia/skills/code-development'
SCRIPT = SKILL / 'scripts/check_reports.py'
spec = importlib.util.spec_from_file_location('camellia_reports', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='camellia-report-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.topic = self.root / 'specs' / '인증 그룹' / '로그인 작업'
        self.topic.mkdir(parents=True)
        self.manifest = self.topic.parent / 'freight-manifest.md'
        self.manifest.write_text('# Freight Manifest\n\n## [로그인 작업](로그인%20작업/)\n\n'
                                 '- stages: [discussion, design, implementation, verification, qa]\n'
                                 '- reference_reports: 없음\n', encoding='utf-8')
        self.write_report('discussion', status='completed')
        self.write_report('design', base='discussion-report-001.md')

    def write_report(self, stage, number=1, status='in_progress', base=None, body='', bundle=None):
        path = self.topic / f'{stage}-report-{number:03d}.md'
        bundle_line = '' if bundle is None else f'bundle: {json.dumps(bundle)}\n'
        areas = {area: '' for area in checker.AREAS}
        if status == 'completed':
            areas['완료 체크리스트'] = ('- [x] 범위 확인\n  - 확인 근거: 실제 범위 대조\n'
                                      '  - 확인 완료 시각: 2026-10-07 12:00:00 (KST)\n')
        if stage in ('verification', 'qa') and status in ('completed', 'awaiting_approval'):
            areas['사용자 승인'] = '### 완료 구분\n\nall_passed\n현재 검사 대상의 결과를 확인함.\n'
        path.write_text(f'---\nstatus: {status}\nbase_on: {base or "null"}\n{bundle_line}---\n\n'
                        '# 작업 결과\n\n' + '\n\n'.join('## ' + a + '\n\n' + b for a, b in areas.items()) + '\n' + body, encoding='utf-8')
        return path

    def bundle_plan(self, names=('api', 'storage', 'public-api', 'db-storage')):
        path = self.topic / 'design-report-001.md'
        body = ('### 작업 묶음표\n\n| 묶음 | 제목 | 범위/완료 기준 | 의존/진입 | 설계 정본 | 결과 참조 |\n'
                '| --- | --- | --- | --- | --- | --- |\n' +
                ''.join(f'| {name} | 계약 | 구현과 QA | 구현부터 | 공통 설계 | 미시작 |\n' for name in names))
        self.change(path, '## 단계 결과\n', '## 단계 결과\n\n' + body)
        return path

    def check(self):
        return checker.Checker(self.topic).run()

    def has(self, result, rule, status):
        self.assertTrue(any(c['id'] == rule and c['status'] == status for c in result['checks']), result)

    def change(self, path, before, after):
        path.write_text(path.read_text(encoding='utf-8').replace(before, after), encoding='utf-8')

    def design_body(self, body):
        return self.write_report('design', base='discussion-report-001.md', body=body)

    def area(self, path, name, body):
        text = path.read_text(encoding='utf-8')
        before, after = text.split('## ' + name + '\n', 1)
        end = after.find('\n## ')
        path.write_text(before + '## ' + name + '\n\n' + body + '\n' +
                        (after[end:] if end >= 0 else ''), encoding='utf-8')

    def batch_checklist(self, rows=None):
        rows = rows if rows is not None else '| B1 | 범위 | 2026-10-07 12:00:00 (KST) |\n'
        return ('- [x] 범위 확인\n  - 확인 근거: [결과](#단계-결과)\n\n'
                '### 일괄 반영 기록\n\n| 묶음 | 대상 항목 | 반영 시각 |\n'
                '| --- | --- | --- |\n' + rows)

    def verification(self, status='completed'):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('implementation', status='completed', base='design-report-001.md')
        return self.write_report('verification', status=status, base='implementation-report-001.md')

    def test_completed_requires_real_nonempty_checked_items(self):
        path = self.topic / 'discussion-report-001.md'
        for body in ('', '- [ ] 범위 확인', '```md\n- [x] 예시\n```',
                     '> - [x] 인용', '<!-- - [x] 주석 -->', '- `[x] 인라인 코드`'):
            with self.subTest(body=body):
                self.area(path, '완료 체크리스트', body)
                self.has(self.check(), 'checklist.completed', 'FAIL')

    def test_draft_and_awaiting_checklists_may_be_unchecked(self):
        for status in ('in_progress', 'awaiting_approval', 'hold'):
            with self.subTest(status=status):
                path = self.write_report('design', status=status, base='discussion-report-001.md')
                self.area(path, '완료 체크리스트', '- [ ] 범위 확인\n  - 확인 근거: <!-- 미작성 -->')
                self.assertEqual(self.check()['exit_code'], 0)

    def test_checked_evidence_cannot_come_from_examples_or_previous_confirmation(self):
        path = self.topic / 'discussion-report-001.md'
        for evidence in ('  - 확인 근거: <!-- 작성 -->',
                         '  > 확인 근거: 인용',
                         '  ```text\n  확인 근거: 예시\n  ```',
                         '  - 이전 확인 기록:\n    - 확인 근거: 과거 근거'):
            with self.subTest(evidence=evidence):
                self.area(path, '완료 체크리스트', '- [x] 대상\n' + evidence +
                          '\n  - 확인 완료 시각: 2026-10-07 12:00:00 (KST)')
                self.has(self.check(), 'checklist.evidence', 'FAIL')

    def test_current_evidence_and_reopened_history_are_separate(self):
        path = self.topic / 'design-report-001.md'
        self.area(path, '완료 체크리스트',
                  '- [ ] 재확인 대상\n  - 확인 근거: <!-- 아직 없음 -->\n'
                  '  - 이전 확인 기록:\n    - [x] 과거 항목\n    - 확인 근거: 과거 결과\n')
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertFalse(any(c['id'] == 'checklist.evidence' and c['source'] == str(path) for c in result['checks']))

    def test_batch_records_and_legacy_timestamps_both_work(self):
        path = self.topic / 'discussion-report-001.md'
        self.area(path, '완료 체크리스트', self.batch_checklist())
        self.assertEqual(self.check()['exit_code'], 0)
        self.change(path, '- [x] 범위 확인', '- [X] **범위** 확인')
        self.assertEqual(self.check()['exit_code'], 0)
        self.area(path, '완료 체크리스트', '- [x] 예전 기록\n  - 확인 근거: 결과 확인\n'
                  '  - 확인 완료 시각: 2024-02-29 23:59:59 (KST)\n\n'
                  '### 일괄 반영 기록\n\n<!-- 신규 반영 없음 -->')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_checked_item_requires_record_but_unchecked_item_does_not(self):
        path = self.topic / 'design-report-001.md'
        self.area(path, '완료 체크리스트', '- [x] 범위\n  - 확인 근거: 확인됨')
        self.has(self.check(), 'checklist.records', 'FAIL')
        self.change(path, '[x]', '[ ]')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_batch_identifiers_targets_and_calendar_are_checked(self):
        path = self.topic / 'discussion-report-001.md'
        cases = [('| B1 | 범위 | 2026-10-07 12:00:00 (KST) |\n' * 2, 'checklist.batch'),
                 ('| B0 | 범위 | 2026-10-07 12:00:00 (KST) |', 'checklist.batch'),
                 ('| B1 | <!-- 비어 있음 --> | 2026-10-07 12:00:00 (KST) |', 'checklist.targets'),
                 ('| B1 | 범위 | 2026-02-29 12:00:00 (KST) |', 'checklist.timestamp'),
                 ('| B1 | 범위 | 2026-10-07 24:00:00 (KST) |', 'checklist.timestamp'),
                 ('| B1 | 범위 | 2026-10-07 12:00:00 (UTC) |', 'checklist.timestamp')]
        for rows, rule in cases:
            with self.subTest(rows=rows):
                self.area(path, '완료 체크리스트', self.batch_checklist(rows))
                self.has(self.check(), rule, 'FAIL')

    def test_batch_table_header_and_section_duplicates_fail(self):
        path = self.topic / 'discussion-report-001.md'
        for body in (self.batch_checklist().replace('대상 항목', '묶음'),
                     self.batch_checklist() + '\n### 일괄 반영 기록\n',
                     self.batch_checklist('')):
            with self.subTest(body=body):
                self.area(path, '완료 체크리스트', body)
                self.has(self.check(), 'checklist.records', 'FAIL')

    def test_legacy_batch_list_and_table_can_coexist_without_duplicate_ids(self):
        path = self.topic / 'discussion-report-001.md'
        body = ('- [x] 범위 확인\n  - 확인 근거: 결과 확인\n\n'
                '### 일괄 반영 기록\n\n- B1: 단계 확인 항목 전체.\n'
                '  - 반영 시각: 2026-10-07 12:00:00 (KST).\n'
                '  - 근거: 기존 대조 기록\n')
        self.area(path, '완료 체크리스트', body)
        self.assertEqual(self.check()['exit_code'], 0)
        table = '\n| 묶음 | 대상 항목 | 반영 시각 |\n| --- | --- | --- |\n| B2 | 재확인 | 2026-10-07 13:00:00 (KST) |\n'
        self.area(path, '완료 체크리스트', body + table)
        self.assertEqual(self.check()['exit_code'], 0)
        self.change(path, '| B2 |', '| B1 |')
        self.has(self.check(), 'checklist.batch', 'FAIL')
        self.area(path, '완료 체크리스트', body.replace('2026-10-07', '2026-02-30'))
        self.has(self.check(), 'checklist.timestamp', 'FAIL')

    def test_checklist_continuation_fields_and_inline_code_examples(self):
        path = self.topic / 'discussion-report-001.md'
        self.area(path, '완료 체크리스트', '- [x] 범위 확인\n'
                  '  확인 근거: 실제 결과\n  확인 완료 시각: 2026-10-07 12:00:00 (KST)')
        self.assertEqual(self.check()['exit_code'], 0)
        self.change(path, '확인 근거: 실제 결과', '`확인 근거: 예시`')
        self.has(self.check(), 'checklist.evidence', 'FAIL')

    def test_bundle_table_reordered_columns_and_reference_style_result(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('implementation', base='design-report-001.md', bundle='api')
        path = self.topic / 'design-report-001.md'
        self.area(path, '단계 결과', '### 작업 묶음표\n\n'
                  '| 제목 | 묶음 | 범위/완료 기준 | 의존/진입 | 결과 참조 | 설계 정본 |\n'
                  '| --- | --- | --- | --- | --- | --- |\n'
                  '| API | api | 계약 확인 | 구현부터 | [결과][impl] | 공통 설계 |\n\n'
                  '[impl]: implementation-report-001.md\n')
        self.assertEqual(self.check()['exit_code'], 0)
        self.change(path, '| API | api |', '| <!-- 제목 없음 --> | api |')
        self.has(self.check(), 'bundle.fields', 'FAIL')

    def test_bundle_table_examples_cannot_supply_registry(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('implementation', base='design-report-001.md', bundle='api')
        path = self.bundle_plan(('api',))
        original = path.read_text()
        table = original.split('## 단계 결과\n', 1)[1].split('\n## 인계 사항', 1)[0].strip()
        for example in ('```markdown\n' + table + '\n```',
                        '\n'.join('> ' + line for line in table.splitlines()),
                        '<!--\n' + table + '\n-->'):
            with self.subTest(example=example):
                self.area(path, '단계 결과', example)
                self.has(self.check(), 'bundle.table', 'UNCHECKED')

    def test_invalid_legacy_timestamp_fails_even_with_batch(self):
        path = self.topic / 'discussion-report-001.md'
        self.area(path, '완료 체크리스트', self.batch_checklist().replace(
            '### 일괄 반영 기록', '  - 확인 완료 시각: 2026-13-01 00:00:00 (KST)\n\n### 일괄 반영 기록'))
        self.has(self.check(), 'checklist.timestamp', 'FAIL')

    def test_completed_and_submitted_completion_require_value_and_explanation(self):
        for status in ('completed', 'awaiting_approval'):
            path = self.verification(status)
            for body in ('', '### 완료 구분\n\n미정', '### 완료 구분\n\nall_passed',
                         '### 완료 구분\n\nqa_handoff\n<!-- 이유 -->',
                         '### 완료 구분\n\nnext_cycle_handoff\n이유',
                         '### 완료 구분\n\nall_passed\nqa_handoff\n이유',
                         '### 완료 구분\n\nall_passed\n이유\n\n### 완료 구분\n\nall_passed\n이유'):
                with self.subTest(status=status, body=body):
                    self.area(path, '사용자 승인', body)
                    self.has(self.check(), 'report.completion', 'FAIL')

    def test_pending_completion_can_be_blank_or_undecided_but_not_invalid(self):
        for status in ('in_progress', 'hold'):
            path = self.verification(status)
            for body in ('', '### 완료 구분\n\n미정', '### 완료 구분\n\n<!-- 작성 중 -->'):
                with self.subTest(status=status, body=body):
                    self.area(path, '사용자 승인', body)
                    self.assertEqual(self.check()['exit_code'], 0)
            self.area(path, '사용자 승인', '### 완료 구분\n\ninvalid\n이유')
            self.has(self.check(), 'report.completion', 'FAIL')

    def test_completion_values_are_scoped_and_examples_do_not_count(self):
        path = self.verification()
        for body in ('```md\n### 완료 구분\nall_passed\n이유\n```',
                     '> ### 완료 구분\n> all_passed\n> 이유',
                     '### 완료 구분\n\n```text\nall_passed\n이유\n```',
                     '### 완료 구분\n\nall_passed\n\n> 인용 이유'):
            with self.subTest(body=body):
                self.area(path, '사용자 승인', body)
                self.has(self.check(), 'report.completion', 'FAIL')
        self.area(path, '사용자 승인', '### 완료 구분\n\n`qa_handoff`\n미확인 범위와 QA 조건을 기록함.')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_qa_completion_uses_its_own_keywords(self):
        self.verification()
        path = self.write_report('qa', status='completed', base='verification-report-001.md')
        self.area(path, '사용자 승인', '### 완료 구분\n\nnext_cycle_handoff\n새 작업 이관 조건을 기록함.')
        self.assertEqual(self.check()['exit_code'], 0)
        self.change(path, 'next_cycle_handoff', 'qa_handoff')
        self.has(self.check(), 'report.completion', 'FAIL')

    def test_bundle_table_missing_is_unchecked_and_empty_marked_table_fails(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('implementation', base='design-report-001.md', bundle='api')
        self.has(self.check(), 'bundle.table', 'UNCHECKED')
        self.area(self.topic / 'design-report-001.md', '단계 결과', '### 작업 묶음표\n\n<!-- 작성 -->')
        self.has(self.check(), 'bundle.table', 'FAIL')

    def test_bundle_table_identifiers_and_registration(self):
        for names, rule in [(('api', 'api'), 'bundle.identifier'),
                            (('Upper',), 'bundle.identifier'), (('storage',), 'bundle.registration')]:
            with self.subTest(names=names):
                self.write_report('design', status='completed', base='discussion-report-001.md')
                self.bundle_plan(names)
                self.write_report('implementation', base='design-report-001.md', bundle='api')
                self.has(self.check(), rule, 'FAIL')

    def test_bundle_result_links_must_match_topic_bundle_and_result_stage(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        shared = self.bundle_plan(('api',))
        self.write_report('implementation', base='design-report-001.md', bundle='api')
        other = self.topic.parent / 'other'
        other.mkdir()
        (other / 'implementation-report-001.md').write_text('---\nbundle: api\n---\n')
        original = shared.read_text()
        for url in ('design-report-001.md', '../other/implementation-report-001.md',
                    'https://example.invalid/result', 'missing-report-001.md'):
            with self.subTest(url=url):
                shared.write_text(original.replace('미시작', f'[결과]({url})'))
                self.has(self.check(), 'bundle.result', 'FAIL')
        shared.write_text(original.replace('미시작', '[구현](implementation-report-001.md)'))
        self.assertEqual(self.check()['exit_code'], 0)
        self.write_report('implementation', base='design-report-001.md', bundle='storage')
        self.has(self.check(), 'bundle.result', 'FAIL')

    def test_unstarted_bundles_and_future_results_do_not_require_reports(self):
        shared = self.bundle_plan(('future',))
        self.change(shared, '미시작', '`implementation-report-002.md` 생성 예정')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_old_superseded_body_is_not_subject_to_new_checks(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan(('api',))
        self.write_report('design', number=2, status='superseded', base='discussion-report-001.md', bundle='api')
        self.write_report('design', number=3, base='discussion-report-001.md', bundle='api')
        # Historical body may contain invalid completion/checklist/table examples.
        old = self.topic / 'design-report-002.md'
        self.area(old, '완료 체크리스트', '- [x] no evidence\n')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_new_checks_are_read_only_deterministic_and_work_after_copy(self):
        self.verification()
        shared = self.bundle_plan(('future',))
        self.area(shared, '완료 체크리스트', self.batch_checklist())
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        first = self.check()
        self.assertEqual(first['exit_code'], 0, first)
        self.assertEqual(first, self.check())
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        installed = self.root / 'installed-skill'
        shutil.copytree(SKILL, installed)
        run = subprocess.run([sys.executable, '-B', str(installed / 'scripts/check_reports.py'),
                              str(self.topic), '--json'], cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), first)

    def run_group(self, group, installed=None, extra=()):
        names = {'structure': 'check_report_structure.py',
                 'completion': 'check_completion_records.py',
                 'bundles': 'check_work_bundles.py',
                 'links': 'check_report_links.py',
                 'diagrams': 'check_report_diagrams.py',
                 'all': 'check_reports.py'}
        script = (installed or SKILL) / 'scripts' / names[group]
        run = subprocess.run([sys.executable, '-B', *extra, str(script), str(self.topic), '--json'],
                             cwd=self.root, capture_output=True, text=True, timeout=15)
        result = json.loads(run.stdout)
        self.assertEqual(run.returncode, result['exit_code'], run.stderr)
        return result

    def test_individual_roles_do_not_run_other_body_checks(self):
        path = self.write_report('design', status='completed', base='discussion-report-001.md')
        self.area(path, '완료 체크리스트', '- [ ] 미확인')
        self.area(path, '단계 결과', '[누락](missing.md)\n\n```text ascii-flow\n[A] → [B]\n```')
        expected = {'structure': 0, 'completion': 1, 'bundles': 0, 'links': 1, 'diagrams': 1}
        forbidden = {'structure': ('checklist.', 'diagram.', 'link.', 'bundle.'),
                     'completion': ('report.predecessor', 'diagram.', 'link.', 'bundle.'),
                     'bundles': ('checklist.', 'diagram.', 'link.', 'report.revision'),
                     'links': ('checklist.', 'diagram.', 'bundle.', 'report.revision'),
                     'diagrams': ('checklist.', 'link.', 'bundle.', 'report.revision')}
        before = {p: p.read_bytes() for p in self.topic.rglob('*') if p.is_file()}
        for group, exit_code in expected.items():
            with self.subTest(group=group):
                result = self.run_group(group)
                self.assertEqual(result['exit_code'], exit_code, result)
                self.assertEqual(result['groups'], [group])
                self.assertFalse(any(c['id'].startswith(forbidden[group]) for c in result['checks']), result)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_individual_union_matches_full_checks_on_mixed_failures(self):
        shared = self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan(('storage',))
        self.write_report('implementation', base='design-report-999.md', bundle='api')
        self.area(shared, '완료 체크리스트', '- [ ] 미확인')
        with shared.open('a') as stream:
            stream.write('\n[missing](absent.md)\n\n```text ascii-flow\n[A] → [B]\n```\n')
        partial = [self.run_group(group) for group, _ in checker.CHECKS]
        full = self.run_group('all')
        self.assertEqual(full['groups'], [group for group, _ in checker.CHECKS])
        normalize = lambda results: {json.dumps(c, sort_keys=True) for r in results for c in r['checks']}
        self.assertEqual(normalize(partial), normalize([full]))
        self.assertEqual(full['exit_code'], 1)
        self.assertTrue(all(r['exit_code'] == 1 for r in partial))

    def test_each_role_reports_shared_input_errors(self):
        path = self.topic / 'design-report-001.md'
        self.change(path, 'status: in_progress', 'status: [invalid]')
        for group, _ in checker.CHECKS:
            with self.subTest(group=group):
                result = self.run_group(group)
                self.has(result, 'report.format', 'FAIL')
                self.assertEqual(result['exit_code'], 1)

    def test_completion_alone_does_not_pass_missing_required_area(self):
        self.change(self.topic / 'discussion-report-001.md', '## 완료 체크리스트', '## 잘못된 제목')
        self.has(self.run_group('completion'), 'completion.input', 'FAIL')

    def test_links_and_diagrams_have_independent_detail_scans(self):
        detail = self.topic / 'design-report-001'
        detail.mkdir()
        (detail / 'flow.md').write_text('[missing](missing.md)\n\n```text ascii-flow\n[A] -> [B]\n```')
        self.assertEqual(self.run_group('diagrams')['exit_code'], 0)
        self.assertEqual(self.run_group('diagrams')['diagrams_checked'], 1)
        self.has(self.run_group('links'), 'link.target', 'FAIL')
        # Completion/structure do not visit unrelated design details.
        self.assertEqual(self.run_group('completion')['exit_code'], 0)
        self.assertEqual(self.run_group('structure')['exit_code'], 0)

    def test_all_six_commands_work_from_copied_skill_and_external_cwd(self):
        self.verification()
        installed = self.root / '배포 사본'
        shutil.copytree(SKILL, installed)
        for group in [name for name, _ in checker.CHECKS] + ['all']:
            with self.subTest(group=group):
                result = self.run_group(group, installed)
                self.assertEqual(result['exit_code'], 0, result)
                # Isolated Python excludes site dependencies, but local module loading must still work.
                missing = self.run_group(group, installed, ('-I', '-S'))
                self.assertEqual(missing['exit_code'], 2)
                self.has(missing, 'dependency', 'ERROR')

    def test_full_run_reuses_detail_traversal(self):
        import report_common
        detail = self.topic / 'design-report-001'
        detail.mkdir()
        (detail / 'flow.md').write_text('# Flow\n\n```text ascii-flow\n[A] -> [B]\n```')
        with patch.object(report_common.os, 'walk', wraps=report_common.os.walk) as walk:
            result = self.check()
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(walk.call_count, 1)

    def test_valid_partial_work_without_future_reports(self):
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(result['diagrams_checked'], 0)

    def test_supported_metadata_and_missing_or_duplicate_keys(self):
        path = self.topic / 'design-report-001.md'
        cases = [('status: in_progress', 'status: done'),
                 ('base_on: discussion-report-001.md', 'base_on: ../discussion-report-001.md'),
                 ('status: in_progress', 'status: in_progress\nstatus: completed'),
                 ('base_on: discussion-report-001.md', ''),
                 ('status: in_progress', 'status: [completed]')]
        original = path.read_text(encoding='utf-8')
        for before, after in cases:
            with self.subTest(after=after):
                path.write_text(original.replace(before, after), encoding='utf-8')
                self.has(self.check(), 'report.format', 'FAIL')

    def test_extra_metadata_is_not_a_new_prohibition(self):
        path = self.topic / 'design-report-001.md'
        self.change(path, 'status: in_progress', 'status: in_progress\ncustom_note: info')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_example_and_quote_headings_do_not_fill_required_area(self):
        path = self.topic / 'design-report-001.md'
        self.change(path, '## 사용자 승인', '```markdown\n## 사용자 승인\n```\n\n> ## 사용자 승인\n\n<!--\n## 사용자 승인\n-->')
        self.has(self.check(), 'report.area', 'FAIL')

    def test_custom_stages_use_manifest_order(self):
        self.change(self.manifest, 'design, implementation, verification, qa', 'review')
        (self.topic / 'design-report-001.md').rename(self.topic / 'review-report-001.md')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_bad_manifest_fields_and_duplicate_topic(self):
        original = self.manifest.read_text(encoding='utf-8')
        for body in [original.replace('design, implementation', 'design, design'),
                     original.replace('- reference_reports: 없음', ''),
                     original + '\n## [duplicate](로그인%20작업/)\n',
                     original.replace('[discussion, design, implementation, verification, qa]', 'null')]:
            with self.subTest(body=body):
                self.manifest.write_text(body, encoding='utf-8')
                self.has(self.check(), 'manifest.format', 'FAIL')

    def test_other_manifest_topics_are_not_scanned(self):
        with self.manifest.open('a') as f:
            f.write('\n## [other](missing/)\n\n- stages: broken\n- reference_reports: [missing](missing.md)\n')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_broken_manifest_reference_is_checked(self):
        self.change(self.manifest, 'reference_reports: 없음', 'reference_reports:\n  - [old](missing.md)')
        self.has(self.check(), 'link.target', 'FAIL')

    def test_missing_or_wrong_predecessor(self):
        self.design_body('')
        path = self.topic / 'design-report-001.md'
        self.change(path, 'discussion-report-001.md', 'discussion-report-999.md')
        self.has(self.check(), 'report.base', 'FAIL')
        self.change(path, 'discussion-report-999.md', 'design-report-001.md')
        self.has(self.check(), 'report.base', 'FAIL')

    def test_current_predecessor_must_be_completed(self):
        self.write_report('discussion')
        self.has(self.check(), 'report.predecessor', 'FAIL')

    def test_hold_can_retain_old_predecessor(self):
        self.write_report('discussion', status='superseded')
        self.write_report('discussion', number=2)
        self.write_report('design', status='hold', base='discussion-report-001.md')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_historical_body_not_forced_to_current_template(self):
        path = self.write_report('design', status='superseded', base='discussion-report-001.md')
        path.write_text('---\nstatus: superseded\nbase_on: discussion-report-001.md\n---\n# old\n[old](gone.md)', encoding='utf-8')
        self.write_report('design', number=3, base='discussion-report-001.md')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_old_report_must_be_superseded(self):
        self.write_report('design', number=2, base='discussion-report-001.md')
        self.has(self.check(), 'report.revision', 'FAIL')

    def test_bundle_completion_survives_next_bundle_and_shared_design(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan()
        self.write_report('implementation', status='completed', base='design-report-001.md', bundle='public-api')
        self.write_report('verification', status='completed', base='implementation-report-001.md', bundle='public-api')
        self.write_report('qa', status='completed', base='verification-report-001.md', bundle='public-api')
        self.write_report('design', number=2, base='discussion-report-001.md', bundle='db-storage')
        self.assertEqual(self.check()['exit_code'], 0)
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='db-storage')
        self.write_report('implementation', number=2, base='design-report-002.md', bundle='db-storage')
        before = {p: p.read_bytes() for p in self.topic.iterdir() if p.is_file()}
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertFalse(any('design-report-001.md' == Path(e['source']).name for e in result['exclusions']))

    def test_revisions_are_per_bundle_and_stage(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan()
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='api')
        self.write_report('design', number=3, base='discussion-report-001.md', bundle='api')
        self.write_report('design', number=4, base='discussion-report-001.md', bundle='storage')
        self.has(self.check(), 'report.revision', 'FAIL')
        self.write_report('design', number=2, status='superseded', base='discussion-report-001.md', bundle='api')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_verification_and_qa_cannot_borrow_another_bundles_approval(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('implementation', status='completed', base='design-report-001.md', bundle='api')
        self.write_report('verification', status='completed', base='implementation-report-001.md', bundle='api')
        for stage, base in [('verification', 'implementation-report-001.md'),
                            ('qa', 'verification-report-001.md')]:
            with self.subTest(stage=stage):
                path = self.write_report(stage, number=2, base=base, bundle='storage')
                self.has(self.check(), 'report.bundle', 'FAIL')
                path.unlink()

    def test_implementation_uses_own_bundle_design_when_present(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan()
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='api')
        self.write_report('implementation', base='design-report-001.md', bundle='api')
        self.has(self.check(), 'report.bundle', 'FAIL')
        self.write_report('implementation', base='design-report-002.md', bundle='api')
        self.assertEqual(self.check()['exit_code'], 0)
        self.write_report('implementation', number=2, base='design-report-002.md', bundle='storage')
        self.has(self.check(), 'report.bundle', 'FAIL')

    def test_hold_bundle_keeps_shared_predecessor_after_design_regression(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan(('api',))
        old = self.write_report('implementation', status='hold', base='design-report-001.md', bundle='api')
        self.write_report('design', number=2, base='discussion-report-001.md', bundle='api')
        original = old.read_bytes()
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(old.read_bytes(), original)

        # Resumed or approval-ready reports must adopt their own bundle design.
        for status in ('in_progress', 'awaiting_approval', 'completed'):
            with self.subTest(status=status):
                self.write_report('implementation', status=status, base='design-report-001.md', bundle='api')
                self.has(self.check(), 'report.bundle', 'FAIL')

    def test_superseded_bundle_keeps_shared_predecessor_after_replacement(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan(('api',))
        old = self.write_report('implementation', status='superseded', base='design-report-001.md', bundle='api')
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='api')
        self.write_report('implementation', number=2, base='design-report-002.md', bundle='api')
        original = old.read_bytes()
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(old.read_bytes(), original)

    def test_historical_bundle_cannot_reference_another_bundles_design(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.bundle_plan(('api', 'storage'))
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='storage')
        self.write_report('design', number=3, status='completed', base='discussion-report-001.md', bundle='api')
        for status in ('hold', 'superseded'):
            with self.subTest(status=status):
                self.write_report('implementation', status=status, base='design-report-002.md', bundle='api')
                if status == 'superseded':
                    self.write_report('implementation', number=2, base='design-report-003.md', bundle='api')
                self.has(self.check(), 'report.bundle', 'FAIL')

    def test_bundle_design_uses_shared_discussion_only(self):
        self.write_report('discussion', number=2, status='completed', bundle='api')
        self.write_report('design', number=2, base='discussion-report-002.md', bundle='api')
        self.has(self.check(), 'report.bundle', 'FAIL')

    def test_bundle_identifier_is_optional_but_validated_when_present(self):
        path = self.topic / 'design-report-001.md'
        original = path.read_text()
        for value in ('null', '001', '""', '"Upper"', '"../api"', '[api]', 'true'):
            with self.subTest(value=value):
                path.write_text(original.replace('status: in_progress', f'status: in_progress\nbundle: {value}'))
                self.has(self.check(), 'report.format', 'FAIL')
        path.write_text(original.replace('status: in_progress', 'status: in_progress\nbundle: "001"'))
        result = self.check()
        self.assertFalse(any(c['id'] == 'report.format' and c['status'] == 'FAIL' for c in result['checks']))
        self.has(result, 'bundle.table', 'UNCHECKED')

    def test_shared_results_cannot_depend_on_bundled_design(self):
        self.write_report('design', status='superseded', base='discussion-report-001.md')
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='api')
        self.write_report('implementation', base='design-report-002.md')
        self.has(self.check(), 'report.bundle', 'FAIL')

    def test_bundle_stages_require_the_supported_pipeline(self):
        self.change(self.manifest, 'design, implementation, verification, qa', 'review')
        path = self.topic / 'design-report-001.md'
        path.rename(self.topic / 'review-report-001.md')
        self.change(self.topic / 'review-report-001.md', 'status: in_progress', 'status: in_progress\nbundle: api')
        self.has(self.check(), 'report.bundle', 'FAIL')

    def test_completed_bundle_details_remain_checked(self):
        self.write_report('design', status='completed', base='discussion-report-001.md')
        self.write_report('design', number=2, status='completed', base='discussion-report-001.md', bundle='api')
        self.write_report('design', number=3, base='discussion-report-001.md', bundle='storage')
        detail = self.topic / 'design-report-002'
        detail.mkdir()
        (detail / 'contracts.md').write_text('[missing](missing.md)')
        self.has(self.check(), 'link.target', 'FAIL')

    def test_bad_filename_and_first_base(self):
        path = self.topic / 'design-report-001.md'
        path.rename(self.topic / 'design-report-1.md')
        self.has(self.check(), 'report.filename', 'FAIL')
        self.write_report('discussion', status='completed', base='design-report-1.md')
        self.has(self.check(), 'report.base', 'FAIL')

    def test_local_links_headings_encoding_and_images(self):
        detail = self.topic / 'design-report-001'
        detail.mkdir()
        (detail / '구조 설명.md').write_text('# **핵심** `데이터`\n\n# 중복\n\n# 중복\n\n<a id="explicit"></a>', encoding='utf-8')
        (detail / 'image.png').write_bytes(b'image')
        self.design_body('[설계](design-report-001/구조%20설명.md#핵심-데이터)\n'
                         '[반복](design-report-001/구조%20설명.md#중복-1)\n'
                         '[명시](design-report-001/구조%20설명.md#explicit)\n'
                         '![그림](design-report-001/image.png)\n'
                         '[참조][r]\n\n[r]: design-report-001/구조%20설명.md\n')
        self.assertEqual(self.check()['exit_code'], 0)
        self.design_body('[설계](design-report-001/구조%20설명.md#없음)')
        self.has(self.check(), 'link.fragment', 'FAIL')

    def test_examples_not_links_and_external_skipped(self):
        self.design_body('```md\n[bad](missing.md)\n```\n`[bad](missing.md)`\n'
                         '<!-- [bad](missing.md) -->\n[web](https://example.invalid)\n')
        result = self.check()
        self.assertEqual(result['exit_code'], 0)
        self.has(result, 'link.external', 'SKIP')

    def test_unknown_fragment_and_invalid_encoding(self):
        (self.topic / 'data.txt').write_text('data', encoding='utf-8')
        self.design_body('[data](data.txt#section)')
        self.assertEqual(self.check()['exit_code'], 2)
        self.design_body('[bad](%FF.md)')
        self.has(self.check(), 'link.syntax', 'FAIL')

    def test_missing_target_and_detail_links(self):
        detail = self.topic / 'design-report-001'
        detail.mkdir()
        (detail / 'flow.md').write_text('[missing](gone.md)', encoding='utf-8')
        self.has(self.check(), 'link.target', 'FAIL')

    def test_detail_symlink_not_recursed(self):
        detail = self.topic / 'design-report-001'
        detail.symlink_to(self.topic, target_is_directory=True)
        self.has(self.check(), 'detail.symlink', 'UNCHECKED')

    def test_only_marked_diagrams_checked(self):
        self.design_body('```python\n\tprint("x")\n```\n'
                         '```text ascii-flow\n[A] -> [B]\n한글 설명\n```')
        result = self.check()
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['diagrams_checked'], 1)
        for glyph in ['\t', '\x1b', '\x00', '→', '│', '➜', '⮕',
                      '\u25bc', '\u25b6', '\u2588', '\u2014', '\u2013',
                      '\uff0b', '\uff0d', '\uff1c', '\uff1e', '\uff5c']:
            self.design_body(f'```text ascii-flow\n[A]{glyph}[B]\n```')
            self.has(self.check(), 'diagram.characters', 'FAIL')

    def test_unclosed_diagram_and_yaml_in_quoted_manifest(self):
        self.design_body('```text ascii-flow\n[A] -> [B]\n')
        self.has(self.check(), 'diagram.fence', 'FAIL')
        self.change(self.manifest, '- stages:', '> stages:')
        self.has(self.check(), 'manifest.format', 'FAIL')

    def test_unreadable_encoding_is_execution_error(self):
        (self.topic / 'design-report-001.md').write_bytes(b'\xff')
        self.has(self.check(), 'report.read', 'ERROR')
        self.assertEqual(self.check()['exit_code'], 2)

    def test_empty_saved_topic_is_not_passed(self):
        for path in self.topic.iterdir():
            path.unlink()
        self.has(self.check(), 'input.reports', 'ERROR')

    def test_link_decode_violation_and_document_read_error_are_distinct(self):
        (self.topic / 'linked.md').write_bytes(b'\xff')
        self.design_body('[bad text](linked.md#title)\n[bad url](%FF.md)')
        result = self.check()
        self.has(result, 'link.read', 'ERROR')
        self.has(result, 'link.syntax', 'FAIL')
        self.assertEqual(result['exit_code'], 2)

    def test_general_markdown_rules_and_yaml_frontmatter(self):
        path = self.topic / 'linked.md'
        for body in ['---\n\n# Title\n', '---\n\n# Title\n\n---\n',
                     '---\nnote: frontmatter\n---\n# Title\n']:
            with self.subTest(body=body):
                path.write_text(body, encoding='utf-8')
                self.design_body('[target](linked.md#title)')
                self.assertEqual(self.check()['exit_code'], 0)
        path = self.topic / 'design-report-001.md'
        path.write_text('---\nstatus: in_progress\n', encoding='utf-8')
        self.has(self.check(), 'report.format', 'FAIL')

    def test_bom_and_crlf_preserve_report_and_diagram_lines(self):
        path = self.design_body('```text ascii-flow\n[A] -> [B]\n```\n')
        path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes().replace(b'\n', b'\r\n'))
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(result['diagrams_checked'], 1)
        self.assertEqual(self.check(), result)

    def test_stat_error_is_structured_execution_error(self):
        output = io.StringIO()
        with patch.object(checker.Path, 'is_dir', side_effect=PermissionError('probe')):
            with contextlib.redirect_stdout(output):
                code = checker.main([str(self.topic), '--json'])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.has(result, 'execution', 'ERROR')

    def test_ascii_stdout_json_and_text(self):
        for args in [['--json'], []]:
            run = subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.topic), *args],
                                 env=dict(os.environ, PYTHONIOENCODING='ascii:strict'),
                                 capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr)
            output = run.stdout.decode('ascii')
            if args:
                self.assertEqual(json.loads(output)['exit_code'], 0)
            else:
                self.assertTrue(output.startswith('PASS\n'))
                self.assertIn('PASS [report.area]', output)

    def test_current_detail_scanned_old_detail_excluded_and_paths_deduplicated(self):
        old = self.topic / 'design-report-001'
        old.mkdir()
        (old / 'flow.md').write_text('[bad](missing.md)\n```text ascii-flow\n\tbroken\n```', encoding='utf-8')
        self.write_report('design', status='superseded', base='discussion-report-001.md')
        self.write_report('design', number=2, base='discussion-report-001.md', body='[detail](design-report-002/flow.md)')
        current = self.topic / 'design-report-002'
        current.mkdir()
        detail = current / 'flow.md'
        detail.write_text('[report](../design-report-002.md#단계-결과)\n```text ascii-flow\n[A] -> [B]\n```', encoding='utf-8')
        result = self.check()
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(result['diagrams_checked'], 1)
        self.assertEqual(result['documents'].count(str(self.topic / 'design-report-002.md')), 1)
        self.assertTrue(any(e['source'].endswith('design-report-001.md') for e in result['exclusions']))
        detail.write_text('```text ascii-flow\n\tbad\n```', encoding='utf-8')
        self.has(self.check(), 'diagram.characters', 'FAIL')

    def test_stage_revision_number_and_duplicate_heading_boundaries(self):
        path = self.topic / 'design-report-001.md'
        original = path.read_text(encoding='utf-8')
        for name, body, rule in [
                ('design-report-001.md', original.replace('in_progress', 'superseded'), 'report.revision'),
                ('design-report-001.md', original + '\n## 사용자 승인\n', 'report.area'),
                ('other-report-001.md', original, 'report.filename'),
                ('design-report-0001.md', original, 'report.filename'),
                ('design-report-000.md', original, 'report.filename'),
                ('implementation-report-001.md', original, 'report.base')]:
            with self.subTest(name=name, rule=rule):
                target = self.topic / name
                path.unlink(missing_ok=True)
                target.write_text(body, encoding='utf-8')
                self.has(self.check(), rule, 'FAIL')
                target.unlink()
                path.write_text(original, encoding='utf-8')
        path.rename(self.topic / 'design-report-1000.md')
        self.assertEqual(self.check()['exit_code'], 0)

    def test_missing_topic_manifest_empty_topic(self):
        self.assertEqual(checker.Checker(self.root / 'missing').run()['exit_code'], 2)
        self.manifest.unlink()
        self.has(self.check(), 'manifest.read', 'ERROR')

    def test_cli_from_other_directory_and_input_unchanged(self):
        snapshot = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        # Runtime needs only the plugin, not the Aster checkout.
        installed = self.root / 'installed-skill'
        shutil.copytree(SKILL, installed)
        script = installed / 'scripts/check_reports.py'
        for args in [[], ['--json']]:
            run = subprocess.run([sys.executable, '-B', str(script), str(self.topic), *args],
                                 cwd=self.root, text=True, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            if args:
                self.assertEqual(json.loads(run.stdout)['exit_code'], 0)
        self.assertEqual(snapshot, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot})
        self.assertEqual(set(self.topic.rglob('*')), {p for p in snapshot if self.topic in p.parents})

    def test_cli_dependencies_and_failure_codes(self):
        run = subprocess.run([sys.executable, '-I', '-B', '-S', str(SCRIPT), str(self.topic), '--json'],
                             text=True, capture_output=True, timeout=15)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)['checks'][0]['id'], 'dependency')
        self.design_body('[broken](missing.md)')
        run = subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.topic), '--json'],
                             text=True, capture_output=True, timeout=15)
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(json.loads(run.stdout)['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
