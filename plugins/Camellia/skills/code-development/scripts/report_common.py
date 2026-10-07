"""Shared input and output for code-development checks; no standalone command."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

yaml = MarkdownIt = None

try:
    import yaml
    from markdown_it import MarkdownIt
except ImportError as exc:
    DEPENDENCY_ERROR = str(exc)
else:
    DEPENDENCY_ERROR = None

REPORT = re.compile(r'([a-z][a-z0-9-]*)-report-([0-9]+)\.md\Z')
BUNDLE = re.compile(r'[a-z0-9][a-z0-9-]*\Z')
STATUSES = {'in_progress', 'awaiting_approval', 'completed', 'hold', 'superseded'}
AREAS = ('단계 결과', '인계 사항', '완료 체크리스트', '사용자 승인')
BASIS = 'references/report-checks.md'


def visible(tokens):
    return ''.join(visible(t.children or []) if t.type == 'image' else
                   t.content if t.type in ('text', 'code_inline') else
                   ' ' if t.type in ('softbreak', 'hardbreak') else ''
                   for t in tokens)


def unquoted(tokens):
    depth = 0
    for token in tokens:
        if token.type == 'blockquote_open':
            depth += 1
        elif token.type == 'blockquote_close':
            depth -= 1
        elif not depth:
            yield token


def sections(tokens, title, level):
    """Return only real, top-level sections, including their source heading."""
    found = []
    for i, token in enumerate(tokens):
        if (token.type != 'heading_open' or token.level != 0 or
                token.tag != f'h{level}' or visible(tokens[i + 1].children or []).strip() != title):
            continue
        end = next((j for j in range(i + 3, len(tokens))
                    if tokens[j].type == 'heading_open' and tokens[j].level == 0 and
                    int(tokens[j].tag[1:]) <= level), len(tokens))
        found.append((token, tokens[i + 3:end]))
    return found


def tables(tokens):
    """Expose table cell tokens so result links need not be reparsed as text."""
    for i, token in enumerate(tokens):
        if token.type != 'table_open' or token.level != 0:
            continue
        end = next(j for j in range(i + 1, len(tokens)) if tokens[j].type == 'table_close')
        rows = []
        for j in range(i + 1, end):
            if tokens[j].type == 'tr_open':
                close = next(k for k in range(j + 1, end) if tokens[k].type == 'tr_close')
                rows.append((tokens[j], [t for t in tokens[j + 1:close] if t.type == 'inline']))
        yield token, rows


def decode(value):
    if re.search(r'%(?![0-9a-fA-F]{2})', value):
        raise ValueError('잘못된 URL 인코딩입니다.')
    result = unquote(value, encoding='utf-8', errors='strict')
    if '\0' in result:
        raise ValueError('경로/절에 NUL을 사용할 수 없습니다.')
    return result


def local_target(source, destination):
    uri = urlsplit(destination)
    if uri.scheme or uri.netloc or destination.startswith('//'):
        return None, None
    path = decode(uri.path)
    return source.parent / path if path else source, decode(uri.fragment)


def yaml_load(text):
    class UniqueLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            seen = set()
            for key, _ in node.value:
                if key.tag == 'tag:yaml.org,2002:merge':
                    continue
                value = self.construct_object(key, deep=deep)
                try:
                    duplicate = value in seen
                    seen.add(value)
                except TypeError as exc:
                    raise ValueError('YAML 키가 스칼라가 아닙니다.') from exc
                if duplicate:
                    raise ValueError(f'중복 YAML 키: {value}')
            return super().construct_mapping(node, deep=deep)

    return yaml.load(text, Loader=UniqueLoader)


class Context:
    def __init__(self, topic):
        self.topic = Path(topic).absolute()
        self.checks, self.docs, self.raw = [], {}, {}
        self.exclusions = []
        self.parser = MarkdownIt('commonmark').enable('table')
        self.diagram_count = 0
        self.selected_groups = []
        self._content_documents = None

    def add(self, rule, status, source, message, line=None):
        self.checks.append(dict(id=rule, status=status, source=str(source),
                                line=line, message=message, basis=BASIS))

    def read(self, path, *, report=False):
        path = Path(path)
        key = (path, report)
        if key not in self.docs:
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError(f'일반 파일이 아닙니다: {path}')
            raw = path.read_text(encoding='utf-8-sig')
            self.raw[path] = raw.split('\n')
            lines = raw.splitlines(keepends=True)
            front = None
            body = raw
            if lines and lines[0].strip() == '---':
                end = next((i for i in range(1, len(lines))
                            if lines[i].strip() == '---'), None)
                if end is None and report:
                    raise ValueError('프론트매터 종료 구분자가 없습니다.')
                if end is not None:
                    candidate = ''.join(lines[1:end])
                    try:
                        mapping = isinstance(yaml_load(candidate), dict)
                    except (ValueError, yaml.YAMLError):
                        mapping = False
                    if report or mapping:
                        front = candidate
                        body = '\n' * (end + 1) + ''.join(lines[end + 1:])
            self.docs[key] = (front, self.parser.parse(body))
        return self.docs[key]

    def manifest(self, path):
        _, tokens = self.read(path)
        matches = []
        heads = [i for i, t in enumerate(tokens)
                 if t.type == 'heading_open' and t.tag == 'h2' and t.level == 0]
        for n, begin in enumerate(heads):
            end = heads[n + 1] if n + 1 < len(heads) else len(tokens)
            for t in tokens[begin + 1].children or []:
                if t.type == 'link_open':
                    target, fragment = local_target(path, t.attrGet('href'))
                    if target is not None and target.resolve() == self.topic.resolve():
                        matches.append(tokens[begin:end])
        if len(matches) != 1:
            raise ValueError(f'manifest의 선택 작업 항목이 {len(matches)}개입니다. 정확히 하나여야 합니다.')
        selected = matches[0]
        fields = {}
        for t in selected:
            if t.type == 'inline' and t.level == 3:
                match = re.fullmatch(r'(stages|reference_reports):\s*(.*)', t.content, re.S)
                if match:
                    if match[1] in fields:
                        raise ValueError(f'manifest 필드 중복: {match[1]}')
                    fields[match[1]] = match[2]
        if set(fields) != {'stages', 'reference_reports'}:
            raise ValueError('선택 작업에 stages/reference_reports가 필요합니다.')
        stages = yaml_load(fields['stages'])
        if (not isinstance(stages, list) or not stages or
                any(not isinstance(s, str) or not re.fullmatch(r'[a-z][a-z0-9-]*', s)
                    for s in stages) or len(stages) != len(set(stages))):
            raise ValueError('stages는 중복 없는 단계 식별자 목록이어야 합니다.')
        self.add('manifest.topic', 'PASS', path, f'선택 작업의 stages: {stages}')
        self.manifest_tokens = selected
        return stages

    def report(self, path):
        front, tokens = self.read(path, report=True)
        if front is None:
            raise ValueError('report 프론트매터가 없습니다.')
        meta = yaml_load(front)
        if not isinstance(meta, dict) or not {'status', 'base_on'} <= meta.keys():
            raise ValueError('report에 status/base_on 매핑이 필요합니다.')
        if not isinstance(meta['status'], str) or meta['status'] not in STATUSES:
            raise ValueError('허용되지 않은 status입니다.')
        base = meta['base_on']
        if base is not None and (not isinstance(base, str) or not REPORT.fullmatch(base)):
            raise ValueError('base_on은 null 또는 선행 report 파일명이어야 합니다.')
        if 'bundle' in meta and (not isinstance(meta['bundle'], str) or not BUNDLE.fullmatch(meta['bundle'])):
            raise ValueError('bundle은 소문자 영문/숫자로 시작하는 소문자 영문/숫자/하이픈 문자열이어야 합니다.')
        self.add('report.metadata', 'PASS', path, 'status/base_on 형식을 확인했습니다.')
        return meta, tokens

    def record_table(self, path, tokens, columns, rule):
        found = list(tables(tokens))
        if len(found) != 1:
            self.add(rule, 'FAIL', path, '지정 열을 가진 표가 정확히 하나 필요합니다.')
            return None
        table, rows = found[0]
        header = [visible(t.children or []).strip() for t in rows[0][1]]
        if Counter(header) != Counter(columns):
            self.add(rule, 'FAIL', path, f'필수 열과 중복을 확인하십시오: {", ".join(columns)}', table.map[0] + 1)
            return None
        if len(rows) == 1:
            self.add(rule, 'FAIL', path, '표에 실제 기록 행이 필요합니다.', table.map[0] + 1)
            return None
        return [(row, dict(zip(header, cells))) for row, cells in rows[1:]]

    def load(self):
        if not self.topic.is_dir():
            self.add('input.topic', 'ERROR', self.topic, '존재하는 작업 주제 디렉토리가 필요합니다.')
            return False
        manifest = self.topic.parent / 'freight-manifest.md'
        try:
            stages = self.manifest(manifest)
        except UnicodeError as exc:
            self.add('manifest.read', 'ERROR', manifest, str(exc))
            return False
        except (ValueError, yaml.YAMLError) as exc:
            self.add('manifest.format', 'FAIL', manifest, str(exc))
            return False
        except (OSError, UnicodeError, RuntimeError) as exc:
            self.add('manifest.read', 'ERROR', manifest, str(exc))
            return False
        groups, parsed, entries_by_stage = {}, {}, {}
        try:
            paths = sorted(self.topic.iterdir())
        except OSError as exc:
            self.add('input.read', 'ERROR', self.topic, str(exc))
            return False
        for path in paths:
            match = REPORT.fullmatch(path.name)
            if not match:
                if '-report-' in path.name and path.suffix == '.md':
                    self.add('report.filename', 'FAIL', path, 'report 파일명 형식이 잘못되었습니다.')
                continue
            stage, number = match[1], int(match[2])
            if number < 1 or match[2] != f'{number:03d}' or stage not in stages:
                self.add('report.filename', 'FAIL', path, '단계/양수 세 자리 이상 번호를 확인하십시오.')
            entries_by_stage.setdefault(stage, []).append((number, path))
            try:
                parsed[path] = self.report(path)
            except UnicodeError as exc:
                self.add('report.read', 'ERROR', path, str(exc))
            except (ValueError, yaml.YAMLError) as exc:
                self.add('report.format', 'FAIL', path, str(exc))
            except (OSError, UnicodeError, RuntimeError) as exc:
                self.add('report.read', 'ERROR', path, str(exc))
        if not entries_by_stage:
            self.add('input.reports', 'ERROR', self.topic, '저장된 report가 없습니다. 최초 저장 전에는 실행하지 않습니다.')
        for stage, entries in entries_by_stage.items():
            for number, path in entries:
                bundle = parsed[path][0].get('bundle') if path in parsed else None
                groups.setdefault((stage, bundle), []).append((number, path))
        self.parsed, self.groups, self.stages = parsed, groups, stages
        self.body_reports, self.current_reports = {}, {}
        for key, entries in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or '')):
            entries.sort()
            for _, path in entries[:-1]:
                if path in parsed:
                    self.exclusions.append(dict(source=str(path), scope='body-links-diagrams',
                                                reason='과거 report 본문은 현재 형식/링크/도식 검사에서 제외합니다.'))
            path = entries[-1][1]
            if path in parsed:
                self.body_reports[path] = parsed[path]
                if parsed[path][0]['status'] != 'superseded':
                    self.current_reports[path] = parsed[path]
        return True

    def content_documents(self):
        if self._content_documents is None:
            self._content_documents = []
            for path, (_, tokens) in self.body_reports.items():
                self._content_documents.append((path, tokens))
                if REPORT.fullmatch(path.name)[1] == 'design':
                    self.details(self.topic / path.stem)
        return self._content_documents

    def details(self, directory):
        if not directory.exists() and not directory.is_symlink():
            return
        if directory.is_symlink():
            self.add('detail.symlink', 'UNCHECKED', directory, '디렉토리 링크는 순회하지 않습니다.')
            return
        if not directory.is_dir():
            self.add('detail.directory', 'FAIL', directory, '상세 자료 경로가 디렉토리가 아닙니다.')
            return
        def error(exc):
            self.add('detail.read', 'ERROR', directory, str(exc))
        for root, dirs, files in os.walk(directory, onerror=error, followlinks=False):
            for name in sorted(dirs):
                child = Path(root) / name
                if child.is_symlink():
                    self.add('detail.symlink', 'UNCHECKED', child, '디렉토리 링크는 순회하지 않습니다.')
            dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink())
            for name in sorted(files):
                if Path(name).suffix.lower() != '.md':
                    continue
                path = Path(root) / name
                try:
                    _, tokens = self.read(path)
                    self._content_documents.append((path, tokens))
                except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
                    self.add('detail.read', 'ERROR', path, str(exc))

    def result(self):
        counts = Counter(c['status'] for c in self.checks)
        code = 2 if counts['ERROR'] or counts['UNCHECKED'] else 1 if counts['FAIL'] else 0
        return dict(topic=str(self.topic), scope='selected-topic-current-reports',
                    groups=self.selected_groups,
                    status=('PASS', 'FAIL', 'INCOMPLETE')[code], exit_code=code,
                    documents=sorted({os.path.realpath(path) for path, _ in self.docs}),
                    exclusions=self.exclusions, diagrams_checked=self.diagram_count,
                    counts=dict(counts), checks=self.checks,
                    limits=['실제 승인, 설계 타당성, 내용의 충실도와 도식 표시/정렬은 판정하지 않습니다.',
                            '과거 report 본문, 미시작 후속 단계와 외부 URL은 전수 검사하지 않습니다.'])


def run_checks(context, checks):
    context.selected_groups = [name for name, _ in checks]
    if context.load():
        for _, check in checks:
            check(context)
    return context.result()


def run_cli(checks, argv=None):
    parser = argparse.ArgumentParser(description='Read-only code-development checks: ' + ', '.join(name for name, _ in checks))
    parser.add_argument('topic', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if DEPENDENCY_ERROR:
        result = dict(status='INCOMPLETE', exit_code=2, groups=[name for name, _ in checks], checks=[dict(
            id='dependency', status='ERROR', source=str(args.topic), line=None,
            message=f'{DEPENDENCY_ERROR}; scripts/requirements.txt의 의존성을 준비하십시오.')])
    else:
        instance = Context(args.topic)
        try:
            result = run_checks(instance, checks)
        except Exception as exc:
            instance.add('execution', 'ERROR', args.topic, f'{type(exc).__name__}: {exc}')
            result = instance.result()
    if args.json:
        encoding = (sys.stdout.encoding or 'ascii').lower().replace('-', '')
        output = json.dumps(result, ensure_ascii=encoding not in ('utf8', 'utf16', 'utf32'), indent=2)
    else:
        lines = [result['status']]
        for item in result['checks']:
            lines.append(f"{item['status']} [{item['id']}] {item['source']}:{item['line'] or ''} {item['message']}")
        lines.append(f"표시된 도식 검사 수: {result.get('diagrams_checked', 0)}. 실제 표시/승인은 별도 판단입니다.")
        output = '\n'.join(lines)
        encoding = sys.stdout.encoding or 'utf-8'
        output = output.encode(encoding, errors='backslashreplace').decode(encoding)
    try:
        print(output)
    except OSError:
        return 2
    return result['exit_code']
