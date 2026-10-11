#!/usr/bin/env python3
"""Atomic run state persistence and per-run locking."""

from contextlib import contextmanager
import fcntl
import os
import stat
import uuid

from runtime_common import canonical, fail
from source_access import absolute, directory_fd, load_json, no_links


def save_state(run, state):
    temporary = run / (".state-" + uuid.uuid4().hex)
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(canonical(state) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, run / "state.json")
        with directory_fd(run) as fd:
            os.fsync(fd)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked_run(value):
    run = absolute(value)
    no_links(run, "INVALID_STATE")
    info = run.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        fail("INVALID_STATE", "사용자 전용 실행 상태 디렉토리가 필요합니다.")
    with directory_fd(run) as folder:
        fd = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=folder)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("INVALID_STATE", "같은 실행을 다른 명령이 처리하고 있습니다.")
        state = load_json(str(run / "state.json"))
        required = {"schema_version", "id", "created_at", "phase", "targets", "files",
                    "output_root", "scope_confirmation", "model", "topics", "proposal_digest",
                    "selected_ids", "user_response", "records"}
        if (not isinstance(state, dict) or state.keys() != required
                or type(state.get("schema_version")) is not int or state["schema_version"] != 1
                or state.get("phase") not in {"collecting", "awaiting-approval", "processing",
                                              "completed", "empty", "excluded"}
                or not isinstance(state.get("files"), dict)
                or not isinstance(state.get("topics"), list)
                or not isinstance(state.get("selected_ids"), list)
                or not isinstance(state.get("records"), dict)):
            fail("INVALID_STATE", "실행 상태 버전을 확인할 수 없습니다.")
        yield run, state
    finally:
        os.close(fd)


def completed_phase(state):
    if state["records"] and all(r["status"] == "saved" for r in state["records"].values()):
        state["phase"] = "completed"
