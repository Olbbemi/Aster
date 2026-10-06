#!/usr/bin/env python3
"""Check requirement, scenario and current-result tables without running scenarios."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from check_references import inline_text, markdown_body

BASIS = "standards/skills/scenario-records.md"
HEADERS = {
    "requirements": ("요건 ID", "필수 여부", "범위", "사유"),
    "scenarios": ("사례 ID", "대응 요건", "필수 여부", "범위", "기대 결과", "사유"),
    "results": ("사례 ID", "상태", "근거/사유"),
}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MARKER = re.compile(r"<!--\s*lifecycle-check:([a-z-]+)\s*-->")
STATES = ("통과", "실패", "미실행", "미판정")


def raw_cell_count(line):
    """Count unescaped table separators before Markdown pads or drops cells."""
    cells, current, escaped = [], "", False
    for char in line.strip():
        if char == "|" and not escaped:
            cells.append(current)
            current = ""
        else:
            current += char
        escaped = char == "\\" and not escaped
    cells.append(current)
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return len(cells)


def read_table(tokens, start, lines, source, add):
    rows, row, headers = [], None, []
    is_header = False
    for token in tokens[start + 1:]:
        if token.type == "table_close":
            break
        if token.type == "thead_open":
            is_header = True
        elif token.type == "thead_close":
            is_header = False
        elif token.type == "tr_open":
            row = {"cells": [], "source": str(source), "line": token.map[0] + 1}
        elif token.type == "inline" and row is not None:
            row["cells"].append(inline_text(token.children or []).strip())
        elif token.type == "tr_close" and row is not None:
            if is_header:
                headers = row["cells"]
            else:
                if raw_cell_count(lines[row["line"] - 1]) != len(headers):
                    add("table.columns", "FAIL", "행의 열 수가 머리글과 다릅니다.", source, row["line"])
                rows.append(row)
            row = None
    return headers, rows


def check_scenario_records(paths, *, phase):
    checks, files, tables = [], [], {kind: [] for kind in HEADERS}
    execution = {"checked": False}

    def add(identifier, status, message, source=None, line=None):
        checks.append(dict(id=identifier, status=status, message=message,
                           source=str(source) if source else None, line=line, basis=BASIS))

    def report():
        counts = Counter(item["status"] for item in checks)
        code = 2 if counts["ERROR"] else 1 if counts["FAIL"] else 0
        return dict(scope="scenario-record-correspondence", phase=phase, files=files,
                    status=("PASS", "FAIL", "INCOMPLETE")[code], exit_code=code,
                    counts=dict(counts), checks=checks, execution=execution,
                    limits=["기록의 형식과 대응만 검사하며 실제 시험, 승인과 완료를 판정하지 않습니다.",
                            "본문/근거의 타당성과 링크 존재는 별도 확인합니다."])

    paths = list(paths)
    if not paths or phase not in ("plan", "results"):
        add("input", "ERROR", "입력 파일과 plan/results 모드가 필요합니다.")
        return report()
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        add("dependency", "ERROR", f"markdown-it-py가 필요합니다: {exc}")
        return report()
    parser = MarkdownIt("commonmark").enable("table")
    seen = set()
    for value in paths:
        source = Path(value).absolute()
        try:
            key = source.resolve(strict=True)
            if key in seen:
                continue
            seen.add(key)
            files.append(str(source))
            if not source.is_file():
                raise ValueError("일반 Markdown 파일이 아닙니다.")
            text = source.read_text(encoding="utf-8-sig")
            tokens = parser.parse(markdown_body(text))
            lines = text.split("\n")
            for index, token in enumerate(tokens):
                if token.type != "html_block" or token.level != 0:
                    continue
                match = MARKER.fullmatch(token.content.strip())
                if not match:
                    continue
                kind, line = match.group(1), token.map[0] + 1
                if kind not in HEADERS:
                    add("table.marker", "FAIL", f"알 수 없는 표 역할: {kind}", source, line)
                    continue
                if phase == "plan" and kind == "results":
                    continue
                if index + 1 >= len(tokens) or tokens[index + 1].type != "table_open":
                    add("table.marker", "FAIL", "표시 바로 다음에 표가 필요합니다.", source, line)
                    continue
                headers, rows = read_table(tokens, index + 1, lines, source, add)
                tables[kind].append(dict(headers=headers, rows=rows, source=str(source), line=line))
        except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
            add("document.read", "ERROR", str(exc), source)

    records = {}
    for kind in ("requirements", "scenarios", *(("results",) if phase == "results" else ())):
        records[kind] = {}
        if len(tables[kind]) != 1:
            add("table.required", "FAIL", f"{kind} 표가 정확히 하나 필요합니다: {len(tables[kind])}개")
            continue
        table = tables[kind][0]
        headers = table["headers"]
        if not set(HEADERS[kind]) <= set(headers) or len(set(headers)) != len(headers) or "" in headers:
            add("table.headers", "FAIL", f"{kind}: 필수 열 누락 또는 열 이름 중복/공백입니다.",
                table["source"], table["line"])
            continue
        if not table["rows"]:
            add("table.empty", "FAIL", f"{kind}: 한 개 이상의 행이 필요합니다.",
                table["source"], table["line"])
        for row in table["rows"]:
            data = dict(zip(headers, row["cells"]))
            identifier = data[HEADERS[kind][0]]
            if not IDENTIFIER.fullmatch(identifier):
                add("record.id", "FAIL", f"{kind}: ID 형식 오류: {identifier!r}", row["source"], row["line"])
                continue
            if identifier in records[kind]:
                add("record.duplicate", "FAIL", f"{kind}: 중복 ID: {identifier}", row["source"], row["line"])
                continue
            data.update(source=row["source"], line=row["line"])
            records[kind][identifier] = data

    def issue(identifier, message, row):
        add(identifier, "FAIL", message, row["source"], row["line"])

    for kind in ("requirements", "scenarios"):
        for identifier, row in records[kind].items():
            if row["필수 여부"] not in ("필수", "선택"):
                issue("record.required", f"{identifier}: 필수 여부는 필수/선택이어야 합니다.", row)
            if row["범위"] not in ("대상", "제외", "보류"):
                issue("record.scope", f"{identifier}: 범위는 대상/제외/보류여야 합니다.", row)
            elif row["범위"] != "대상" and not row["사유"]:
                issue("record.reason", f"{identifier}: 제외/보류 사유가 필요합니다.", row)

    covered = set()
    for identifier, row in records["scenarios"].items():
        requirements = [value.strip() for value in row["대응 요건"].split(",")]
        if any(not IDENTIFIER.fullmatch(value) for value in requirements) or len(set(requirements)) != len(requirements):
            issue("scenario.requirements", f"{identifier}: 대응 요건 ID의 형식/중복을 확인하십시오.", row)
        for requirement in requirements:
            if requirement and requirement not in records["requirements"]:
                issue("scenario.unknown-requirement", f"{identifier}: 등록되지 않은 요건 {requirement}", row)
        if not row["기대 결과"]:
            issue("scenario.expected", f"{identifier}: 기대 결과 또는 상세 링크가 필요합니다.", row)
        if row["범위"] == "대상":
            covered.update(requirements)
    for identifier, row in records["requirements"].items():
        if row["범위"] == "대상" and identifier not in covered:
            issue("requirement.uncovered", f"{identifier}: 현재 대상 사례에 연결되지 않았습니다.", row)

    if phase == "results":
        for identifier, row in records["results"].items():
            if identifier not in records["scenarios"]:
                issue("result.unregistered", f"계획에 없는 사례입니다: {identifier}", row)
            if row["상태"] not in STATES:
                issue("result.state", f"{identifier}: 상태는 {STATES!r} 중 하나여야 합니다.", row)
            if not row["근거/사유"]:
                issue("result.evidence", f"{identifier}: 근거 또는 사유가 필요합니다.", row)
        for identifier, row in records["scenarios"].items():
            if identifier not in records["results"]:
                issue("result.missing", f"{identifier}: 현재 결과가 없습니다.", row)
        execution = dict(
            checked=True,
            counts=dict(Counter(row["상태"] for identifier, row in records["results"].items()
                                if identifier in records["scenarios"] and row["상태"] in STATES)),
            required_cases_not_passed=[identifier for identifier, row in records["scenarios"].items()
                                       if row["범위"] == "대상" and row["필수 여부"] == "필수"
                                       and records["results"].get(identifier, {}).get("상태") != "통과"],
        )
    if not checks:
        add("records.correspondence", "PASS", "선택한 범위의 표 형식과 ID 대응이 맞습니다.")
    return report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="한 시나리오 묶음의 Markdown 정본 파일들")
    parser.add_argument("--phase", required=True, choices=("plan", "results"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_scenario_records(args.files, phase=args.phase)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"기록 대조: {result['status']} ({result['phase']})")
        for item in result["checks"]:
            print(f"  {item['status']} [{item['id']}] {item['source']}:{item['line'] or ''} {item['message']}")
        print("실제 시험 상태: " + json.dumps(result["execution"], ensure_ascii=False))
        for limit in result["limits"]:
            print(f"범위: {limit}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
