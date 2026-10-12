"""Read selected sources and parse static contracts independently of the skill."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit

SKILL = "plugins/Camellia/skills/code-development"
PLUGIN = "plugins/Camellia"
STAGES = ("discussion", "design", "implementation", "verification", "qa")
ENTRYPOINTS = ("check_task_start", "check_stage_entry", "check_report_submission",
               "check_review_receipt", "check_task_completion")
REPORT_AREAS = ("단계 결과", "인계 사항", "완료 체크리스트", "사용자 승인")
APPROVAL_AREAS = ("사용자 판단", "보완 요청과 처리 결과", "남은 사항과 인계 조건")
REVIEW_AREAS = ("실행 대상과 근거", "검토 범위와 기준", "검토 결과", "확인하지 못한 사항", "종합 의견")
DEFERRED_AREAS = ("필요한 작업", "보류 이유와 현재 범위", "논의 내용과 근거", "재검토 조건과 미결정 사항")


class Violation(ValueError):
    """A documented requirement is false for the selected source."""


def git_environment():
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


class Repository:
    def __init__(self, root, revision=None):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise OSError("repository root must be a directory")
        actual = self.git("rev-parse", "--show-toplevel").decode().strip()
        if Path(actual).resolve() != self.root:
            raise OSError("repository-root must identify the Git root")
        self.commit = None
        self.entries = {}
        self.blobs = {}
        if revision is not None:
            self.commit = self.git("rev-parse", "--verify", "--end-of-options",
                                   revision + "^{commit}").decode().strip()
            for raw in self.git("ls-tree", "-rz", "--full-tree", self.commit).split(b"\0"):
                if raw:
                    meta, path = raw.split(b"\t", 1)
                    mode, kind, oid = meta.decode("ascii").split()
                    self.entries[os.fsdecode(path)] = (mode, kind, oid)
        else:
            base = self.root / PLUGIN
            # Never follow directory links while collecting the selected package.
            if (self.root / "plugins").is_symlink() or base.is_symlink():
                raise OSError("plugin directory must not be a symlink")
            if base.exists():
                def onerror(error):
                    raise error
                for folder, dirs, files in os.walk(base, followlinks=False, onerror=onerror):
                    for name in sorted(dirs + files):
                        path = Path(folder) / name
                        mode = path.lstat().st_mode
                        relative = path.relative_to(self.root).as_posix()
                        if stat.S_ISLNK(mode):
                            entry = ("120000", "blob", None)
                        elif stat.S_ISREG(mode):
                            entry = ("100755" if mode & 0o111 else "100644", "blob", None)
                        elif stat.S_ISDIR(mode):
                            continue
                        else:
                            entry = ("other", "other", None)
                        self.entries[relative] = entry
        self.directories = {""}
        for path in self.entries:
            self.directories.update(str(parent) if str(parent) != "." else ""
                                    for parent in PurePosixPath(path).parents)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                capture_output=True, timeout=10, stdin=subprocess.DEVNULL,
                                env=git_environment())
        if result.returncode:
            raise OSError("Git read failed: " + os.fsdecode(result.stderr).strip())
        return result.stdout

    def files(self, prefix=SKILL):
        return sorted(path for path in self.entries
                      if path == prefix or path.startswith(prefix + "/"))

    def raw(self, path):
        entry = self.entries.get(path)
        if entry is None:
            raise Violation("required source is absent: " + path)
        mode, kind, oid = entry
        if kind != "blob" or mode not in ("100644", "100755", "120000"):
            raise OSError("unsupported source entry: " + path)
        if self.commit is not None:
            if oid not in self.blobs:
                self.blobs[oid] = self.git("cat-file", "blob", oid)
            return self.blobs[oid]
        if mode == "120000":
            return os.fsencode(os.readlink(self.root / path))
        return (self.root / path).read_bytes()

    def resolve(self, path):
        pending = deque(PurePosixPath(path).parts)
        if PurePosixPath(path).is_absolute():
            raise Violation("absolute local reference is not distributable")
        resolved = []
        links = 0
        while pending:
            part = pending.popleft()
            if part in ("", "."):
                continue
            if part == "..":
                if not resolved:
                    raise Violation("reference escapes the repository")
                resolved.pop()
                continue
            candidate = "/".join(resolved + [part])
            if self.entries.get(candidate, (None,))[0] == "120000":
                links += 1
                if links > 40:
                    raise Violation("cyclic local reference")
                target = self.raw(candidate).decode("utf-8")
                if PurePosixPath(target).is_absolute():
                    raise Violation("absolute symlink is not distributable")
                pending.extendleft(reversed(PurePosixPath(target).parts))
            else:
                resolved.append(part)
        return "/".join(resolved)

    def exists(self, path):
        resolved = self.resolve(path)
        return resolved in self.entries or resolved in self.directories

    def read(self, path):
        return self.raw(self.resolve(path))

    def text(self, path):
        return self.read(path).decode("utf-8-sig")


def yaml_mapping(text):
    import yaml

    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        values = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in values
            except TypeError as exc:
                raise Violation("unhashable YAML key") from exc
            if duplicate:
                raise Violation("duplicate YAML key: " + str(key))
            values[key] = loader.construct_object(value_node, deep=deep)
        return values

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try:
        value = yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise Violation("invalid YAML: " + str(exc)) from exc
    if not isinstance(value, dict):
        raise Violation("YAML frontmatter must be a mapping")
    return value


def inline_text(token):
    children = token.children or []
    pieces = []
    for child in children:
        if child.type in ("text", "code_inline"):
            pieces.append(child.content)
        elif child.type == "image":
            pieces.append(inline_text(child) if child.children else child.content)
        elif child.type in ("softbreak", "hardbreak"):
            pieces.append(" ")
    return "".join(pieces)


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    start: int
    end: int
    line: int


class ExplicitAnchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is not None and (name == "id" or (tag == "a" and name == "name")):
                self.values.add(value)

    handle_startendtag = handle_starttag


class Document:
    def __init__(self, text):
        from markdown_it import MarkdownIt
        self.text = text
        self.meta = None
        self.meta_error = None
        self.offset = 0
        lines = text.splitlines(keepends=True)
        if lines and lines[0].strip() == "---":
            close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
            if close is not None:
                try:
                    self.meta = yaml_mapping("".join(lines[1:close]))
                except Violation as exc:
                    self.meta_error = exc
                else:
                    self.offset = close + 1
        parser = MarkdownIt("commonmark").enable("table")
        parser.validateLink = lambda _destination: True
        self.tokens = parser.parse("".join(lines[self.offset:]))
        self.headings = []
        quote_depth = 0
        self.quoted = set()
        for i, token in enumerate(self.tokens):
            if token.type == "blockquote_open":
                quote_depth += 1
            if quote_depth:
                self.quoted.add(i)
            if token.type == "blockquote_close":
                quote_depth -= 1
            if token.type == "heading_open" and i not in self.quoted:
                level = int(token.tag[1:])
                self.headings.append(Heading(level, inline_text(self.tokens[i + 1]).strip(),
                                             i, len(self.tokens), self.line(token)))
        self.headings = [Heading(h.level, h.text, h.start,
                                  next((other.start for other in self.headings[index + 1:]
                                        if other.level <= h.level), len(self.tokens)), h.line)
                         for index, h in enumerate(self.headings)]

    def line(self, token):
        return token.map[0] + self.offset + 1 if token.map else None

    def sections(self, name, level, parent=None):
        return [h for h in self.headings if h.level == level and h.text == name
                and (parent is None or parent.start < h.start < parent.end)]

    def one(self, name, level, parent=None):
        values = self.sections(name, level, parent)
        if len(values) != 1:
            raise Violation(f"expected one H{level} {name}; found {len(values)}")
        return values[0]

    def links(self, section=None):
        start, end = (section.start, section.end) if section else (0, len(self.tokens))
        for index in range(start, end):
            token = self.tokens[index]
            if token.type != "inline":
                continue
            for child in token.children or []:
                if child.type == "link_open":
                    yield child.attrGet("href") or "", self.line(token)
                elif child.type == "image":
                    yield child.attrGet("src") or "", self.line(token)

    def anchors(self):
        used, values = set(), set()
        for index, token in enumerate(self.tokens):
            if token.type == "heading_open":
                name = inline_text(self.tokens[index + 1]).strip().lower()
                stem = "".join("-" if char == " " else char for char in name
                               if char == " " or char in "-_" or unicodedata.category(char)[0] in "LMN")
                anchor, number = stem, 0
                while anchor in used:
                    number += 1
                    anchor = stem + "-" + str(number)
                used.add(anchor)
                values.add(anchor)
            if token.type in ("html_block", "html_inline"):
                parser = ExplicitAnchors()
                parser.feed(token.content)
                values.update(parser.values)
            for child in token.children or []:
                if child.type == "html_inline":
                    parser = ExplicitAnchors()
                    parser.feed(child.content)
                    values.update(parser.values)
        return values

    def tables(self, section):
        tables, rows, cells = [], None, None
        for token in self.tokens[section.start:section.end]:
            if token.type == "table_open":
                rows = []
            elif token.type == "tr_open" and rows is not None:
                cells = []
            elif token.type == "inline" and cells is not None:
                links = [child.attrGet("href") for child in token.children or []
                         if child.type == "link_open"]
                cells.append((inline_text(token).strip(), links))
            elif token.type == "tr_close" and cells is not None:
                rows.append(cells)
                cells = None
            elif token.type == "table_close" and rows is not None:
                tables.append(rows)
                rows = None
        return tables


def link_parts(destination):
    try:
        value = urlsplit(destination)
    except ValueError as exc:
        raise Violation("invalid reference URI") from exc
    if value.scheme or value.netloc:
        return None
    pieces = []
    for encoded in (value.path, value.fragment):
        if re.search(r"%(?![0-9A-Fa-f]{2})", encoded):
            raise Violation("invalid percent escape")
        try:
            decoded = unquote(encoded, encoding="utf-8", errors="strict")
        except UnicodeError as exc:
            raise Violation("invalid UTF-8 in reference") from exc
        if "\0" in decoded:
            raise Violation("NUL in reference")
        pieces.append(decoded)
    return tuple(pieces)


def local_target(repository, source, destination):
    parts = link_parts(destination)
    if parts is None:
        return None
    path, fragment = parts
    candidate = str(PurePosixPath(source).parent / path) if path else source
    if path.startswith("/"):
        raise Violation("absolute local reference")
    target = repository.resolve(candidate)
    if target != PLUGIN and not target.startswith(PLUGIN + "/"):
        raise Violation("reference is outside the Camellia distribution")
    if not repository.exists(target):
        raise Violation("missing reference target: " + target)
    return target, fragment
