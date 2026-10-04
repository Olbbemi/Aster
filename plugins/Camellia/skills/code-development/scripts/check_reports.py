#!/usr/bin/env python3
"""Read-only checks for one existing code-development topic.

The contract and limitations live in references/report-checks.md.
"""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

try:
    import yaml
    from markdown_it import MarkdownIt
except ImportError as exc:
    DEPENDENCY_ERROR = str(exc)
else:
    DEPENDENCY_ERROR = None

REPORT = re.compile(r'([a-z][a-z0-9-]*)-report-([0-9]+)\.md\Z')
STATUSES = {'in_progress', 'awaiting_approval', 'completed', 'hold', 'superseded'}
AREAS = ('단계 결과', '인계 사항', '완료 체크리스트', '사용자 승인')
BASIS = 'references/report-checks.md'


def visible(tokens):
    return ''.join(visible(t.children or []) if t.type == 'image' else
                   t.content if t.type in ('text', 'code_inline') else
                   ' ' if t.type in ('softbreak', 'hardbreak') else ''
                   for t in tokens)


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


class Checker:
    def __init__(self, topic):
        self.topic = Path(topic).absolute()
        self.checks, self.docs, self.raw = [], {}, {}
        self.exclusions = []
        self.parser = MarkdownIt('commonmark').enable('table')
        self.diagram_count = 0

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
        self.links(path, selected)
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
        self.add('report.metadata', 'PASS', path, 'status/base_on 형식을 확인했습니다.')
        return meta, tokens

    def links(self, source, tokens):
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
                    self.add('link.syntax', 'FAIL', source, f'{url}: {exc}', line)
                    continue
                try:
                    if target is None:
                        self.add('link.external', 'SKIP', source, url, line)
                        continue
                    mode = target.stat().st_mode
                    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                        raise ValueError('일반 파일/디렉토리가 아닌 대상입니다.')
                    if fragment:
                        if not stat.S_ISREG(mode) or target.suffix.lower() != '.md':
                            self.add('link.fragment', 'UNCHECKED', source, f'비Markdown 절: {url}', line)
                            continue
                        if fragment not in anchors(self.read(target)[1]):
                            self.add('link.fragment', 'FAIL', source, f'절 누락: {url}', line)
                            continue
                    self.add('link.local', 'PASS', source, url, line)
                except (FileNotFoundError, NotADirectoryError):
                    self.add('link.target', 'FAIL', source, f'대상 누락: {url}', line)
                except UnicodeError as exc:
                    self.add('link.read', 'ERROR', source, f'{url}: {exc}', line)
                except ValueError as exc:
                    self.add('link.syntax', 'FAIL', source, f'{url}: {exc}', line)
                except (OSError, RuntimeError) as exc:
                    self.add('link.read', 'ERROR', source, f'{url}: {exc}', line)

    def diagrams(self, source, tokens):
        for token in tokens:
            if token.type != 'fence' or token.info.split() != ['text', 'ascii-flow']:
                continue
            self.diagram_count += 1
            raw_lines = self.raw[source]
            final = raw_lines[token.map[1] - 1].lstrip(' >')
            closed = re.fullmatch(re.escape(token.markup[0]) + '{' + str(len(token.markup)) + r',}\s*', final) is not None
            self.add('diagram.fence', 'PASS' if closed else 'FAIL', source,
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
            self.add('diagram.characters', 'FAIL' if bad else 'PASS', source,
                     ', '.join(bad) if bad else '문자 형식만 확인했습니다. 표시/정렬은 별도 확인입니다.',
                     token.map[0] + 1)

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
                    self.links(path, tokens)
                    self.diagrams(path, tokens)
                except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
                    self.add('detail.read', 'ERROR', path, str(exc))

    def run(self):
        if not self.topic.is_dir():
            self.add('input.topic', 'ERROR', self.topic, '존재하는 작업 주제 디렉토리가 필요합니다.')
            return self.result()
        manifest = self.topic.parent / 'freight-manifest.md'
        try:
            stages = self.manifest(manifest)
        except UnicodeError as exc:
            self.add('manifest.read', 'ERROR', manifest, str(exc))
            return self.result()
        except (ValueError, yaml.YAMLError) as exc:
            self.add('manifest.format', 'FAIL', manifest, str(exc))
            return self.result()
        except (OSError, UnicodeError, RuntimeError) as exc:
            self.add('manifest.read', 'ERROR', manifest, str(exc))
            return self.result()
        groups, parsed = {}, {}
        try:
            paths = sorted(self.topic.iterdir())
        except OSError as exc:
            self.add('input.read', 'ERROR', self.topic, str(exc))
            return self.result()
        for path in paths:
            match = REPORT.fullmatch(path.name)
            if not match:
                if '-report-' in path.name and path.suffix == '.md':
                    self.add('report.filename', 'FAIL', path, 'report 파일명 형식이 잘못되었습니다.')
                continue
            stage, number = match[1], int(match[2])
            if number < 1 or match[2] != f'{number:03d}' or stage not in stages:
                self.add('report.filename', 'FAIL', path, '단계/양수 세 자리 이상 번호를 확인하십시오.')
            groups.setdefault(stage, []).append((number, path))
            try:
                parsed[path] = self.report(path)
            except UnicodeError as exc:
                self.add('report.read', 'ERROR', path, str(exc))
            except (ValueError, yaml.YAMLError) as exc:
                self.add('report.format', 'FAIL', path, str(exc))
            except (OSError, UnicodeError, RuntimeError) as exc:
                self.add('report.read', 'ERROR', path, str(exc))
        if not groups:
            self.add('input.reports', 'ERROR', self.topic, '저장된 report가 없습니다. 최초 저장 전에는 실행하지 않습니다.')
        for stage, entries in sorted(groups.items()):
            entries.sort()
            for n, (number, path) in enumerate(entries):
                if path not in parsed:
                    continue
                meta, tokens = parsed[path]
                current = n == len(entries) - 1
                if (current and meta['status'] == 'superseded') or (not current and meta['status'] != 'superseded'):
                    self.add('report.revision', 'FAIL', path, '현재 번호/이전 번호의 superseded 상태가 맞지 않습니다.')
                base = meta['base_on']
                if stage in stages:
                    index = stages.index(stage)
                    if index == 0:
                        if base is not None:
                            self.add('report.base', 'FAIL', path, '선행 단계 없는 report의 base_on은 null이어야 합니다.')
                    elif base is None or self.topic / base not in parsed:
                        self.add('report.base', 'FAIL', path, '유효한 형식의 선행 report가 없습니다.')
                    else:
                        match = REPORT.fullmatch(base)
                        if match[1] != stages[index - 1]:
                            self.add('report.base', 'FAIL', path, 'stages의 바로 앞 단계 report를 참조해야 합니다.')
                        elif meta['status'] not in ('hold', 'superseded') and parsed[self.topic / base][0]['status'] != 'completed':
                            self.add('report.predecessor', 'FAIL', path, '현재 report의 선행 입력이 completed 상태가 아닙니다.')
                if not current:
                    self.exclusions.append(dict(source=str(path), scope='body-links-diagrams',
                                                reason='과거 report 본문은 현재 형식/링크/도식 검사에서 제외합니다.'))
                    continue
                heads = Counter(visible(tokens[i + 1].children or []) for i, t in enumerate(tokens)
                                if t.type == 'heading_open' and t.tag == 'h2' and t.level == 0)
                for name in AREAS:
                    self.add('report.area', 'PASS' if heads[name] == 1 else 'FAIL', path,
                             f'{name}: {heads[name]}개')
                self.links(path, tokens)
                self.diagrams(path, tokens)
                if stage == 'design':
                    self.details(self.topic / path.stem)
        return self.result()

    def result(self):
        counts = Counter(c['status'] for c in self.checks)
        code = 2 if counts['ERROR'] or counts['UNCHECKED'] else 1 if counts['FAIL'] else 0
        return dict(topic=str(self.topic), scope='selected-topic-current-reports',
                    status=('PASS', 'FAIL', 'INCOMPLETE')[code], exit_code=code,
                    documents=sorted({os.path.realpath(path) for path, _ in self.docs}),
                    exclusions=self.exclusions, diagrams_checked=self.diagram_count,
                    counts=dict(counts), checks=self.checks,
                    limits=['실제 승인, 설계 타당성, 내용의 충실도와 도식 표시/정렬은 판정하지 않습니다.',
                            '과거 report 본문, 미시작 후속 단계와 외부 URL은 전수 검사하지 않습니다.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('topic', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if DEPENDENCY_ERROR:
        result = dict(status='INCOMPLETE', exit_code=2, checks=[dict(
            id='dependency', status='ERROR', source=str(args.topic), line=None,
            message=f'{DEPENDENCY_ERROR}; scripts/requirements.txt의 의존성을 준비하십시오.')])
    else:
        instance = Checker(args.topic)
        try:
            result = instance.run()
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


if __name__ == '__main__':
    sys.exit(main())
