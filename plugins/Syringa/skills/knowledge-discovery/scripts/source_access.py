#!/usr/bin/env python3
"""Validated source files and Git output roots."""

from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import stat
import subprocess

from runtime_common import digest_bytes, fail, json_pairs, text_value, unique_strings


def absolute(value):
    text_value(value, "path")
    path = Path(value)
    if not path.is_absolute():
        fail("INVALID_PAYLOAD", f"절대 경로가 필요합니다: {value}")
    return path


def no_links(path, code):
    # Inspect every existing component before resolving it.
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part == "..":
            fail(code, f"정규화된 경로가 필요합니다: {path}")
        current /= part
        if current.is_symlink():
            fail(code, f"링크 경로를 명시적 실제 경로로 확인하십시오: {current}")


@contextmanager
def directory_fd(path):
    """Walk from / using no-follow handles instead of following output links."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            if part in (".", ".."):
                fail("INVALID_OUTPUT_ROOT", "정규화되지 않은 출력 경로입니다.")
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    finally:
        os.close(fd)


def regular_bytes(path, code="INVALID_TARGET"):
    no_links(path, code)
    try:
        with directory_fd(path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            fail(code, f"파일 경로가 링크 또는 디렉토리가 아닌 항목으로 바뀌었습니다: {path}")
        raise
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            fail(code, f"일반 파일이 아닙니다: {path}")
        return stream.read()


def decode_source(raw, path):
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("IO_ERROR", f"UTF-8 텍스트를 읽을 수 없습니다: {path}", 3)
    if "\x00" in value:
        fail("IO_ERROR", f"텍스트 자료에 NUL이 있습니다: {path}", 3)
    return value


def load_json(path):
    try:
        return json.loads(regular_bytes(absolute(path), "INVALID_PAYLOAD").decode("utf-8"),
                          object_pairs_hook=json_pairs,
                          parse_constant=lambda value: fail("INVALID_PAYLOAD", f"JSON 상수: {value}"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("INVALID_PAYLOAD", f"JSON을 읽을 수 없습니다: {exc}")


def output_root(value):
    path = absolute(value)
    if not path.is_dir():
        fail("INVALID_OUTPUT_ROOT", f"기존 Git 작업 트리 루트가 필요합니다: {path}")
    no_links(path, "INVALID_OUTPUT_ROOT")
    path = path.resolve(strict=True)
    environment = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        environment.pop(key, None)
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, env=environment)
    if result.returncode or Path(result.stdout.strip()).resolve() != path:
        fail("INVALID_OUTPUT_ROOT", f"입력 경로가 Git 작업 트리의 정확한 루트가 아닙니다: {path}")
    if not os.access(path, os.W_OK | os.X_OK):
        fail("INVALID_OUTPUT_ROOT", f"출력 루트에 쓸 수 없습니다: {path}")
    return path


def targets(values):
    result = []
    for value in unique_strings(values, "targets"):
        path = absolute(value)
        no_links(path, "INVALID_TARGET")
        try:
            mode = path.stat().st_mode
        except OSError:
            fail("INVALID_TARGET", f"대상을 확인할 수 없습니다: {path}")
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)) or not os.access(path, os.R_OK):
            fail("INVALID_TARGET", f"읽기 가능한 일반 파일/디렉토리가 필요합니다: {path}")
        result.append(path.resolve(strict=True))
    if len(set(result)) != len(result):
        fail("INVALID_PAYLOAD", "정규화 후 중복 대상입니다.")
    return result


def unchanged(state):
    for filename, expected in state["files"].items():
        try:
            raw = regular_bytes(Path(filename), "SOURCE_CHANGED")
        except OSError:
            fail("SOURCE_CHANGED", f"고정된 자료를 읽을 수 없습니다: {filename}")
        if digest_bytes(raw) != expected:
            fail("SOURCE_CHANGED", f"자료가 변경되었습니다: {filename}")
