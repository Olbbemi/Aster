#!/usr/bin/env python3
"""Propagate origin/main to every origin/integrate/* without checking them out.

Contract: standards/git-workflow.md, tools/main-propagation.md.
This command pushes real changes to origin. Tests use disposable local remotes.
"""

import argparse
import html
import json
import os
from pathlib import Path
import subprocess


class GitError(RuntimeError):
    pass


class Repository:
    def __init__(self, path):
        self.path = path
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="github-actions[bot]",
                        GIT_AUTHOR_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
                        GIT_COMMITTER_NAME="github-actions[bot]",
                        GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com")

    def git(self, *args, accepted=(0,)):
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path), *args], env=self.env,
                text=True, capture_output=True, timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitError(f"git {args[0]} timed out after 120 seconds") from exc
        if result.returncode not in accepted:
            raise GitError(f"git {args[0]} failed ({result.returncode}): "
                           f"{result.stdout.strip()}\n{result.stderr.strip()}")
        return result

    def output(self, *args):
        return self.git(*args).stdout.strip()

    def contains(self, ancestor, descendant):
        return self.git("merge-base", "--is-ancestor", ancestor, descendant,
                        accepted=(0, 1)).returncode == 0

    def snapshot(self):
        # Update only remote-tracking refs. Never move local branches or the index.
        self.git("fetch", "--atomic", "--prune", "--no-tags", "origin",
                 "+refs/heads/*:refs/remotes/origin/*")
        main = self.output("rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
        refs = self.output("for-each-ref", "--format=%(refname) %(objectname)",
                           "refs/remotes/origin/integrate/")
        branches = []
        for line in refs.splitlines():
            ref, sha = line.split()
            branches.append((ref.removeprefix("refs/remotes/origin/"), sha))
        return main, branches

    def propagate(self, branch, before, main):
        result = {"branch": branch, "before": before, "after": None,
                  "action": "pending", "status": "failure", "detail": ""}
        try:
            if self.contains(main, before):
                result["action"] = "already-current"
                candidate = before
            elif self.contains(before, main):
                result["action"] = "fast-forward"
                candidate = main
            else:
                result["action"] = "merge"
                # Exit 1 means conflicts. Never commit or push that tree.
                tree = self.output("merge-tree", "--write-tree", before, main)
                candidate = self.output(
                    "commit-tree", tree, "-p", before, "-p", main,
                    "-m", f"Merge main into {branch}",
                    "-m", f"Propagate main commit {main} after integration.\n\n"
                          "Preserve the integration branch history and its existing changes.",
                )

            if candidate != before:
                # A normal push rejects intervening, incompatible remote commits.
                # Re-check existence to avoid recreating a branch already deleted.
                self.git("ls-remote", "--exit-code", "origin", f"refs/heads/{branch}")
                self.git("push", "--porcelain", "origin", f"{candidate}:refs/heads/{branch}")

            # Check the remote result, including branches that were already current.
            self.git("fetch", "--no-tags", "origin", f"refs/heads/{branch}")
            after = self.output("rev-parse", "--verify", "FETCH_HEAD^{commit}")
            result["after"] = after
            if not self.contains(main, after) or not self.contains(before, after):
                raise GitError("Remote branch does not contain both main and its previous commit")
            result["status"] = "success"
            result["detail"] = "Remote history verified"
        except (GitError, OSError) as exc:
            result["detail"] = str(exc)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="Repository with origin configured (default: current directory)")
    args = parser.parse_args()
    report = {"main": None, "results": [], "error": None}
    repo = Repository(args.repo)
    try:
        report["main"], branches = repo.snapshot()
        for branch, before in branches:
            report["results"].append(repo.propagate(branch, before, report["main"]))
    except (GitError, OSError) as exc:
        report["error"] = str(exc)

    failed = report["error"] is not None or any(
        item["status"] == "failure" for item in report["results"]
    )
    report["status"] = "failure" if failed else "success"
    # JSON escapes newlines in Git output, so it cannot inject Actions log commands.
    print(json.dumps(report, ensure_ascii=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("## Main propagation\n\n<pre>" +
                         html.escape(json.dumps(report, ensure_ascii=True, indent=2)) +
                         "</pre>\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
