#!/usr/bin/env python3
"""Persistent checks for markdown output."""

from pathlib import Path
import sys

# -I excludes the script directory; only these local check helpers are added.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import RuntimeFixture, run_check


class MarkdownOutputChecks(RuntimeFixture):
    """markdown output checks."""

    def test_renderer_supported_sections_and_code_fence(self):
        run = self.approved(ids=["ownership"])
        value = self.detail()
        value["concepts"][0]["example"]["text"] = "```\ncode\n```"
        result = self.command("save-topic", run, value)
        text = Path(result["path"]).read_text()
        self.assertTrue(text.startswith("# 소유권\n"))
        self.assertNotIn("## 동작과 조건", text)
        self.assertIn("````rust\n```\ncode\n```\n````", text)
        self.assertNotIn(str(self.source), text)
        self.assertNotIn("matching", text)


    def test_generic_notation_stays_visible_in_rendered_markdown(self):
        from markdown_it import MarkdownIt
        run = self.approved(ids=["ownership"])
        value = self.detail()
        value["concepts"][0]["explanation"] = "Option<T>와 Option<i32>는 타입 표기다."
        value["concepts"][0]["usage"] = "`Option<T>`와 ``Option<i32>``를 표현한다."
        result = self.command("save-topic", run, value)
        tokens = MarkdownIt().parse(Path(result["path"]).read_text())
        children = [child for token in tokens if token.type == "inline" for child in token.children or []]
        self.assertFalse([token for token in children if token.type == "html_inline"])
        self.assertIn("Option<T>", "".join(token.content for token in children if token.type == "text"))
        self.assertEqual(["Option<T>", "Option<i32>"],
                         [token.content for token in children if token.type == "code_inline"])


    def test_already_escaped_angles_and_html_syntax_remain_literal(self):
        from markdown_it import MarkdownIt
        run = self.approved(ids=["ownership"])
        value = self.detail()
        value["concepts"][0]["explanation"] = r"Option\<T\>와 <p> 태그의 표기다."
        result = self.command("save-topic", run, value)
        tokens = MarkdownIt().parse(Path(result["path"]).read_text())
        children = [child for token in tokens if token.type == "inline" for child in token.children or []]
        self.assertFalse([token for token in children if token.type == "html_inline"])
        visible = "".join(token.content for token in children if token.type == "text")
        self.assertIn("Option<T>와 <p>", visible)


    def test_renderer_rejects_path_metadata_empty_and_extra_headings(self):
        run = self.approved(ids=["ownership"])
        for change in ({"source": str(self.first)}, {"explanation": "# injected"},
                       {"explanation": "heading\n===\n"}, {"explanation": " "}):
            value = self.detail()
            value["concepts"][0].update(change)
            self.assert_error("INVALID_PAYLOAD", self.command, "save-topic", run, value)
        self.assertFalse((self.repo / "knowledge-candidate").exists())



def main(argv=None):
    return run_check("markdown-output", MarkdownOutputChecks, argv)


if __name__ == "__main__":
    sys.exit(main())
