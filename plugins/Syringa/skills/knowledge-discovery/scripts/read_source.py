#!/usr/bin/env python3
"""Read one confirmed source after validating its snapshot."""

import sys
from runtime_common import digest_bytes, fail
from source_access import absolute, decode_source, no_links, regular_bytes
from run_state import locked_run
from runtime_common import Parser, run_cli


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


def execute(args):
    with locked_run(args.run) as (_, state):
        return read_file(args, state)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--file", required=True)
    return run_cli('read', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
