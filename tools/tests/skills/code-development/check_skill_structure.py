#!/usr/bin/env python3
"""Check skill metadata, declared runtime resources and Python syntax."""

import ast
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import require, run_check
from repository_support import Document, ENTRYPOINTS, SKILL


def check(repository, results):
    def metadata():
        doc = Document(repository.text(SKILL + "/SKILL.md"))
        require(doc.meta is not None, "SKILL.md requires valid unique YAML frontmatter")
        name, description = doc.meta.get("name"), doc.meta.get("description")
        require(isinstance(name, str) and name == "code-development" and re.fullmatch(r"[a-z0-9-]+", name), "invalid skill name")
        require(isinstance(description, str) and bool(description.strip()), "description must be nonempty text")
    results.case("S01.metadata", metadata, SKILL + "/SKILL.md")
    for file in ["scripts/" + name + ".py" for name in ENTRYPOINTS] + [
            "scripts/requirements.txt", "references/report-check-contract.md", "references/report-checks.md"]:
        path = SKILL + "/" + file
        def resource(p=path):
            target = repository.resolve(p)
            entry = repository.entries.get(target)
            require(entry is not None and entry[1] == "blob" and entry[0] in ("100644", "100755"),
                    "required resource must resolve to a regular file")
        results.case("S02.resource." + file, resource, path)
    for path in repository.files(SKILL + "/scripts"):
        if path.endswith(".py"):
            def syntax(p=path):
                try:
                    ast.parse(repository.text(p), filename=p)
                except SyntaxError as exc:
                    raise AssertionError(f"Python syntax error at {exc.lineno}: {exc.msg}") from exc
            results.case("S03.syntax." + path, syntax, path)

    def requirements():
        lines = repository.text(SKILL + "/scripts/requirements.txt").splitlines()
        declared = {}
        for line in lines:
            line = line.partition("#")[0].strip()
            match = re.fullmatch(r"(PyYAML|markdown-it-py)\s*(.+)", line, re.IGNORECASE)
            if match:
                package = match[1].lower()
                require(package not in declared, "duplicate parser requirement")
                bounds = set()
                for bound in match[2].split(","):
                    value = re.fullmatch(r"\s*(>=|<)\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*", bound)
                    require(value is not None, "unsupported parser requirement bound")
                    bounds.add((value[1], tuple(int(v or 0) for v in value.groups()[1:])))
                declared[package] = bounds
        require(declared.get("pyyaml") == {(">=", (6, 0, 0)), ("<", (7, 0, 0))}, "PyYAML range differs from contract")
        require(declared.get("markdown-it-py") == {(">=", (3, 0, 0)), ("<", (4, 0, 0))}, "markdown-it-py range differs from contract")
    results.case("S04.requirements", requirements, SKILL + "/scripts/requirements.txt")


if __name__ == "__main__":
    raise SystemExit(run_check(check))
