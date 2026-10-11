#!/usr/bin/env python3
"""Register the first-stage topic and candidate list."""

import sys
from runtime_common import digest, fail, identifier, shape, text_value
from source_access import load_json, unchanged
from run_state import locked_run, save_state
from runtime_common import Parser, run_cli


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


def execute(args):
    with locked_run(args.run) as (run, state):
        result = propose(load_json(args.input), state)
        save_state(run, state)
        return result


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--input", required=True)
    return run_cli('propose', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
