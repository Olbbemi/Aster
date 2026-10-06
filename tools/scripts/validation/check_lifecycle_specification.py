#!/usr/bin/env python3
"""Read-only format checks for lifecycle specifications, stage documents and templates."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from check_structure import load_frontmatter
from check_references import inline_text, markdown_body


DEFAULT_LIFECYCLE = Path(__file__).resolve().parents[3] / ".agents/skills/skill-lifecycle"
SPEC = ".agents/skills/skill-lifecycle/references/specification.md"
ORDER = ".agents/skills/skill-lifecycle/references/lifecycle.md#생명-주기-순서"
STAGE_STRUCTURE = ".agents/skills/skill-lifecycle/references/lifecycle.md#단계-정의-공통-항목"
STAGE_SECTIONS = ("단계 운영 규칙", "명세서 기록 항목")
COMMON = ("진입 조건 확인", "완료 조건 확인", "단계 이동 기록")
OPERATIONS = {"create", "update", "integrate", "deprecate"}
FIELDS = {"name", "target_path", "operation", "current_stage"}


def headings(tokens):
    """Read document headings, excluding examples, comments and nested quotations."""
    return [
        (int(token.tag[1:]), inline_text(tokens[index + 1].children or []).strip(),
         token.map[0] + 1)
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.level == 0
    ]


def section_tokens(tokens, title):
    for index, token in enumerate(tokens):
        if (token.type == "heading_open" and token.tag == "h2" and token.level == 0
                and inline_text(tokens[index + 1].children or []).strip() == title):
            end = next((j for j in range(index + 3, len(tokens))
                        if tokens[j].type == "heading_open" and tokens[j].level == 0
                        and tokens[j].tag in ("h1", "h2")), len(tokens))
            return tokens[index + 3:end]
    raise ValueError(f"기준 문서의 절이 없습니다: {title}")


def stage_sections(items):
    """Return h2 sections and direct h3 headings, without absorbing later h1 content."""
    result = []
    current = None
    for level, title, line in items:
        if level == 1:
            current = None
        elif level == 2:
            current = {"title": title, "line": line, "headings": []}
            result.append(current)
        elif level == 3 and current is not None:
            current["headings"].append((title, line))
    return result


def first_list_titles(tokens, kind):
    """Read direct items of the first top-level list, ignoring nested examples."""
    titles = []
    in_list = False
    for token in tokens:
        if token.type == f"{kind}_list_open" and token.level == 0:
            in_list = True
        elif token.type == f"{kind}_list_close" and token.level == 0 and in_list:
            break
        elif in_list and token.type == "inline" and token.level == 3:
            titles.append(inline_text(token.children or []).strip())
    return titles


def read_stage_order(tokens):
    titles = first_list_titles(section_tokens(tokens, "생명 주기 순서"), "ordered")
    stages = []
    for title in titles:
        match = re.fullmatch(r"([a-z][a-z0-9-]*) \(.+\)", title)
        if not match:
            raise ValueError(f"단계 목록을 해석할 수 없습니다: {title}")
        stages.append((match.group(1), title))
    if not stages or len({stage for stage, _ in stages}) != len(stages):
        raise ValueError("단계 목록이 비어 있거나 단계 식별자가 중복됩니다.")
    return stages


def read_rules(directory, parser):
    def parse(path):
        return parser.parse(markdown_body(path.read_text(encoding="utf-8-sig")))

    stages = read_stage_order(parse(directory / "references/lifecycle.md"))
    records = {}
    for stage, _ in stages:
        path = directory / f"references/stages/{stage}.md"
        items = headings(section_tokens(parse(path), "명세서 기록 항목"))
        titles = [title for level, title, _ in items if level == 3]
        if not titles or len(set(titles)) != len(titles) or set(titles) & set(COMMON):
            raise ValueError(f"단계 기록 제목이 없거나 중복됩니다: {path}")
        records[stage] = titles
    return stages, records


def check_stage_documents(directory, parser, add):
    rules_path = directory / "references/lifecycle.md"
    try:
        tokens = parser.parse(markdown_body(rules_path.read_text(encoding="utf-8-sig")))
        for title in ("생명 주기 순서", "단계 정의 공통 항목"):
            if sum(level == 2 and name == title for level, name, _ in headings(tokens)) != 1:
                raise ValueError(f"기준 문서의 절은 한 번 있어야 합니다: {title}")
        stages = read_stage_order(tokens)
        operations = first_list_titles(section_tokens(tokens, "단계 정의 공통 항목"), "bullet")
        if not operations or any(not title for title in operations) or len(set(operations)) != len(operations):
            raise ValueError("운영 항목 목록이 비어 있거나 제목이 중복됩니다.")
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        add("stage-documents.rules", "ERROR", f"단계 구조 기준을 읽을 수 없습니다: {exc}",
            rules_path, basis=STAGE_STRUCTURE)
        return

    stage_directory = directory / "references/stages"
    expected_files = {f"{stage}.md" for stage, _ in stages}
    try:
        actual_files = {path.name for path in stage_directory.iterdir() if path.suffix.lower() == ".md"}
    except FileNotFoundError:
        actual_files = set()
    except OSError as exc:
        add("stage-documents.directory", "ERROR", f"단계 디렉토리를 읽을 수 없습니다: {exc}",
            stage_directory, basis=STAGE_STRUCTURE)
        return
    missing, extra = sorted(expected_files - actual_files), sorted(actual_files - expected_files)
    add("stage-documents.files", "PASS" if not missing and not extra else "FAIL",
        f"단계 파일: 누락={missing!r}, 목록에 없음={extra!r}", stage_directory, basis=STAGE_STRUCTURE)

    for stage, title in stages:
        path = stage_directory / f"{stage}.md"
        try:
            items = headings(parser.parse(markdown_body(path.read_text(encoding="utf-8-sig"))))
        except FileNotFoundError:
            add("stage-documents.read", "FAIL", "단계 파일이 없습니다.", path, basis=STAGE_STRUCTURE)
            continue
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            add("stage-documents.read", "ERROR", f"단계 파일을 읽을 수 없습니다: {exc}",
                path, basis=STAGE_STRUCTURE)
            continue

        h1 = [item for item in items if item[0] == 1]
        title_ok = len(h1) == 1 and h1[0][1] == title and items[0] == h1[0]
        add("stage-documents.title", "PASS" if title_ok else "FAIL",
            f"문서 제목: {[name for _, name, _ in h1]!r}; 기준: {title!r}",
            path, h1[0][2] if h1 else 1, STAGE_STRUCTURE)

        sections = stage_sections(items)
        actual_sections = [section["title"] for section in sections]
        add("stage-documents.sections", "PASS" if actual_sections == list(STAGE_SECTIONS) else "FAIL",
            f"공통 구역: {actual_sections!r}; 기준: {list(STAGE_SECTIONS)!r}",
            path, sections[0]["line"] if sections else 1, STAGE_STRUCTURE)
        for section in sections:
            if section["title"] != STAGE_SECTIONS[0]:
                continue
            actual = [name for name, _ in section["headings"]]
            add("stage-documents.operations", "PASS" if actual == operations else "FAIL",
                f"운영 항목: {actual!r}; 기준: {operations!r}", path, section["line"], STAGE_STRUCTURE)


def check_lifecycle_specification(specification=None, *, check_template=False,
                                  check_stages=False,
                                  lifecycle_directory=DEFAULT_LIFECYCLE):
    directory = Path(lifecycle_directory).absolute()
    target = Path(specification).absolute() if specification is not None else None
    checks = []

    def add(identifier, status, message, path=None, line=None, basis=SPEC):
        checks.append(dict(id=identifier, status=status, message=message,
                           target=str(path) if path else None, line=line, basis=basis))

    def result():
        states = {check["status"] for check in checks}
        code = 2 if "ERROR" in states else 1 if "FAIL" in states else 0
        return dict(target=str(target) if target else None,
                    lifecycle_directory=str(directory), scope="lifecycle-format",
                    check_template=check_template, check_stages=check_stages,
                    status=("PASS", "FAIL", "INCOMPLETE")[code], exit_code=code,
                    checks=checks,
                    limits=["표준 형식의 구조만 검사하며 승인, 요건 충족과 실제 완료를 판정하지 않습니다.",
                            "name/target_path의 null 허용 조건과 실제 작업 대상은 별도 확인합니다.",
                            "본문 내용과 링크, 자체 수정용 축약 명세서는 검사 범위 밖입니다."]
                    + (["단계 문서의 본문 충분성과 전이 조건의 타당성은 별도 검토합니다."]
                       if check_stages else []))

    if target is None and not check_template and not check_stages:
        add("input.required", "ERROR", "명세서, --check-template 또는 --check-stages가 필요합니다.")
        return result()
    try:
        import yaml
        from markdown_it import MarkdownIt
    except ImportError as exc:
        add("dependency", "ERROR", f"tools/requirements.txt의 의존성이 필요합니다: {exc}")
        return result()
    parser = MarkdownIt("commonmark").enable("table")
    if check_stages:
        check_stage_documents(directory, parser, add)
    if target is None and not check_template:
        return result()
    try:
        stages, records = read_rules(directory, parser)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        add("rules.read", "ERROR", f"검사 기준을 읽을 수 없습니다: {exc}", directory)
        return result()

    stage_titles = [title for _, title in stages]

    def check_body(text, path, template=False):
        items = headings(parser.parse(markdown_body(text)))
        h1 = [item for item in items if item[0] == 1]
        sections = stage_sections(items)
        actual_titles = [section["title"] for section in sections]
        # Other h2 sections are allowed; required stages must occur exactly once in order.
        present = actual_titles if template else [title for title in actual_titles if title in stage_titles]
        first_stage_line = next((section["line"] for section in sections
                                 if section["title"] in stage_titles), None)
        title_ok = (len(h1) == 1 and bool(h1[0][1])
                    and (first_stage_line is None or h1[0][2] < first_stage_line))
        add("document.title", "PASS" if title_ok else "FAIL",
            "단계 본문 앞의 문서 제목을 확인했습니다.", path, basis=SPEC + "#명세서의-전체-구성")
        add("stages.order", "PASS" if present == stage_titles else "FAIL",
            f"단계 제목/순서: {present!r}; 기준: {stage_titles!r}", path, basis=ORDER)
        for stage, title in stages:
            matches = [section for section in sections if section["title"] == title]
            if len(matches) != 1:
                add("stage.required", "FAIL", f"{title}: 정확히 한 구역이 필요합니다.", path)
                continue
            section = matches[0]
            actual = [name for name, _ in section["headings"]]
            expected = [COMMON[0], *records[stage], *COMMON[1:]]
            counts = Counter(actual)
            missing = [name for name in expected if not counts[name]]
            duplicate = [name for name in expected if counts[name] > 1]
            ok = actual == expected if template else not missing and not duplicate
            add("template.headings" if template else "stage.headings",
                "PASS" if ok else "FAIL",
                f"{stage}: 누락={missing!r}, 중복={duplicate!r}"
                + (f", 제목/순서 일치={actual == expected}" if template else ""),
                path, section["line"], SPEC + "#명세서-템플릿")

    if check_template:
        path = directory / "assets/lifecycle-template.md"
        try:
            check_body(path.read_text(encoding="utf-8-sig"), path, template=True)
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            add("template.read", "ERROR", f"템플릿을 읽을 수 없습니다: {exc}", path)

    if target is None:
        return result()
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        add("specification.read", "ERROR", f"명세서를 읽을 수 없습니다: {exc}", target)
        return result()
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if not lines or lines[0].rstrip() != "---" or end is None:
        add("frontmatter.delimiters", "FAIL", "첫 줄의 YAML 시작/종료 구분자가 필요합니다.", target, 1)
        return result()
    try:
        data = load_frontmatter("\n".join(lines[1:end]), yaml)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        add("frontmatter.yaml", "FAIL", str(exc), target, mark.line + 2 if mark else None)
        return result()
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        add("frontmatter.mapping", "FAIL", "문자열 필드명의 YAML 매핑이 필요합니다.", target, 2)
        return result()
    add("frontmatter.yaml", "PASS", "YAML 매핑을 파싱했습니다.", target, 2)
    missing, extra = sorted(FIELDS - data.keys()), sorted(data.keys() - FIELDS)
    add("frontmatter.fields", "PASS" if not missing and not extra else "FAIL",
        f"누락={missing!r}, 정의되지 않은 필드={extra!r}", target, 2, SPEC + "#프론트매터")
    for field in sorted(FIELDS):
        if field not in data:
            continue
        value = data[field]
        nullable = field in ("name", "target_path")
        valid = (nullable and value is None) or (isinstance(value, str) and bool(value.strip()))
        add(f"{field}.type", "PASS" if valid else "FAIL",
            f"{field}: 비공백 문자열" + (" 또는 초기 null" if nullable else "") + " 형식입니다.",
            target, basis=SPEC + "#프론트매터")
        if not valid:
            continue
        if field in ("operation", "current_stage"):
            allowed = OPERATIONS if field == "operation" else {stage for stage, _ in stages}
            add(f"{field}.value", "PASS" if value in allowed else "FAIL",
                f"{field}={value!r}, 허용값={sorted(allowed)!r}", target)
    try:
        check_body(text, target)
    except (ValueError, RecursionError) as exc:
        add("specification.markdown", "ERROR", f"본문을 파싱할 수 없습니다: {exc}", target)
    return result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specification", nargs="?", type=Path, help="표준 형식의 lifecycle 명세서")
    parser.add_argument("--check-template", action="store_true", help="단계 문서와 템플릿의 제목 대응 검사")
    parser.add_argument("--check-stages", action="store_true", help="lifecycle 단계 문서의 운영 구조 검사")
    parser.add_argument("--lifecycle-directory", type=Path, default=DEFAULT_LIFECYCLE,
                        help="검사 기준인 skill-lifecycle 디렉토리")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args(argv)
    if args.specification is None and not args.check_template and not args.check_stages:
        parser.error("명세서, --check-template 또는 --check-stages가 필요합니다.")
    report = check_lifecycle_specification(args.specification, check_template=args.check_template,
                                          check_stages=args.check_stages,
                                          lifecycle_directory=args.lifecycle_directory)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status']} (lifecycle-format)")
        for check in report["checks"]:
            print(f"  {check['status']} [{check['id']}] {check['target']}:{check['line'] or ''} {check['message']}")
        for limit in report["limits"]:
            print(f"범위: {limit}")
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
