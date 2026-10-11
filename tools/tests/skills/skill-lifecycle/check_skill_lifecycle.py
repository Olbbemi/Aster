#!/usr/bin/env python3
"""Validate the lifecycle skill itself, from a commit or an explicit working tree."""

import argparse
from collections import deque
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True

SKILL = ".agents/skills/skill-lifecycle"
POLICY = SKILL + "/references/lifecycle.md"
TEMPLATE = SKILL + "/assets/lifecycle-template.md"
SPECIFICATION_RULES = SKILL + "/references/records/specification.md"
COMMON_RECORDS = ("진입 조건 확인", "완료 조건 확인", "단계 이동 기록")
TEMPLATE_FIELDS = {"name", "target_path", "operation", "current_stage", "in_review"}


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
                                capture_output=True, timeout=30)
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
            mode = (self.root / path).stat().st_mode
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

    def files(self, suffix):
        if self.kind(SKILL) != "directory":
            raise Violation("skill-lifecycle 디렉토리가 없습니다.")
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
        return sorted(path for path in paths if PurePosixPath(path).suffix.lower() == suffix)


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


def headings(tokens):
    return [(int(t.tag[1:]), inline_text(tokens[i + 1].children or []).strip(), t.map[0] + 1)
            for i, t in enumerate(tokens) if t.type == "heading_open" and t.level == 0]


def section(tokens, title, depth=2):
    matches = [i for i, t in enumerate(tokens)
               if t.type == "heading_open" and t.level == 0 and t.tag == f"h{depth}"
               and inline_text(tokens[i + 1].children or []).strip() == title]
    if len(matches) != 1:
        raise Violation(f"'{title}' 구역은 정확히 한 번 있어야 합니다.")
    start = matches[0] + 3
    end = next((i for i in range(start, len(tokens))
                if tokens[i].type == "heading_open" and tokens[i].level == 0
                and int(tokens[i].tag[1:]) <= depth), len(tokens))
    return tokens[start:end]


def first_list(tokens, kind):
    titles, active = [], False
    for token in tokens:
        if token.type == kind + "_list_open" and token.level == 0:
            active = True
        elif token.type == kind + "_list_close" and token.level == 0 and active:
            break
        elif active and token.type == "inline" and token.level == 3:
            titles.append(inline_text(token.children or []).strip())
    if not titles or any(not title for title in titles) or len(set(titles)) != len(titles):
        raise Violation("기준 목록이 비어 있거나 항목이 중복됩니다.")
    return titles


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


class Context:
    def __init__(self, repository, yaml, markdown):
        self.repo, self.yaml = repository, yaml
        self.parser = markdown("commonmark").enable("table")
        self.parser.validateLink = lambda destination: True
        self.documents, self.issues, self.excluded = {}, [], []

    def tokens(self, path):
        if path not in self.documents:
            self.documents[path] = self.parser.parse(body(self.repo.read(path).decode("utf-8-sig")))
        return self.documents[path]

    def add(self, error, path, line=None):
        self.issues.append({"kind": "violation" if isinstance(error, (Violation,
                           FileNotFoundError, NotADirectoryError)) else "error",
                            "path": path, "line": line, "message": str(error)})

    def require(self, valid, message):
        if not valid:
            raise Violation(message)

    def stages(self):
        values = first_list(section(self.tokens(POLICY), "생명 주기 순서"), "ordered")
        matches = [re.fullmatch(r"([a-z][a-z0-9-]*) \(([^()]+)\)", value) for value in values]
        self.require(all(matches), "단계 식별자와 이름을 해석할 수 없습니다.")
        stages = [(match[1], value) for match, value in zip(matches, values)]
        self.require(len({stage for stage, _ in stages}) == len(stages), "단계 식별자가 중복됩니다.")
        return stages


def check_metadata(ctx):
    path = SKILL + "/SKILL.md"
    try:
        data = safe_mapping(frontmatter(ctx.repo.read(path).decode("utf-8-sig"))[0], ctx.yaml)
        for key in ("name", "description"):
            ctx.require(isinstance(data.get(key), str) and bool(data[key].strip()),
                        key + "은 비어 있지 않은 문자열이어야 합니다.")
        ctx.require(data["name"] == PurePosixPath(SKILL).name, "name과 디렉토리명이 다릅니다.")
        ctx.require(re.fullmatch(r"[a-z0-9-]+", data["name"]), "name의 허용 문자 규칙 위반입니다.")
    except (OSError, ValueError) as exc:
        ctx.add(exc, path)


def check_local_references(ctx):
    for path in ctx.repo.files(".md"):
        try:
            tokens = ctx.tokens(path)
        except (OSError, ValueError) as exc:
            ctx.add(exc, path)
            continue
        enclosing_line = None
        for token in tokens:
            if token.map:
                enclosing_line = token.map[0] + 1
            if token.type != "inline":
                continue
            for item in token.children or []:
                destination = (item.attrGet("href") if item.type == "link_open" else
                               item.attrGet("src") if item.type == "image" else None)
                if destination is None:
                    continue
                try:
                    parts = urlsplit(destination)
                    if parts.scheme or parts.netloc or destination.startswith("//"):
                        ctx.excluded.append({"path": path, "destination": destination})
                        continue
                    decoded = unquote(parts.path, encoding="utf-8", errors="strict")
                    target = str(PurePosixPath(path).parent / decoded) if decoded else path
                    kind = ctx.repo.kind(target)
                    if parts.fragment:
                        if re.search(r"%(?![0-9a-fA-F]{2})", parts.fragment):
                            raise Violation("fragment의 percent escape가 잘못되었습니다.")
                        fragment = unquote(parts.fragment, encoding="utf-8", errors="strict")
                        ctx.require("\0" not in fragment, "fragment에 NUL이 있습니다.")
                        if kind != "file" or PurePosixPath(target).suffix.lower() != ".md":
                            raise OSError("Markdown 이외 대상의 절은 판정할 수 없습니다.")
                        ctx.require(fragment in anchors(ctx.tokens(target)),
                                    "지정한 절이 없습니다: " + destination)
                except (OSError, ValueError) as exc:
                    ctx.add(exc, path, enclosing_line)


def check_stage_inventory(ctx):
    expected = {stage + ".md" for stage, _ in ctx.stages()}
    prefix = SKILL + "/references/stages/"
    paths = ctx.repo.files(".md")
    actual = {path[len(prefix):] for path in paths
              if path.startswith(prefix) and "/" not in path[len(prefix):]}
    ctx.require(actual == expected,
                f"단계 파일 누락={sorted(expected - actual)}, 미등록={sorted(actual - expected)}")


def check_stage_structure(ctx):
    operations = first_list(section(ctx.tokens(POLICY), "단계 정의 공통 항목"), "bullet")
    for stage, title in ctx.stages():
        path = SKILL + f"/references/stages/{stage}.md"
        try:
            tokens = ctx.tokens(path)
            items = headings(tokens)
            h1 = [item for item in items if item[0] == 1]
            h2 = [item for item in items if item[0] == 2]
            ctx.require(len(h1) == 1 and h1[0][1] == title and
                        (not h2 or h1[0][2] < h2[0][2]),
                        "단계 본문 앞에 정확한 단계 제목이 한 번 있어야 합니다.")
            ctx.require([item[1] for item in h2] == ["단계 운영 규칙", "명세서 기록 항목"],
                        "필수 구역의 제목, 개수 또는 순서가 다릅니다.")
            actual = [name for depth, name, _ in headings(section(tokens, "단계 운영 규칙"))
                      if depth == 3]
            ctx.require(actual == operations, "운영 항목의 제목, 개수, 제목 단계 또는 순서가 다릅니다.")
        except (OSError, ValueError) as exc:
            ctx.add(exc, path)


def check_template(ctx):
    stages = ctx.stages()
    text = ctx.repo.read(TEMPLATE).decode("utf-8-sig")
    data = safe_mapping(frontmatter(text)[0], ctx.yaml)
    ctx.require(set(data) == TEMPLATE_FIELDS, "템플릿 프론트매터 필드가 규격과 다릅니다.")
    for key in ("name", "target_path", "operation", "current_stage"):
        ctx.require(isinstance(data[key], str) and bool(data[key].strip()),
                    "템플릿 " + key + "은 비어 있지 않은 문자열이어야 합니다.")
    ctx.require(data["in_review"] is False, "템플릿의 초기 in_review는 boolean false여야 합니다.")
    ctx.require(data["current_stage"] in {stage for stage, _ in stages},
                "템플릿 current_stage가 등록된 단계가 아닙니다.")
    operation_tokens = section(ctx.tokens(SPECIFICATION_RULES), "operation (작업 유형)", 3)
    operations = [match[1] for token in operation_tokens if token.type == "inline"
                  for match in [re.match(r"^([a-z][a-z0-9-]*):", inline_text(token.children or []))]
                  if match]
    ctx.require(operations and len(set(operations)) == len(operations),
                "지침의 operation 허용값을 해석할 수 없습니다.")
    value = data["operation"]
    if value.startswith("<") and value.endswith(">"):
        choices = value[1:-1].split("|")
        ctx.require(len(set(choices)) == len(choices) and set(choices) == set(operations),
                    "템플릿의 operation 자리표시자와 지침의 허용값이 다릅니다.")
    else:
        ctx.require(value in operations, "템플릿의 operation 값이 지침에 없습니다.")
    tokens = ctx.tokens(TEMPLATE)
    items = headings(tokens)
    h1, h2 = ([item for item in items if item[0] == depth] for depth in (1, 2))
    ctx.require(len(h1) == 1 and bool(h1[0][1]) and h2 and h1[0][2] < h2[0][2],
                "템플릿의 단계 본문 앞에 문서 제목이 한 번 있어야 합니다.")
    ctx.require([title for _, title, _ in h2] == [title for _, title in stages],
                "템플릿의 단계 제목, 개수 또는 순서가 다릅니다.")
    for stage, title in stages:
        path = SKILL + f"/references/stages/{stage}.md"
        records = [name for depth, name, _ in headings(section(ctx.tokens(path), "명세서 기록 항목"))
                   if depth == 3]
        ctx.require(records and len(set(records)) == len(records) and
                    not set(records).intersection(COMMON_RECORDS),
                    "단계 지침의 기록 항목이 없거나 중복됩니다: " + path)
        actual = [name for depth, name, _ in headings(section(tokens, title)) if depth == 3]
        ctx.require(actual == [COMMON_RECORDS[0], *records, *COMMON_RECORDS[1:]],
                    "템플릿 기록 항목의 제목, 개수, 제목 단계 또는 순서가 다릅니다: " + stage)


def check_python_syntax(ctx):
    for path in ctx.repo.files(".py"):
        try:
            compile(ctx.repo.read(path), path, "exec", dont_inherit=True)
        except SyntaxError as exc:
            ctx.add(Violation(exc.msg), path, exc.lineno)
        except (OSError, ValueError) as exc:
            ctx.add(exc, path)


CHECKS = (
    ("skill_metadata", SKILL + "/SKILL.md", check_metadata),
    ("local_references", SKILL, check_local_references),
    ("stage_inventory", POLICY, check_stage_inventory),
    ("stage_structure", POLICY, check_stage_structure),
    ("template_correspondence", TEMPLATE, check_template),
    ("python_syntax", SKILL, check_python_syntax),
)


def validate(root, revision=None):
    report = {"passed": False, "source": {"repository": str(root), "revision": revision,
              "mode": "commit" if revision is not None else "working-tree"},
              "checks": [], "excluded_external_links": []}
    try:
        import yaml
        from markdown_it import MarkdownIt
        repository = Repository(root, revision)
        report["source"]["commit"] = repository.commit
        ctx = Context(repository, yaml, MarkdownIt)
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report["checks"].append({"id": "input", "passed": False, "issues": [
            {"kind": "error", "path": str(root), "line": None, "message": str(exc)}]})
        return report
    for identifier, path, check in CHECKS:
        start = len(ctx.issues)
        try:
            check(ctx)
        except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as exc:
            ctx.add(exc, path)
        issues = ctx.issues[start:]
        report["checks"].append({"id": identifier, "passed": not issues, "issues": issues})
    report["excluded_external_links"] = ctx.excluded
    report["passed"] = all(item["passed"] for item in report["checks"])
    return report


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            print("false")
            super().error(message)

    parser = Parser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[4],
                        help="대상 Aster 저장소 또는 시험용 사본의 루트")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--revision", help="검사할 커밋. 파일과 참조 대상을 모두 해당 커밋에서 읽음")
    source.add_argument("--working-tree", action="store_true", help="개발 중인 작업 트리를 명시적으로 검사")
    parser.add_argument("--json", action="store_true", help="boolean 판정과 실패 원인을 JSON으로 출력")
    args = parser.parse_args(argv)
    report = validate(args.repository_root, args.revision)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(str(report["passed"]).lower())
        for check in report["checks"]:
            print(f"{check['id']}: {str(check['passed']).lower()}")
            for issue in check["issues"]:
                position = f":{issue['line']}" if issue["line"] else ""
                print(f"  {issue['kind']}: {issue['path']}{position}: {issue['message']}")
        print(f"외부 링크 검사 제외: {len(report['excluded_external_links'])}건")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
