#!/usr/bin/env python3
"""Exercise each packaged CLI and shared runtime boundaries through public files."""

import importlib.metadata
from pathlib import Path
import platform
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import Results, expect, require, run_check, snapshot, tree_state
from repository_support import ENTRYPOINTS


def arguments(fixture, entry):
    if entry == "check_task_start":
        values = fixture.args(entry)
        values[values.index("--topic-dir") + 1] = str(fixture.topic.with_name("새 작업"))
        return values
    if entry == "check_stage_entry":
        return fixture.args(entry, base=fixture.reports["discussion"])
    if entry == "check_review_receipt":
        return fixture.args(entry, review=fixture.review())
    if entry == "check_task_completion":
        fixture.section(fixture.reports["qa"], "완료 구분", "all_passed\n고정 시험 근거\n", 3)
    return fixture.args(entry)


def check(repository, results):
    with snapshot(repository) as harness:
        def case(identifier, function):
            def execute():
                with harness.fixture(through="qa") as fixture:
                    function(fixture)
            results.case(identifier, execute)

        for entry in ENTRYPOINTS:
            def normal(f, name=entry):
                argv = arguments(f, name)
                data = expect(harness.invoke(name, argv, process=True), entrypoint=name)
                expected = {argv[i][2:].replace("-", "_"): argv[i + 1]
                            for i in range(0, len(argv), 2)}
                require(data["inputs"] == expected, "explicit inputs were changed")
                require(data["runtime"]["packages"] == {p: importlib.metadata.version(p)
                        for p in ("PyYAML", "markdown-it-py")}, "reported package versions are incorrect")
                require(data["runtime"]["python"] == platform.python_version(), "reported Python version is incorrect")
                required = {
                    "check_task_start": {"C1"},
                    "check_stage_entry": {f"C{i}" for i in range(2, 12)},
                    "check_report_submission": {f"C{i}" for i in range(2, 13)} | {"C14"},
                    "check_review_receipt": {"C11", "C13"},
                    "check_task_completion": {f"C{i}" for i in range(2, 15)},
                }[name]
                actual = {item["id"].split(".")[0] for item in data["items"]}
                require(required <= actual, "normal invocation omitted mandatory rule categories")
            case("R01." + entry, normal)
            required = ["project-root", "topic-dir"] + {
                "check_task_start": [], "check_stage_entry": ["stage", "scope-dir", "base-report"],
                "check_report_submission": ["report"], "check_review_receipt": ["report", "review"],
                "check_task_completion": ["qa-report"],
            }[entry]
            for option in required:
                def missing(f, name=entry, flag="--" + option):
                    argv = arguments(f, name)
                    index = argv.index(flag)
                    del argv[index:index + 2]
                    expect(harness.invoke(name, argv, process=True), 2, entrypoint=name)
                case("R02.missing." + entry + "." + option, missing)
            for suffix, flags in (("unknown", ["--unknown", "value"]),
                                  ("abbreviation", ["--proj", "value"]),
                                  ("duplicate", ["--project-root", "value"]),
                                  ("duplicate_json", ["--json"]),
                                  ("duplicate_help", ["--help", "--help"])):
                def invalid(f, name=entry, extra=flags):
                    expect(harness.invoke(name, arguments(f, name) + extra), 2, entrypoint=name)
                case("R02." + suffix + "." + entry, invalid)
            def same_value(f, name=entry):
                argv = arguments(f, name)
                expect(harness.invoke(name, argv + argv[:2]), 2, entrypoint=name)
            case("R02.same_value." + entry, same_value)

            for module in ("_check_runtime", "_check_records", "_check_markdown", "_check_content"):
                if entry == "check_task_start" and module == "_check_content":
                    continue
                def missing_internal(f, name=entry, selected=module):
                    argv = arguments(f, name)
                    path = harness.skill / "scripts" / (selected + ".py")
                    original = path.read_bytes()
                    path.unlink()
                    try:
                        data = expect(harness.invoke(name, argv, process=True), 2, entrypoint=name)
                        expected = {argv[i][2:].replace("-", "_"): argv[i + 1]
                                    for i in range(0, len(argv), 2)}
                        require(data["inputs"] == expected, "loading failure lost explicit inputs")
                        call = harness.invoke(name, argv, json_output=False, process=True)
                        require(call.code == 2 and not call.stderr and "outcome: error; exit_code: 2" in call.stdout,
                                "loading failure did not return a text error")
                    finally:
                        path.write_bytes(original)
                case("R09.internal." + entry + "." + module, missing_internal)
            def help_only(f, name=entry):
                call = harness.invoke(name, ["--help"], json_output=False, process=True)
                require(call.code == 0 and "--project-root" in call.stdout and not call.stderr, "help-only call failed")
                before = tree_state(harness.skill)
                no_package = harness.invoke(name, ["--help"], json_output=False, fault=("missing_package", None))
                require(no_package.code == 0 and "--project-root" in no_package.stdout, "help should not need parser packages")
                require(tree_state(harness.skill) == before, "help modified skill files")
            case("R04." + entry, help_only)

        for suffix, option, value in (("relative", "--project-root", "."),
                                     ("hierarchy", "--topic-dir", "invalid"),
                                     ("stage", "--stage", "unsupported"),
                                     ("scope", "--scope-dir", "invalid")):
            def invalid_path(f, flag=option, supplied=value):
                argv = arguments(f, "check_stage_entry")
                if supplied == "invalid":
                    supplied = str(f.root / "outside")
                argv[argv.index(flag) + 1] = supplied
                expect(harness.invoke("check_stage_entry", argv), 2)
            case("R03." + suffix, invalid_path)
        def missing_file(f):
            argv = f.args("check_report_submission", report=f.topic / "design-report-rev-999.md")
            expect(harness.invoke("check_report_submission", argv), 2)
        case("R03.missing_file", missing_file)
        def scope_escape(f):
            outside = harness.root / "outside"
            outside.mkdir()
            link = f.topic.parent / "escape"
            link.symlink_to(outside, target_is_directory=True)
            expect(harness.invoke("check_task_start", ["--project-root", f.root, "--topic-dir", link]), 2)
        case("R03.realpath_escape", scope_escape)
        def wrong_task(f):
            other = f.topic.with_name("other")
            path = f.report("design", scope=other)
            expect(harness.invoke("check_report_submission", f.args("check_report_submission", report=path)), 2)
        case("R03.wrong_task", wrong_task)

        for code in (0, 1, 2):
            def output(f, expected=code):
                entry = "check_report_submission"
                argv = f.args(entry)
                if expected == 1:
                    f.replace(f.reports["design"], "## 인계 사항", "## 다른 영역")
                elif expected == 2:
                    argv += ["--unknown"]
                json_call = harness.invoke(entry, argv)
                data = expect(json_call, expected)
                text = harness.invoke(entry, argv, json_output=False)
                require(text.code == expected and not text.stderr, "text and JSON exit/stderr differ")
                require(f"outcome: {data['outcome']}; exit_code: {expected}" in text.stdout, "text outcome missing")
                for item in data["items"]:
                    require(item["status"] + " " + item["id"] + " " in text.stdout, "text omits an item status/ID")
                require("counts:" in text.stdout and "files_read:" in text.stdout and "inputs:" in text.stdout, "text metadata is incomplete")
            case("R05.output." + str(code), output)

        def ordering(f):
            path = f.reports["design"]
            f.section(path, "단계 결과", "[중복](discussion-report.md)\n[재참조](discussion-report.md)\n")
            first = expect(harness.invoke("check_report_submission", f.args("check_report_submission")))
            second = expect(harness.invoke("check_report_submission", f.args("check_report_submission")))
            require(first == second, "repeat result is not deterministic")
        case("R06.ordering", ordering)
        def combined(f):
            path = f.reports["design"]
            f.replace(path, "## 인계 사항", "## 다른 영역")
            extra = f.topic / "evidence.md"
            extra.write_text("# 근거\n", encoding="utf-8")
            f.section(path, "단계 결과", "[근거](evidence.md#근거)")
            data = expect(harness.invoke("check_report_submission", f.args("check_report_submission"),
                                         fault=("read", extra)), 2, "C6")
            require(any(item["status"] == "error" for item in data["items"]), "read error was lost")
        case("R07.error_and_false", combined)
        def encoding(f):
            path = f.reports["design"]
            content = path.read_text(encoding="utf-8").replace("## 인계 사항", "## 다른 영역")
            path.write_bytes(b"\xef\xbb\xbf" + content.replace("\n", "\r\n").encode("utf-8"))
            data = expect(harness.invoke("check_report_submission", f.args("check_report_submission")), 1, "C6")
            lines = len(content.splitlines())
            require(all(item["line"] is None or item["line"] <= lines for item in data["items"] if item["path"] == str(path)), "line lies outside original source")
            # C4's metadata location must preserve the original first line despite BOM.
            require(any(item["id"].startswith("C4.") and item["line"] == 1 for item in data["items"]), "frontmatter origin was shifted")
        case("R08.bom_crlf", encoding)
        for name, fault in (("missing", ("missing_package", None)), ("unsupported", ("package_version", "7.0.0")),
                            ("import", ("import", None))):
            def dependency(f, injected=fault):
                expect(harness.invoke("check_report_submission", f.args("check_report_submission"), fault=injected), 2)
            case("R09." + name, dependency)
        for kind in ("read", "stat", "list"):
            def unreadable(f, failure=kind):
                selected = f.topic if failure == "list" else f.reports["design"]
                expect(harness.invoke("check_report_submission", f.args("check_report_submission"),
                                      fault=(failure, selected)), 2)
            case("R10." + kind, unreadable)
        def invalid_utf8(f):
            f.reports["design"].write_bytes(b"\xff\xfe")
            expect(harness.invoke("check_report_submission", f.args("check_report_submission")), 2)
        case("R10.utf8", invalid_utf8)
        for entry in ENTRYPOINTS:
            for code in (0, 1, 2):
                def readonly(f, name=entry, expected=code):
                    argv = arguments(f, name)
                    if expected == 1:
                        if name == "check_task_start":
                            argv[argv.index("--topic-dir") + 1] = str(f.topic)
                        elif name == "check_stage_entry":
                            f.replace(f.reports["discussion"], "status: completed", "status: hold")
                        elif name == "check_review_receipt":
                            path = Path(argv[argv.index("--review") + 1])
                            f.replace(path, "## 종합 의견", "## 다른 영역")
                        elif name == "check_task_completion":
                            f.replace(f.reports["verification"], "status: completed", "status: in_progress")
                        else:
                            f.replace(f.reports["design"], "## 인계 사항", "## 다른 영역")
                    elif expected == 2:
                        argv += ["--unknown"]
                    before = tree_state(harness.root)
                    expect(harness.invoke(name, argv, process=True, bytecode=True), expected)
                    require(tree_state(harness.root) == before, "target modified files, metadata or directory entries")
                case("R11.readonly." + entry + "." + str(code), readonly)
        def external(f):
            f.section(f.reports["design"], "단계 결과", "[외부](https://example.invalid/fixture)")
            expect(harness.invoke("check_report_submission", f.args("check_report_submission"),
                                  fault=("external_calls", None)))
        case("R11.external_calls", external)
        def mtime(f):
            import os
            argv = f.args("check_report_submission")
            before = expect(harness.invoke("check_report_submission", argv))
            for path in f.topic.iterdir():
                if path.is_file():
                    os.utime(path, (1, 1))
            require(expect(harness.invoke("check_report_submission", argv)) == before, "mtime influenced result")
            files = [(path, path.read_bytes()) for path in f.topic.iterdir() if path.is_file()]
            for path, _content in files:
                path.unlink()
            for path, content in reversed(files):
                path.write_bytes(content)
            require(expect(harness.invoke("check_report_submission", argv)) == before, "creation order influenced result")
        case("R12.filesystem_order", mtime)

        def preparation_classification(f):
            import io
            import json
            from contextlib import redirect_stdout
            for operation in (lambda: f.replace(f.reports["design"], "ABSENT_FIXTURE_TARGET", "x"),
                              lambda: f.section(f.reports["design"], "ABSENT_FIXTURE_SECTION", "x"),
                              lambda: f.replace_text("original", "ABSENT_FIXTURE_TARGET", "x"),
                              lambda: f.transform(f.reports["design"], lambda content: content)):
                probe = Results()
                probe.case("preparation", operation)
                output = io.StringIO()
                with redirect_stdout(output):
                    code = probe.emit(True)
                data = json.loads(output.getvalue())
                require(code == 2 and data["checks"][0]["issues"][0]["kind"] == "error",
                        "fixture preparation must be an execution error")
            probe = Results()
            probe.case("mismatch", lambda: require(False, "observed contract mismatch"))
            with redirect_stdout(io.StringIO()):
                code = probe.emit(True)
            require(code == 1 and probe.checks[0]["issues"][0]["kind"] == "violation",
                    "target expectation mismatch must remain a violation")
        case("R13.preparation_classification", preparation_classification)


if __name__ == "__main__":
    raise SystemExit(run_check(check))
