#!/usr/bin/env python3
"""Check local link targets and Markdown fragments in a skill directory."""

import argparse
from collections import Counter, deque
import json
from html.parser import HTMLParser
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

REFERENCE = "standards/skills/skill-validation.md#구조-검증"
PATH_BASE = "standards/skills/skill-content.md#단계적-공개"
ANCHORS = "standards/skills/skill-validation.md#로컬-markdown-절-링크의-기계-판정"
ANCHOR_POLICY = "aster-markdown-headings-v1"
PRESERVATION = "standards/skills/skill-validation.md#완료-보고서의-로컬-참조"


class PreservationError(ValueError):
    """A local reference cannot be preserved by this repository."""


class Preservation:
    """Read-only repository boundary checks; untracked files need a later commit."""

    def __init__(self, directory):
        self.repository = directory.resolve(strict=True)
        self.repository = Path(os.fsdecode(self.git("rev-parse", "--show-toplevel")).rstrip("\n"))
        self.tracked = set(self.names(self.git("ls-files", "--cached", "-z")))
        self.untracked = set()
        self.cache = {}

    def git(self, *args, input=None, accepted=(0,)):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repository), *args], input=input,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OSError(f"Git 조회 실패: {exc}") from exc
        if result.returncode not in accepted:
            raise OSError(f"Git 조회 실패 ({result.returncode}): {os.fsdecode(result.stderr).strip()}")
        return result.stdout

    @staticmethod
    def names(raw):
        return [os.fsdecode(name) for name in raw.split(b"\0") if name]

    def relative(self, path):
        try:
            name = path.relative_to(self.repository)
        except ValueError as exc:
            raise PreservationError("참조가 저장소 밖으로 나갑니다.") from exc
        if ".git" in name.parts:
            raise PreservationError("Git 내부 메타데이터는 보존 자료가 아닙니다.")
        return name.as_posix()

    def git_state(self, path):
        name = self.relative(path)
        if name not in self.cache:
            ignored = self.git("check-ignore", "--stdin", "-z",
                               input=os.fsencode(name) + b"\0", accepted=(0, 1))
            if ignored:
                raise PreservationError("Git 추적에서 제외된 자료를 참조합니다.")
            if path.is_dir():
                entries = self.names(self.git("ls-files", "--cached", "--others",
                                             "--exclude-standard", "-z", "--",
                                             ":(literal)" + name))
                entries = [entry for entry in entries if (self.repository / entry).exists()]
                if not entries:
                    raise PreservationError("디렉토리에 Git으로 보존할 파일이 없습니다.")
            else:
                entries = [name]
            pending = set(entries) - self.tracked
            self.untracked.update(pending)
            self.cache[name] = "untracked" if pending else "tracked"
        return self.cache[name]

    def path(self, target):
        resolved = target.resolve(strict=True)
        self.relative(resolved)
        pending = deque(target.relative_to(self.repository).parts)
        cursor, links = self.repository, 0
        states = []
        while pending:
            part = pending.popleft()
            if part == ".":
                continue
            if part == "..":
                cursor = cursor.parent
                self.relative(cursor)
                continue
            cursor = cursor / part
            self.relative(cursor)
            if cursor.is_symlink():
                links += 1
                if links > 40:
                    raise PreservationError("심볼릭 링크 연결이 너무 깊습니다.")
                destination = os.readlink(cursor)
                if Path(destination).is_absolute() or PureWindowsPath(destination).is_absolute():
                    raise PreservationError("절대 경로를 사용하는 심볼릭 링크는 보존 참조로 사용할 수 없습니다.")
                states.append(self.git_state(cursor))
                pending.extendleft(reversed(Path(destination).parts))
                cursor = cursor.parent
        states.append(self.git_state(resolved))
        return dict(repository_target=self.relative(resolved),
                    git_state="untracked" if "untracked" in states else "tracked",
                    needs_commit="untracked" in states)

    def reference(self, source, destination):
        item = dict(destination=destination, target=None, resolved_target=None,
                    fragment=None, fragment_checked=False, basis=PRESERVATION)
        try:
            parts = urlsplit(destination)
            decoded = unquote(parts.path, encoding="utf-8", errors="strict")
            if (parts.scheme.lower() == "file"
                    or (not destination.startswith("//") and PureWindowsPath(destination).is_absolute())
                    or (not parts.scheme and not parts.netloc and Path(decoded).is_absolute())):
                raise PreservationError("로컬 절대 경로나 file URI 대신 저장소 상대 링크를 사용해야 합니다.")
            if parts.scheme or parts.netloc or destination.startswith("//"):
                return None
            target = source if not decoded else source.parent / decoded
            item.update(target=str(target), fragment=parts.fragment or None)
            details = self.path(target)
            return details
        except (PreservationError, ValueError, UnicodeError, FileNotFoundError, NotADirectoryError) as exc:
            item.update(status="FAIL", id="reference.preservation", message=str(exc))
        except (OSError, RuntimeError) as exc:
            item.update(status="ERROR", id="reference.preservation.read", message=str(exc))
        return item


def markdown_body(text):
    """Mask YAML frontmatter while retaining original Markdown line numbers."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].rstrip() == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip() == "---":
                return "\n" * (index + 1) + "".join(lines[index + 1:])
        raise ValueError("YAML 프론트매터의 종료 구분자가 없습니다.")
    return text


def extract_links(tokens):
    """Yield destinations and containing-block positions, never invented exact lines."""
    enclosing_line = None
    for block in tokens:
        if block.map:
            enclosing_line = block.map[0] + 1
        if block.type != "inline":
            continue
        # Table-cell inline tokens have no map; their row's map supplies context.
        line = block.map[0] + 1 if block.map else enclosing_line
        for token in block.children or []:
            if token.type == "link_open":
                yield token.attrGet("href"), "link", line
            elif token.type == "image":
                # Image children form alt text, not additional navigable links.
                yield token.attrGet("src"), "image", line


def inline_text(tokens):
    """Use rendered textual content, not Markdown formatting or HTML tags."""
    return "".join(
        inline_text(token.children or []) if token.type == "image" else
        token.content if token.type in ("text", "code_inline") else
        " " if token.type in ("softbreak", "hardbreak") else ""
        for token in tokens
    )


class ExplicitAnchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value and (name == "id" or (tag == "a" and name == "name")):
                self.anchors.add(value)


def collect_anchors(tokens):
    """Apply the documented policy in document order; custom IDs do not number headings."""
    automatic, html = set(), ExplicitAnchors()
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = inline_text(tokens[index + 1].children or []).strip().lower()
            base = "".join(
                "-" if char == " " else char for char in title
                if char in " -_" or unicodedata.category(char)[0] in "LMN"
            )
            anchor, suffix = base, 0
            while anchor in automatic:
                suffix += 1
                anchor = f"{base}-{suffix}"
            automatic.add(anchor)
        for part in [token, *(token.children or [])]:
            if part.type in ("html_block", "html_inline"):
                html.feed(part.content)
    html.close()
    return automatic | html.anchors


def check_fragment(item, target, load_document):
    item.update(basis=ANCHORS, anchor_policy=ANCHOR_POLICY)
    try:
        encoded = item["fragment"]
        if re.search(r"%(?![0-9a-fA-F]{2})", encoded):
            raise ValueError("fragment의 percent escape가 올바르지 않습니다.")
        fragment = unquote(encoded, encoding="utf-8", errors="strict")
        if "\0" in fragment:
            raise ValueError("fragment에 NUL을 사용할 수 없습니다.")
        item["fragment_decoded"] = fragment
    except (ValueError, UnicodeError) as exc:
        item.update(status="FAIL", id="reference.fragment.encoding", message=str(exc))
        return item
    if item["target_kind"] != "file" or target.suffix.lower() != ".md":
        item.update(status="UNCHECKED", id="reference.fragment.unsupported",
                    message="Markdown 파일 이외 대상의 fragment는 판정하지 않습니다.")
        return item
    try:
        anchors = load_document(target)[1]
    except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
        item.update(status="ERROR", id="reference.fragment.read",
                    message=f"절 확인용 문서를 읽거나 파싱할 수 없습니다: {exc}")
        return item
    found = fragment in anchors
    item.update(status="PASS" if found else "FAIL", id="reference.fragment",
                fragment_checked=True, matched_anchor=fragment if found else None,
                message="대상 문서의 앵커가 존재합니다." if found else "대상 문서에 지정한 앵커가 없습니다.")
    return item


def check_destination(source, destination, load_document):
    """Check filesystem existence before interpreting a local Markdown fragment."""
    item = dict(destination=destination, target=None, resolved_target=None,
                fragment=None, fragment_checked=False, basis=REFERENCE)
    try:
        parts = urlsplit(destination)
        item["fragment"] = parts.fragment or None
        if parts.scheme or parts.netloc or destination.startswith("//"):
            item.update(status="SKIP", id="reference.scheme",
                        message="외부 URL/별도 URI 스킴은 로컬 파일 검사 범위 밖입니다.")
            return item
        decoded = unquote(parts.path, encoding="utf-8", errors="strict")
        target = source if not decoded else source.parent / decoded
        item["target"] = str(target)
        mode = target.stat().st_mode
        item["resolved_target"] = str(target.resolve(strict=True))
        if stat.S_ISREG(mode) or stat.S_ISDIR(mode):
            item.update(status="PASS", id="reference.exists",
                        target_kind="directory" if stat.S_ISDIR(mode) else "file",
                        message="로컬 대상이 존재합니다. 쿼리의 동적 의미는 검사하지 않습니다.")
            if parts.fragment:
                return check_fragment(item, target, load_document)
        else:
            item.update(status="FAIL", id="reference.kind",
                        message="대상이 일반 파일이나 디렉토리가 아닙니다.")
    except (FileNotFoundError, NotADirectoryError):
        item.update(status="FAIL", id="reference.exists", message="로컬 대상이 존재하지 않습니다.")
    except (ValueError, UnicodeError) as exc:
        item.update(status="FAIL", id="reference.path", message=f"경로를 해석할 수 없습니다: {exc}")
    except (OSError, RuntimeError) as exc:
        item.update(status="ERROR", id="reference.access", message=f"대상을 확인할 수 없습니다: {exc}")
    return item


def check_references(directory, *, completion_report=False):
    # Preserve '..' until filesystem resolution; a preceding component may be
    # a symlink, so lexical normalization can select the wrong directory.
    root = Path(directory).absolute()
    checks, documents = [], []
    preservation = None

    def problem(check_id, status, message, source=None):
        checks.append(dict(id=check_id, status=status, message=message,
                           source=str(source or root), block_line=None, basis=REFERENCE))

    def report():
        counts = Counter(item["status"] for item in checks)
        if counts["ERROR"] or counts["UNCHECKED"]:
            status, code = "INCOMPLETE", 2
        elif counts["FAIL"]:
            status, code = "FAIL", 1
        else:
            status, code = "PASS", 0
        result = dict(root=str(root), scope=("completion-report-local-references" if completion_report
                                           else "markdown-local-targets-and-fragments"),
                    anchor_policy=ANCHOR_POLICY,
                    status=status, exit_code=code, documents=documents,
                    counts={key: counts[key] for key in ("PASS", "FAIL", "SKIP", "UNCHECKED", "ERROR")},
                    links_extracted=sum("destination" in item for item in checks),
                    checks=checks)
        if completion_report:
            result["preservation"] = dict(
                repository=str(preservation.repository) if preservation else None,
                untracked_files=sorted(preservation.untracked) if preservation else [],
                limits="참조 경로만 검사합니다. 커밋 여부, 본문 완결성 및 실제 승인은 별도 확인합니다.",
            )
        return result

    try:
        if not root.is_dir():
            problem("target.directory", "ERROR", "스킬 디렉토리를 찾을 수 없습니다.")
            return report()
    except OSError as exc:
        problem("target.directory", "ERROR", str(exc))
        return report()
    if completion_report:
        try:
            preservation = Preservation(root)
            root = root.resolve(strict=True)
        except (OSError, ValueError, RuntimeError) as exc:
            problem("preservation.repository", "ERROR", str(exc))
            return report()
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        problem("dependency.markdown", "ERROR", "markdown-it-py가 필요합니다. requirements.txt를 확인하십시오.")
        return report()
    parser = MarkdownIt("commonmark").enable("table")
    # This checker never renders or executes links. Recognize all schemes so
    # that even file:/custom: destinations appear explicitly as excluded.
    parser.validateLink = lambda destination: True
    cache = {}

    def load_document(source):
        # Cache content by real file; relative links still use their source location.
        key = source.resolve(strict=True)
        if key not in cache:
            tokens = parser.parse(markdown_body(source.read_text(encoding="utf-8-sig")))
            cache[key] = (tokens, collect_anchors(tokens))
        return cache[key]

    def walk_error(exc):
        problem("scan.read", "ERROR", f"디렉토리를 읽을 수 없습니다: {exc}", exc.filename)

    paths = []
    for parent, dirs, files in os.walk(root, onerror=walk_error, followlinks=False):
        dirs.sort()
        for name in dirs[:]:
            child = Path(parent) / name
            try:
                linked = child.is_symlink()
            except OSError as exc:
                dirs.remove(name)
                problem("scan.read", "ERROR", f"디렉토리를 확인할 수 없습니다: {exc}", child)
                continue
            if linked:
                dirs.remove(name)
                problem("scan.symlink", "UNCHECKED", "하위 심볼릭 링크 디렉토리는 재귀 탐색하지 않았습니다.", child)
        paths.extend(Path(parent) / name for name in sorted(files)
                     if Path(name).suffix.lower() == ".md")
    if not paths:
        problem("scan.empty", "ERROR", "검사할 Markdown 파일을 찾지 못했습니다.")
    for source in sorted(paths):
        document = dict(path=str(source), parsed=False, links=0)
        documents.append(document)
        try:
            # Avoid blocking on a FIFO named '*.md'. Follow file symlinks only.
            if not source.is_file():
                problem("document.file", "ERROR", "Markdown 대상이 읽을 수 있는 일반 파일이 아닙니다.", source)
                continue
            if preservation:
                try:
                    document.update(preservation.path(source))
                except PreservationError as exc:
                    problem("document.preservation", "FAIL", str(exc), source)
                    continue
            links = list(extract_links(load_document(source)[0]))
        except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
            problem("document.read", "ERROR", f"Markdown을 읽거나 파싱할 수 없습니다: {exc}", source)
            continue
        document.update(parsed=True, links=len(links))
        for destination, kind, line in links:
            details = preservation.reference(source, destination) if preservation else None
            if details and "status" in details:
                item = details
            else:
                item = check_destination(source, destination, load_document)
                if details:
                    item.update(details)
            item.update(source=str(source), block_line=line, kind=kind, path_basis=PATH_BASE)
            checks.append(item)
    return report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="검사할 스킬 또는 완료 보고서 묶음 디렉토리")
    parser.add_argument("--completion-report", action="store_true",
                        help="완료 보고서의 저장소 참조 경계와 Git 제외 여부도 검사")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과 출력")
    args = parser.parse_args(argv)
    result = check_references(args.directory, completion_report=args.completion_report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} {result['root']} ({result['scope']})")
        print(f"Markdown {len(result['documents'])}개, 추출 링크 {result['links_extracted']}개, {result['counts']}")
        for item in result["checks"]:
            line = f":{item['block_line']} (블록 시작)" if item["block_line"] else ""
            print(f"  {item['status']} {item['source']}{line} [{item['id']}]")
            if "destination" in item:
                print(f"    {item['destination']} -> {item['target'] or '(로컬 검사 제외)'}")
            print(f"    {item['message']}")
        print(f"범위: 로컬 링크 대상과 Markdown 절({ANCHOR_POLICY}). 외부 URL/일반 텍스트 경로는 미검사입니다.")
        if args.completion_report:
            preservation = result["preservation"]
            print(preservation["limits"])
            print(f"커밋 필요 파일 {len(preservation['untracked_files'])}개: {preservation['untracked_files']}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
