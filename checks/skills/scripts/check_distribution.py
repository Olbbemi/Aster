#!/usr/bin/env python3
"""Check an Aster local plugin's manifest, two catalogs and expected file inventory."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

LAYOUT = "standards/repository-layout.md#플러그인-경계"
VALIDATION = "standards/skills/skill-validation.md#하네스-및-배포-검증"
CLAUDE = "https://code.claude.com/docs/en/plugins-reference"
CATALOGS = {"codex": "https://developers.openai.com/plugins/build/plugins",
            "claude": "https://code.claude.com/docs/en/plugin-marketplaces"}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"중복 JSON 키: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"JSON에서 허용하지 않는 값: {value}")


def relative_name(value):
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("비어 있지 않은 / 구분 상대 경로가 필요합니다.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) == ".":
        raise ValueError("파일 경로에 절대 경로, .. 또는 루트를 사용할 수 없습니다.")
    return str(path)


class DistributionCheck:
    def __init__(self, plugin, repository, expectations):
        self.plugin = Path(plugin).absolute()
        self.repository = Path(repository).absolute()
        self.expectations = Path(expectations).absolute()
        self.checks = []
        self.expected_files = []
        self.actual_files = []

    def add(self, check_id, status, source, message, basis=VALIDATION):
        self.checks.append(dict(id=check_id, status=status, source=str(source),
                                message=message, basis=basis))

    def read_json(self, path, input_file=False):
        invalid = "ERROR" if input_file else "FAIL"
        try:
            if not path.is_file():
                self.add("json.file", invalid, path, "JSON 파일이 없거나 일반 파일이 아닙니다.")
                return None
            data = json.loads(path.read_text(encoding="utf-8-sig"),
                              object_pairs_hook=unique_object, parse_constant=reject_constant)
            if not isinstance(data, dict):
                raise ValueError("최상위 JSON object가 필요합니다.")
        except (ValueError, UnicodeError, RecursionError) as exc:
            self.add("json.format", invalid, path, str(exc))
            return None
        except OSError as exc:
            self.add("json.read", "ERROR", path, str(exc))
            return None
        self.add("json.format", "PASS", path, "JSON object를 정상 파싱했습니다.")
        return data

    def text_field(self, obj, key, source, basis, required=True):
        if key not in obj and not required:
            return True
        value = obj.get(key)
        valid = isinstance(value, str) and bool(value.strip())
        self.add("field." + key, "PASS" if valid else "FAIL", source,
                 f"{key}: 비공백 문자열 {'확인' if valid else '필요'}", basis)
        return valid

    def resolve_directory(self, base, value, source, check_id, basis, allow_dot=False):
        if not isinstance(value, str) or not (value.startswith("./") or (allow_dot and value == ".")):
            self.add(check_id, "FAIL", source, "./로 시작하는 상대 경로가 필요합니다.", basis)
            return None
        if "\\" in value or "\0" in value or ".." in PurePosixPath(value).parts:
            self.add(check_id, "FAIL", source, "경로에 역슬래시, NUL 또는 ..가 있습니다.", basis)
            return None
        try:
            resolved = (base / value).resolve(strict=True)
            if not resolved.is_relative_to(base):
                self.add(check_id, "FAIL", source, f"기준 경계 밖의 대상입니다: {resolved}", LAYOUT)
                return None
            if not resolved.is_dir():
                self.add(check_id, "FAIL", source, f"디렉토리가 아닙니다: {resolved}", basis)
                return None
        except (FileNotFoundError, NotADirectoryError):
            self.add(check_id, "FAIL", source, f"디렉토리가 없습니다: {value}", basis)
            return None
        except (OSError, RuntimeError, ValueError) as exc:
            self.add(check_id, "ERROR", source, str(exc), basis)
            return None
        self.add(check_id, "PASS", source, f"경계 안의 디렉토리 확인: {resolved}", basis)
        return resolved

    def inventory(self):
        complete = True
        def walk_error(exc):
            nonlocal complete
            complete = False
            self.add("inventory.read", "ERROR", exc.filename, str(exc))

        for parent, dirs, files in os.walk(self.plugin, onerror=walk_error, followlinks=False):
            dirs.sort()
            for name in dirs[:]:
                child = Path(parent) / name
                try:
                    linked = child.is_symlink()
                except OSError as exc:
                    dirs.remove(name)
                    complete = False
                    self.add("inventory.read", "ERROR", child, str(exc))
                    continue
                if linked:
                    dirs.remove(name)
                    complete = False
                    try:
                        inside = child.resolve(strict=True).is_relative_to(self.plugin)
                        self.add("inventory.symlink", "UNCHECKED" if inside else "FAIL", child,
                                 "디렉토리 링크는 목록을 재귀 수집하지 않습니다." if inside else "배포 경계 밖의 링크입니다.", LAYOUT)
                    except (OSError, RuntimeError) as exc:
                        self.add("inventory.symlink", "ERROR", child, str(exc))
            for name in sorted(files):
                path = Path(parent) / name
                self.actual_files.append(path.relative_to(self.plugin).as_posix())
                try:
                    resolved = path.resolve(strict=True)
                    if not resolved.is_relative_to(self.plugin):
                        self.add("inventory.boundary", "FAIL", path, "배포 경계 밖의 파일을 가리킵니다.", LAYOUT)
                    elif not stat.S_ISREG(path.stat().st_mode):
                        self.add("inventory.kind", "FAIL", path, "일반 파일이 아닙니다.")
                except (FileNotFoundError, NotADirectoryError):
                    self.add("inventory.file", "FAIL", path, "파일이 없거나 끊어진 링크입니다.")
                except (OSError, RuntimeError) as exc:
                    complete = False
                    self.add("inventory.read", "ERROR", path, str(exc))
        self.actual_files.sort()
        if not complete:
            self.add("inventory.compare", "UNCHECKED", self.plugin, "전체 목록을 읽지 못해 정확한 파일 집합 대조를 완료하지 못했습니다.")
            return
        expected, actual = set(self.expected_files), set(self.actual_files)
        for name in sorted(expected - actual):
            self.add("inventory.missing", "FAIL", self.plugin / name, "기대 배포 파일이 누락되었습니다.")
        for name in sorted(actual - expected):
            self.add("inventory.extra", "FAIL", self.plugin / name, "기대 목록에 없는 파일이 배포 경계에 있습니다.")
        if expected == actual:
            self.add("inventory.compare", "PASS", self.plugin, f"기대/실제 파일 {len(expected)}개가 일치합니다.")

    def manifest(self, expected):
        path = self.plugin / expected["manifest"]
        try:
            if not path.resolve().is_relative_to(self.plugin):
                self.add("manifest.boundary", "FAIL", path, "manifest가 배포 경계 밖을 가리킵니다.", LAYOUT)
                return
        except (OSError, RuntimeError) as exc:
            self.add("manifest.boundary", "ERROR", path, str(exc))
            return
        data = self.read_json(path)
        if data is None:
            return
        if self.text_field(data, "name", path, CLAUDE):
            self.add("manifest.name", "PASS" if data["name"] == expected["plugin_name"] else "FAIL",
                     path, f"manifest name과 기대 이름 {expected['plugin_name']!r} 대조", str(self.expectations))
        for key in ("version", "description"):
            # Both are optional strings; empty description is not made mandatory.
            if key in data:
                self.add("manifest." + key, "PASS" if isinstance(data[key], str) else "FAIL",
                         path, f"선택 필드 {key}의 문자열 형식 대조", CLAUDE)
        for key in sorted(set(data) - {"name", "version", "description", "skills"}):
            self.add("manifest.optional", "UNCHECKED", path,
                     f"추가 필드 {key!r}은 이 기본 검사기의 스키마 범위 밖입니다.", CLAUDE)
        paths = data.get("skills", "./skills/")
        if isinstance(paths, str):
            paths = [paths]
        if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
            self.add("manifest.skills", "FAIL", path, "skills에는 경로 문자열 또는 문자열 배열이 필요합니다.", CLAUDE)
            return
        roots = []
        for value in paths:
            resolved = self.resolve_directory(self.plugin, value, path, "manifest.skills", CLAUDE, allow_dot=True)
            if resolved:
                roots.append(resolved)
        default = self.plugin / "skills"
        try:
            if default.is_dir():
                resolved = default.resolve(strict=True)
                if resolved.is_relative_to(self.plugin):
                    roots.append(resolved)
        except (OSError, RuntimeError) as exc:
            self.add("manifest.skills", "ERROR", default, str(exc))
        for name in self.expected_files:
            if PurePosixPath(name).name != "SKILL.md":
                continue
            skill = self.plugin / name
            try:
                location = skill.resolve(strict=True)
                covered = skill.is_file() and any(location.is_relative_to(root) for root in roots)
                self.add("manifest.skill-file", "PASS" if covered else "FAIL", skill,
                         "기대 SKILL.md의 스킬 경로 내 배치를 대조했습니다.", CLAUDE)
            except (FileNotFoundError, NotADirectoryError):
                self.add("manifest.skill-file", "FAIL", skill, "기대 SKILL.md가 없습니다.")
            except (OSError, RuntimeError) as exc:
                self.add("manifest.skill-file", "ERROR", skill, str(exc))

    def catalog(self, harness, plugin_name):
        relative = ".agents/plugins/marketplace.json" if harness == "codex" else ".claude-plugin/marketplace.json"
        path = self.repository / relative
        basis = CATALOGS[harness]
        data = self.read_json(path)
        if data is None:
            return
        self.text_field(data, "name", path, basis)
        if harness == "claude":
            owner = data.get("owner")
            if not isinstance(owner, dict):
                self.add("catalog.owner", "FAIL", path, "owner object가 필요합니다.", basis)
            else:
                self.text_field(owner, "name", path, basis)
        entries = data.get("plugins")
        if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
            self.add("catalog.plugins", "FAIL", path, "plugins object 배열이 필요합니다.", basis)
            return
        names = [e.get("name") for e in entries]
        if any(not isinstance(n, str) or not n.strip() for n in names):
            self.add("catalog.plugin-names", "FAIL", path, "각 항목의 name 문자열이 필요합니다.", basis)
        elif len(set(names)) != len(names):
            self.add("catalog.plugin-names", "FAIL", path, "중복 플러그인 이름이 있습니다.", basis)
        matches = [e for e in entries if e.get("name") == plugin_name]
        if len(matches) != 1:
            self.add("catalog.registration", "FAIL", path, f"{plugin_name!r} 등록 {len(matches)}개: 정확히 1개 필요", str(self.expectations))
            return
        entry = matches[0]
        self.add("catalog.registration", "PASS", path, f"{plugin_name!r} 등록을 확인했습니다.", str(self.expectations))
        source = entry.get("source")
        if harness == "codex" and isinstance(source, dict) and source.get("source") == "local":
            source = source.get("path")
        if isinstance(source, dict):
            self.add("catalog.source", "UNCHECKED", path, "로컬 경로 외 source 형식은 이 검사기에서 확인하지 않습니다.", basis)
        else:
            resolved = self.resolve_directory(self.repository, source, path, "catalog.source", basis)
            if resolved:
                self.add("catalog.target", "PASS" if resolved == self.plugin else "FAIL", path,
                         f"등록 대상 {resolved}과 검사 대상 {self.plugin} 대조", str(self.expectations))
        if harness == "codex":
            self.text_field(entry, "category", path, basis)
            policy = entry.get("policy")
            if not isinstance(policy, dict):
                self.add("catalog.policy", "FAIL", path, "policy object가 필요합니다.", basis)
            else:
                for key in ("installation", "authentication"):
                    self.text_field(policy, key, path, basis)

    def run(self):
        try:
            self.plugin = self.plugin.resolve(strict=True)
            self.repository = self.repository.resolve(strict=True)
            if not self.plugin.is_dir() or not self.repository.is_dir():
                raise ValueError("플러그인/저장소 디렉토리가 필요합니다.")
            if not self.plugin.is_relative_to(self.repository):
                raise ValueError("플러그인이 지정 저장소의 경계 안에 있어야 합니다.")
        except (OSError, RuntimeError, ValueError) as exc:
            self.add("input.directory", "ERROR", self.plugin, str(exc))
            return self.report()
        expected = self.read_json(self.expectations, input_file=True)
        if expected is None:
            return self.report()
        try:
            if set(expected) != {"plugin_name", "manifest", "files"}:
                raise ValueError("기대 구성에는 plugin_name, manifest, files 필드가 필요합니다.")
            if not isinstance(expected["plugin_name"], str) or not expected["plugin_name"].strip():
                raise ValueError("기대 plugin_name은 비공백 문자열이어야 합니다.")
            if not isinstance(expected["files"], list) or not expected["files"]:
                raise ValueError("기대 files는 비어 있지 않은 상대 파일 경로 배열이어야 합니다.")
            self.expected_files = sorted(relative_name(p) for p in expected["files"])
            if len(set(self.expected_files)) != len(self.expected_files):
                raise ValueError("기대 files에 중복 경로가 있습니다.")
            expected["manifest"] = relative_name(expected["manifest"])
            if expected["manifest"] not in self.expected_files:
                raise ValueError("기대 manifest는 files 목록에 포함되어야 합니다.")
        except (ValueError, TypeError) as exc:
            self.add("input.expectations", "ERROR", self.expectations, str(exc))
            return self.report()
        self.inventory()
        self.manifest(expected)
        self.catalog("codex", expected["plugin_name"])
        self.catalog("claude", expected["plugin_name"])
        return self.report()

    def report(self):
        counts = Counter(c["status"] for c in self.checks)
        if counts["ERROR"] or counts["UNCHECKED"]:
            status, code = "INCOMPLETE", 2
        elif counts["FAIL"]:
            status, code = "FAIL", 1
        else:
            status, code = "PASS", 0
        return dict(scope="aster-local-distribution", status=status, exit_code=code,
                    plugin=str(self.plugin), repository=str(self.repository),
                    expectations=str(self.expectations), expected_files=self.expected_files,
                    actual_files=self.actual_files, checks=self.checks)


def check_distribution(plugin, repository, expectations):
    return DistributionCheck(plugin, repository, expectations).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin", type=Path, help="플러그인 최상위 디렉토리")
    parser.add_argument("--repository-root", type=Path, required=True, help="두 marketplace가 있는 저장소 루트")
    parser.add_argument("--expected-files", type=Path, required=True, help="plugin_name/manifest/files 기대 구성 JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_distribution(args.plugin, args.repository_root, args.expected_files)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} {result['plugin']} ({result['scope']})")
        for c in result["checks"]:
            print(f"  {c['status']} [{c['id']}] {c['source']}: {c['message']}")
        print("범위: 기본 JSON/로컬 경로/기대 파일 목록. 전체 제품 스키마와 실제 설치/로딩은 미검사입니다.")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
