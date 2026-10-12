#!/usr/bin/env python3
"""Check selected scope and explicit predecessor before entry/resumption."""

import sys

sys.dont_write_bytecode = True

try:
    from _check_runtime import CheckError, Context, STAGES, command, inspect_available, lexical_path, resolve_path, within
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
        "contract_version": 1, "checker": "check_stage_entry", "inputs": inputs,
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
        print("checker: check_stage_entry; contract_version: 1")
        for key in ("inputs", "runtime"):
            print(key + ": " + json.dumps(data[key], ensure_ascii=False, sort_keys=True))
        print("error runtime.bootstrap -: " + reason)
        print("files_read: []")
        print("counts: " + json.dumps(data["counts"], sort_keys=True))
        print("outcome: error; exit_code: 2")
    raise SystemExit(2)


def run(args, result):
    from _check_content import bundles, report_body
    from _check_records import Task
    context = Context(args, result)
    if args.stage not in STAGES:
        result.error("input.stage", "unsupported entry stage")
        raise CheckError
    scope_path = lexical_path(args.scope_dir, result, "scope-dir")
    if (scope_path != context.topic and scope_path.parent != context.topic) or not within(
        resolve_path(scope_path, result), context.real_topic,
    ):
        result.error("input.scope_dir", "scope must be task root or an immediate bundle path", scope_path)
        raise CheckError
    if args.base_report != "none":
        context.argument_file(args.base_report, "base-report")
    task = Task(context, relationships=False)
    scope, target, source = task.entry_input(args)
    task.check_bases()
    inspect_available(bundles, task)
    inspect_available(task.manifest.links)
    selected = [report for (report_scope, stage), report in task.current.items() if report_scope == scope]
    if source is not None:
        selected.append(source)
    common_design = task.current.get((None, "design"))
    if task.table_applied and common_design is not None:
        selected.append(common_design)
    seen = set()
    for report in selected:
        if report.path not in seen:
            seen.add(report.path)
            inspect_available(report_body, task, report, include_diagrams=False)


if __name__ == "__main__":
    raise SystemExit(command("check_stage_entry", ("stage", "scope-dir", "base-report"), run, ("bundle-id",)))
