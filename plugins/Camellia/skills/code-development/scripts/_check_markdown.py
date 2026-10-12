"""CommonMark, YAML and local-reference helpers for deterministic checks."""

from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml

from _check_runtime import CheckError, file_kind, resolve_path


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None, "unhashable mapping key", key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate mapping key", key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def yaml_value(text):
    return yaml.load(text, Loader=UniqueLoader)


def remove_comments(text):
    def erase(match):
        return "".join("\n" if char == "\n" else " " for char in match[0])
    return re.sub(r"<!--[\s\S]*?(?:-->|\Z)", erase, text)


def inline_text(token):
    if token.children is not None:
        return "".join(inline_text(child) for child in token.children)
    if token.type in ("text", "code_inline", "code_block", "fence"):
        return token.content
    if token.type in ("softbreak", "hardbreak"):
        return "\n"
    return ""


def inline_value(token):
    """Preserve nonempty link/image values even when their display labels are empty."""
    if token.children is None:
        return inline_text(token)
    output = []
    opened = []
    for child in token.children:
        if child.type == "link_open":
            opened.append((len(output), child.attrGet("href") or ""))
        elif child.type == "link_close" and opened:
            start, destination = opened.pop()
            if not "".join(output[start:]).strip():
                output.append(destination)
        elif child.type == "image":
            output.append(inline_text(child) or child.attrGet("src") or "")
        else:
            output.append(inline_value(child))
    return "".join(output)


def token_links(token):
    if token.type == "link_open":
        yield token.attrGet("href") or ""
    elif token.type == "image":
        yield token.attrGet("src") or ""
    for child in token.children or []:
        yield from token_links(child)


@dataclass
class Section:
    title: str
    level: int
    start: int
    end: int
    line: int


@dataclass
class Item:
    start: int
    end: int
    parent: int | None
    line: int


class Document:
    def __init__(self, path, raw):
        self.path = path
        self.raw = raw
        self.frontmatter = None
        self.yaml_error = None
        self.has_frontmatter = False
        self.offset = 0
        lines = raw.splitlines(keepends=True)
        body = raw
        if lines and lines[0].strip() == "---":
            closing = next((index for index in range(1, len(lines))
                            if lines[index].strip() == "---"), None)
            if closing is None:
                self.yaml_error = "unclosed YAML frontmatter"
            else:
                self.has_frontmatter = True
                try:
                    self.frontmatter = yaml_value("".join(lines[1:closing]))
                except yaml.YAMLError as exc:
                    self.yaml_error = str(exc)
                # General Markdown only excludes a valid mapping; reports additionally
                # reject invalid frontmatter when their metadata is requested.
                if isinstance(self.frontmatter, dict) and self.yaml_error is None:
                    self.offset = closing + 1
                    body = "".join(lines[self.offset:])
        # Let CommonMark identify comments. Do not erase literal <!--...--> in code.
        self.body = body
        parser = MarkdownIt("commonmark", {"html": True}).enable("table")
        parser.validateLink = lambda destination: True
        parsed = parser.parse(self.body)
        self.tokens = []
        quote_depth = 0
        for token in parsed:
            if token.type == "blockquote_open":
                quote_depth += 1
            elif token.type == "blockquote_close":
                quote_depth -= 1
            elif quote_depth == 0:
                self.tokens.append(token)
        self.sections = []
        for index, token in enumerate(self.tokens):
            if token.type == "heading_open":
                level = int(token.tag[1:])
                title = inline_text(self.tokens[index + 1]).strip()
                self.sections.append(Section(title, level, index, len(self.tokens), self.line(token)))
        for index, section in enumerate(self.sections):
            for later in self.sections[index + 1:]:
                if later.level <= section.level:
                    section.end = later.start
                    break
        self.items = []
        stack = []
        for index, token in enumerate(self.tokens):
            if token.type == "list_item_open":
                item = Item(index, len(self.tokens), stack[-1] if stack else None, self.line(token))
                self.items.append(item)
                stack.append(index)
            elif token.type == "list_item_close":
                if stack:
                    opened = stack.pop()
                    for item in reversed(self.items):
                        if item.start == opened:
                            item.end = index + 1
                            break

    def line(self, token):
        return token.map[0] + self.offset + 1 if token.map is not None else None

    def headings(self, title, level, parent=None):
        return [section for section in self.sections
                if section.title == title and section.level == level
                and (parent is None or parent.start < section.start < parent.end)]

    def text(self, start=0, end=None, code=True):
        kinds = ("inline", "code_block", "fence") if code else ("inline",)
        return "\n".join(inline_text(token) for token in self.tokens[start:end]
                         if token.type in kinds)

    def content(self, section):
        return self.text(section.start + 3, section.end).strip()

    def has_content(self, section):
        text = self.content(section)
        if text and not re.fullmatch(r"`+", text):
            return True
        return any(destination for destination, line in self.links(section.start + 3, section.end))

    def item_text(self, item, direct=False):
        output = []
        depth = 0
        for token in self.tokens[item.start + 1:item.end - 1]:
            if token.type == "list_item_open":
                depth += 1
            elif token.type == "list_item_close":
                depth -= 1
            elif token.type == "inline" and (not direct or depth == 0):
                output.append(inline_text(token))
        return "\n".join(output)

    def item_links(self, item, direct=False):
        links = []
        depth = 0
        for token in self.tokens[item.start + 1:item.end - 1]:
            if token.type == "list_item_open":
                depth += 1
            elif token.type == "list_item_close":
                depth -= 1
            elif not direct or depth == 0:
                links.extend(token_links(token))
        return links

    def links(self, start=0, end=None):
        for token in self.tokens[start:end]:
            for destination in token_links(token):
                yield destination, self.line(token)

    def tables(self, section):
        """Return table cells with their rendered text and explicit link destinations."""
        tables = []
        rows = None
        row = None
        cell = None
        for token in self.tokens[section.start:section.end]:
            if token.type == "table_open":
                rows = []
            elif token.type == "tr_open" and rows is not None:
                row = []
            elif token.type in ("th_open", "td_open") and row is not None:
                cell = {"text": "", "links": [], "line": self.line(token)}
            elif token.type == "inline" and cell is not None:
                cell["text"] += inline_text(token).strip()
                cell["links"].extend(token_links(token))
                cell["line"] = cell["line"] or self.line(token)
            elif token.type in ("th_close", "td_close") and cell is not None:
                row.append(cell)
                cell = None
            elif token.type == "tr_close" and row is not None:
                rows.append(row)
                row = None
            elif token.type == "table_close" and rows is not None:
                tables.append(rows)
                rows = None
        return tables

    def anchors(self):
        used = set()
        for index, token in enumerate(self.tokens):
            if token.type == "heading_open":
                title = inline_text(self.tokens[index + 1]).strip().lower().replace(" ", "-")
                slug = "".join(char for char in title if char in "-_"
                               or unicodedata.category(char)[0] in "LMN")
                candidate = slug
                suffix = 0
                while candidate in used:
                    suffix += 1
                    candidate = f"{slug}-{suffix}"
                used.add(candidate)
            candidates = [token] + list(token.children or [])
            for child in candidates:
                if child.type not in ("html_block", "html_inline"):
                    continue
                for tag in re.findall(r"<[A-Za-z][^>]*>", remove_comments(child.content)):
                    for match in re.finditer(r"\s(id|name)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", tag, re.I):
                        if match[1].lower() == "id" or re.match(r"<a(?:\s|>)", tag, re.I):
                            used.add(html.unescape(next(value for value in match.groups()[1:] if value is not None)))
        return used


def link_target(doc, destination, result, line=None, record=True):
    try:
        parts = urlsplit(destination)
        if parts.scheme or parts.netloc:
            if record:
                result.na("C11.external", "external URI is not inspected", doc.path)
            return None
        if re.search(r"%(?![0-9a-fA-F]{2})", parts.path + parts.fragment):
            raise ValueError("invalid percent encoding")
        value = unquote(parts.path, errors="strict")
        fragment = unquote(parts.fragment, errors="strict")
        if "\x00" in value + fragment:
            raise ValueError("NUL in local reference")
        path = Path(value) if value.startswith("/") else doc.path.parent / value if value else doc.path
        return resolve_path(path, result), fragment
    except (ValueError, UnicodeError) as exc:
        if record:
            result.check("C11.encoding", False, str(exc), doc.path, line)
        return None


def check_links(context, doc, start=0, end=None):
    result = context.result
    found = False
    for destination, line in doc.links(start, end):
        found = True
        try:
            target = link_target(doc, destination, result, line)
            if target is None:
                continue
            path, fragment = target
            kind = file_kind(path, result)
            exists = result.check("C11.target", kind is not None, f"local target: {path}", doc.path, line)
            if not exists or not fragment:
                continue
            if kind != "file" or path.suffix.lower() != ".md":
                result.error("C11.fragment", "cannot interpret fragment of a non-Markdown target", doc.path, line)
                continue
            other = context.document(path)
            result.check("C11.fragment", fragment in other.anchors(), f"Markdown fragment: {fragment}", doc.path, line)
        except CheckError:
            continue
    if not found:
        result.na("C11.links", "no local or external Markdown references in selected region", doc.path)
