#!/usr/bin/env python3
"""Read-only plugin version checks. Policy: standards/git-workflow.md."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class CheckError(Exception):
    """Input or Git failure: cannot determine compliance."""


class InvalidPlugin(Exception):
    """A changed plugin violates the version policy."""


def version_key(value):
    match = SEMVER.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise InvalidPlugin(f"invalid SemVer version: {value!r}")
    major, minor, patch, prerelease, _build = match.groups()
    identifiers = []
    for part in prerelease.split(".") if prerelease else []:
        if part.isdigit():
            if len(part) > 1 and part.startswith("0"):
                raise InvalidPlugin(f"invalid numeric prerelease: {value!r}")
            identifiers.append((0, int(part)))
        else:
            identifiers.append((1, part))
    return (int(major), int(minor), int(patch), prerelease is None, tuple(identifiers))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidPlugin(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def invalid_constant(value):
    raise InvalidPlugin(f"invalid JSON constant: {value}")


def report(message):
    print(message, file=sys.stderr)


class Checker:
    def __init__(self, remote=None):
        self.remote = remote
        self.snapshots = {}
        self.remote_tips = None
        self.frontiers = {}
        self.root = None
        self.root = self.git("rev-parse", "--show-toplevel").decode().strip()
        if self.git("rev-parse", "--is-shallow-repository").strip() != b"false":
            raise CheckError("shallow history; fetch the full history before checking")

    def command(self, *args):
        command = ["git"]
        if self.root:
            command += ["-C", self.root]
        try:
            return subprocess.run(command + list(args), capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CheckError(f"Git could not run: {exc}") from exc

    def git(self, *args):
        result = self.command(*args)
        if result.returncode:
            detail = result.stderr.decode(errors="replace").strip()
            raise CheckError(f"git {args[0]} failed: {detail}")
        return result.stdout

    def commit(self, ref):
        return self.git("rev-parse", "--verify", "--end-of-options",
                        f"{ref}^{{commit}}").decode().strip()

    def snapshot(self, commit):
        """Map plugin directories to index/tree entries without reading worktree files."""
        if commit is None:
            return {}
        if commit in self.snapshots:
            return self.snapshots[commit]
        if commit == "INDEX":
            data = self.git("ls-files", "--stage", "-z", "--", "plugins")
        else:
            data = self.git("ls-tree", "-r", "-z", "--full-tree", commit, "--", "plugins")
        plugins = {}
        for entry in data.split(b"\0"):
            if not entry:
                continue
            metadata, path = entry.split(b"\t", 1)
            fields = metadata.decode("ascii").split()
            if commit == "INDEX":
                mode, oid, stage = fields
                if stage != "0":
                    raise CheckError("unmerged plugin files in the index")
            else:
                mode, _kind, oid = fields
            parts = os.fsdecode(path).split("/", 2)
            if len(parts) < 2 or parts[0] != "plugins":
                continue
            # A replaced directory (symlink or submodule) still needs a valid manifest.
            relative = parts[2] if len(parts) == 3 else ""
            plugins.setdefault(parts[1], {})[relative] = (mode, oid)
        self.snapshots[commit] = plugins
        return plugins

    def version(self, entries):
        found = [path for path in MANIFESTS if path in entries]
        if len(found) != 1:
            raise InvalidPlugin(f"expected one plugin manifest, found {len(found)}")
        mode, oid = entries[found[0]]
        if mode not in ("100644", "100755"):
            raise InvalidPlugin("plugin manifest must be a regular file")
        try:
            data = json.loads(self.git("cat-file", "blob", oid),
                              object_pairs_hook=unique_object, parse_constant=invalid_constant)
        except ValueError as exc:
            raise InvalidPlugin(f"invalid manifest JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise InvalidPlugin("plugin manifest must be a JSON object")
        value = data.get("version")
        return value, version_key(value)

    def published_tips(self):
        """Query this push's remote, not possibly stale local remote-tracking refs."""
        if self.remote_tips is not None:
            return self.remote_tips
        if not self.remote:
            raise CheckError("a remote is needed to establish published history")
        raw = self.git("ls-remote", "--heads", "--tags", "--", self.remote)
        refs = {}
        for line in raw.splitlines():
            oid, ref = line.decode().split("\t", 1)
            if ref.endswith("^{}"):
                refs[ref[:-3]] = oid
            else:
                refs.setdefault(ref, oid)
        tips = set()
        for ref, oid in refs.items():
            exists = self.command("cat-file", "-t", oid)
            if exists.returncode:
                raise CheckError(f"missing remote object {oid} ({ref}); fetch remote history/tags first")
            resolved = self.command("rev-parse", "--verify", f"{oid}^{{commit}}")
            if resolved.returncode == 0:
                tips.add(resolved.stdout.decode().strip())
            elif ref.startswith("refs/heads/"):
                raise CheckError(f"remote branch {ref} does not resolve to a commit")
            # Tags of blobs/trees have no commit ancestry to use as a baseline.
        self.remote_tips = sorted(tips)
        return self.remote_tips

    def published_frontier(self, target):
        """Find the already-published boundary of the target's new commit range."""
        if target in self.frontiers:
            return self.frontiers[target]
        tips = self.published_tips()
        if not tips:
            frontier = [None]
        else:
            history = self.git("rev-list", "--boundary", target, "--not", *tips).decode().splitlines()
            if not history:
                frontier = [target]  # Target itself is already in published history.
            else:
                frontier = sorted(line[1:] for line in history if line.startswith("-"))
                if not frontier:
                    raise CheckError("no common history with remote; cannot choose a version baseline")
        self.frontiers[target] = frontier
        return frontier

    def published_plugin(self, name, entries, target):
        if not self.remote or target == "INDEX":
            return False
        return any(base is not None and self.snapshot(base).get(name) == entries
                   for base in self.published_frontier(target))

    def check(self, base, target):
        before, after = self.snapshot(base), self.snapshot(target)
        report(f"CHECK {base or 'EMPTY'} -> {target}")
        failed = False
        changed = [name for name in sorted(before.keys() | after.keys())
                   if before.get(name) != after.get(name)
                   and (any(before.get(name, {})) or any(after.get(name, {})))]
        if not changed:
            report("OK no changed plugins")
        for name in changed:
            old, new = before.get(name), after.get(name)
            try:
                if not new:
                    report(f"OK plugins/{name}: REMOVED; no version increase required")
                    continue
                new_text, new_key = self.version(new)
                if not old:
                    report(f"OK plugins/{name}: NEW {new_text}")
                    continue
                old_text, old_key = self.version(old)
                if new_key > old_key:
                    report(f"OK plugins/{name}: {old_text} -> {new_text}")
                elif new_key == old_key and self.published_plugin(name, new, target):
                    report(f"OK plugins/{name}: {old_text} -> {new_text}; published synchronization")
                else:
                    raise InvalidPlugin(f"{old_text} -> {new_text}; changed plugin requires a higher version")
            except InvalidPlugin as exc:
                failed = True
                report(f"FAIL plugins/{name}: {exc}")
        return not failed


def is_zero(oid):
    return not oid.strip("0")


def pre_push(checker, lines):
    updates = []
    for line in lines:
        fields = line.split()
        if len(fields) != 4 or not OID.fullmatch(fields[1]) or not OID.fullmatch(fields[3]):
            raise CheckError("invalid pre-push input; expected local-ref local-oid remote-ref remote-oid")
        updates.append(fields)
    passed = True
    for _local_ref, local_oid, remote_ref, remote_oid in updates:
        report(f"REF {remote_ref}")
        if is_zero(local_oid):
            report("OK ref deletion; no version increase required")
            continue
        target = checker.commit(local_oid)
        bases = (checker.published_frontier(target) if is_zero(remote_oid)
                 else [checker.commit(remote_oid)])
        for base in bases:
            if not checker.check(base, target):
                passed = False
    return 0 if passed else 1



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    check = commands.add_parser("check", help="compare a base commit with a commit or the index")
    check.add_argument("--base", required=True)
    targets = check.add_mutually_exclusive_group(required=True)
    targets.add_argument("--target")
    targets.add_argument("--staged", action="store_true")
    check.add_argument("--remote", help="remote name or URL used to confirm published synchronization")
    hook = commands.add_parser("pre-push", help="consume Git pre-push arguments and stdin")
    hook.add_argument("remote_name")
    hook.add_argument("remote_location")
    args = parser.parse_args()
    try:
        checker = Checker(args.remote_location if args.mode == "pre-push" else getattr(args, "remote", None))
        if args.mode == "pre-push":
            return pre_push(checker, sys.stdin)
        base = checker.commit(args.base)
        target = "INDEX" if args.staged else checker.commit(args.target)
        return 0 if checker.check(base, target) else 1
    except (CheckError, OSError, ValueError) as exc:
        report(f"ERROR {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
