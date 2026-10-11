#!/usr/bin/env python3
"""Run plugin version and registered skill checks for Git's exact push input."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# The project hook uses isolated Python; only this operations directory is added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_plugin_versions as versions


SKILL_PATH = re.compile(r"^(?:\.agents/skills|plugins/[^/]+/skills)/([^/]+)(?:/|$)")
SCRIPT_NAME = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.py")
CHECK_TIMEOUT = 60


def skill_jobs(checker, lines):
    """Select each changed skill once per target commit, across all push refs."""
    jobs = {}
    for line in lines:
        _local_ref, local_oid, remote_ref, remote_oid = line.split()
        if versions.is_zero(local_oid):
            continue
        target = checker.commit(local_oid)
        bases = (checker.published_frontier(target) if versions.is_zero(remote_oid)
                 else [checker.commit(remote_oid)])
        names = set()
        for base in bases:
            if base is None:
                paths = checker.git("ls-tree", "-r", "-z", "--name-only", "--full-tree", target)
            else:
                paths = checker.git("diff", "--name-only", "-z", "--no-renames",
                                    "--no-ext-diff", "--no-textconv", base, target, "--")
            for raw in paths.split(b"\0"):
                match = SKILL_PATH.match(os.fsdecode(raw))
                if match:
                    name = match[1]
                    if name in (".", ".."):
                        raise versions.CheckError("invalid skill directory name")
                    names.add(name)
        versions.report(f"SKILLS {remote_ref} -> {target}: {', '.join(sorted(names)) or 'none'}")
        jobs.setdefault(target, set()).update(names)
    return jobs


def registered_scripts(root, name):
    """Read explicit registration; never infer hook checks from script names."""
    directory = Path(root) / "tools/tests/skills" / name
    manifest = directory / "checks.json"
    if not manifest.is_symlink() and not manifest.exists():
        return None
    for path in (directory.parent, directory, manifest):
        if path.is_symlink():
            raise versions.CheckError(f"registration must not use symlinks: {path}")
    if not manifest.is_file():
        raise versions.CheckError(f"registration is not a regular file: {manifest}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"),
                          object_pairs_hook=versions.unique_object,
                          parse_constant=versions.invalid_constant)
    except (OSError, ValueError, versions.InvalidPlugin) as exc:
        raise versions.CheckError(f"invalid registration {manifest}: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"scripts"}:
        raise versions.CheckError(f"registration must contain only scripts: {manifest}")
    scripts = data["scripts"]
    if (not isinstance(scripts, list) or not scripts
            or any(not isinstance(name, str) or not SCRIPT_NAME.fullmatch(name) for name in scripts)
            or len(set(scripts)) != len(scripts)):
        raise versions.CheckError(f"scripts must be unique Python basenames: {manifest}")
    paths = [directory / filename for filename in scripts]
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise versions.CheckError(f"registered script is missing or not a regular file: {path}")
    return paths


def run_skill_check(root, name, script, commit):
    label = f"{name}/{script.name}"
    versions.report(f"CHECK {label} @ {commit}")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(script), "--repository-root", str(root),
             "--revision", commit, "--json"],
            cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=CHECK_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        versions.report(f"ERROR {label}: {exc}")
        return 2
    if result.stderr.strip():
        versions.report(result.stderr.strip())
    try:
        data = json.loads(result.stdout, object_pairs_hook=versions.unique_object,
                          parse_constant=versions.invalid_constant)
    except (ValueError, versions.InvalidPlugin) as exc:
        versions.report(f"ERROR {label}: invalid JSON result (exit {result.returncode}): {exc}")
        return 2
    if not isinstance(data, dict) or type(data.get("passed")) is not bool:
        versions.report(f"ERROR {label}: result must contain boolean passed")
        return 2
    if data["passed"] != (result.returncode == 0):
        versions.report(f"ERROR {label}: boolean result and exit {result.returncode} disagree")
        return 2
    if data["passed"]:
        versions.report(f"OK {label}")
        return 0
    status = 1 if result.returncode == 1 else 2
    versions.report(f"FAIL {label}: exit {result.returncode}")
    checks = data.get("checks", [])
    for check in checks if isinstance(checks, list) else []:
        if not isinstance(check, dict):
            continue
        issues = check.get("issues", [])
        for issue in issues if isinstance(issues, list) else []:
            if not isinstance(issue, dict):
                continue
            kind = issue.get("kind", "violation")
            if kind == "error":
                status = 2
            position = str(issue.get("path", ""))
            if issue.get("line"):
                position += f":{issue['line']}"
            versions.report(f"  {kind} {check.get('id', '')} {position}: {issue.get('message', '')}")
    return status


def check_skills(checker, lines):
    status = 0
    for commit, names in skill_jobs(checker, lines).items():
        for name in sorted(names):
            try:
                scripts = registered_scripts(checker.root, name)
            except (versions.CheckError, OSError) as exc:
                versions.report(f"ERROR {name}: {exc}")
                status = 2
                continue
            if scripts is None:
                versions.report(f"SKIP {name}: no registered skill checks")
                continue
            for script in scripts:
                status = max(status, run_skill_check(checker.root, name, script, commit))
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("remote_name")
    parser.add_argument("remote_location")
    args = parser.parse_args(argv)
    try:
        checker = versions.Checker(args.remote_location)
        lines = list(sys.stdin)
        # Existing version validation also validates every input line before use.
        version_status = versions.pre_push(checker, lines)
        skill_status = check_skills(checker, lines)
        return max(version_status, skill_status)
    except (versions.CheckError, OSError, ValueError, subprocess.SubprocessError) as exc:
        versions.report(f"ERROR {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
