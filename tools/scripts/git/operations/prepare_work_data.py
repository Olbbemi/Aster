#!/usr/bin/env python3
"""Prepare project-owned work data for checkout or explicit initialization."""

from pathlib import Path
import subprocess
import sys


def git_path(option):
    result = subprocess.run(
        ["git", "rev-parse", option], check=True, capture_output=True, text=True,
    )
    return Path(result.stdout.strip()).resolve()


def check_directory(path):
    # Check every existing ancestor before creating anything. Never repair links.
    for candidate in (path, *path.parents):
        if candidate.is_symlink() and not candidate.is_dir():
            raise OSError(f"broken or non-directory link: {candidate}")
        if candidate.exists() and not candidate.is_dir():
            raise OSError(f"not a directory: {candidate}")


def prepare(root):
    public = Path.home() / ".local/share/aster"
    if public.is_symlink():
        check_directory(public)
        data = public.resolve(strict=True)
    elif public.exists():
        raise OSError(f"shared path is not a symlink: {public}")
    else:
        data = root / "data"
        if data.is_symlink():
            raise OSError(f"project data must be a real directory: {data}")
    for path in (public.parent, data, data / "todo", data / "cargo"):
        check_directory(path)
    for name in ("todo", "cargo"):
        (data / name).mkdir(parents=True, exist_ok=True)
    public.parent.mkdir(parents=True, exist_ok=True)
    if not public.is_symlink():
        # symlink() refuses a concurrent conflicting path instead of replacing it.
        public.symlink_to(data, target_is_directory=True)


def main():
    args = sys.argv[1:]
    if args not in (["--initialize"], ["--checkout"]):
        print("Usage: prepare_work_data.py --initialize | --checkout", file=sys.stderr)
        return 1
    explicit = args == ["--initialize"]
    try:
        root = git_path("--show-toplevel")
        if git_path("--git-dir") != git_path("--git-common-dir"):
            if explicit:
                raise OSError("initialize in the main worktree, not a linked worktree")
            return 0
        prepare(root)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Aster work-data preparation: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
