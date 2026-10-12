"""Read-only CLI and result support for the report-check contract, version 1."""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import stat
import sys
from typing import Callable

STAGES = ("discussion", "design", "implementation", "verification", "qa")


class CheckError(Exception):
    """An input, dependency or read error already included in the result."""


class ArgumentError(Exception):
    pass


def inspect_available(callback, *args, **kwargs):
    """Continue independent checks after a read error already recorded by a helper."""
    try:
        return callback(*args, **kwargs)
    except CheckError:
        return None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError(message)


class Result:
    def __init__(self, checker):
        self.checker = checker
        self.inputs = {}
        self.items = []
        self.files_read = set()
        self.runtime = {"python": platform.python_version(),
                        "packages": {"PyYAML": None, "markdown-it-py": None}}

    def add(self, rule, status, reason, path=None, line=None):
        self.items.append({
            "id": rule, "path": str(path) if path is not None else None,
            "line": line, "status": status,
            "value": {"pass": True, "fail": False}.get(status), "reason": reason,
        })

    def check(self, rule, condition, reason, path=None, line=None):
        self.add(rule, "pass" if condition else "fail", reason, path, line)
        return bool(condition)

    def error(self, rule, reason, path=None, line=None):
        self.add(rule, "error", reason, path, line)

    def na(self, rule, reason, path=None):
        self.add(rule, "not_applicable", reason, path)

    def data(self):
        items = sorted(self.items, key=lambda item: (
            item["id"], (item["path"] is not None, item["path"] or ""),
            (item["line"] is not None, item["line"] or 0), item["reason"],
        ))
        counts = Counter(item["status"] for item in items)
        code = 2 if counts["error"] else 1 if counts["fail"] else 0
        return {
            "contract_version": 1, "checker": self.checker, "inputs": self.inputs,
            "runtime": self.runtime, "outcome": ("pass", "fail", "error")[code],
            "exit_code": code, "files_read": sorted(self.files_read), "items": items,
            "counts": {key: counts[key] for key in ("pass", "fail", "error", "not_applicable")},
        }

    def emit(self, as_json):
        data = self.data()
        if as_json:
            print(json.dumps(data, ensure_ascii=False, sort_keys=True))
        else:
            print(f"checker: {self.checker}; contract_version: 1")
            print("inputs: " + json.dumps(self.inputs, ensure_ascii=False, sort_keys=True))
            print("runtime: " + json.dumps(self.runtime, ensure_ascii=False, sort_keys=True))
            for item in data["items"]:
                location = item["path"] or "-"
                if item["line"] is not None:
                    location += f":{item['line']}"
                print(f"{item['status']} {item['id']} {location}: {item['reason']}")
            print("files_read: " + json.dumps(data["files_read"], ensure_ascii=False))
            print("counts: " + json.dumps(data["counts"], sort_keys=True))
            print(f"outcome: {data['outcome']}; exit_code: {data['exit_code']}")
        return data["exit_code"]


def within(path, parent):
    return path == parent or parent in path.parents


def lexical_path(value, result, key):
    path = Path(value)
    # Examine the supplied spelling before pathlib can discard empty/dot components.
    components = value.split("/")[1:]
    if not path.is_absolute() or any(part in (".", "..") for part in components):
        result.error("input.path", f"{key}: absolute path without dot components required", path)
        raise CheckError
    return path


def resolve_path(path, result):
    try:
        return path.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        result.error("runtime.path", f"cannot resolve path: {exc}", path)
        raise CheckError from exc


def file_kind(path, result):
    try:
        mode = path.stat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    except (OSError, ValueError) as exc:
        result.error("runtime.access", f"cannot inspect path: {exc}", path)
        raise CheckError from exc
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    return "other"


def present(path, result):
    try:
        path.lstat()
        return True
    except (FileNotFoundError, NotADirectoryError):
        return False
    except (OSError, ValueError) as exc:
        result.error("runtime.access", f"cannot inspect path: {exc}", path)
        raise CheckError from exc


def list_directory(path, result):
    if path.is_symlink():
        result.error("runtime.directory", "required directory is a symlink; not traversed", path)
        raise CheckError
    try:
        return sorted(path.iterdir(), key=lambda child: child.name)
    except OSError as exc:
        result.error("runtime.directory", f"cannot list directory: {exc}", path)
        raise CheckError from exc


def read_text(path, result):
    try:
        with path.open("r", encoding="utf-8-sig") as stream:
            text = stream.read()
        result.files_read.add(str(path.resolve()))
        return text
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        result.error("runtime.read", f"cannot read UTF-8 file: {exc}", path)
        raise CheckError from exc


def dependencies(result):
    valid = True
    for package, major in (("PyYAML", 6), ("markdown-it-py", 3)):
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            version = None
        result.runtime["packages"][package] = version
        match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.post[0-9]+)?(?:\+[A-Za-z0-9.-]+)?", version or "")
        if not match or int(match[1]) != major:
            result.error("runtime.dependency", f"{package} requires >= {major}.0, < {major + 1}; installed {version}")
            valid = False
    if sys.version_info < (3, 10):
        result.error("runtime.python", "Python >= 3.10 required")
        valid = False
    if not valid:
        raise CheckError
    try:
        import yaml  # noqa: F401
        import markdown_it  # noqa: F401
    except (ImportError, OSError) as exc:
        result.error("runtime.dependency", f"cannot import parser dependency: {exc}")
        raise CheckError from exc


class Context:
    def __init__(self, args, result, first=False):
        self.args = args
        self.result = result
        self.root = lexical_path(args.project_root, result, "project-root")
        self.topic = lexical_path(args.topic_dir, result, "topic-dir")
        if file_kind(self.root, result) != "directory":
            result.error("input.project_root", "project-root must be an existing directory", self.root)
            raise CheckError
        try:
            parts = self.topic.relative_to(self.root).parts
        except ValueError:
            parts = ()
        if len(parts) != 3 or parts[0] != "specs" or any(
            not part or part in (".", "..") or "\\" in part for part in parts[1:]
        ):
            result.error("input.topic_dir", "topic-dir must be project-root/specs/<major>/<topic>", self.topic)
            raise CheckError
        self.real_root = resolve_path(self.root, result)
        self.real_topic = resolve_path(self.topic, result)
        if not within(self.real_topic, self.real_root):
            result.error("input.topic_dir", "topic-dir resolves outside project-root", self.topic)
            raise CheckError
        self.manifest_path = self.topic.parent / "freight-manifest.md"
        if not first and file_kind(self.topic, result) != "directory":
            result.error("input.topic_dir", "existing topic directory required", self.topic)
            raise CheckError
        self.docs = {}

    def document(self, path):
        from _check_markdown import Document
        if path not in self.docs:
            self.docs[path] = Document(path, read_text(path, self.result))
        return self.docs[path]

    def argument_file(self, value, key, review=False):
        path = lexical_path(value, self.result, key)
        valid_parent = path.parent == self.topic or path.parent.parent == self.topic
        if not valid_parent or not within(resolve_path(path, self.result), self.real_topic):
            self.result.error("input.file_scope", f"{key}: file outside root or immediate bundle scope", path)
            raise CheckError
        if file_kind(path, self.result) != "file":
            self.result.error("input.file", f"{key}: existing regular file required", path)
            raise CheckError
        from _check_records import report_candidate
        if (review and path.suffix != ".md") or (not review and not report_candidate(path.name)):
            self.result.error("input.file", f"{key}: unsupported report/review filename", path)
            raise CheckError
        return path


def command(checker: str, extra: tuple[str, ...], run: Callable, optional=()):
    """Bootstrap one independent entry point; no purpose/mode CLI is exposed."""
    result = Result(checker)
    parser = Parser(prog=checker + ".py", allow_abbrev=False, add_help=False,
                    description="Read-only report checks (contract version 1).")
    for name in ("project-root", "topic-dir") + extra:
        parser.add_argument("--" + name, required=True)
    for name in optional:
        parser.add_argument("--" + name)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--help", action="store_true")
    argv = sys.argv[1:]
    if argv == ["--help"]:
        parser.print_help()
        return 0
    # Keep explicit input values even when parsing fails. Never manufacture defaults.
    names = {"--" + name for name in ("project-root", "topic-dir") + extra + optional}
    seen = set()
    duplicate = False
    for index, arg in enumerate(argv):
        flag, separator, value = arg.partition("=")
        if flag.startswith("--"):
            if flag in seen:
                duplicate = True
            seen.add(flag)
        if flag in names:
            if separator:
                result.inputs[flag[2:].replace("-", "_")] = value
            elif index + 1 < len(argv) and not argv[index + 1].startswith("--"):
                result.inputs[flag[2:].replace("-", "_")] = argv[index + 1]
    as_json = "--json" in argv
    try:
        if duplicate:
            raise ArgumentError("duplicate option")
        args = parser.parse_args(argv)
        as_json = args.json
        if args.help:
            parser.print_help()
            return 0
        dependencies(result)
        run(args, result)
    except ArgumentError as exc:
        result.error("input.arguments", str(exc))
    except CheckError:
        pass
    except Exception as exc:
        # Unanticipated parser/OS failures must never be reported as successful checks.
        result.error("runtime.unexpected", f"{type(exc).__name__}: {exc}")
    return result.emit(as_json)
