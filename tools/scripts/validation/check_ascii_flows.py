#!/usr/bin/env python3
"""Check marked ASCII flow blocks without assessing their visual layout or meaning."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import unicodedata

sys.dont_write_bytecode = True
from check_references import markdown_body

BASIS = "standards/skills/skill-validation.md#ascii-도식의-기계-판정"


def invalid_character(char):
    code = ord(char)
    return (unicodedata.category(char).startswith("C")
            or (char.isspace() and char != " ")
            or 0x2500 <= code <= 0x25FF
            or code in (0x2013, 0x2014, 0xFF0B, 0xFF0D, 0xFF1C, 0xFF1E, 0xFF5C)
            or (code > 127 and "ARROW" in unicodedata.name(char, "")))


def check_ascii_flows(paths):
    checks, files, diagrams, seen = [], [], 0, set()

    def add(identifier, status, message, source=None, line=None, column=None):
        checks.append(dict(id=identifier, status=status, message=message,
                           source=str(source) if source else None, line=line, column=column, basis=BASIS))

    def report():
        counts = Counter(item["status"] for item in checks)
        code = 2 if counts["ERROR"] else 1 if counts["FAIL"] else 0
        return dict(scope="marked-ascii-flow-format", files=files, diagrams_checked=diagrams,
                    status=("PASS", "FAIL", "INCOMPLETE")[code], exit_code=code,
                    counts=dict(counts), checks=checks,
                    limits=["표시한 도식의 문자 형식만 검사합니다. 정렬과 흐름의 의미는 별도 확인합니다.",
                            "도식 0개는 도식 검증 완료가 아닙니다. 실제 글꼴/뷰어에서의 표시 확인은 별도입니다."])

    paths = list(paths)
    if not paths:
        add("input", "ERROR", "검사할 Markdown 파일이 필요합니다.")
        return report()
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        add("dependency", "ERROR", f"markdown-it-py가 필요합니다: {exc}")
        return report()
    parser = MarkdownIt("commonmark")
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
            text = source.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
            # Keep lone CR controls on their original line for reporting.
            tokens = parser.parse(markdown_body(text).replace("\r", "\ufffd"))
            lines = text.split("\n")
            for token in tokens:
                if token.type != "fence" or token.info.split() != ["text", "ascii-flow"]:
                    continue
                diagrams += 1
                start, end = token.map
                # The parser consumes the closing fence but excludes it from content.
                # Counting LF (not splitlines) preserves controls for the raw character check.
                closed = token.content.count("\n") == end - start - 2
                add("diagram.fence", "PASS" if closed else "FAIL",
                    "닫는 구분자를 확인했습니다." if closed else "닫는 구분자가 없습니다.",
                    source, start + 1)
                bad = False
                for number in range(start + 1, end - (1 if closed else 0)):
                    for column, char in enumerate(lines[number], 1):
                        if invalid_character(char):
                            bad = True
                            add("diagram.character", "FAIL", f"허용하지 않는 문자 U+{ord(char):04X}",
                                source, number + 1, column)
                if not bad:
                    add("diagram.characters", "PASS", "문자 형식을 확인했습니다.", source, start + 1)
        except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
            add("document.read", "ERROR", str(exc), source)
    if not diagrams and not checks:
        add("diagram.none", "SKIP", "표시된 도식이 없습니다.")
    return report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="도식이 있는 Markdown 정본 파일들")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_ascii_flows(args.files)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} (도식 {result['diagrams_checked']}개)")
        for item in result["checks"]:
            position = f"{item['source']}:{item['line'] or ''}"
            if item["column"]:
                position += f":{item['column']}"
            print(f"  {item['status']} [{item['id']}] {position} {item['message']}")
        for limit in result["limits"]:
            print(f"범위: {limit}")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
