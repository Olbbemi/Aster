"""Check local links and anchors in reports and current design details."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import stat
import unicodedata
from html.parser import HTMLParser
from report_common import visible, local_target, run_cli


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = set()

    def handle_starttag(self, tag, attrs):
        self.values.update(value for key, value in attrs
                           if value and (key == 'id' or (tag == 'a' and key == 'name')))



def anchors(tokens):
    auto, explicit = set(), Anchors()
    for i, t in enumerate(tokens):
        if t.type == 'heading_open':
            title = visible(tokens[i + 1].children or []).strip().lower()
            base = ''.join('-' if c == ' ' else c for c in title
                           if c in ' -_' or unicodedata.category(c)[0] in 'LMN')
            value, n = base, 0
            while value in auto:
                n += 1
                value = f'{base}-{n}'
            auto.add(value)
        for part in [t, *(t.children or [])]:
            if part.type in ('html_inline', 'html_block'):
                explicit.feed(part.content)
    explicit.close()
    return auto | explicit.values



def links(ctx, source, tokens):
    line = None
    for block in tokens:
        if block.map:
            line = block.map[0] + 1
        if block.type != 'inline':
            continue
        for token in block.children or []:
            if token.type not in ('link_open', 'image'):
                continue
            url = token.attrGet('href' if token.type == 'link_open' else 'src')
            try:
                target, fragment = local_target(source, url)
            except (ValueError, UnicodeError) as exc:
                ctx.add('link.syntax', 'FAIL', source, f'{url}: {exc}', line)
                continue
            try:
                if target is None:
                    ctx.add('link.external', 'SKIP', source, url, line)
                    continue
                mode = target.stat().st_mode
                if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise ValueError('일반 파일/디렉토리가 아닌 대상입니다.')
                if fragment:
                    if not stat.S_ISREG(mode) or target.suffix.lower() != '.md':
                        ctx.add('link.fragment', 'UNCHECKED', source, f'비Markdown 절: {url}', line)
                        continue
                    if fragment not in anchors(ctx.read(target)[1]):
                        ctx.add('link.fragment', 'FAIL', source, f'절 누락: {url}', line)
                        continue
                ctx.add('link.local', 'PASS', source, url, line)
            except (FileNotFoundError, NotADirectoryError):
                ctx.add('link.target', 'FAIL', source, f'대상 누락: {url}', line)
            except UnicodeError as exc:
                ctx.add('link.read', 'ERROR', source, f'{url}: {exc}', line)
            except ValueError as exc:
                ctx.add('link.syntax', 'FAIL', source, f'{url}: {exc}', line)
            except (OSError, RuntimeError) as exc:
                ctx.add('link.read', 'ERROR', source, f'{url}: {exc}', line)



def check(ctx):
    links(ctx, ctx.topic.parent / 'freight-manifest.md', ctx.manifest_tokens)
    for path, tokens in ctx.content_documents():
        links(ctx, path, tokens)


def main(argv=None):
    return run_cli([('links', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
