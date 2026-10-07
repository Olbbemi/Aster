"""Check report structure, revisions and predecessor/bundle connections."""

import sys
from pathlib import Path

# Keep sibling modules available for direct execution, including Python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from collections import Counter
from report_common import AREAS, REPORT, visible, run_cli


BUNDLE_STAGES = ('design', 'implementation', 'verification', 'qa')


def bundle_basis(ctx, path, stage, meta, predecessor, parsed, bundled, stages):
    bundle = meta.get('bundle')
    if bundle is not None:
        if stages != ['discussion', *BUNDLE_STAGES] or stage not in BUNDLE_STAGES:
            ctx.add('report.bundle', 'FAIL', path, '순차 묶음은 기본 다섯 단계의 설계/구현/검증/QA report에 적용합니다.')
            return
    elif bundled and stage not in ('discussion', 'design'):
        ctx.add('report.bundle', 'FAIL', path, '순차 묶음 작업의 구현/검증/QA에는 묶음 식별자가 필요합니다.')
        return
    if predecessor is None:
        return
    previous_bundle = predecessor.get('bundle')
    if bundle is None:
        valid = previous_bundle is None
    elif stage == 'design':
        valid = previous_bundle is None
    elif stage == 'implementation':
        has_design = any(REPORT.fullmatch(other.name)[1] == 'design' and
                         other_meta.get('bundle') == bundle
                         for other, (other_meta, _) in parsed.items())
        # A later bundle design must not invalidate a preserved shared input.
        preserves_shared_input = meta['status'] in ('hold', 'superseded')
        valid = previous_bundle == bundle or (
            previous_bundle is None and (not has_design or preserves_shared_input))
    else:
        valid = previous_bundle == bundle
    if not valid:
        ctx.add('report.bundle', 'FAIL', path, '공통/같은 묶음의 선행 report 연결을 확인하십시오.')



def check(ctx):
    parsed, groups, stages = ctx.parsed, ctx.groups, ctx.stages
    bundled = any(meta.get("bundle") is not None for meta, _ in parsed.values())
    for (stage, _), entries in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or '')):
        entries.sort()
        for n, (number, path) in enumerate(entries):
            if path not in parsed:
                continue
            meta, tokens = parsed[path]
            current = n == len(entries) - 1
            if (current and meta['status'] == 'superseded') or (not current and meta['status'] != 'superseded'):
                ctx.add('report.revision', 'FAIL', path, '현재 번호/이전 번호의 superseded 상태가 맞지 않습니다.')
            base = meta['base_on']
            predecessor = parsed.get(ctx.topic / base, (None, None))[0] if base is not None else None
            bundle_basis(ctx, path, stage, meta, predecessor, parsed, bundled, stages)
            if stage in stages:
                index = stages.index(stage)
                if index == 0:
                    if base is not None:
                        ctx.add('report.base', 'FAIL', path, '선행 단계 없는 report의 base_on은 null이어야 합니다.')
                elif base is None or ctx.topic / base not in parsed:
                    ctx.add('report.base', 'FAIL', path, '유효한 형식의 선행 report가 없습니다.')
                else:
                    match = REPORT.fullmatch(base)
                    if match[1] != stages[index - 1]:
                        ctx.add('report.base', 'FAIL', path, 'stages의 바로 앞 단계 report를 참조해야 합니다.')
                    elif meta['status'] not in ('hold', 'superseded') and parsed[ctx.topic / base][0]['status'] != 'completed':
                        ctx.add('report.predecessor', 'FAIL', path, '현재 report의 선행 입력이 completed 상태가 아닙니다.')
    for path, (_, tokens) in ctx.body_reports.items():
        heads = Counter(visible(tokens[i + 1].children or []) for i, t in enumerate(tokens)
                        if t.type == 'heading_open' and t.tag == 'h2' and t.level == 0)
        for name in AREAS:
            ctx.add('report.area', 'PASS' if heads[name] == 1 else 'FAIL', path, f'{name}: {heads[name]}개')


def main(argv=None):
    return run_cli([('structure', check)], argv)


if __name__ == '__main__':
    sys.exit(main())
