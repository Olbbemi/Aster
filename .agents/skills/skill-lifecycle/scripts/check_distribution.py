#!/usr/bin/env python3
"""Check Aster plugin files and local or branch-specific git-subdir catalogs."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from urllib.parse import urlsplit

LAYOUT = "standards/repository-layout.md#플러그인-경계"
VALIDATION = "standards/skills/skill-validation.md#하네스-및-배포-검증"
CLAUDE = "https://code.claude.com/docs/en/plugins-reference"
CATALOGS = {"codex": "https://learn.chatgpt.com/docs/enterprise/plugin-management",
            "claude": "https://code.claude.com/docs/en/plugins/marketplace-reference"}


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


def git_source(value):
    """Normalize the deliberately limited, branch-based source profile."""
    if not isinstance(value, dict) or set(value) != {"source", "url", "path", "ref"}:
        raise ValueError("git-subdir 소스에는 source, url, path, ref 필드만 필요합니다.")
    if value["source"] != "git-subdir":
        raise ValueError("지원하는 원격 소스는 git-subdir입니다.")
    url, ref = value["url"], value["ref"]
    if not isinstance(url, str) or any(c.isspace() for c in url):
        raise ValueError("Git URL 문자열이 필요합니다.")
    parsed = urlsplit(url)
    # file:// is for local Git fixtures; it does not assert CLI support.
    if (parsed.scheme not in {"https", "file"} or parsed.query or parsed.fragment
            or parsed.username or parsed.password
            or (parsed.scheme == "https" and not parsed.hostname)
            or (parsed.scheme == "file" and (parsed.netloc or not parsed.path.startswith("/")))):
        raise ValueError("이 검사 범위는 HTTPS Git URL 또는 로컬 시험용 file:/// URL입니다.")
    if (not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", ref)
            or ".." in ref or "//" in ref or ref.endswith(("/", "."))
            or any(p.startswith(".") or p.endswith(".lock") for p in ref.split("/"))):
        raise ValueError("ref에는 유효한 branch 이름이 필요합니다. tag/sha 선택은 이 범위 밖입니다.")
    return dict(source="git-subdir", url=url, path=relative_name(value["path"]), ref=ref)


class DistributionCheck:
    def __init__(self, plugin, repository, expectations, source_repository=None, verify_remote=False):
        self.plugin = Path(plugin).absolute()
        self.repository = Path(repository).absolute()
        self.expectations = Path(expectations).absolute()
        self.checks = []
        self.expected_files = []
        self.actual_files = []
        self.expected_source = None
        self.source_repository = Path(source_repository or repository).absolute()
        self.verify_remote = verify_remote
        self.remote_commit = None
        self.remote_checked = False

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

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.source_repository), *args],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        if result.returncode:
            raise OSError(result.stderr.decode("utf-8", errors="replace").strip()
                          or f"Git 종료 코드 {result.returncode}")
        return result.stdout

    def remote_snapshot(self, source):
        if self.remote_checked:
            return
        self.remote_checked = True
        if not self.verify_remote:
            self.add("source.remote", "UNCHECKED", self.expectations,
                     "원격 ref/파일 대조에는 --verify-remote가 필요합니다.")
            return
        try:
            ref = "refs/heads/" + source["ref"]
            rows = self.git("ls-remote", "--exit-code", "--refs", "--", source["url"], ref).decode().splitlines()
            matches = [row.split("\t")[0] for row in rows if row.endswith("\t" + ref)]
            if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{40}", matches[0]):
                raise ValueError("원격 branch의 단일 SHA-1 커밋을 확인하지 못했습니다.")
            self.remote_commit = matches[0]
            self.git("cat-file", "-e", self.remote_commit + "^{commit}")
            tree = self.git("ls-tree", "-r", "-z", self.remote_commit + ":" + source["path"])
            files = {}
            for row in tree.split(b"\0"):
                if not row:
                    continue
                metadata, name = row.split(b"\t", 1)
                mode, kind, oid = metadata.decode("ascii").split()
                files[relative_name(name.decode("utf-8"))] = (mode, kind, oid)
            same_names = set(files) == set(self.actual_files) == set(self.expected_files)
            self.add("source.inventory", "PASS" if same_names else "FAIL", self.plugin,
                     f"원격 {self.remote_commit}:{source['path']}의 파일 집합과 기대/실제 목록 대조")
            matched = 0
            for name in sorted(set(files) & set(self.actual_files)):
                mode, kind, oid = files[name]
                path = self.plugin / name
                if kind != "blob" or mode not in {"100644", "100755"}:
                    self.add("source.kind", "UNCHECKED", path,
                             "원격 symlink/submodule 등 일반 파일 외 항목은 미검사입니다.")
                    continue
                if path.is_symlink() or not path.resolve(strict=True).is_relative_to(self.plugin):
                    self.add("source.file", "FAIL", path, "원격 일반 파일과 다른 링크입니다.")
                    continue
                info = path.stat()
                if not stat.S_ISREG(info.st_mode):
                    self.add("source.file", "FAIL", path, "일반 파일이 아닙니다.")
                    continue
                content = self.git("cat-file", "blob", oid)
                same = path.read_bytes() == content and bool(info.st_mode & stat.S_IXUSR) == (mode == "100755")
                if not same:
                    self.add("source.file", "FAIL", path, f"원격 blob {oid}의 내용 또는 실행 권한과 다릅니다.")
                else:
                    matched += 1
            self.add("source.snapshot", "PASS" if same_names and matched == len(files) else "FAIL",
                     self.plugin, f"원격 커밋 {self.remote_commit}의 일반 파일 {matched}/{len(files)}개 일치")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.add("source.remote", "ERROR", self.source_repository, str(exc))

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
        if self.expected_source is not None:
            try:
                normalized = git_source(source)
            except ValueError as exc:
                self.add("catalog.source", "FAIL", path, str(exc), basis)
            else:
                same = normalized == self.expected_source
                self.add("catalog.target", "PASS" if same else "FAIL", path,
                         "URL, branch ref, 하위 경로를 독립 기대 소스와 대조했습니다.", str(self.expectations))
                if same:
                    self.remote_snapshot(normalized)
        elif isinstance(source, dict) and source.get("source") == "git-subdir":
            self.add("catalog.source", "UNCHECKED", path,
                     "git-subdir 검사에는 기대 구성의 source가 필요합니다.", basis)
        else:
            self.local_source(harness, source, path, basis)
        if harness == "codex":
            self.text_field(entry, "category", path, basis)
            policy = entry.get("policy")
            if not isinstance(policy, dict):
                self.add("catalog.policy", "FAIL", path, "policy object가 필요합니다.", basis)
            else:
                for key in ("installation", "authentication"):
                    self.text_field(policy, key, path, basis)

    def local_source(self, harness, source, path, basis):
        if harness == "codex" and isinstance(source, dict) and source.get("source") == "local":
            source = source.get("path")
        if isinstance(source, dict):
            self.add("catalog.source", "UNCHECKED", path, "로컬 경로 외 source 형식은 이 검사기에서 확인하지 않습니다.", basis)
        else:
            resolved = self.resolve_directory(self.repository, source, path, "catalog.source", basis)
            if resolved:
                self.add("catalog.target", "PASS" if resolved == self.plugin else "FAIL", path,
                         f"등록 대상 {resolved}과 검사 대상 {self.plugin} 대조", str(self.expectations))

    def run(self):
        try:
            self.plugin = self.plugin.resolve(strict=True)
            self.repository = self.repository.resolve(strict=True)
            if not self.plugin.is_dir() or not self.repository.is_dir():
                raise ValueError("플러그인/저장소 디렉토리가 필요합니다.")
        except (OSError, RuntimeError, ValueError) as exc:
            self.add("input.directory", "ERROR", self.plugin, str(exc))
            return self.report()
        expected = self.read_json(self.expectations, input_file=True)
        if expected is None:
            return self.report()
        try:
            if set(expected) not in ({"plugin_name", "manifest", "files"}, {"plugin_name", "manifest", "files", "source"}):
                raise ValueError("기대 구성에는 plugin_name, manifest, files 및 선택 source만 허용합니다.")
            if "source" in expected:
                self.expected_source = git_source(expected["source"])
            elif not self.plugin.is_relative_to(self.repository):
                raise ValueError("로컬 플러그인이 지정 저장소의 경계 안에 있어야 합니다.")
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
        return dict(scope="aster-git-subdir-distribution" if self.expected_source else "aster-local-distribution",
                    status=status, exit_code=code, remote_commit=self.remote_commit,
                    source_repository=str(self.source_repository),
                    plugin=str(self.plugin), repository=str(self.repository),
                    expectations=str(self.expectations), expected_files=self.expected_files,
                    actual_files=self.actual_files, checks=self.checks)


def check_distribution(plugin, repository, expectations, source_repository=None, verify_remote=False):
    return DistributionCheck(plugin, repository, expectations, source_repository, verify_remote).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin", type=Path, help="플러그인 최상위 디렉토리")
    parser.add_argument("--repository-root", type=Path, required=True, help="두 marketplace가 있는 저장소 루트")
    parser.add_argument("--expected-files", type=Path, required=True, help="plugin_name/manifest/files 기대 구성 JSON")
    parser.add_argument("--source-repository", type=Path, help="원격 커밋 객체가 준비된 로컬 Git 저장소 (기본: repository-root)")
    parser.add_argument("--verify-remote", action="store_true", help="원격 branch 조회 및 준비된 객체와 파일 대조 (자동 fetch 없음)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check_distribution(args.plugin, args.repository_root, args.expected_files,
                                args.source_repository, args.verify_remote)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['status']} {result['plugin']} ({result['scope']})")
        for c in result["checks"]:
            print(f"  {c['status']} [{c['id']}] {c['source']}: {c['message']}")
        print("범위: 기본 JSON/소스/기대 파일 목록 및 선택 원격 대조. 전체 제품 스키마와 실제 설치/로딩은 미검사입니다.")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
