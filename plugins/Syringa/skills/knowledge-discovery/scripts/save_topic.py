#!/usr/bin/env python3
"""Render and atomically publish one approved topic."""

import sys
from datetime import datetime
import os
import re
import uuid

from runtime_common import DiscoveryError, digest, digest_bytes, fail, identifier, shape, text_value
from source_access import load_json, output_root, unchanged
from run_state import completed_phase, locked_run, save_state
from storage_recovery import output_folder, reconcile
from runtime_common import Parser, run_cli


FIELDS = (
    ("explanation", "개념 설명"),
    ("usage", "문법과 사용 형태"),
    ("behavior", "동작과 조건"),
    ("example", "최소 예시"),
)


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


def execute(args):
    with locked_run(args.run) as (run, state):
        value = load_json(args.input)
        try:
            result = save_topic(value, run, state)
        except (DiscoveryError, OSError) as exc:
            tid = value.get("topic_id") if isinstance(value, dict) else None
            record = state["records"].get(tid) if isinstance(tid, str) else None
            if record is not None and record["status"] not in ("saved", "publishing"):
                record.update(status="failed", error={"code": getattr(exc, "code", "IO_ERROR"), "message": str(exc)})
                save_state(run, state)
            raise
        save_state(run, state)
        return result


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--input", required=True)
    return run_cli('save-topic', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
