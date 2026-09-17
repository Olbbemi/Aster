"""Runner contract tests using a local fake CLI, with no model/API invocation."""

import argparse
from contextlib import redirect_stdout
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('scenario_runner', Path(__file__).parents[1] / 'scenario_runner.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
THREAD = '12345678-1234-1234-1234-123456789abc'
FAKE = '''#!/usr/bin/python3
import json, pathlib, sys, time
args = sys.argv[1:]
prompt = sys.stdin.read().strip()
if prompt == 'timeout':
    time.sleep(30)
    sys.exit(0)
if prompt == 'fail':
    print('initialization failed', file=sys.stderr)
    sys.exit(1)
thread = '12345678-1234-1234-1234-123456789abc'
if prompt == 'wrong-thread':
    thread = 'aaaaaaaa-1234-1234-1234-123456789abc'
print(json.dumps({'type': 'thread.started', 'thread_id': thread}))
if prompt == 'bad-json':
    print('not json')
if prompt == 'incomplete':
    sys.exit(0)
if prompt != 'no-response':
    pathlib.Path(args[args.index('-o') + 1]).write_text('DONE\\n')
pathlib.Path('marker.txt').write_text(prompt)
print(json.dumps({'type': 'turn.completed'}))
'''


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aster-runner-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        (self.repo / '.codex').mkdir(parents=True)
        self.allowed = self.root / 'allowed'
        self.case = self.allowed / 'case'
        self.project = self.case / 'project'
        self.project.mkdir(parents=True)
        (self.case / 'inputs').mkdir()
        (self.repo / '.codex/config.toml').write_text(
            '[sandbox_workspace_write]\nwritable_roots = [' + json.dumps(str(self.allowed)) + ']\n')
        self.fake = self.root / 'fake-codex'
        self.fake.write_text(FAKE)
        self.fake.chmod(0o700)
        self.patch_repo = patch.object(runner, 'REPO', self.repo)
        self.patch_codex = patch.object(runner, 'CODEX', self.fake)
        self.patch_repo.start()
        self.patch_codex.start()
        self.addCleanup(self.patch_repo.stop)
        self.addCleanup(self.patch_codex.stop)
        old_cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, old_cwd)

    def args(self, step='01', prompt='hello', timeout=10):
        (self.case / 'inputs' / (step + '.md')).write_text(prompt)
        return argparse.Namespace(case=str(self.case), step=step, timeout=timeout)

    def invoke(self, args):
        with redirect_stdout(io.StringIO()):
            return runner.run(args)

    def test_exec_resume_evidence_and_sandbox(self):
        self.assertEqual(self.invoke(self.args()), 0)
        first = self.case / 'turns/01'
        saved = json.loads((self.case / 'session.json').read_text())
        self.assertEqual(saved['thread_id'], THREAD)
        self.assertEqual(json.loads((first / 'before.json').read_text()), {})
        self.assertEqual(json.loads((first / 'after.json').read_text())['marker.txt']['text'], 'hello')
        self.assertEqual(self.invoke(self.args('02', 'again')), 0)
        second = self.case / 'turns/02'
        resumed_args = json.loads((second / 'execution.json').read_text())['argv']
        self.assertEqual(resumed_args[resumed_args.index('resume') + 1], THREAD)
        for turn in (first, second):
            with self.subTest(turn=turn.name):
                args = json.loads((turn / 'execution.json').read_text())['argv']
                for option in ('sandbox_mode="workspace-write"', 'approval_policy="never"',
                               'sandbox_workspace_write.writable_roots=[]',
                               'sandbox_workspace_write.network_access=false'):
                    self.assertIn(option, args)
                self.assertNotIn('--ignore-rules', args)
                self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', args)
                self.assertEqual(args[-1], '-')
        self.assertEqual((second / 'input.md').read_text(), 'again')

    def test_refuses_overwriting_evidence(self):
        args = self.args()
        self.invoke(args)
        old = (self.case / 'turns/01/outcome.json').read_bytes()
        with self.assertRaises(runner.RunnerError):
            self.invoke(args)
        self.assertEqual(old, (self.case / 'turns/01/outcome.json').read_bytes())

    def test_outside_allowed_root(self):
        with self.assertRaises(runner.RunnerError):
            runner.validate_case(str(self.repo), '01')

    def test_case_symlink_escape(self):
        (self.allowed / 'escape').symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(runner.RunnerError):
            runner.validate_case(str(self.allowed / 'escape'), '01')

    def test_shared_root_alias_is_accepted(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.allowed, target_is_directory=True)
        self.args()
        self.assertEqual(runner.validate_case(str(alias / 'case'), '01')[0], self.case)

    def test_project_symlink_escape(self):
        self.project.rmdir()
        self.project.symlink_to(self.repo, target_is_directory=True)
        self.args()
        with self.assertRaises(runner.RunnerError):
            runner.validate_case(str(self.case), '01')

    def test_input_symlink_escape(self):
        args = self.args()
        prompt = self.case / 'inputs/01.md'
        prompt.unlink()
        prompt.symlink_to(self.repo / '.codex/config.toml')
        with self.assertRaises(runner.RunnerError):
            self.invoke(args)

    def test_turns_symlink_escape(self):
        (self.case / 'turns').symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args())

    def test_invalid_steps_and_empty_input(self):
        for step in ('../escape', '--config', 'a/b', '', 'x' * 81):
            with self.subTest(step=step), self.assertRaises(runner.RunnerError):
                runner.validate_case(str(self.case), step)
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args(prompt=' '))

    def test_wrong_cwd(self):
        os.chdir(self.root)
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args())

    def test_concurrent_invocation(self):
        with (self.case / '.runner.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(runner.RunnerError):
                self.invoke(self.args())

    def test_changed_session_project_is_rejected(self):
        self.invoke(self.args())
        file = self.case / 'session.json'
        data = json.loads(file.read_text())
        data['project'] = str(self.repo)
        file.write_text(json.dumps(data))
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args('02'))

    def test_missing_session_is_not_silently_restarted(self):
        self.invoke(self.args())
        (self.case / 'session.json').unlink()
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args('02'))

    def test_incomplete_previous_attempt_is_not_silently_restarted(self):
        (self.case / 'turns/00-interrupted').mkdir(parents=True)
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args())

    def test_missing_cli_preserves_failure_evidence(self):
        with patch.object(runner, 'CODEX', self.root / 'missing-cli'):
            self.assertEqual(self.invoke(self.args()), 1)
        self.assertTrue((self.case / 'turns/01/outcome.json').is_file())
        self.assertTrue((self.case / 'blocked.json').is_file())

    def test_failed_turn_blocks_automatic_continuation(self):
        self.assertEqual(self.invoke(self.args(prompt='fail')), 1)
        self.assertFalse((self.case / 'session.json').exists())
        self.assertTrue((self.case / 'blocked.json').exists())
        with self.assertRaises(runner.RunnerError):
            self.invoke(self.args('02'))

    def test_incomplete_turn_is_failure_even_with_zero_exit(self):
        self.assertEqual(self.invoke(self.args(prompt='incomplete')), 1)
        result = json.loads((self.case / 'turns/01/outcome.json').read_text())
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['success'])

    def test_final_response_required(self):
        self.assertEqual(self.invoke(self.args(prompt='no-response')), 1)

    def test_malformed_json_is_failure(self):
        self.assertEqual(self.invoke(self.args(prompt='bad-json')), 1)

    def test_wrong_resume_thread_does_not_advance_session(self):
        self.invoke(self.args())
        old = (self.case / 'session.json').read_bytes()
        self.assertEqual(self.invoke(self.args('02', 'wrong-thread')), 1)
        self.assertEqual(old, (self.case / 'session.json').read_bytes())

    def test_timeout_stops_process_and_preserves_failure(self):
        self.assertEqual(self.invoke(self.args(prompt='timeout', timeout=1)), 1)
        outcome = json.loads((self.case / 'turns/01/outcome.json').read_text())
        self.assertIn('timeout', outcome['errors'])
        self.assertIsNotNone(outcome['exit_code'])

    def test_snapshot_does_not_read_links_or_mount_metadata(self):
        (self.project / 'secret-link').symlink_to(self.repo / '.codex/config.toml')
        (self.project / '.codex').mkdir()
        (self.project / '.codex/config.toml').write_text('not host evidence')
        snap = runner.snapshot(self.project)
        self.assertEqual(set(snap), {'secret-link'})
        self.assertIn('symlink', snap['secret-link'])
        self.assertNotIn('text', snap['secret-link'])


if __name__ == '__main__':
    unittest.main()
