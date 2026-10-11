#!/usr/bin/env python3
"""Freeze confirmed sources and create a private discovery run."""

import sys
from datetime import datetime
import os
from pathlib import Path
import tempfile
import uuid

from runtime_common import digest_bytes, fail, shape, text_value, unique_strings
from source_access import absolute, decode_source, load_json, no_links, output_root, regular_bytes, targets
from run_state import save_state
from runtime_common import Parser, run_cli


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


def execute(args):
    return start(args)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--input", required=True)
    return run_cli('start', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
