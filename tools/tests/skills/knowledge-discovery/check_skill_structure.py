#!/usr/bin/env python3
"""Validate knowledge-discovery metadata, local references and Python syntax."""

import ast
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import unittest
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import run_check
from repository_support import SKILL, Violation, anchors, body, frontmatter, safe_mapping


class SkillStructureChecks(unittest.TestCase):
    """Static conditions of the skill itself, without executing skill code."""

    def test_skill_frontmatter(self):
        import yaml

        path = SKILL + "/SKILL.md"
        data = safe_mapping(frontmatter(self.repository.read(path).decode("utf-8-sig"))[0], yaml)
        for key in ("name", "description"):
            self.assertIsInstance(data.get(key), str, key)
            self.assertTrue(data[key].strip(), key)
        self.assertEqual(PurePosixPath(SKILL).name, data["name"])
        self.assertRegex(data["name"], r"\A[a-z0-9-]+\Z")

    def test_local_markdown_references(self):
        from markdown_it import MarkdownIt

        parser = MarkdownIt("commonmark").enable("table")
        parser.validateLink = lambda destination: True
        cache = {}

        def tokens(path):
            if path not in cache:
                cache[path] = parser.parse(body(self.repository.read(path).decode("utf-8-sig")))
            return cache[path]

        for path in self.repository.files(".md"):
            for token in tokens(path):
                if token.type != "inline":
                    continue
                for item in token.children or []:
                    destination = (item.attrGet("href") if item.type == "link_open" else
                                   item.attrGet("src") if item.type == "image" else None)
                    if destination is None:
                        continue
                    with self.subTest(path=path, link=destination):
                        parts = urlsplit(destination)
                        decoded = unquote(parts.path, encoding="utf-8", errors="strict")
                        if (parts.scheme.lower() == "file"
                                or (not destination.startswith("//")
                                    and PureWindowsPath(destination).is_absolute())
                                or (not parts.scheme and not parts.netloc
                                    and PurePosixPath(decoded).is_absolute())):
                            raise Violation("Use a repository-relative local reference: " + destination)
                        if parts.scheme or parts.netloc or destination.startswith("//"):
                            continue
                        target = str(PurePosixPath(path).parent / decoded) if decoded else path
                        kind = self.repository.kind(target)
                        if parts.fragment:
                            self.assertIsNone(re.search(r"%(?![0-9a-fA-F]{2})", parts.fragment))
                            fragment = unquote(parts.fragment, encoding="utf-8", errors="strict")
                            self.assertNotIn("\0", fragment)
                            if kind != "file" or PurePosixPath(target).suffix.lower() != ".md":
                                raise OSError("Cannot judge a fragment on a non-Markdown target: " + destination)
                            self.assertIn(fragment, anchors(tokens(target)), destination)

    def test_python_syntax(self):
        for path in self.repository.files(".py"):
            with self.subTest(path=path):
                ast.parse(self.repository.read(path), filename=path)


def main(argv=None):
    return run_check("skill-structure", SkillStructureChecks, argv, runtime=False)


if __name__ == "__main__":
    sys.exit(main())
