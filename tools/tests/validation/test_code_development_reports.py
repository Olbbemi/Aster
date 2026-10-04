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

    def write_report(self, stage, number=1, status='in_progress', base=None, body=''):
        path = self.topic / f'{stage}-report-{number:03d}.md'
        path.write_text(f'---\nstatus: {status}\nbase_on: {base or "null"}\n---\n\n'
                        '# 작업 결과\n\n' + '\n\n'.join('## ' + a for a in checker.AREAS) + '\n' + body, encoding='utf-8')
        return path

    def check(self):
        return checker.Checker(self.topic).run()

    def has(self, result, rule, status):
        self.assertTrue(any(c['id'] == rule and c['status'] == status for c in result['checks']), result)

    def change(self, path, before, after):
        path.write_text(path.read_text(encoding='utf-8').replace(before, after), encoding='utf-8')

    def design_body(self, body):
        return self.write_report('design', base='discussion-report-001.md', body=body)

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
