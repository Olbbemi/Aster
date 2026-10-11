"""Read one repository revision and apply documented Markdown structure rules."""

from collections import deque
from html.parser import HTMLParser
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import unicodedata

SKILL = "plugins/Syringa/skills/knowledge-discovery"


def git_environment():
    # Hooks export repository-specific values; fixtures and explicit -C reads must not inherit them.
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


class Violation(ValueError):
    """A source file violates a documented structural requirement."""


class Repository:
    """Read files without checking out a revision or modifying repository state."""

    def __init__(self, root, revision=None):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise OSError("저장소 경로가 디렉토리가 아닙니다.")
        self.commit = None
        self.entries = {}
        self.directories = {""}
        self.blobs = {}
        if revision is not None:
            self.commit = self.git("rev-parse", "--verify", "--end-of-options",
                                   revision + "^{commit}").decode().strip()
            for entry in self.git("ls-tree", "-rz", self.commit).split(b"\0"):
                if not entry:
                    continue
                metadata, raw_path = entry.split(b"\t", 1)
                mode, kind, oid = metadata.decode("ascii").split()
                path = os.fsdecode(raw_path)
                self.entries[path] = (mode, kind, oid)
                self.directories.update(str(parent) if str(parent) != "." else ""
                                        for parent in PurePosixPath(path).parents)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                capture_output=True, timeout=10, env=git_environment())
        if result.returncode:
            raise OSError("Git 읽기 실패: " + os.fsdecode(result.stderr).strip())
        return result.stdout

    def blob(self, oid):
        if oid not in self.blobs:
            self.blobs[oid] = self.git("cat-file", "blob", oid)
        return self.blobs[oid]

    def resolve(self, path):
        """Resolve snapshot links before '..', using only committed entries."""
        if PurePosixPath(path).is_absolute():
            raise OSError("커밋 밖의 절대 경로는 스냅샷에서 확인할 수 없습니다.")
        pending, resolved, links = deque(PurePosixPath(path).parts), [], 0
        while pending:
            part = pending.popleft()
            if part == ".":
                continue
            if part == "..":
                if not resolved:
                    raise OSError("참조가 커밋의 저장소 경계 밖으로 나갑니다.")
                resolved.pop()
                continue
            resolved.append(part)
            candidate = "/".join(resolved)
            entry = self.entries.get(candidate)
            if entry and entry[0] == "120000":
                links += 1
                if links > 40:
                    raise OSError("심볼릭 링크 연결이 너무 깊습니다.")
                destination = self.blob(entry[2]).decode("utf-8")
                if PurePosixPath(destination).is_absolute():
                    raise OSError("커밋의 절대 심볼릭 링크는 확인할 수 없습니다.")
                resolved.pop()
                pending.extendleft(reversed(PurePosixPath(destination).parts))
            elif candidate not in self.directories:
                if entry is None:
                    raise FileNotFoundError(candidate)
                if pending:
                    raise NotADirectoryError(candidate)
        return "/".join(resolved)

    def kind(self, path):
        if self.commit is None:
            target = (self.root / path).resolve(strict=True)
            if not target.is_relative_to(self.root):
                raise OSError("참조가 저장소 경계 밖으로 나갑니다: " + path)
            mode = target.stat().st_mode
            if stat.S_ISREG(mode):
                return "file"
            if stat.S_ISDIR(mode):
                return "directory"
            raise OSError("일반 파일이나 디렉토리가 아닙니다: " + path)
        resolved = self.resolve(path)
        if resolved in self.directories:
            return "directory"
        entry = self.entries[resolved]
        if entry[1] != "blob":
            raise OSError("읽을 수 있는 커밋 파일이 아닙니다: " + path)
        return "file"

    def read(self, path):
        if self.kind(path) != "file":
            raise OSError("일반 파일이 아닙니다: " + path)
        if self.commit is None:
            return (self.root / path).read_bytes()
        return self.blob(self.entries[self.resolve(path)][2])

    def files(self, suffix=None):
        if self.kind(SKILL) != "directory":
            raise Violation("knowledge-discovery 디렉토리가 없습니다.")
        if self.commit is not None:
            paths = [path for path in self.entries if path.startswith(SKILL + "/")]
            for path in paths:
                mode = self.entries[path][0]
                if mode == "160000" or (mode == "120000" and self.kind(path) == "directory"):
                    raise OSError("하위 연결 디렉토리는 전체 검사할 수 없습니다: " + path)
        else:
            paths = []

            def fail(error):
                raise error

            for parent, dirs, files in os.walk(self.root / SKILL, onerror=fail):
                for name in dirs:
                    if (Path(parent) / name).is_symlink():
                        raise OSError("하위 심볼릭 링크 디렉토리는 전체 검사할 수 없습니다: "
                                      + str(Path(parent) / name))
                paths.extend(str((Path(parent) / name).relative_to(self.root)) for name in files)
        return sorted(path for path in paths if suffix is None or PurePosixPath(path).suffix.lower() == suffix)


def frontmatter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        raise Violation("첫 줄의 YAML 시작 구분자가 없습니다.")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        raise Violation("YAML 종료 구분자가 없습니다.")
    return "".join(lines[1:end]), "\n" * (end + 1) + "".join(lines[end + 1:])


def body(text):
    first = text.splitlines()[:1]
    return frontmatter(text)[1] if first and first[0].rstrip() == "---" else text


def safe_mapping(text, yaml):
    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            keys = set()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue
                key = self.construct_object(key_node, deep=deep)
                try:
                    duplicate = key in keys
                    keys.add(key)
                except TypeError as exc:
                    raise yaml.constructor.ConstructorError(
                        None, None, "unhashable mapping key", key_node.start_mark) from exc
                if duplicate:
                    raise yaml.constructor.ConstructorError(
                        None, None, "duplicate mapping key", key_node.start_mark)
            return super().construct_mapping(node, deep=deep)

    try:
        value = yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise Violation("YAML 파싱 실패: " + str(exc)) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise Violation("문자열 키의 YAML 매핑이 필요합니다.")
    return value


def inline_text(tokens):
    return "".join(inline_text(t.children or []) if t.type == "image" else
                   t.content if t.type in ("text", "code_inline") else
                   " " if t.type in ("softbreak", "hardbreak") else "" for t in tokens)


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = set()

    def handle_starttag(self, tag, attrs):
        self.values.update(value for name, value in attrs if value and
                           (name == "id" or (tag == "a" and name == "name")))


def anchors(tokens):
    automatic, explicit = set(), Anchors()
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            title = inline_text(tokens[i + 1].children or []).strip().lower()
            base = "".join("-" if c == " " else c for c in title
                           if c in " -_" or unicodedata.category(c)[0] in "LMN")
            name, suffix = base, 0
            while name in automatic:
                suffix += 1
                name = f"{base}-{suffix}"
            automatic.add(name)
        for item in (token, *(token.children or [])):
            if item.type in ("html_block", "html_inline"):
                explicit.feed(item.content)
    explicit.close()
    return automatic | explicit.values
