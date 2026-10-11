#!/usr/bin/env python3
"""Fix the selected candidate IDs for the registered proposal."""

import sys
from runtime_common import fail, shape, text_value, unique_strings
from source_access import load_json, unchanged
from run_state import locked_run, save_state
from runtime_common import Parser, run_cli


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


def execute(args):
    with locked_run(args.run) as (run, state):
        result = approve(load_json(args.input), state)
        save_state(run, state)
        return result


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--input", required=True)
    return run_cli('approve', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
