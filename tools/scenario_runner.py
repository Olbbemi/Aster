#!/usr/bin/env python3
"""Deliver one scenario turn to Codex; never decide or synthesize an approval."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone


REPO = Path(__file__).resolve().parents[1]
CODEX = Path('/home/olbbemi/.npm-global/bin/codex')
EXCLUDED = {'.git', '.agents', '.codex', '__pycache__'}
STEP = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')


class RunnerError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def within(path, root):
    return path != root and path.is_relative_to(root)


def snapshot(root):
    """Do not traverse links, tool mount directories, devices or large file bodies."""
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for name in sorted(files + [d for d in dirs if (Path(directory) / d).is_symlink()]):
            path = Path(directory) / name
            rel = str(path.relative_to(root))
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                result[rel] = {'symlink': os.readlink(path)}
            elif stat.S_ISREG(mode):
                h = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(chunk)
                item = {'sha256': h.hexdigest(), 'size': path.stat().st_size}
                if item['size'] <= 2 * 1024 * 1024:
                    try:
                        item['text'] = path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        pass
                result[rel] = item
            else:
                result[rel] = {'special_file': True}
    return result


def validate_case(raw, step):
    if not STEP.fullmatch(step):
        raise RunnerError('step must contain only letters, digits, underscore or hyphen')
    config = tomllib.loads((REPO / '.codex/config.toml').read_text())
    raw_roots = config.get('sandbox_workspace_write', {}).get('writable_roots', [])
    if not raw_roots or not all(isinstance(r, str) and Path(r).is_absolute() for r in raw_roots):
        raise RunnerError('Aster writable_roots must contain absolute paths')
    roots = [Path(r).resolve(strict=True) for r in raw_roots]
    case = Path(raw)
    if not case.is_absolute():
        raise RunnerError('case must be an absolute path')
    case = case.resolve(strict=True)
    if not case.is_dir() or not any(within(case, r) for r in roots):
        raise RunnerError('case must be inside an explicit Aster writable_root')
    project = (case / 'project').resolve(strict=True)
    if not project.is_dir() or not within(project, case):
        raise RunnerError('project must be a directory inside case')
    inputs = case / 'inputs'
    if inputs.is_symlink() or not inputs.is_dir():
        raise RunnerError('inputs must be a real directory inside case')
    prompt = inputs / (step + '.md')
    if prompt.is_symlink() or not prompt.is_file() or not within(prompt.resolve(), inputs):
        raise RunnerError('input must be a regular file inside case/inputs')
    data = prompt.read_bytes()
    if not data.strip() or len(data) > 1024 * 1024:
        raise RunnerError('input must be nonempty and at most 1 MiB')
    data.decode('utf-8')
    turns = case / 'turns'
    if turns.is_symlink() or (turns.exists() and not turns.is_dir()):
        raise RunnerError('turns must be a real directory inside case')
    if (turns / step).exists() or (turns / step).is_symlink():
        raise RunnerError('turn already exists; use a new step to preserve evidence')
    return case, project, data


def previous_session(case, project):
    for turn in (case / 'turns').glob('*'):
        if turn.is_symlink() or not turn.is_dir() or not (turn / 'outcome.json').is_file():
            raise RunnerError('incomplete or unexpected previous turn; inspect before retry')
    path = case / 'session.json'
    if path.is_symlink():
        raise RunnerError('session.json must not be a symlink')
    if not path.exists():
        if any((case / 'turns').glob('*/outcome.json')):
            raise RunnerError('missing session record for existing turns; inspect before retry')
        return None
    saved = json.loads(path.read_text())
    if (saved.get('case') != str(case) or saved.get('project') != str(project)
            or not UUID.fullmatch(saved.get('thread_id', ''))
            or not STEP.fullmatch(saved.get('last_step', ''))):
        raise RunnerError('session record does not match this case/project')
    previous = case / 'turns' / saved['last_step'] / 'outcome.json'
    outcome = json.loads(previous.read_text())
    if not outcome.get('success') or outcome.get('thread_id') != saved['thread_id']:
        raise RunnerError('previous turn is not a successfully completed matching session')
    return saved['thread_id']


def argv_for(project, turn, thread_id):
    # These overrides also apply to resume; no arbitrary CLI options are forwarded.
    args = [str(CODEX), 'exec',
            '-c', 'sandbox_mode="workspace-write"',
            '-c', 'approval_policy="never"',
            '-c', 'sandbox_workspace_write.writable_roots=[]',
            '-c', 'sandbox_workspace_write.network_access=false']
    if thread_id:
        args += ['resume', thread_id]
    args += ['--skip-git-repo-check', '--json',
             '-o', str(turn / 'response.md'), '-']
    return args


def stop_child(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.wait()
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def read_events(path, expected_thread):
    threads, completed, errors = set(), 0, []
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError('event is not an object')
        except ValueError:
            errors.append('invalid JSONL event')
            continue
        if event.get('type') == 'thread.started':
            threads.add(event.get('thread_id', ''))
        if event.get('type') == 'turn.completed':
            completed += 1
        if event.get('type') in {'turn.failed', 'error'}:
            errors.append(event.get('type'))
    thread = next(iter(threads)) if len(threads) == 1 else None
    if not thread or not isinstance(thread, str) or not UUID.fullmatch(thread):
        errors.append('missing or inconsistent thread ID')
    if expected_thread and thread != expected_thread:
        errors.append('resume returned a different thread ID')
    if completed != 1:
        errors.append('expected exactly one completed turn')
    return thread, errors


def run_locked(case, project, step, prompt, timeout):
    thread = previous_session(case, project)
    turn = case / 'turns' / step
    turn.mkdir(parents=True, exist_ok=False)
    (turn / 'input.md').write_bytes(prompt)
    before = snapshot(project)
    write_json(turn / 'before.json', before)
    args = argv_for(project, turn, thread)
    write_json(turn / 'execution.json', {
        'started_at': now(), 'cwd': str(project), 'argv': args,
        'runner_sha256': digest(Path(__file__).read_bytes()),
        'input_sha256': digest(prompt), 'previous_thread_id': thread,
        'timeout_seconds': timeout,
        'approval_kind': 'caller-provided scenario input; simulated approval is not human review',
        'snapshot_exclusions': sorted(EXCLUDED),
    })
    failure, code, proc = None, None, None
    try:
        with (turn / 'events.jsonl').open('x') as out, (turn / 'stderr.txt').open('x') as err:
            with (turn / 'input.md').open('rb') as inp:
                proc = subprocess.Popen(args, cwd=project, stdin=inp, stdout=out, stderr=err,
                                        start_new_session=True)
                deadline = time.monotonic() + timeout
                while proc.poll() is None:
                    if time.monotonic() >= deadline:
                        failure = 'timeout'
                        stop_child(proc)
                        break
                    time.sleep(0.2)
                code = proc.wait()
    except (OSError, KeyboardInterrupt) as exc:
        failure = 'interrupted' if isinstance(exc, KeyboardInterrupt) else str(exc)
    finally:
        if proc is not None:
            stop_child(proc)
    after = snapshot(project)
    write_json(turn / 'after.json', after)
    new_thread, errors = read_events(turn / 'events.jsonl', thread)
    if failure:
        errors.append(failure)
    if code != 0:
        errors.append('CLI did not exit successfully')
    response = turn / 'response.md'
    if not response.is_file() or not response.read_text(encoding='utf-8').strip():
        errors.append('missing final response')
    outcome = {
        'ended_at': now(), 'success': not errors, 'exit_code': code,
        'thread_id': new_thread, 'errors': errors,
        'changed_files': sorted(k for k in before.keys() | after.keys()
                                if before.get(k) != after.get(k)),
    }
    write_json(turn / 'outcome.json', outcome)
    if not errors:
        state = {'case': str(case), 'project': str(project),
                 'thread_id': new_thread, 'last_step': step}
        # A same-directory temporary file makes successful state advancement atomic.
        temp = case / '.session-next.json'
        write_json(temp, state)
        temp.replace(case / 'session.json')
    else:
        # Never automatically continue from a failed or partially executed turn.
        write_json(case / 'blocked.json', {'step': step, 'errors': errors})
    print(json.dumps({'turn': str(turn), **outcome}, ensure_ascii=False))
    return 0 if not errors else 1


def run(args):
    if not Path.cwd().resolve().is_relative_to(REPO):
        raise RunnerError('invoke the runner from the Aster repository')
    case, project, prompt = validate_case(args.case, args.step)
    if (case / 'blocked.json').exists() or (case / 'blocked.json').is_symlink():
        raise RunnerError('case is blocked by a previous failure; inspect its evidence first')
    # A persistent empty lock file avoids unlink/relock races between invocations.
    fd = os.open(case / '.runner.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RunnerError('another runner owns this case') from None
        # Recheck after obtaining the lock to avoid accepting stale validation.
        case, project, prompt = validate_case(args.case, args.step)
        if (case / 'blocked.json').exists():
            raise RunnerError('case is blocked by a previous failure')
        return run_locked(case, project, args.step, prompt, args.timeout)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    child = sub.add_parser('run', allow_abbrev=False)
    child.add_argument('--case', required=True)
    child.add_argument('--step', required=True)
    child.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 7200:
        parser.error('timeout must be between 1 and 7200 seconds')
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        return run(args)
    except (RunnerError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'scenario-runner: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
