"""Check completion checklists, outcomes and confirmation records."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import re
from datetime import datetime
from report_common import REPORT, sections, visible, tables, unquoted, run_cli


COMPLETIONS = {'verification': {'all_passed', 'qa_handoff'},
               'qa': {'all_passed', 'next_cycle_handoff'}}


def inline_lines(token, *, prose=False):
    lines, code_lines = [''], set()
    for part in token.children or []:
        if part.type in ('softbreak', 'hardbreak'):
            lines.append('')
        else:
            value = visible([part])
            if not lines[-1].strip() and value.strip() and part.type == 'code_inline':
                code_lines.add(len(lines) - 1)
            lines[-1] += value
    return [line for i, line in enumerate(lines) if not prose or i not in code_lines]


def item_fields(item, first, rest):
    """Read current direct fields, never a deeper previous-confirmation record."""
    fields = {}
    candidates = inline_lines(first, prose=True)[1:]
    for token in rest:
        if token.type == 'inline' and token.level in (item.level + 2, item.level + 4):
            candidates.extend(inline_lines(token, prose=True))
    for line in candidates:
        name, sep, value = line.strip().partition(':')
        if sep:
            fields.setdefault(name, []).append(value.strip())
    return fields


def list_items(tokens):
    stack = []
    for i, token in enumerate(tokens):
        if token.type == 'list_item_open':
            stack.append(i)
        elif token.type == 'list_item_close':
            start = stack.pop()
            if start + 2 < i and tokens[start + 1].type == 'paragraph_open':
                yield tokens[start], tokens[start + 2], tokens[start + 3:i]


def timestamp(value):
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} \(KST\)', value):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%d %H:%M:%S (KST)')
    except ValueError:
        return False
    return True



def checklist(ctx, path, meta, tokens):
    found = sections(tokens, '완료 체크리스트', 2)
    if len(found) != 1:
        return  # report.area already explains missing/duplicate H2 areas.
    heading, body = found[0]
    items = list(list_items(body))
    previous = [item.map for item, first, _ in items
                if visible(first.children or []).strip().startswith('이전 확인 기록:')]
    checked, tasks, legacy = [], [], []
    for item, first, rest in items:
        if any(begin <= item.map[0] < end for begin, end in previous):
            continue
        children = first.children or []
        # An inline-code example such as `[x] item` is not a task marker.
        match = re.match(r'^\[([ xX])\]\s+', children[0].content) if children and children[0].type == 'text' else None
        if not match or not visible(children)[match.end():].strip():
            continue
        tasks.append(match[1] != ' ')
        if match[1] == ' ':
            continue
        checked.append(item)
        fields = item_fields(item, first, [part for part in rest if not part.map or
                             not any(begin <= part.map[0] < end for begin, end in previous)])
        evidence = fields.get('확인 근거', [])
        ctx.add('checklist.evidence', 'PASS' if any(evidence) else 'FAIL', path,
                 '현재 확인 근거의 존재를 확인합니다. 내용/승인은 별도 판단입니다.', item.map[0] + 1)
        old = fields.get('확인 완료 시각', [])
        legacy.append(bool(old) and all(timestamp(value) for value in old))
        if old:
            ctx.add('checklist.timestamp', 'PASS' if legacy[-1] else 'FAIL', path,
                     '기존 항목별 확인 완료 시각의 형식을 확인합니다.', item.map[0] + 1)
    if meta['status'] == 'completed':
        ctx.add('checklist.completed', 'PASS' if tasks and all(tasks) else 'FAIL', path,
                 'completed에는 비어 있지 않고 모두 체크된 완료 체크리스트가 필요합니다.', heading.map[0] + 1)
    batches = sections(body, '일괄 반영 기록', 3)
    if len(batches) > 1:
        ctx.add('checklist.records', 'FAIL', path, '일괄 반영 기록 영역이 중복되었습니다.')
        return
    batch_body = batches[0][1] if batches else []
    has_body = any(t.type in ('inline', 'fence', 'code_block') for t in batch_body)
    if not has_body and not (checked and not all(legacy)):
        return
    if not batches:
        ctx.add('checklist.records', 'FAIL', path, '체크된 항목의 일괄 반영 기록 또는 기존 항목별 시각이 필요합니다.')
        return
    records = []
    if list(tables(batch_body)):
        rows = ctx.record_table(path, batch_body, ('묶음', '대상 항목', '반영 시각'), 'checklist.records')
        records.extend((row.map[0] + 1, {key: visible(cell.children or []).strip()
                                        for key, cell in cells.items()}) for row, cells in rows or [])
    for item, first, rest in list_items(batch_body):
        if item.level != 1:
            continue
        lines = inline_lines(first, prose=True)
        match = re.match(r'^(B[^:\s]*):\s*(.*)', lines[0]) if lines else None
        if not match:
            continue
        times = item_fields(item, first, rest).get('반영 시각', [])
        records.append((item.map[0] + 1, {'묶음': match[1], '대상 항목': match[2],
                                        '반영 시각': times[0].removesuffix('.') if len(times) == 1 else ''}))
    if not records:
        ctx.add('checklist.records', 'FAIL', path, '반영 기록의 표 또는 B1: 대상/하위 반영 시각 목록이 필요합니다.')
    seen = set()
    for line, values in records:
        key = values['묶음']
        valid = bool(re.fullmatch(r'B[1-9][0-9]*', key)) and key not in seen
        ctx.add('checklist.batch', 'PASS' if valid else 'FAIL', path,
                 f'반영 묶음 식별자의 형식/중복: {key}', line)
        seen.add(key)
        ctx.add('checklist.targets', 'PASS' if values['대상 항목'] else 'FAIL', path,
                 '반영 대상 이름의 존재만 확인하며 항목별 의미 대응은 판정하지 않습니다.', line)
        ctx.add('checklist.timestamp', 'PASS' if timestamp(values['반영 시각']) else 'FAIL', path,
                 '반영 시각의 형식과 달력 범위를 확인합니다.', line)



def completion(ctx, path, stage, meta, tokens):
    if stage not in COMPLETIONS:
        return
    allowed = COMPLETIONS[stage] if ctx.legacy else {'all_passed', 'handoff'}
    areas = sections(tokens, '사용자 승인', 2)
    if len(areas) != 1:
        return
    found = sections(areas[0][1], '완료 구분', 3)
    required = meta['status'] in ('awaiting_approval', 'completed')
    if len(found) != 1:
        if required or found:
            ctx.add('report.completion', 'FAIL', path, '완료 구분 영역이 정확히 하나 필요합니다.')
        return
    heading, body = found[0]
    lines = [line.strip() for token in body if token.type == 'inline'
             for line in inline_lines(token) if line.strip()]
    keywords = set().union(*COMPLETIONS.values(), {'handoff'})
    if not required and (not lines or (lines[0] == '미정' and not any(line in keywords for line in lines[1:]))):
        return
    valid = (len(lines) >= 2 and lines[0] in allowed and
             not any(line in keywords for line in lines[1:]))
    ctx.add('report.completion', 'PASS' if valid else 'FAIL', path,
             f'단계에 맞는 키워드 하나와 설명이 필요합니다: {", ".join(sorted(allowed))}',
             heading.map[0] + 1)



def check(ctx):
    for path, (meta, tokens) in ctx.current_reports.items():
        body = list(unquoted(tokens))
        # Missing areas make this role's input indeterminate even without a structure run.
        for title in ('완료 체크리스트', '사용자 승인'):
            if len(sections(body, title, 2)) != 1:
                ctx.add('completion.input', 'FAIL', path, f'{title} 영역이 정확히 하나 필요합니다.')
        checklist(ctx, path, meta, body)
        completion(ctx, path, REPORT.fullmatch(path.name)[1], meta, body)


def main(argv=None):
    return run_cli([('completion', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
