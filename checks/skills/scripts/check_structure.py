#!/usr/bin/env python3
"""Read-only checks for the agreed Aster SKILL.md structure and frontmatter."""

import argparse
import json
import os
from pathlib import Path
import re
import sys

CONTENT = "standards/skills/skill-content.md#skillmd-frontmatter"
VALIDATION = "standards/skills/skill-validation.md#구조-검증"
LAYOUT = "standards/skills/skill-layout.md#기본-구조"


def load_frontmatter(text, yaml):
    """Keep SafeLoader behavior, but reject duplicate explicit mapping keys."""
    class UniqueKeyLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            keys = set()
            for key_node, _ in node.value:
                # A YAML merge may legitimately be overridden by an explicit key.
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue
                key = self.construct_object(key_node, deep=deep)
                try:
                    duplicate = key in keys
                    keys.add(key)
                except TypeError as exc:
                    raise yaml.constructor.ConstructorError(
                        None, None, "unhashable mapping key", key_node.start_mark
                    ) from exc
                if duplicate:
                    raise yaml.constructor.ConstructorError(
                        None, None, "duplicate mapping key", key_node.start_mark
                    )
            return super().construct_mapping(node, deep=deep)

    return yaml.load(text, Loader=UniqueKeyLoader)


def check_structure(directory):
    # abspath normalizes a trailing '/.' without renaming a symlinked directory.
    directory = Path(os.path.abspath(directory))
    skill = directory / "SKILL.md"
    checks = []

    def add(check_id, status, message, basis, line=None):
        checks.append(dict(id=check_id, status=status, message=message,
                           basis=basis, line=line))

    def report():
        states = {item["status"] for item in checks}
        if states & {"ERROR", "UNCHECKED"}:
            status, code = "INCOMPLETE", 2
        elif "FAIL" in states:
            status, code = "FAIL", 1
        else:
            status, code = "PASS", 0
        return dict(target=str(skill), scope="basic-structure", status=status,
                    exit_code=code, checks=checks)

    try:
        if not directory.is_dir():
            add("target.directory", "ERROR", "스킬 디렉토리를 찾을 수 없습니다.", LAYOUT)
            return report()
        if not skill.is_file():
            add("skill.file", "FAIL", "SKILL.md 파일이 없거나 일반 파일이 아닙니다.", LAYOUT)
            return report()
        text = skill.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        add("skill.read", "ERROR", f"파일을 읽을 수 없습니다: {exc}", VALIDATION)
        return report()
    add("skill.file", "PASS", "SKILL.md 파일을 확인했습니다.", LAYOUT)

    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        add("frontmatter.delimiters", "FAIL", "첫 줄에 YAML 시작 구분자가 없습니다.", CONTENT, 1)
        return report()
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        add("frontmatter.delimiters", "FAIL", "YAML 종료 구분자가 없습니다.", CONTENT, 1)
        return report()
    add("frontmatter.delimiters", "PASS", "프론트매터 구분자를 확인했습니다.", CONTENT, 1)

    try:
        import yaml
    except ImportError:
        add("dependency.yaml", "ERROR", "PyYAML이 필요합니다. checks/skills/requirements.txt를 확인하십시오.", VALIDATION)
        return report()
    try:
        data = load_frontmatter("\n".join(lines[1:end]), yaml)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 2 if mark else None
        add("frontmatter.yaml", "FAIL", f"YAML 파싱 오류: {exc}", VALIDATION, line)
        return report()
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        add("frontmatter.mapping", "FAIL", "프론트매터는 문자열 필드명을 가진 YAML 매핑이어야 합니다.", CONTENT, 2)
        return report()
    add("frontmatter.yaml", "PASS", "YAML 매핑을 정상 파싱했습니다.", VALIDATION, 2)

    for field in ("name", "description"):
        if field not in data:
            add(f"{field}.required", "FAIL", f"필수 필드 {field}이(가) 없습니다.", CONTENT)
        elif not isinstance(data[field], str):
            add(f"{field}.type", "FAIL", f"{field}은(는) 문자열이어야 합니다.", CONTENT)
        elif not data[field].strip():
            add(f"{field}.nonempty", "FAIL", f"{field}이(가) 비어 있거나 공백뿐입니다.", VALIDATION)
        else:
            add(f"{field}.value", "PASS", f"{field} 필수 문자열을 확인했습니다.", CONTENT)

    name = data.get("name")
    if isinstance(name, str) and name.strip():
        add("name.directory", "PASS" if name == directory.name else "FAIL",
            f"name={name!r}, 디렉토리명={directory.name!r}을 대조했습니다.", CONTENT)
        add("name.characters", "PASS" if re.fullmatch(r"[a-z0-9-]+", name) else "FAIL",
            "name은 소문자 영문자, 숫자, 하이픈만 허용합니다.", CONTENT)

    for field in sorted(set(data) - {"name", "description"}):
        add("optional.schema", "UNCHECKED",
            f"선택 필드 {field!r}의 공용 형식/지원 기준이 아직 검사기에 정의되지 않았습니다.", CONTENT)
    return report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="검사할 스킬 디렉토리")
    parser.add_argument("--json", action="store_true", help="JSON으로 결과 출력")
    args = parser.parse_args(argv)
    result = check_structure(args.directory)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} {result['target']} (basic-structure)")
        for check in result["checks"]:
            location = f":{check['line']}" if check["line"] else ""
            print(f"  {check['status']} [{check['id']}]{location} {check['message']}")
        print("범위: 기본 구조와 필수 프론트매터. 링크/배포/내용/실행 호환성은 검사하지 않았습니다.")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
