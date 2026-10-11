#!/usr/bin/env python3
"""Validate targets and list their structure without reading content."""

import sys
import os
from pathlib import Path

from runtime_common import fail
from source_access import directory_fd, output_root, targets
from runtime_common import Parser, run_cli


def inspect(args):
    if not args.target or not args.output_root:
        fail("MISSING_INPUT", "분석 대상과 저장 기준 경로를 모두 지정하십시오.")
    root = output_root(args.output_root)
    found = []
    for path in targets(args.target):
        entry = {"path": str(path), "kind": "directory" if path.is_dir() else "file"}
        if path.is_dir():
            structure = []

            def walk(folder, prefix=Path()):
                with os.scandir(folder) as entries:
                    for child in sorted(entries, key=lambda item: item.name):
                        kind = ("link" if child.is_symlink() else
                                "directory" if child.is_dir(follow_symlinks=False) else
                                "file" if child.is_file(follow_symlinks=False) else "special")
                        relative = prefix / child.name
                        structure.append({"path": str(relative), "kind": kind})
                        if kind == "directory":
                            fd = os.open(child.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                         dir_fd=folder)
                            try:
                                walk(fd, relative)
                            finally:
                                os.close(fd)
            with directory_fd(path) as folder:
                walk(folder)
            entry["structure"] = structure
        found.append(entry)
    return {"targets": found, "output_root": str(root)}


def execute(args):
    return inspect(args)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    return run_cli('inspect', parser, execute, argv)


if __name__ == "__main__":
    sys.exit(main())
