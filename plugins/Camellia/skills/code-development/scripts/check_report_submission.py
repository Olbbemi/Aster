#!/usr/bin/env python3
"""Check a saved current report before review or approval submission."""

import sys

sys.dont_write_bytecode = True

try:
    from _check_runtime import Context, command, inspect_available
except Exception as exc:
    # This fallback cannot depend on the missing runtime module.
    import json

    inputs = {}
    arguments = sys.argv[1:]
    for index, argument in enumerate(arguments):
        flag, separator, value = argument.partition("=")
        if flag.startswith("--") and flag not in ("--json", "--help"):
            if separator:
                inputs[flag[2:].replace("-", "_")] = value
            elif index + 1 < len(arguments) and not arguments[index + 1].startswith("--"):
                inputs[flag[2:].replace("-", "_")] = arguments[index + 1]
    reason = f"{type(exc).__name__}: cannot load internal runtime: {exc}"
    data = {
        "contract_version": 1, "checker": "check_report_submission", "inputs": inputs,
        "runtime": {"python": sys.version.split()[0],
                    "packages": {"PyYAML": None, "markdown-it-py": None}},
        "outcome": "error", "exit_code": 2, "files_read": [],
        "items": [{"id": "runtime.bootstrap", "path": None, "line": None,
                   "status": "error", "value": None, "reason": reason}],
        "counts": {"pass": 0, "fail": 0, "error": 1, "not_applicable": 0},
    }
    if "--json" in arguments:
        print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    else:
        print("checker: check_report_submission; contract_version: 1")
        for key in ("inputs", "runtime"):
            print(key + ": " + json.dumps(data[key], ensure_ascii=False, sort_keys=True))
        print("error runtime.bootstrap -: " + reason)
        print("files_read: []")
        print("counts: " + json.dumps(data["counts"], sort_keys=True))
        print("outcome: error; exit_code: 2")
    raise SystemExit(2)


def run(args, result):
    from _check_content import bundles, deferred, report_body
    from _check_records import Task
    context = Context(args, result)
    path = context.argument_file(args.report, "report")
    task = Task(context)
    report = task.current_report(path)
    task.submission_target(report)
    inspect_available(bundles, task)
    inspect_available(task.manifest.links)
    inspect_available(report_body, task, report)
    inspect_available(deferred, context)


if __name__ == "__main__":
    raise SystemExit(command("check_report_submission", ("report",), run))
