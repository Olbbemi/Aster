#!/usr/bin/env python3
"""Check actual Markdown references within the selected distribution."""

from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import require, run_check
from repository_support import Document, SKILL, local_target


def check(repository, results):
    cache = {}
    def document(path):
        if path not in cache:
            cache[path] = Document(repository.text(path))
        return cache[path]
    paths = [path for path in repository.files() if path.endswith(".md")]
    results.case("L01.source", lambda: require(SKILL + "/SKILL.md" in paths, "skill Markdown source is absent"))
    for path in paths:
        def links(p=path):
            doc = document(p)
            for index, (destination, line) in enumerate(doc.links()):
                def inspect_link(d=destination, source=p):
                    target = local_target(repository, source, d)
                    if target is None:
                        results.excluded.append({"path": source + " -> " + d, "reason": "external URI; not accessed"})
                        return
                    name, fragment = target
                    if fragment:
                        if not name.lower().endswith(".md"):
                            raise OSError("fragment of a non-Markdown target cannot be judged")
                        require(fragment in document(name).anchors(), "missing Markdown anchor: " + fragment)
                results.case(f"L01-L03.{p}.{index:04d}", inspect_link, p, line)
        results.case("L01.document." + path, links, path)


if __name__ == "__main__":
    raise SystemExit(run_check(check))
