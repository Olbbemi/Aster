#!/usr/bin/env python3
"""Reconcile interrupted storage and report saved, failed and pending topics."""

import sys
from runtime_common import DiscoveryError
from run_state import locked_run, save_state
from storage_recovery import reconcile
from runtime_common import Parser, run_cli


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


def execute(args):
    with locked_run(args.run) as (run, state):
        result = status(state)
        save_state(run, state)
        return result


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--run", required=True)
    return run_cli('status', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
