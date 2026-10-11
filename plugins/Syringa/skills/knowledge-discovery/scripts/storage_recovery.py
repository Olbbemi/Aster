#!/usr/bin/env python3
"""Output directory access and interrupted publication recovery."""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import re
import stat

from runtime_common import digest_bytes, fail
from source_access import directory_fd, output_root
from run_state import completed_phase


@contextmanager
def output_folder(root, day, create=False):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        fail("INVALID_STATE", "출력 날짜가 올바르지 않습니다.")
    with directory_fd(root) as parent:
        opened = []
        try:
            for name in ("knowledge-candidate", day):
                if create:
                    try:
                        os.mkdir(name, dir_fd=parent)
                        os.fsync(parent)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                except OSError as exc:
                    if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                        fail("INVALID_OUTPUT_ROOT", "저장 하위 경로가 링크 또는 디렉토리가 아닌 항목입니다.")
                    raise
                opened.append(child)
                parent = child
            yield parent
        finally:
            for fd in reversed(opened):
                os.close(fd)


def reconcile(state):
    for record in state["records"].values():
        if record["status"] != "publishing":
            continue
        root = output_root(state["output_root"])
        path = Path(record["path"])
        if path.parent.parent != root / "knowledge-candidate" or not re.fullmatch(
                r"knowledge-\d{8}-\d{6}-[a-z0-9-]+\.md", path.name):
            fail("INVALID_STATE", "저장 의도의 경로가 올바르지 않습니다.")
        try:
            with output_folder(root, path.parent.name) as fd:
                try:
                    final_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                except FileNotFoundError:
                    record.update(status="failed", error={"code": "IO_ERROR", "message": "공개 전에 중단되었습니다."})
                else:
                    with os.fdopen(final_fd, "rb") as stream:
                        info = os.fstat(stream.fileno())
                        valid = (stat.S_ISREG(info.st_mode)
                                 and [info.st_dev, info.st_ino] == record["identity"]
                                 and digest_bytes(stream.read()) == record["content_digest"])
                    if not valid:
                        fail("RECOVERY_REQUIRED", f"저장 의도와 파일이 일치하지 않습니다: {path}", 3)
                    record["status"] = "saved"
                # Remove only our own temporary inode if it survived interruption.
                temp = record.get("temporary")
                if temp and re.fullmatch(r"\.knowledge-[a-f0-9]{32}\.tmp", temp):
                    try:
                        info = os.stat(temp, dir_fd=fd, follow_symlinks=False)
                        if [info.st_dev, info.st_ino] == record["identity"]:
                            os.unlink(temp, dir_fd=fd)
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            record.update(status="failed", error={"code": "IO_ERROR", "message": "출력 경로가 없습니다."})
    completed_phase(state)
