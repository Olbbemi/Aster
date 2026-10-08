"""Check the work bundle registry and result report links."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_common import (REPORT, BUNDLE, BUNDLE_DIRECTORY, sections, unquoted, visible,
                           local_target, run_cli)


BUNDLE_COLUMNS = ('묶음', '제목', '범위/완료 기준', '의존/진입', '설계 정본', '결과 참조')
DIRECTORY_COLUMNS = ('묶음', '범위/완료 기준', '의존/진입', '설계 정본', '디렉토리', '결과 참조')


def check(ctx):
    parsed, current = ctx.parsed, ctx.current_reports
    bundled = [(path, meta) for path, (meta, _) in current.items() if ctx.scope(path, meta) is not None]
    shared = [(path, tokens) for path, (meta, tokens) in current.items()
              if REPORT.fullmatch(path.name)[1] == 'design' and ctx.scope(path, meta) is None]
    if not ctx.legacy:
        numbers = set()
        for directory in ctx.bundle_directories:
            match = BUNDLE_DIRECTORY.fullmatch(directory.name)
            if not match:
                ctx.add('bundle.directory', 'FAIL', directory, '번들 이름은 두 자리 이상 순번과 소문자 이름이어야 합니다.')
                continue
            digits = match[1]
            number = int(digits)
            valid = number > 0 and digits == f'{number:02d}' and number not in numbers
            ctx.add('bundle.directory', 'PASS' if valid else 'FAIL', directory, '양수 순번의 형식과 중복을 확인합니다.')
            numbers.add(number)
    if not shared:
        if bundled or ctx.bundle_directories:
            ctx.add('bundle.table', 'UNCHECKED', ctx.topic, '현재 공통 design이 없어 묶음표를 대조하지 못했습니다.')
        return
    path, tokens = shared[0]
    areas = sections(list(unquoted(tokens)), '단계 결과', 2)
    found = sections(areas[0][1], '작업 묶음표', 3) if len(areas) == 1 else []
    if not found:
        if bundled or ctx.bundle_directories:
            ctx.add('bundle.table', 'UNCHECKED', path, '정형 작업 묶음표가 없습니다. 기존 표는 자동 변환하지 않습니다.')
        return
    if len(found) != 1:
        ctx.add('bundle.table', 'FAIL', path, '작업 묶음표 영역이 중복되었습니다.')
        return
    rows = ctx.record_table(path, found[0][1], BUNDLE_COLUMNS if ctx.legacy else DIRECTORY_COLUMNS, 'bundle.table')
    if rows is None:
        return
    seen = set()
    directories = set()
    for row, cells in rows:
        values = {key: visible(cell.children or []).strip() for key, cell in cells.items()}
        key = values['묶음']
        valid = bool(BUNDLE.fullmatch(key) if ctx.legacy else key) and key not in seen
        ctx.add('bundle.identifier', 'PASS' if valid else 'FAIL', path,
                 f'작업 묶음 식별자의 형식/중복: {key}', row.map[0] + 1)
        seen.add(key)
        directory = None
        if not ctx.legacy and values['디렉토리'] != '미시작':
            directory = values['디렉토리'].rstrip('/')
            valid = (bool(BUNDLE_DIRECTORY.fullmatch(directory)) and directory not in directories and
                     ctx.topic / directory in ctx.bundle_directories)
            ctx.add('bundle.directory', 'PASS' if valid else 'FAIL', path, f'실제 번들 디렉토리 연결: {directory}', row.map[0] + 1)
            directories.add(directory)
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
                valid = (result is not None and ctx.scope(*result) == (key if ctx.legacy else directory) and
                         (ctx.legacy or directory is not None) and
                         REPORT.fullmatch(result[0].name)[1] in ('implementation', 'verification', 'qa'))
            except (ValueError, OSError, RuntimeError):
                valid = False
            ctx.add('bundle.result', 'PASS' if valid else 'FAIL', path,
                     f'같은 작업/묶음의 구현/검증/QA report 연결: {url}', row.map[0] + 1)
    for report, meta in bundled:
        scope = ctx.scope(report, meta)
        ctx.add('bundle.registration', 'PASS' if scope in (seen if ctx.legacy else directories) else 'FAIL', report,
                 f'공통 설계의 묶음표 등록: {scope}')
    if not ctx.legacy:
        for directory in ctx.bundle_directories:
            ctx.add('bundle.registration', 'PASS' if directory.name in directories else 'FAIL', directory,
                    '시작한 번들의 공통 설계 등록을 확인합니다.')


def main(argv=None):
    return run_cli([('bundles', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
