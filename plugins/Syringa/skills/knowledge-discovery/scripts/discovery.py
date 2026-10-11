#!/usr/bin/env python3
"""Validate and persist a two-stage knowledge-discovery run on Linux."""

import argparse
from contextlib import contextmanager
from datetime import datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import uuid


ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FIELDS = (
    ("explanation", "개념 설명"),
    ("usage", "문법과 사용 형태"),
    ("behavior", "동작과 조건"),
    ("example", "최소 예시"),
)


class DiscoveryError(Exception):
    def __init__(self, code, message, exit_code=2):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def fail(code, message, exit_code=2):
    raise DiscoveryError(code, message, exit_code)


def text_value(value, label, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        fail("INVALID_PAYLOAD", f"{label}: 문자열이 필요합니다.")
    if "\x00" in value:
        fail("INVALID_PAYLOAD", f"{label}: NUL은 허용하지 않습니다.")
    return value


def shape(value, required, optional=()):
    if not isinstance(value, dict):
        fail("INVALID_PAYLOAD", "JSON 객체가 필요합니다.")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        fail("INVALID_PAYLOAD", f"누락 키: {sorted(missing)}, 알 수 없는 키: {sorted(extra)}")


def unique_strings(value, label, empty=False):
    if not isinstance(value, list) or (not empty and not value):
        fail("INVALID_PAYLOAD", f"{label}: 배열이 필요합니다.")
    for entry in value:
        text_value(entry, label)
    if len(value) != len(set(value)):
        fail("INVALID_PAYLOAD", f"{label}: 중복 항목이 있습니다.")
    return value


def identifier(value):
    text_value(value, "id")
    if not ID.fullmatch(value):
        fail("INVALID_PAYLOAD", f"안전한 소문자 ID가 필요합니다: {value}")
    return value


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


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return digest_bytes(canonical(value).encode("utf-8"))


def json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("INVALID_PAYLOAD", f"중복 JSON 키: {key}")
        result[key] = value
    return result


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


def inspect(args):
    if not args.target or not args.output_root:
        fail("MISSING_INPUT", "분석 대상과 저장 기준 경로를 모두 지정하십시오.")
    root = output_root(args.output_root)
    found = []
    for path in targets(args.target):
        entry = {"path": str(path), "kind": "directory" if path.is_dir() else "file"}
        if path.is_dir():
            structure = []

            def walk(folder, prefix=Path()):
                with os.scandir(folder) as entries:
                    for child in sorted(entries, key=lambda item: item.name):
                        kind = ("link" if child.is_symlink() else
                                "directory" if child.is_dir(follow_symlinks=False) else
                                "file" if child.is_file(follow_symlinks=False) else "special")
                        relative = prefix / child.name
                        structure.append({"path": str(relative), "kind": kind})
                        if kind == "directory":
                            fd = os.open(child.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                         dir_fd=folder)
                            try:
                                walk(fd, relative)
                            finally:
                                os.close(fd)
            with directory_fd(path) as folder:
                walk(folder)
            entry["structure"] = structure
        found.append(entry)
    return {"targets": found, "output_root": str(root)}


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


def start(args):
    value = load_json(args.input)
    shape(value, ("targets", "output_root", "files", "scope_confirmation", "model"))
    selected_targets = targets(value["targets"])
    root = output_root(value["output_root"])
    text_value(value["scope_confirmation"], "scope_confirmation")
    shape(value["model"], ("name", "effort", "approval", "verification"))
    for key, item in value["model"].items():
        text_value(item, f"model.{key}")
    if value["model"]["verification"] not in ("runtime-confirmed", "user-confirmed"):
        fail("INVALID_PAYLOAD", "model.verification이 올바르지 않습니다.")
    files = {}
    for item in unique_strings(value["files"], "files", empty=True):
        path = absolute(item)
        no_links(path, "SCOPE_VIOLATION")
        path = path.resolve(strict=True)
        if not any(path == target or (target.is_dir() and target in path.parents)
                   for target in selected_targets):
            fail("SCOPE_VIOLATION", f"분석 범위 밖 파일입니다: {path}")
        if str(path) in files:
            fail("INVALID_PAYLOAD", "정규화 후 중복 파일입니다.")
        raw = regular_bytes(path)
        decode_source(raw, path)
        files[str(path)] = digest_bytes(raw)
    if any(target.is_file() and str(target) not in files for target in selected_targets):
        fail("SCOPE_VIOLATION", "명시한 대상 파일이 확인된 파일 목록에 없습니다.")
    run = Path(tempfile.mkdtemp(prefix="knowledge-discovery-"))
    os.chmod(run, 0o700)
    state = {"schema_version": 1, "id": uuid.uuid4().hex,
             "created_at": datetime.now().astimezone().isoformat(), "phase": "collecting",
             "targets": list(map(str, selected_targets)), "files": files,
             "output_root": str(root), "scope_confirmation": value["scope_confirmation"],
             "model": value["model"], "topics": [], "proposal_digest": None,
             "selected_ids": [], "user_response": None, "records": {}}
    save_state(run, state)
    return {"run": str(run), "phase": state["phase"], "files": list(files)}


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


def unchanged(state):
    for filename, expected in state["files"].items():
        try:
            raw = regular_bytes(Path(filename), "SOURCE_CHANGED")
        except OSError:
            fail("SOURCE_CHANGED", f"고정된 자료를 읽을 수 없습니다: {filename}")
        if digest_bytes(raw) != expected:
            fail("SOURCE_CHANGED", f"자료가 변경되었습니다: {filename}")


def read_file(args, state):
    path = absolute(args.file)
    no_links(path, "SCOPE_VIOLATION")
    key = str(path.resolve())
    if key not in state["files"]:
        fail("SCOPE_VIOLATION", "확정한 파일만 읽을 수 있습니다.")
    try:
        raw = regular_bytes(path, "SOURCE_CHANGED")
    except OSError:
        fail("SOURCE_CHANGED", f"고정된 자료를 읽을 수 없습니다: {path}")
    if digest_bytes(raw) != state["files"][key]:
        fail("SOURCE_CHANGED", f"자료가 변경되었습니다: {path}")
    return {"file": key, "text": decode_source(raw, path)}


def propose(value, state):
    shape(value, ("topics",))
    if state["phase"] != "collecting":
        fail("INVALID_STATE", "후보 등록 단계가 아닙니다.")
    if not isinstance(value["topics"], list):
        fail("INVALID_PAYLOAD", "topics 배열이 필요합니다.")
    topics_seen, candidates_seen = set(), set()
    for topic in value["topics"]:
        shape(topic, ("id", "title", "candidates"))
        tid = identifier(topic["id"])
        text_value(topic["title"], "title")
        if tid in topics_seen:
            fail("INVALID_PAYLOAD", "중복 주제 ID입니다.")
        topics_seen.add(tid)
        if not isinstance(topic["candidates"], list) or not topic["candidates"]:
            fail("INVALID_PAYLOAD", "주제에는 후보가 필요합니다.")
        for candidate in topic["candidates"]:
            shape(candidate, ("id", "keyword", "summary"))
            cid = identifier(candidate["id"])
            text_value(candidate["keyword"], "keyword")
            text_value(candidate["summary"], "summary")
            if "\n" in candidate["keyword"] or "\r" in candidate["keyword"]:
                fail("INVALID_PAYLOAD", "키워드는 한 줄이어야 합니다.")
            if cid in candidates_seen:
                fail("INVALID_PAYLOAD", "중복 후보 ID입니다.")
            candidates_seen.add(cid)
    unchanged(state)
    state["topics"] = value["topics"]
    state["proposal_digest"] = digest(value)
    state["phase"] = "awaiting-approval" if value["topics"] else "empty"
    return {"phase": state["phase"], "proposal_digest": state["proposal_digest"],
            "topics": state["topics"]}


def approve(value, state):
    shape(value, ("proposal_digest", "selected_ids", "user_response"))
    if state["phase"] != "awaiting-approval":
        fail("INVALID_STATE", "승인 대기 단계가 아닙니다.")
    if value["proposal_digest"] != state["proposal_digest"]:
        fail("APPROVAL_MISMATCH", "승인한 후보 목록이 현재 목록과 다릅니다.")
    selected = unique_strings(value["selected_ids"], "selected_ids", empty=True)
    known = {c["id"] for topic in state["topics"] for c in topic["candidates"]}
    if not set(selected) <= known:
        fail("APPROVAL_MISMATCH", "등록하지 않은 후보는 승인할 수 없습니다.")
    text_value(value["user_response"], "user_response")
    unchanged(state)
    state["selected_ids"] = selected
    state["user_response"] = value["user_response"]
    state["phase"] = "processing" if selected else "excluded"
    state["records"] = {topic["id"]: {"status": "pending"} for topic in state["topics"]
                        if any(c["id"] in selected for c in topic["candidates"])}
    return {"phase": state["phase"], "selected_ids": selected}


def prose(value, label):
    text_value(value, label)
    if (re.search(r"(?m)^ {0,3}#{1,2}(?:\s|$)", value)
            or re.search(r"(?m)^ {0,3}(?:=+|-+)\s*$", value)
            or re.search(r"<\s*h[12](?:\s|>)", value, re.I)):
        fail("INVALID_PAYLOAD", f"{label}: H1/H2 구조를 추가할 수 없습니다.")
    return visible_angles(value.strip())


def visible_angles(value):
    """Keep literal type/tag notation visible without changing code spans."""
    span = re.compile(r"(?<!`)(`+)(?!`)([\s\S]*?)(?<!`)\1(?!`)")
    chunks = []
    position = 0

    def escape(part):
        return re.sub(r"(?<!\\)((?:\\\\)*)([<>])",
                      lambda match: match.group(1) + "\\" + match.group(2), part)

    for match in span.finditer(value):
        before = value[:match.start()]
        backslashes = len(before) - len(before.rstrip("\\"))
        if backslashes % 2:
            continue
        chunks.append(escape(value[position:match.start()]))
        chunks.append(match.group())
        position = match.end()
    chunks.append(escape(value[position:]))
    return "".join(chunks)


def render(value, state):
    shape(value, ("topic_id", "concepts"))
    tid = identifier(value["topic_id"])
    topic = next((t for t in state["topics"] if t["id"] == tid), None)
    if topic is None or tid not in state["records"]:
        fail("APPROVAL_MISMATCH", "승인된 주제만 저장할 수 있습니다.")
    expected = {c["id"]: c for c in topic["candidates"] if c["id"] in state["selected_ids"]}
    if not isinstance(value["concepts"], list) or not value["concepts"]:
        fail("INVALID_PAYLOAD", "개념 배열이 필요합니다.")
    indexed = {}
    for concept in value["concepts"]:
        shape(concept, ("candidate_id",), tuple(key for key, _ in FIELDS))
        cid = identifier(concept["candidate_id"])
        if cid not in expected:
            fail("APPROVAL_MISMATCH", "해당 주제의 승인 범위 밖 개념입니다.")
        if cid in indexed or len(concept) == 1:
            fail("INVALID_PAYLOAD", "중복 또는 내용 없는 개념입니다.")
        indexed[cid] = concept
    if indexed.keys() != expected.keys():
        fail("APPROVAL_MISMATCH", "승인된 주제의 개념을 빠짐없이 포함하십시오.")
    chunks = []
    for cid, candidate in expected.items():
        concept = indexed[cid]
        keyword = re.sub(r"([\\`*_{}\[\]()#+.!<>|~\-])", r"\\\1", candidate["keyword"])
        chunks.append("# " + keyword)
        for key, title in FIELDS:
            if key not in concept:
                continue
            chunks.append("## " + title)
            if key == "example":
                example = concept[key]
                shape(example, ("language", "text"))
                language = text_value(example["language"], "language", empty=True)
                if language and not re.fullmatch(r"[A-Za-z0-9_+.-]+", language):
                    fail("INVALID_PAYLOAD", "코드 언어 식별자가 올바르지 않습니다.")
                body = text_value(example["text"], "example.text").strip("\n")
                width = max([2] + [len(match) for match in re.findall(r"`+", body)]) + 1
                fence = "`" * width
                chunks.append(f"{fence}{language}\n{body}\n{fence}")
            else:
                chunks.append(prose(concept[key], key))
    return tid, "\n\n".join(chunks) + "\n"


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


def completed_phase(state):
    if state["records"] and all(r["status"] == "saved" for r in state["records"].values()):
        state["phase"] = "completed"


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


def save_topic(value, run, state):
    if state["phase"] not in ("processing", "completed"):
        fail("INVALID_STATE", "승인 이후에만 저장할 수 있습니다.")
    reconcile(state)
    tid, content = render(value, state)
    payload_digest = digest(value)
    record = state["records"][tid]
    if record["status"] == "saved":
        if record["payload_digest"] != payload_digest:
            fail("TOPIC_CONFLICT", "이미 저장한 주제를 다른 내용으로 덮어쓸 수 없습니다.")
        return {"topic_id": tid, "path": record["path"], "reused": True}
    unchanged(state)
    root = output_root(state["output_root"])
    moment = datetime.now().astimezone()
    day = moment.strftime("%Y-%m-%d")
    stem = f"knowledge-{moment:%Y%m%d-%H%M%S}-{tid}"
    raw = content.encode("utf-8")
    with output_folder(root, day, create=True) as folder:
        temporary = ".knowledge-" + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                info = os.fstat(stream.fileno())
            suffix = 1
            while True:
                filename = stem + ("" if suffix == 1 else f"-{suffix}") + ".md"
                record.clear()
                record.update(status="publishing", path=str(root / "knowledge-candidate" / day / filename),
                              payload_digest=payload_digest, content_digest=digest_bytes(raw),
                              identity=[info.st_dev, info.st_ino], temporary=temporary)
                save_state(run, state)
                try:
                    os.link(temporary, filename, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
                    break
                except FileExistsError:
                    suffix += 1
            os.fsync(folder)
            record["status"] = "saved"
            completed_phase(state)
            save_state(run, state)
        finally:
            os.unlink(temporary, dir_fd=folder)
    return {"topic_id": tid, "path": record["path"], "reused": False}


def status(state):
    recovery = None
    try:
        reconcile(state)
    except DiscoveryError as exc:
        recovery = {"code": exc.code, "message": str(exc)}
    result = {"phase": state["phase"], "saved": [], "failed": [], "pending": [],
              "recovery_required": recovery}
    for tid, record in state["records"].items():
        item = {"topic_id": tid}
        if record["status"] == "saved":
            item["path"] = record["path"]
            result["saved"].append(item)
        elif record["status"] == "failed":
            item["error"] = record["error"]
            result["failed"].append(item)
        else:
            result["pending"].append(item)
    return result


def run_command(args):
    if args.command == "inspect":
        return inspect(args)
    if args.command == "start":
        return start(args)
    with locked_run(args.run) as (run, state):
        if args.command == "read":
            return read_file(args, state)
        if args.command == "status":
            result = status(state)
            save_state(run, state)
            return result
        value = load_json(args.input)
        try:
            if args.command == "propose":
                result = propose(value, state)
            elif args.command == "approve":
                result = approve(value, state)
            else:
                result = save_topic(value, run, state)
        except (DiscoveryError, OSError) as exc:
            tid = value.get("topic_id") if isinstance(value, dict) else None
            record = state["records"].get(tid) if isinstance(tid, str) else None
            if args.command == "save-topic" and record is not None and record["status"] not in ("saved", "publishing"):
                record.update(status="failed", error={"code": getattr(exc, "code", "IO_ERROR"), "message": str(exc)})
                save_state(run, state)
            raise
        save_state(run, state)
        return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail("MISSING_INPUT", message)


def main(argv=None):
    command = None
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        p = commands.add_parser("inspect")
        p.add_argument("--target", action="append", required=True)
        p.add_argument("--output-root", required=True)
        p = commands.add_parser("start")
        p.add_argument("--input", required=True)
        for name in ("read", "propose", "approve", "save-topic", "status"):
            p = commands.add_parser(name)
            p.add_argument("--run", required=True)
            if name == "read":
                p.add_argument("--file", required=True)
            elif name != "status":
                p.add_argument("--input", required=True)
        args = parser.parse_args(argv)
        command = args.command
        data = run_command(args)
        print(json.dumps({"ok": True, "command": command, "data": data}, ensure_ascii=False))
        return 0
    except DiscoveryError as exc:
        response = {"ok": False, "command": command,
                    "error": {"code": exc.code, "message": str(exc)}}
        code = exc.exit_code
    except (OSError, ValueError) as exc:
        response = {"ok": False, "command": command,
                    "error": {"code": "IO_ERROR", "message": str(exc)}}
        code = 3
    print(json.dumps(response, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
