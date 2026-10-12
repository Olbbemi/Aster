"""Common reporting, isolated fixtures and public-entrypoint test support."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

from repository_support import (APPROVAL_AREAS, DEFERRED_AREAS, REPORT_AREAS,
                                REVIEW_AREAS, SKILL, STAGES, Repository, Violation, git_environment)

sys.dont_write_bytecode = True


class ArgumentError(ValueError):
    pass


class PreparationError(Exception):
    """The test input could not be prepared; no target judgment was made."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError(message)


class Results:
    def __init__(self):
        self.checks = []
        self.excluded = []

    def case(self, identifier, function, path=None, line=None):
        issues = []
        try:
            function()
        except (AssertionError, Violation) as exc:
            issues.append({"kind": "violation", "path": str(path) if path is not None else None,
                           "line": line, "message": str(exc) or "contract condition is false"})
        except Exception as exc:
            issues.append({"kind": "error", "path": str(path) if path is not None else None,
                           "line": line, "message": f"{type(exc).__name__}: {exc}"})
        self.checks.append({"id": identifier, "passed": not issues, "issues": issues})

    def emit(self, as_json):
        for check in self.checks:
            check["issues"].sort(key=lambda item: (item["kind"], item["path"] or "",
                                                  item["line"] or 0, item["message"]))
        checks = sorted(self.checks, key=lambda check: check["id"])
        errors = any(issue["kind"] == "error" for check in checks for issue in check["issues"])
        code = 2 if errors else 1 if any(not check["passed"] for check in checks) else 0
        data = {"passed": code == 0, "checks": checks,
                "excluded": sorted(self.excluded, key=lambda item: (item["path"], item["reason"]))}
        if as_json:
            print(json.dumps(data, ensure_ascii=False, sort_keys=True))
        else:
            print("true" if data["passed"] else "false")
            for check in checks:
                print(("OK " if check["passed"] else "FAIL ") + check["id"])
                for issue in check["issues"]:
                    position = issue["path"] or "-"
                    if issue["line"] is not None:
                        position += ":" + str(issue["line"])
                    print(f"  {issue['kind']} {position}: {issue['message']}")
            for excluded in data["excluded"]:
                print(f"EXCLUDED {excluded['path']}: {excluded['reason']}")
        return code


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def dependencies():
    if sys.version_info < (3, 10):
        raise OSError("Python >= 3.10 is required")
    for package, major in (("PyYAML", 6), ("markdown-it-py", 3)):
        version = importlib.metadata.version(package)
        match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.post\d+)?(?:\+[A-Za-z0-9.-]+)?", version)
        if match is None or int(match[1]) != major:
            raise OSError(f"unsupported {package} version: {version}")
    import yaml  # noqa: F401
    import markdown_it  # noqa: F401


def run_check(function, argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    results = Results()
    as_json = "--json" in arguments
    parser = Parser(allow_abbrev=False, add_help=False, description=__doc__)
    parser.add_argument("--repository-root", default=str(Path(__file__).resolve().parents[4]))
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--revision")
    selection.add_argument("--working-tree", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--help", action="store_true")
    if arguments == ["--help"]:
        parser.print_help()
        return 0
    try:
        seen = set()
        for value in arguments:
            option = value.partition("=")[0]
            if option.startswith("--"):
                if option in seen:
                    raise ArgumentError("duplicate option: " + option)
                seen.add(option)
        args = parser.parse_args(arguments)
        as_json = args.json
        if args.help:
            parser.print_help()
            return 0
        root = Path(args.repository_root)
        if not root.is_absolute():
            raise ArgumentError("repository-root must be absolute")
        dependencies()
        repository = Repository(root, args.revision)
    except Exception as exc:
        def fail(error=exc):
            raise OSError(str(error)) from error
        results.case("input.or_environment", fail)
    else:
        results.case("execution", lambda: function(repository, results))
    return results.emit(as_json)


@dataclass
class Invocation:
    code: int
    stdout: str
    stderr: str

    def json(self):
        try:
            value = json.loads(self.stdout)
        except (ValueError, TypeError) as exc:
            raise AssertionError("target did not return one JSON object: " + self.stdout[:300]) from exc
        require(isinstance(value, dict), "target JSON must be an object")
        return value


def validate_runtime(call, entrypoint=None):
    data = call.json()
    expected = {"contract_version", "checker", "inputs", "runtime", "outcome", "exit_code",
                "files_read", "items", "counts"}
    require(expected <= data.keys(), "target result lacks required fields")
    require(type(data["contract_version"]) is int and data["contract_version"] == 1, "contract version mismatch")
    require(type(data["exit_code"]) is int and data["exit_code"] in (0, 1, 2), "invalid target exit_code")
    require(call.code == data["exit_code"], "process and JSON exit codes disagree")
    require(data["outcome"] == ("pass", "fail", "error")[call.code], "outcome and exit code disagree")
    require(isinstance(data["checker"], str) and (entrypoint is None or data["checker"] == entrypoint), "wrong checker")
    require(isinstance(data["inputs"], dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in data["inputs"].items()), "explicit inputs must be string values")
    require("json" not in data["inputs"] and "help" not in data["inputs"], "output options are not inputs")
    runtime = data["runtime"]
    require(isinstance(runtime, dict) and isinstance(runtime.get("python"), str)
            and isinstance(runtime.get("packages"), dict), "invalid runtime fields")
    require({"PyYAML", "markdown-it-py"} <= runtime["packages"].keys(), "missing package version fields")
    require(all(v is None or isinstance(v, str) for v in runtime["packages"].values()), "invalid package version")
    require(isinstance(data["items"], list), "items must be a list")
    status_values = {"pass": True, "fail": False, "error": None, "not_applicable": None}
    for item in data["items"]:
        require(isinstance(item, dict) and {"id", "path", "line", "status", "value", "reason"} <= item.keys(), "invalid result item")
        require(isinstance(item["id"], str) and bool(item["id"]), "missing stable rule ID")
        require(item["status"] in status_values and item["value"] is status_values[item["status"]], "status/value mismatch")
        require(item["path"] is None or isinstance(item["path"], str), "invalid item path")
        require(item["line"] is None or (type(item["line"]) is int and item["line"] > 0), "invalid item line")
        require(isinstance(item["reason"], str) and bool(item["reason"].strip()), "missing item reason")
    key = lambda item: (item["id"], (item["path"] is not None, item["path"] or ""),
                        (item["line"] is not None, item["line"] or 0), item["reason"])
    require(data["items"] == sorted(data["items"], key=key), "unstable item ordering")
    counts = Counter(item["status"] for item in data["items"])
    require(isinstance(data["counts"], dict) and set(data["counts"]) == set(status_values), "invalid counts")
    require(all(type(data["counts"][status]) is int and data["counts"][status] == counts[status]
                for status in status_values), "counts do not match items")
    code = 2 if counts["error"] else 1 if counts["fail"] else 0
    require(code == call.code, "result severity is incorrect")
    paths = data["files_read"]
    require(isinstance(paths, list) and all(isinstance(p, str) and Path(p).is_absolute() for p in paths), "invalid files_read")
    require(paths == sorted(set(paths)), "files_read is not unique and sorted")
    require(all(str(Path(path).resolve()) == path for path in paths), "files_read is not real paths")
    require(not call.stderr.strip(), "normal result must not include stderr logs: " + call.stderr[:200])
    return data


def expect(call, code=0, category=None, status="fail", forbidden=(), entrypoint=None, rules=()):
    data = validate_runtime(call, entrypoint)
    require(call.code == code, f"expected exit {code}; got {call.code}: " + call.stdout[:900])
    if category:
        require(any(item["id"].split(".")[0] == category and item["status"] == status
                    for item in data["items"]), f"missing {category}/{status}: " + call.stdout[:900])
    for identifier in rules:
        require(any(item["id"] == identifier and item["status"] == status for item in data["items"]),
                f"missing {identifier}/{status}: " + call.stdout[:900])
    for category in forbidden:
        require(not any(item["id"].split(".")[0] == category and item["status"] in ("fail", "error")
                        for item in data["items"]), "out-of-scope failure: " + category)
    return data


@contextmanager
def snapshot(repository):
    with tempfile.TemporaryDirectory(prefix="camellia-check-") as folder:
        root = Path(folder).resolve()
        files = repository.files()
        if not files:
            raise Violation("selected skill source is absent")
        for relative in files:
            mode, kind, _oid = repository.entries[relative]
            if kind != "blob" or mode not in ("100644", "100755"):
                raise OSError("execution snapshot requires regular files: " + relative)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(repository.raw(relative))
            target.chmod(0o755 if mode == "100755" else 0o644)
        yield Harness(root, root / SKILL)


class Harness:
    def __init__(self, root, skill):
        self.root = root
        self.skill = skill

    @contextmanager
    def fixture(self, **kwargs):
        with tempfile.TemporaryDirectory(prefix="consumer-", dir=self.root) as folder:
            yield Fixture(Path(folder), **kwargs)

    def invoke(self, entrypoint, arguments, *, json_output=True, process=False, bytecode=False, fault=None):
        script = self.skill / "scripts" / (entrypoint + ".py")
        if not script.is_file():
            raise Violation("target entrypoint is absent: " + entrypoint)
        argv = [str(value) for value in arguments] + (["--json"] if json_output else [])
        if process:
            environment = git_environment()
            for name in ("PYTHONPATH", "PYTHONHOME"):
                environment.pop(name, None)
            command = [sys.executable] + ([] if bytecode else ["-B"]) + [str(script), *argv]
            call = subprocess.run(command, cwd=self.root, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, encoding="utf-8", timeout=10,
                                  env=environment)
            return Invocation(call.returncode, call.stdout, call.stderr)
        stdout, stderr = io.StringIO(), io.StringIO()
        old_modules = {name: sys.modules.pop(name) for name in tuple(sys.modules) if name.startswith("_check_")}
        old_path, old_argv, old_cwd = list(sys.path), list(sys.argv), Path.cwd()
        old_bytecode = sys.dont_write_bytecode
        code = 0
        try:
            sys.path.insert(0, str(script.parent))
            sys.argv = [str(script), *argv]
            os.chdir(self.root)
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with injected_fault(fault):
                    try:
                        runpy.run_path(str(script), run_name="__main__")
                    except SystemExit as exc:
                        code = exc.code if isinstance(exc.code, int) else 1 if exc.code else 0
        finally:
            sys.path[:] = old_path
            sys.argv[:] = old_argv
            os.chdir(old_cwd)
            sys.dont_write_bytecode = old_bytecode
            for name in tuple(sys.modules):
                if name.startswith("_check_"):
                    sys.modules.pop(name, None)
            sys.modules.update(old_modules)
        return Invocation(code, stdout.getvalue(), stderr.getvalue())


@contextmanager
def injected_fault(fault):
    if fault is None:
        yield
        return
    kind, value = fault
    if kind in ("missing_package", "package_version"):
        original = importlib.metadata.version
        def version(package):
            if package == "PyYAML":
                if kind == "missing_package":
                    raise importlib.metadata.PackageNotFoundError(package)
                return value
            return original(package)
        with patch("importlib.metadata.version", version):
            yield
    elif kind == "import":
        import builtins
        original = builtins.__import__
        def importing(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("injected parser import failure")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", importing):
            yield
    elif kind in ("read", "stat", "list"):
        attribute = {"read": "open", "stat": "stat", "list": "iterdir"}[kind]
        original = getattr(Path, attribute)
        selected = Path(value)
        def access(path, *args, **kwargs):
            if path == selected:
                raise PermissionError("injected file access failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, attribute, access):
            yield
    elif kind == "external_calls":
        def prohibited(*_args, **_kwargs):
            raise AssertionError("target attempted an external call")
        import socket
        with patch("subprocess.Popen", prohibited), patch.object(os, "system", prohibited), \
                patch.object(socket, "create_connection", prohibited), patch.object(socket.socket, "connect", prohibited):
            yield
    else:
        raise OSError("unknown fixture fault: " + kind)


class Fixture:
    def __init__(self, root, *, legacy=False, stages=STAGES, through="design", target_status="in_progress"):
        self.root = root
        self.topic = root / "specs" / "인증 그룹" / "로그인 작업"
        self.topic.mkdir(parents=True)
        self.manifest = self.topic.parent / "freight-manifest.md"
        self.legacy = legacy
        self.stages = tuple(stages)
        self.write_manifest()
        self.reports = {}
        prior = None
        for stage in self.stages:
            path = self.report(stage, status=target_status if stage == through else "completed", base=prior)
            self.reports[stage] = path
            prior = path
            if stage == through:
                break

    def write_manifest(self):
        self.manifest.write_text("# Freight Manifest\n\n## [로그인 작업](로그인%20작업/)\n\n"
                                 "- stages: [" + ", ".join(self.stages) + "]\n- reference_reports: 없음\n", encoding="utf-8")

    def report(self, stage, *, scope=None, status="in_progress", base=None, revision=None,
               bundle=None, keyword=None, body=""):
        scope = self.topic if scope is None else scope
        scope.mkdir(parents=True, exist_ok=True)
        suffix = f"-{revision or 1:03d}" if self.legacy else (f"-rev-{revision:03d}" if revision else "")
        path = scope / f"{stage}-report{suffix}.md"
        base_value = None if base is None else os.path.relpath(base, scope)
        front = "status: " + status + "\nbase_on: " + ("null" if base_value is None else json.dumps(base_value, ensure_ascii=False)) + "\n"
        if bundle is not None:
            front += "bundle: " + json.dumps(bundle) + "\n"
        checklist = "- [ ] 대상 확인\n"
        if status == "completed":
            checklist = self.checked()
        approval = "\n".join("### " + name + "\n\n" for name in APPROVAL_AREAS)
        if stage in ("verification", "qa"):
            value = (keyword or "all_passed") + "\n고정 시험 결과를 확인했다.\n" if status in ("completed", "awaiting_approval") or keyword else "미정\n"
            approval = "### 완료 구분\n\n" + value + "\n" + approval
        sections = {"단계 결과": body, "인계 사항": "", "완료 체크리스트": checklist, "사용자 승인": approval}
        text = "---\n" + front + "---\n\n# 고정 시험 report\n\n"
        text += "\n\n".join("## " + area + "\n\n" + sections[area] for area in REPORT_AREAS) + "\n"
        path.write_text(text, encoding="utf-8")
        return path

    @staticmethod
    def checked(evidence="고정 시험 근거", timestamp="2024-02-29 12:34:56 (KST)"):
        return "- [x] 대상 확인\n  - 확인 근거: " + evidence + "\n\n### 일괄 반영 기록\n\n" \
               "| 묶음 | 대상 항목 | 반영 시각 |\n| --- | --- | --- |\n| B1 | 대상 확인 | " + timestamp + " |\n"

    @staticmethod
    def replace_text(text, before, after, count=-1):
        if before not in text:
            raise PreparationError("fixture mutation target is absent: " + before)
        return text.replace(before, after, count)

    @staticmethod
    def transform(path, operation):
        text = path.read_text(encoding="utf-8")
        changed = operation(text)
        if changed == text:
            raise PreparationError("fixture transformation did not change the input")
        path.write_text(changed, encoding="utf-8")

    @staticmethod
    def replace(path, before, after):
        text = path.read_text(encoding="utf-8")
        path.write_text(Fixture.replace_text(text, before, after), encoding="utf-8")

    @staticmethod
    def section(path, heading, content, level=2):
        text = path.read_text(encoding="utf-8")
        marker = "#" * level + " " + heading + "\n"
        if marker not in text:
            raise PreparationError("fixture section is absent: " + heading)
        head, tail = text.split(marker, 1)
        match = re.search(r"(?m)^#{1," + str(level) + r"} ", tail)
        rest = tail[match.start():] if match else ""
        path.write_text(head + marker + "\n" + content + "\n\n" + rest, encoding="utf-8")

    def args(self, entrypoint, report=None, review=None, stage="design", scope=None, base=None, bundle=None):
        args = ["--project-root", self.root, "--topic-dir", self.topic]
        if entrypoint == "check_stage_entry":
            args += ["--stage", stage, "--scope-dir", scope or self.topic,
                     "--base-report", base if base is not None else "none"]
            if bundle is not None:
                args += ["--bundle-id", bundle]
        elif entrypoint in ("check_report_submission", "check_review_receipt"):
            args += ["--report", report or self.reports.get("design")]
            if entrypoint == "check_review_receipt":
                args += ["--review", review]
        elif entrypoint == "check_task_completion":
            args += ["--qa-report", report or self.reports.get("qa")]
        return [str(value) for value in args]

    def review(self, report=None, *, number=1):
        report = report or self.reports["design"]
        path = report.with_name(report.stem + f"-review-{number:03d}.md")
        path.write_text("# 고정 시험 review\n\n- 검토자: fixture\n- 모델명/버전: 확인 불가\n"
                        "- 검토 대상: " + report.name + "\n\n" +
                        "\n\n".join("## " + area + "\n\n고정 자료\n" for area in REVIEW_AREAS), encoding="utf-8")
        return path

    def deferred(self):
        path = self.topic / "deferred" / "pending.md"
        path.parent.mkdir()
        path.write_text("# 후속 작업\n\n" + "\n\n".join("## " + name + "\n\n고정 자료\n"
                          for name in DEFERRED_AREAS), encoding="utf-8")
        return path

    def bundles(self, *, own_design=False, completed=False, unstarted=False):
        common = self.reports["design"]
        if "status: in_progress" in common.read_text(encoding="utf-8"):
            self.replace(common, "status: in_progress", "status: completed")
        self.section(common, "완료 체크리스트", self.checked())
        rows = []
        records = {}
        for ordinal, name in enumerate(("01-api", "02-store"), 1):
            scope = self.topic / name if not self.legacy else self.topic
            bundle = name.split("-", 1)[1] if self.legacy else None
            source = common
            if own_design:
                source = self.report("design", scope=scope, status="completed", bundle=bundle,
                                     revision=ordinal + 1 if self.legacy else None,
                                     base=self.reports["discussion"] if self.legacy else common)
            target = self.report("implementation", scope=scope, status="completed" if completed else "in_progress",
                                 bundle=bundle, revision=ordinal if self.legacy else None, base=source)
            verif = qa = None
            if completed:
                verif = self.report("verification", scope=scope, status="completed", base=target, bundle=bundle,
                                    revision=ordinal if self.legacy else None)
                qa = self.report("qa", scope=scope, status="completed", base=verif, bundle=bundle,
                                 revision=ordinal if self.legacy else None)
            records[name] = {"design": source, "implementation": target, "verification": verif, "qa": qa}
            link = os.path.relpath(qa or target, self.topic)
            if self.legacy:
                rows.append(f"| {bundle} | fixture | 범위 | 구현부터 | 공통 설계 | [결과]({link}) |")
            else:
                rows.append(f"| {name} | 범위 | 구현부터 | 공통 설계 | {name} | [결과]({link}) |")
        if unstarted:
            rows.append("| 후속 작업 | 범위 | 구현부터 | 공통 설계 | 미시작 | 미시작 |")
        columns = "묶음 | 제목 | 범위/완료 기준 | 의존/진입 | 설계 정본 | 결과 참조" if self.legacy else "묶음 | 범위/완료 기준 | 의존/진입 | 설계 정본 | 디렉토리 | 결과 참조"
        table = "### 작업 묶음표\n\n| " + columns + " |\n| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows)
        self.section(common, "단계 결과", table)
        return records


def tree_state(root):
    entries = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(folder) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                content = os.readlink(path)
            elif path.is_file():
                content = path.read_bytes()
            else:
                content = None
            entries[relative] = (info.st_mode, info.st_mtime_ns, content)
    return entries
