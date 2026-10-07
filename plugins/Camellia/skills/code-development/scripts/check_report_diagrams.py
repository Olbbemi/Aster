"""Check marked ASCII diagram character format; not visual rendering."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import unicodedata
from report_common import run_cli


def diagrams(ctx, source, tokens):
    for token in tokens:
        if token.type != 'fence' or token.info.split() != ['text', 'ascii-flow']:
            continue
        ctx.diagram_count += 1
        raw_lines = ctx.raw[source]
        # A parsed closing fence occupies a mapped line outside the content.
        # Count LF only: other control characters remain content to validate.
        content_lines = token.content.count('\n') + bool(token.content and not token.content.endswith('\n'))
        closed = token.map[1] - token.map[0] == content_lines + 2
        ctx.add('diagram.fence', 'PASS' if closed else 'FAIL', source,
                 '도식 코드 블록이 닫혔습니다.' if closed else '도식 코드 블록의 닫는 구분자가 없습니다.',
                 token.map[0] + 1)
        bad = []
        content = raw_lines[token.map[0] + 1:token.map[1] - (1 if closed else 0)]
        for offset, line in enumerate(content):
            for char in line:
                code = ord(char)
                if (unicodedata.category(char).startswith('C') or
                        0x2500 <= code <= 0x25FF or
                        code in (0x2013, 0x2014, 0xFF0B, 0xFF0D, 0xFF1C, 0xFF1E, 0xFF5C) or
                        (code > 127 and 'ARROW' in unicodedata.name(char, ''))):
                    bad.append(f'{token.map[0] + offset + 2}:U+{code:04X}')
        ctx.add('diagram.characters', 'FAIL' if bad else 'PASS', source,
                 ', '.join(bad) if bad else '문자 형식만 확인했습니다. 표시/정렬은 별도 확인입니다.',
                 token.map[0] + 1)



def check(ctx):
    for path, tokens in ctx.content_documents():
        diagrams(ctx, path, tokens)


def main(argv=None):
    return run_cli([('diagrams', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
