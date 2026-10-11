"""Shared fixtures and reporting for independent knowledge-discovery push checks."""

import argparse
from contextlib import contextmanager, redirect_stdout
from datetime import datetime
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from repository_support import Repository, SKILL, Violation, git_environment

sys.dont_write_bytecode = True

ENTRYPOINTS = {
    "inspect": "inspect_inputs", "start": "start_run", "read": "read_source",
    "propose": "propose_candidates", "approve": "approve_candidates",
    "save-topic": "save_topic", "status": "run_status",
}


def run_process(*args, **kwargs):
    kwargs.setdefault("timeout", 10)
    environment = git_environment()
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    kwargs.setdefault("env", environment)
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(*args, **kwargs)


class FixedClock:
    @staticmethod
    def now():
        return datetime(2026, 10, 11, 23, 59, 59).astimezone()


@contextmanager
def snapshot(repository):
    """Materialize only this skill, with no checkout or writes to the input repository."""
    parent = Path(tempfile.gettempdir()).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="syringa-check-", dir=parent) as folder:
        root = Path(folder)
        for relative in repository.files():
            if repository.commit is not None:
                mode, kind, _ = repository.entries[relative]
                if kind != "blob" or mode not in ("100644", "100755"):
                    raise OSError("실행용 사본에는 일반 파일이 필요합니다: " + relative)
            elif (repository.root / relative).is_symlink():
                raise OSError("실행용 사본의 링크는 검사할 수 없습니다: " + relative)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(repository.read(relative))
        runs = root / "runs"
        runs.mkdir()
        prior_env = os.environ.get("TMPDIR")
        prior_temp = tempfile.tempdir
        module_names = set(ENTRYPOINTS.values()) | {
            "runtime_common", "source_access", "run_state", "storage_recovery"}
        prior_modules = {name: sys.modules.pop(name, None) for name in module_names}
        os.environ["TMPDIR"] = str(runs)
        tempfile.tempdir = str(runs)
        try:
            yield root / SKILL
        finally:
            for name, module in prior_modules.items():
                sys.modules.pop(name, None)
                if module is not None:
                    sys.modules[name] = module
            tempfile.tempdir = prior_temp
            if prior_env is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = prior_env


class CheckResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.checks = {}

    def startTest(self, test):
        super().startTest(test)
        self.checks[test.id()] = {"id": test.id().split(".")[-1], "passed": True, "issues": []}

    def issue(self, test, error, kind):
        # Subtests belong to the surrounding persistent test case.
        parent = getattr(test, "test_case", test)
        check = self.checks[parent.id()]
        check["passed"] = False
        check["issues"].append({"kind": kind, "path": SKILL, "line": None,
                                "message": self._exc_info_to_string(error, test)})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.issue(test, error, "violation")

    def addError(self, test, error):
        super().addError(test, error)
        self.issue(test, error, self.error_kind(error))

    @staticmethod
    def error_kind(error):
        violations = (AssertionError, Violation, FileNotFoundError, NotADirectoryError, SyntaxError)
        return "violation" if issubclass(error[0], violations) else "error"

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        if error is not None:
            self.issue(test, error, self.error_kind(error))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        check = self.checks[test.id()]
        check["passed"] = False
        check["issues"].append({"kind": "error", "path": SKILL, "line": None,
                                "message": "Required check was skipped: " + reason})

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.issue(test, error, "violation")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        check = self.checks[test.id()]
        check["passed"] = False
        check["issues"].append({"kind": "error", "path": SKILL, "line": None,
                                "message": "Unexpected-success annotations are not push check criteria"})


def failed_report(identifier, root, revision, error):
    return {"passed": False, "source": {"repository": str(root), "revision": revision},
            "checks": [{"id": identifier, "passed": False, "issues": [
                {"kind": "error", "path": SKILL, "line": None, "message": str(error)}]}]}


def emit(report, as_json):
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(str(report["passed"]).lower())
        for check in report["checks"]:
            print(f"{check['id']}: {str(check['passed']).lower()}")
            for issue in check["issues"]:
                print(f"  {issue['kind']}: {issue['message']}")


def run_check(identifier, test_class, argv=None, *, runtime=True):
    argv = list(sys.argv[1:] if argv is None else argv)

    class Parser(argparse.ArgumentParser):
        def error(self, message):
            emit(failed_report("input", "", None, message), "--json" in argv)
            raise SystemExit(2)

    parser = Parser(description=test_class.__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[4])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--revision")
    mode.add_argument("--working-tree", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = failed_report(identifier, args.repository_root, args.revision, "Check did not run")
    try:
        repository = Repository(args.repository_root, args.revision)
        test_class.repository = repository

        def execute():
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_class)
            if not suite.countTestCases():
                raise ValueError("No checks were selected")
            result = CheckResult()
            with redirect_stdout(io.StringIO()):
                suite.run(result)
            checks = list(result.checks.values())
            return {"passed": bool(checks) and all(check["passed"] for check in checks),
                    "source": {"repository": str(repository.root), "revision": args.revision,
                               "commit": repository.commit,
                               "mode": "working-tree" if args.working_tree else "commit"},
                    "checks": checks}

        if runtime:
            with snapshot(repository) as skill:
                test_class.skill_directory = skill
                report = execute()
        else:
            report = execute()
    except Exception as error:
        report = failed_report(identifier, args.repository_root, args.revision, error)
    emit(report, args.json)
    if report["passed"]:
        return 0
    return 2 if any(issue["kind"] == "error" for check in report["checks"]
                    for issue in check["issues"]) else 1


class RuntimeFixture(unittest.TestCase):
    def setUp(self):
        self.scripts = self.skill_directory / "scripts"
        sys.path.insert(0, str(self.scripts))
        self.addCleanup(sys.path.remove, str(self.scripts))
        self.commands = {name: importlib.import_module(module) for name, module in ENTRYPOINTS.items()}
        self.common = importlib.import_module("runtime_common")
        self.sources = importlib.import_module("source_access")
        self.state_store = importlib.import_module("run_state")
        self.storage = self.commands["save-topic"]
        self.fixture = tempfile.TemporaryDirectory(prefix="syringa-runtime-test-")
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q", str(self.repo))
        self.source = self.root / "materials"
        self.source.mkdir()
        self.first = self.source / "mixed.md"
        self.first.write_text("Rust: match value { _ => () }\nSQL: BEGIN; COMMIT;\n", encoding="utf-8")
        self.second = self.source / "detail.rs"
        self.second.write_text("let name = String::new();\n", encoding="utf-8")
        self.other = self.root / "outside.md"
        self.other.write_text("outside\n", encoding="utf-8")
        self.request = {
            "targets": [str(self.source)], "output_root": str(self.repo),
            "files": [str(self.first), str(self.second)], "scope_confirmation": "두 파일만 분석",
            "model": {"name": "test", "effort": "medium", "approval": "시험 승인 기록",
                      "verification": "user-confirmed"},
        }
        self.proposal = {"topics": [
            {"id": "rust", "title": "Rust", "candidates": [
                {"id": "ownership", "keyword": "소유권", "summary": "값의 수명 관리"},
                {"id": "matching", "keyword": "패턴 매칭", "summary": "형태에 따른 분기"}]},
            {"id": "postgresql", "title": "PostgreSQL", "candidates": [
                {"id": "transaction", "keyword": "트랜잭션", "summary": "작업의 묶음"}]}]}


    @staticmethod
    def git(*args):
        return run_process(["git", *args], check=True, capture_output=True, text=True)


    def control(self, value):
        path = self.root / "control.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return str(path)


    def command(self, name, run=None, value=None, **options):
        args = argparse.Namespace(command=name, **options)
        if run is not None:
            args.run = str(run)
        if value is not None:
            args.input = self.control(value)
        return self.commands[name].execute(args)


    def begin(self, request=None):
        result = self.command("start", value=self.request if request is None else request)
        run = Path(result["run"])
        self.addCleanup(shutil.rmtree, run, True)
        return run


    def approved(self, ids=None):
        run = self.begin()
        proposed = self.command("propose", run, self.proposal)
        self.command("approve", run, {"proposal_digest": proposed["proposal_digest"],
                                     "selected_ids": ["ownership", "transaction"] if ids is None else ids,
                                     "user_response": "matching 제외"})
        return run


    @staticmethod
    def detail(topic="rust"):
        if topic == "rust":
            return {"topic_id": topic, "concepts": [
                {"candidate_id": "ownership", "explanation": "값의 수명을 관리한다.",
                 "example": {"language": "rust", "text": "let name = String::new();"}}]}
        return {"topic_id": topic, "concepts": [
            {"candidate_id": "transaction", "usage": "작업을 묶는다.",
             "example": {"language": "sql", "text": "BEGIN;\nCOMMIT;"}}]}


    def assert_error(self, code, callable_, *args, **kwargs):
        with self.assertRaises(self.common.DiscoveryError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
