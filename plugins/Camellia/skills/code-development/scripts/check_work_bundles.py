"""Check the work bundle registry and result report links."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_common import (REPORT, BUNDLE, sections, unquoted, visible,
                           local_target, run_cli)


BUNDLE_COLUMNS = ('묶음', '제목', '범위/완료 기준', '의존/진입', '설계 정본', '결과 참조')


def check(ctx):
    parsed, current = ctx.parsed, ctx.current_reports
    bundled = [(path, meta) for path, (meta, _) in current.items() if meta.get('bundle') is not None]
    shared = [(path, tokens) for path, (meta, tokens) in current.items()
              if REPORT.fullmatch(path.name)[1] == 'design' and meta.get('bundle') is None]
    if not shared:
        if bundled:
            ctx.add('bundle.table', 'UNCHECKED', ctx.topic, '현재 공통 design이 없어 묶음표를 대조하지 못했습니다.')
        return
    path, tokens = shared[0]
    areas = sections(list(unquoted(tokens)), '단계 결과', 2)
    found = sections(areas[0][1], '작업 묶음표', 3) if len(areas) == 1 else []
    if not found:
        if bundled:
            ctx.add('bundle.table', 'UNCHECKED', path, '정형 작업 묶음표가 없습니다. 기존 표는 자동 변환하지 않습니다.')
        return
    if len(found) != 1:
        ctx.add('bundle.table', 'FAIL', path, '작업 묶음표 영역이 중복되었습니다.')
        return
    rows = ctx.record_table(path, found[0][1], BUNDLE_COLUMNS, 'bundle.table')
    if rows is None:
        return
    seen = set()
    for row, cells in rows:
        values = {key: visible(cell.children or []).strip() for key, cell in cells.items()}
        key = values['묶음']
        valid = bool(BUNDLE.fullmatch(key)) and key not in seen
        ctx.add('bundle.identifier', 'PASS' if valid else 'FAIL', path,
                 f'작업 묶음 식별자의 형식/중복: {key}', row.map[0] + 1)
        seen.add(key)
        ctx.add('bundle.fields', 'PASS' if all(values.values()) else 'FAIL', path,
                 '묶음표 필수 값의 존재만 확인합니다.', row.map[0] + 1)
        for link in cells['결과 참조'].children or []:
            if link.type != 'link_open':
                continue
            url = link.attrGet('href')
            try:
                target, _ = local_target(path, url)
                resolved = target.resolve() if target is not None else None
                result = next(((p, m) for p, (m, _) in parsed.items() if p.resolve() == resolved), None)
                valid = (result is not None and result[1].get('bundle') == key and
                         REPORT.fullmatch(result[0].name)[1] in ('implementation', 'verification', 'qa'))
            except (ValueError, OSError, RuntimeError):
                valid = False
            ctx.add('bundle.result', 'PASS' if valid else 'FAIL', path,
                     f'같은 작업/묶음의 구현/검증/QA report 연결: {url}', row.map[0] + 1)
    for report, meta in bundled:
        ctx.add('bundle.registration', 'PASS' if meta['bundle'] in seen else 'FAIL', report,
                 f'공통 설계의 묶음표 등록: {meta["bundle"]}')


def main(argv=None):
    return run_cli([('bundles', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
