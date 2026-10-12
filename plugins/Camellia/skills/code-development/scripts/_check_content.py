"""Report bodies, bundles, diagrams, reviews and deferred-record checks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from _check_markdown import check_links, inline_value, link_target
from _check_records import (
    BUNDLE_ID, STATUS, section_one, review_name, valid_bundle_name,
)
from _check_runtime import CheckError, STAGES, file_kind, list_directory, present, resolve_path

COMMON_H2 = ("단계 결과", "인계 사항", "완료 체크리스트", "사용자 승인")
APPROVAL_H3 = ("사용자 판단", "보완 요청과 처리 결과", "남은 사항과 인계 조건")
REVIEW_H2 = ("실행 대상과 근거", "검토 범위와 기준", "검토 결과", "확인하지 못한 사항", "종합 의견")
DEFERRED_H2 = ("필요한 작업", "보류 이유와 현재 범위", "논의 내용과 근거", "재검토 조건과 미결정 사항")
BATCH_ID = re.compile(r"B[1-9][0-9]*\Z")


def timestamp_valid(value, historical=False):
    value = value.strip()
    if historical and value.endswith("."):
        value = value[:-1]
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} \(KST\)", value):
        return False
    try:
        datetime.strptime(value[:-6], "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def section_fields(context, doc):
    fields = {title: section_one(context, doc, title, 2, "C6.section") for title in COMMON_H2}
    approval = fields["사용자 승인"]
    if approval is not None:
        for title in APPROVAL_H3:
            section_one(context, doc, title, 3, "C6.approval_section", approval)
    return fields


def confirmation_text(doc, item):
    """Direct field text; code bodies can fill evidence but cannot define fields."""
    parts = []
    depth = 0
    for token in doc.tokens[item.start + 1:item.end - 1]:
        if token.type == "list_item_open":
            depth += 1
        elif token.type == "list_item_close":
            depth -= 1
        elif depth == 0 and token.type == "inline":
            parts.append(inline_value(token))
        elif depth == 0 and token.type in ("fence", "code_block") and token.content.strip():
            if parts and re.search(r"(?:^|\n)\s*확인 근거:\s*$", parts[-1]):
                # Only presence matters. Literal code labels are not metadata.
                parts[-1] += " nonempty code evidence"
    return "\n".join(parts)


def checklist(context, doc, section, status):
    result = context.result
    if section is None:
        result.check("C7.section_dependency", False, "checklist section not uniquely available", doc.path)
        return
    previous = doc.headings("이전 확인 기록", 3, section) + doc.headings("이전 확인 기록", 4, section)
    previous_items = [item for item in doc.items if section.start < item.start < section.end
                      and re.match(r"^이전 확인 기록(?:\s*:|\s*$)", doc.item_text(item, True))]
    def is_previous(index):
        return any(area.start < index < area.end for area in previous + previous_items)
    items = [item for item in doc.items if section.start < item.start < section.end and not is_previous(item.start)]
    checked = []
    check_items = []
    historical = set()
    for item in items:
        text = doc.item_text(item, True)
        match = re.match(r"^\[([ xX])\](?:\s|$)", text)
        if match is None:
            continue
        check_items.append(item)
        if match[1] == " ":
            continue
        checked.append(item)
        direct_parts = [confirmation_text(doc, item)]
        direct_parts.extend(confirmation_text(doc, child) for child in items if child.parent == item.start
                            and child not in previous_items)
        evidence = []
        times = []
        for part in direct_parts:
            # Labels belong to direct explanatory paragraphs/items, never historical descendants.
            for match in re.finditer(r"(?:^|\n)\s*(확인 근거|확인 완료 시각):\s*([\s\S]*?)(?=\n\s*(?:확인 근거|확인 완료 시각|이전 확인 기록):|\Z)", part):
                if match[1] == "확인 근거":
                    value = match[2].strip()
                    evidence.append(value if not re.fullmatch(r"`+", value) else "")
                else:
                    times.append(match[2].strip())
        result.check("C7.evidence", bool(evidence) and all(evidence), "checked item requires nonempty direct 확인 근거", doc.path, item.line)
        if times:
            historical.add(item.start)
            result.check("C8.item_time", len(times) == 1 and timestamp_valid(times[0], True),
                         "legacy item timestamp must have valid KST date/time", doc.path, item.line)
    if not isinstance(status, str) or status not in STATUS:
        result.error("C7.state_dependency", "completion checklist requires a valid status", doc.path)
    elif status == "completed":
        result.check("C7.completed", bool(check_items) and len(checked) == len(check_items),
                     "completed requires at least one checklist item and all checked", doc.path, section.line)
    else:
        result.na("C7.completed", "unchecked items are allowed before completion", doc.path)
    batches = []
    areas = doc.headings("일괄 반영 기록", 3)
    for area in areas:
        tables = doc.tables(area)
        for table in tables:
            if not table:
                continue
            required = ("묶음", "대상 항목", "반영 시각")
            headers = [cell["text"] for cell in table[0]]
            valid = all(headers.count(label) == 1 for label in required)
            result.check("C8.columns", valid, "batch table requires unique 묶음/대상 항목/반영 시각 columns", doc.path, area.line)
            if not valid:
                result.error("C8.table_dependency", "batch columns cannot be interpreted", doc.path, area.line)
                continue
            for row in table[1:]:
                if len(row) != len(headers):
                    result.check("C8.row", False, "batch table row width mismatch", doc.path, area.line)
                    continue
                cells = {label: row[headers.index(label)] for label in required}
                batches.append((cells["묶음"]["text"], cells["대상 항목"]["text"] or " ".join(cells["대상 항목"]["links"]),
                                cells["반영 시각"]["text"], False, cells["묶음"]["line"] or area.line))
        for item in doc.items:
            if not area.start < item.start < area.end:
                continue
            text = doc.item_text(item, True)
            match = re.match(r"^(B[^\s:]*)\s*:\s*([\s\S]*)", text)
            if match is None:
                continue
            times = []
            for child in doc.items:
                if child.parent != item.start:
                    continue
                time_match = re.match(r"^반영 시각:\s*([\s\S]*)", doc.item_text(child, True))
                if time_match:
                    times.append(time_match[1].strip())
            result.check("C8.list_time_count", len(times) == 1, "legacy batch list requires one timestamp", doc.path, item.line)
            batches.append((match[1], match[2].strip(), times[0] if len(times) == 1 else "", True, item.line))
    identifiers = [batch[0] for batch in batches]
    for identifier, target, timestamp, old, line in batches:
        result.check("C8.batch_id", BATCH_ID.fullmatch(identifier) is not None and identifiers.count(identifier) == 1,
                     f"unique positive batch identifier required: {identifier}", doc.path, line)
        result.check("C8.batch_target", bool(target.strip()), "batch target must be nonempty", doc.path, line)
        result.check("C8.batch_time", timestamp_valid(timestamp, old), "valid KST batch timestamp required", doc.path, line)
    needing_batch = [item for item in checked if item.start not in historical]
    if needing_batch:
        result.check("C8.batch_required", bool(areas) and bool(batches), "checked items without legacy per-item time require batch records", doc.path, section.line)
    else:
        result.na("C8.batch_required", "no checked item requiring a batch record", doc.path)
    for area in previous + previous_items:
        for match in re.finditer(r"반영 기록:\s*(B[0-9A-Za-z-]+)\b", doc.text(area.start, area.end, code=False)):
            result.check("C8.previous_reference", match[1] in identifiers, f"previous batch reference must exist: {match[1]}", doc.path, area.line)
    for item in doc.items:
        if not section.start < item.start < section.end:
            continue
        for line in doc.item_text(item, True).splitlines():
            if line.strip().startswith("확인 완료 시각:"):
                value = line.strip().split(":", 1)[1].strip()
                result.check("C8.recorded_item_time", timestamp_valid(value, True),
                             "recorded legacy item timestamp must be valid, including previous records", doc.path, item.line)


def completion_kind(context, task, report, approval, final=False):
    result = context.result
    if report.stage not in ("verification", "qa"):
        result.na("C9.completion", "completion keyword applies only to verification/qa", report.path)
        return
    if not isinstance(report.status, str) or report.status not in STATUS:
        result.error("C9.state_dependency", "completion keyword requires a valid status", report.path)
        return
    if approval is None:
        result.check("C9.section_dependency", False, "approval section not uniquely available", report.path)
        return
    areas = report.doc.headings("완료 구분", 3, approval)
    required = final or report.status in ("awaiting_approval", "completed")
    if not areas and not required:
        result.na("C9.completion", "unfinished report may omit completion keyword", report.path)
        return
    if not result.check("C9.section", len(areas) == 1, "exactly one completion section required", report.path,
                        areas[0].line if areas else None):
        return
    area = areas[0]
    value = report.doc.content(area)
    if (not value or value == "미정") and not required:
        result.na("C9.completion", "unfinished completion keyword is allowed", report.path)
        return
    lines = value.splitlines()
    keyword = lines[0].strip() if lines else ""
    allowed = {"all_passed", "handoff"}
    if report.format == "legacy":
        allowed = {"all_passed", "qa_handoff" if report.stage == "verification" else "next_cycle_handoff"}
    if report.stage == "qa" and report.format == "current" and (final or not task.is_bundled):
        allowed = {"all_passed"}
    result.check("C9.keyword", keyword in allowed, "completion keyword must be one of " + ", ".join(sorted(allowed)), report.path, area.line)
    result.check("C9.explanation", bool("\n".join(lines[1:]).strip()), "completion keyword requires explanation on following lines", report.path, area.line)


def diagrams(context, doc):
    found = False
    for token in doc.tokens:
        if token.type != "fence" or token.info.strip() != "text ascii-flow":
            continue
        found = True
        line = doc.line(token)
        # CommonMark maps include the closing marker only when the parser recognized
        # one. This also works for correctly indented fences inside list items.
        # CommonMark counts LF physical lines, not Unicode text separators.
        content_lines = token.content.count("\n") + int(bool(token.content) and not token.content.endswith("\n"))
        closing = token.map is not None and token.map[1] - token.map[0] == content_lines + 2
        context.result.check("C12.fence", closing, "marked ASCII flow requires closing fence", doc.path, line)
        forbidden = set()
        for char in token.content:
            code = ord(char)
            if char == "\n":
                continue
            if char == "\t" or unicodedata.category(char) == "Cc" or 0x2500 <= code <= 0x25FF \
                    or (code > 127 and "ARROW" in unicodedata.name(char, "")) \
                    or code in (0x2013, 0x2014) or char in "＋－｜＜＞":
                forbidden.add(f"U+{code:04X}")
        context.result.check("C12.symbols", not forbidden,
                             "no forbidden controls/flow symbols" + (": " + ", ".join(sorted(forbidden)) if forbidden else ""), doc.path, line)
    if not found:
        context.result.na("C12.diagram", "no explicitly marked ASCII flow", doc.path)


def design_details(context, report, include_diagrams):
    if report.stage != "design":
        return
    directory = report.path.parent / report.path.stem
    if not present(directory, context.result):
        context.result.na("C11.design_details", "no separate design details directory", report.path)
        return
    if not context.result.check("C11.detail_directory", file_kind(directory, context.result) == "directory",
                                "design details path must be a directory", directory):
        return
    destinations = set()
    for destination, line in report.doc.links():
        target = link_target(report.doc, destination, context.result, line, record=False)
        if target:
            destinations.add(target[0])
    try:
        entries = list_directory(directory, context.result)
    except CheckError:
        return
    for path in entries:
        valid = path.suffix == ".md" and file_kind(path, context.result) == "file"
        if not context.result.check("C11.detail_location", valid, "design details must be direct <group>.md files", path):
            continue
        context.result.check("C11.detail_link", resolve_path(path, context.result) in destinations,
                             "design detail must be linked from current report", path)
        try:
            doc = context.document(path)
            check_links(context, doc)
            if include_diagrams:
                diagrams(context, doc)
        except CheckError:
            continue


def report_body(task, report, include_diagrams=True, final=False):
    context = task.context
    fields = section_fields(context, report.doc)
    checklist(context, report.doc, fields["완료 체크리스트"], report.status)
    completion_kind(context, task, report, fields["사용자 승인"], final)
    check_links(context, report.doc)
    design_details(context, report, include_diagrams)
    if include_diagrams:
        diagrams(context, report.doc)


def bundles(task):
    context = task.context
    result = context.result
    scopes = {report.scope for report in task.reports if report.scope is not None and report.status != "superseded"}
    task.is_bundled = bool(task.bundle_dirs or scopes)
    if task.manifest.stages != list(STAGES):
        result.na("C10.bundles", "bundle table applies to the default five-stage flow", context.topic)
        return
    design = task.current.get((None, "design"))
    regions = []
    if design is not None:
        parents = design.doc.headings("단계 결과", 2)
        if len(parents) == 1:
            regions = design.doc.headings("작업 묶음표", 3, parents[0])
    written = design is not None and any(design.doc.content(region) for region in regions)
    if not task.is_bundled and not written:
        result.na("C10.bundles", "no bundle scopes or table region", context.topic)
        return
    task.table_applied = True
    if design is None or len(regions) != 1:
        task.table_readable = False
        result.check("C10.table_section", False, "bundle work requires unique common design/table section", context.topic)
        return
    task.table_doc = design.doc
    region = regions[0]
    tables = design.doc.tables(region)
    if len(tables) != 1 or not tables[0]:
        task.table_readable = False
        if task.format == "legacy" and design.doc.content(region):
            result.error("C10.legacy_table", "nonformal legacy bundle table cannot be interpreted", design.path, region.line)
        else:
            result.check("C10.table", False, "one formal bundle table required", design.path, region.line)
        return
    table = tables[0]
    headers = [cell["text"] for cell in table[0]]
    required = ("묶음", "제목", "범위/완료 기준", "의존/진입", "설계 정본", "결과 참조") if task.format == "legacy" else \
               ("묶음", "범위/완료 기준", "의존/진입", "설계 정본", "디렉토리", "결과 참조")
    valid = all(headers.count(label) == 1 for label in required)
    result.check("C10.columns", valid, "bundle table requires each contracted column exactly once", design.path, region.line)
    if not valid:
        task.table_readable = False
        return
    names = set()
    registered = set()
    for row in table[1:]:
        if len(row) != len(headers):
            result.check("C10.row", False, "bundle row width mismatch", design.path, region.line)
            continue
        cells = {label: row[headers.index(label)] for label in required}
        line = cells["묶음"]["line"] or region.line
        result.check("C10.cells", all(cells[label]["text"].strip() or cells[label]["links"] for label in required), "required bundle cells must be nonempty", design.path, line)
        name = cells["묶음"]["text"]
        result.check("C10.bundle_unique", bool(name) and name not in names, "bundle name/ID must be unique", design.path, line)
        names.add(name)
        scope = name if task.format == "legacy" else cells["디렉토리"]["text"].rstrip("/")
        unstarted = scope == "미시작" or cells["결과 참조"]["text"] == "미시작"
        if task.format == "current" and cells["디렉토리"]["links"]:
            links = cells["디렉토리"]["links"]
            target = link_target(design.doc, links[0], result, line) if len(links) == 1 else None
            if target and target[0].parent == context.real_topic and not target[1]:
                scope = target[0].name
            else:
                result.check("C10.directory_link", False, "directory cell must link one immediate bundle directory", design.path, line)
        if task.format == "legacy":
            result.check("C10.bundle_id", BUNDLE_ID.fullmatch(scope) is not None, "legacy bundle cell must contain valid ID", design.path, line)
        elif scope != "미시작":
            result.check("C10.directory_name", valid_bundle_name(scope), "bundle directory requires padded positive number and lowercase name", design.path, line)
        if scope != "미시작":
            result.check("C10.directory_unique", scope not in registered, "bundle directory/ID must be unique", design.path, line)
            registered.add(scope)
            if task.format == "current" and valid_bundle_name(scope):
                result.check("C10.directory_exists", file_kind(context.topic / scope, result) == "directory",
                             "named started bundle directory must exist", design.path, line)
        task.rows.append({"scope": scope, "unstarted": unstarted, "line": line})
        for destination in cells["결과 참조"]["links"]:
            target = link_target(design.doc, destination, result, line)
            linked = task.by_path.get(target[0]) if target else None
            result.check("C10.result_scope", linked is not None and linked.scope == scope
                         and linked.stage in ("implementation", "verification", "qa"),
                         "result reference must select implementation/verification/qa of this bundle", design.path, line)
    task.is_bundled = task.is_bundled or bool(task.rows)
    number_names = set()
    for path in task.bundle_dirs:
        valid = valid_bundle_name(path.name)
        result.check("C10.directory_name", valid, "bundle directory requires padded positive number and lowercase name", path)
        if valid:
            number_names.add(path.name)
        # Empty directories still represent started scopes and require registration.
        if any(report.scope == path.name and report.status != "superseded" for report in task.reports) or not any(
            report.scope == path.name for report in task.reports
        ):
            result.check("C10.registration", path.name in registered, "started bundle directory must be registered", path)
    if task.format == "current":
        number_names.update(scope for scope in registered if valid_bundle_name(scope))
    numbers = [int(name.split("-", 1)[0]) for name in sorted(number_names)]
    result.check("C10.number_unique", len(numbers) == len(set(numbers)), "bundle directory numbers must be unique", context.topic)
    for scope in sorted(scopes):
        result.check("C10.registration", scope in registered, "started bundle report must be registered", context.topic)
    if task.is_bundled:
        for (scope, stage), report in task.current.items():
            if scope is None and stage in ("implementation", "verification", "qa"):
                result.check("C10.root_results", report.status == "superseded", "bundle task must not mix current root implementation/verification/qa", report.path)
    check_links(context, design.doc, region.start, region.end)


def review(context, report_path, review_path):
    result = context.result
    parsed = review_name(review_path.name)
    result.check("C13.filename", parsed is not None and parsed[0] == report_path.stem,
                 "review filename must identify specified report and padded positive number", review_path)
    result.check("C13.location", review_path.parent == report_path.parent,
                 "review must be in same directory as specified report", review_path)
    try:
        doc = context.document(review_path)
    except CheckError:
        return
    first_h2 = min((section.start for section in doc.sections if section.level == 2), default=len(doc.tokens))
    top_items = [item for item in doc.items if item.parent is None and item.start < first_h2]
    for label in ("검토자", "모델명/버전", "검토 대상"):
        items = [item for item in top_items if re.match(r"^" + re.escape(label) + r":", doc.item_text(item, True))]
        valid = len(items) == 1
        result.check("C13.field", valid, f"exactly one top list field {label} required", review_path)
        if not valid:
            continue
        item = items[0]
        value = doc.item_text(item, True).split(":", 1)[1].strip()
        result.check("C13.field_value", bool(value), f"nonempty {label} value required", review_path, item.line)
        if label == "검토 대상":
            links = doc.item_links(item, direct=True)
            if links:
                target = link_target(doc, links[0], result, item.line) if len(links) == 1 else None
                same = target is not None and target[0] == resolve_path(report_path, result) and not target[1]
                if same:
                    uri = urlsplit(links[0])
                    same = not (uri.scheme or uri.netloc or uri.query or uri.fragment) and not Path(unquote(uri.path)).is_absolute()
            else:
                same = bool(value) and not Path(value).is_absolute() and "\x00" not in value
                same = same and resolve_path(review_path.parent / value, result) == resolve_path(report_path, result)
            result.check("C13.target", same, "review target must be exact relative path to specified report", review_path, item.line)
    for title in REVIEW_H2:
        section_one(context, doc, title, 2, "C13.section")
    check_links(context, doc)


def deferred(context, final=False):
    directory = context.topic / "deferred"
    result = context.result
    exists = present(directory, result)
    if final:
        result.check("C14.cleanup", not exists, "deferred path must be absent for overall completion", directory)
        return
    if not exists:
        result.na("C14.deferred", "no current deferred records", directory)
        return
    if not result.check("C14.directory", file_kind(directory, result) == "directory", "deferred must be a directory", directory):
        return
    try:
        entries = list_directory(directory, result)
    except CheckError:
        return
    for path in entries:
        valid = path.suffix == ".md" and file_kind(path, result) == "file"
        if not result.check("C14.location", valid, "deferred items must be direct Markdown files", path):
            continue
        try:
            doc = context.document(path)
        except CheckError:
            continue
        for title in DEFERRED_H2:
            area = section_one(context, doc, title, 2, "C14.section")
            if area is not None:
                result.check("C14.content", doc.has_content(area), f"nonempty {title} body required", path, area.line)
        check_links(context, doc)


def overall(task, final_report):
    result = task.result
    if task.is_bundled:
        if task.table_applied and not task.table_readable:
            result.check("C10.completion_dependency", False, "bundle completion requires readable registration table", task.context.topic)
        required = [(None, "discussion"), (None, "design")]
        for row in task.rows:
            result.check("C10.started", not row["unstarted"], "all registered bundles must have started results", task.table_doc.path, row["line"])
            if row["scope"] != "미시작":
                required.extend((row["scope"], stage) for stage in ("implementation", "verification", "qa"))
    else:
        required = [(None, stage) for stage in task.manifest.stages or []]
    for key in required:
        result.check("C3.required_stage", key in task.current, f"required current report: {key}", task.context.topic)
    is_current = task.current.get((final_report.scope, final_report.stage)) is final_report
    result.check("C9.final_qa", is_current and final_report.stage == "qa"
                 and final_report.status in ("in_progress", "awaiting_approval", "completed"),
                 "specified last QA must be current and in_progress/awaiting_approval/completed", final_report.path)
    for report in task.current.values():
        if report is not final_report:
            result.check("C7.prior_completed", report.status == "completed", "all other current reports must be completed", report.path, 1)
