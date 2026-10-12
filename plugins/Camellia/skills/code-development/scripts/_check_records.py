"""Selected manifest, report revisions and predecessor relationships."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit

import yaml

from _check_markdown import check_links, link_target, yaml_value
from _check_runtime import (
    CheckError, STAGES, file_kind, inspect_available, list_directory, present, resolve_path, within,
)

STATUS = {"in_progress", "in_review", "awaiting_approval", "completed", "hold", "superseded"}
ACTIVE = {"in_progress", "in_review", "awaiting_approval"}
STAGE_PATTERN = "(?:" + "|".join(STAGES) + ")"
REPORT_PATTERN = re.compile(r"^(" + STAGE_PATTERN + r")-report(?:-(rev-)?([0-9]+))?\.md$")
REVIEW_PATTERN = re.compile(r"^(.+)-review-([0-9]+)\.md$")
BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
BUNDLE_DIR = re.compile(r"([0-9]+)-([a-z][a-z0-9-]*)\Z")


def number_valid(value, width=3):
    return value.isascii() and value.isdecimal() and int(value) > 0 and value == str(int(value)).zfill(width)


def report_name(name):
    match = REPORT_PATTERN.fullmatch(name)
    if not match:
        return None
    number = match[3]
    if number is not None and not number_valid(number):
        return None
    return match[1], ("legacy" if number is not None and match[2] is None else "current"), int(number or 0)


def review_name(name):
    match = REVIEW_PATTERN.fullmatch(name)
    if not match or not number_valid(match[2]) or report_name(match[1] + ".md") is None:
        return None
    return match[1], int(match[2])


def report_candidate(name):
    return name.endswith(".md") and re.match(r"^" + STAGE_PATTERN + r"-report", name) is not None


def is_review_candidate(name):
    return report_candidate(name) and "-review-" in name


def section_one(context, doc, title, level, rule, parent=None):
    found = doc.headings(title, level, parent)
    context.result.check(rule, len(found) == 1, f"exactly one H{level} '{title}' required", doc.path,
                         found[0].line if found else None)
    return found[0] if len(found) == 1 else None


def manifest_sections(context, first=False):
    result = context.result
    path = context.manifest_path
    kind = file_kind(path, result)
    if kind is None:
        if first:
            if present(path, result):
                result.check("C1.manifest_path", False, "manifest path is a broken link or inaccessible target", path)
            return None, []
        result.check("C2.manifest", False, "selected freight-manifest.md is missing", path)
        result.error("C2.selection", "cannot select task without manifest", path)
        raise CheckError
    if kind != "file":
        result.check("C1.manifest_path" if first else "C2.manifest", False,
                     "manifest path must be a regular file", path)
        if not first:
            result.error("C2.selection", "manifest cannot be parsed", path)
            raise CheckError
        return None, []
    doc = context.document(path)
    selected = []
    for section in [section for section in doc.sections if section.level == 2]:
        matches = False
        # Only title links identify a task; body links and images are references.
        title = doc.tokens[section.start + 1]
        for token in title.children or []:
            if token.type != "link_open":
                continue
            destination, line = token.attrGet("href") or "", section.line
            target = link_target(doc, destination, result, line, record=False)
            if target and target[0] == context.real_topic and not target[1]:
                matches = True
        if matches:
            selected.append(section)
    return doc, selected


class Manifest:
    def __init__(self, context):
        self.context = context
        self.doc, selected = manifest_sections(context)
        result = context.result
        if not result.check("C2.registration", len(selected) == 1,
                            "exactly one H2 must link the selected task directory", self.doc.path):
            result.error("C2.selection", "selected manifest task is not uniquely identifiable", self.doc.path)
            raise CheckError
        self.section = selected[0]
        items = [item for item in self.doc.items if self.section.start < item.start < self.section.end]
        fields = {}
        for label in ("stages", "reference_reports"):
            entries = [item for item in items if re.match(r"^" + label + r"\s*:", self.doc.item_text(item, True))]
            result.check("C2." + label, len(entries) == 1, f"exactly one list field {label} required", self.doc.path)
            fields[label] = entries[0] if len(entries) == 1 else None
        self.stages = None
        stages = fields["stages"]
        if stages is not None:
            value = self.doc.item_text(stages, True).split(":", 1)[1].strip()
            try:
                parsed = yaml_value(value)
            except yaml.YAMLError as exc:
                parsed = None
                result.check("C2.stages_format", False, f"invalid stages syntax: {exc}", self.doc.path, stages.line)
            valid = isinstance(parsed, list) and bool(parsed) and all(isinstance(stage, str) for stage in parsed)
            if valid:
                valid = len(set(parsed)) == len(parsed)
            result.check("C2.stages_list", valid, "nonempty list of unique stage strings required", self.doc.path, stages.line)
            if valid:
                unsupported = [stage for stage in parsed if stage not in STAGES]
                if unsupported:
                    result.error("C2.unsupported_stage", "unsupported stages: " + ", ".join(unsupported), self.doc.path, stages.line)
                else:
                    self.stages = parsed
        if self.stages is None:
            result.error("C2.stage_dependency", "cannot inspect stage relationships without valid stages", self.doc.path)
        reference = fields["reference_reports"]
        if reference is not None:
            text = self.doc.item_text(reference, True).split(":", 1)[1].strip()
            links = self.doc.item_links(reference)
            children = [item for item in items if item.parent == reference.start]
            valid = text == "없음" and not links and not children
            valid = valid or (bool(links) and text != "없음" and
                              all(bool(self.doc.item_links(item)) for item in children))
            result.check("C2.reference_reports_format", valid, "reference_reports must be 없음 or Markdown links", self.doc.path, reference.line)

    def links(self):
        check_links(self.context, self.doc, self.section.start, self.section.end)


@dataclass
class Report:
    path: Path
    stage: str
    format: str
    number: int
    doc: object
    metadata: dict | None
    scope: str | None

    @property
    def status(self):
        return self.metadata.get("status") if self.metadata is not None else None


class Task:
    def __init__(self, context, relationships=True):
        self.context = context
        self.result = context.result
        self.manifest = Manifest(context)
        self.reports = []
        self.reviews = []
        self.bundle_dirs = []
        self.current = {}
        self.by_path = {}
        self.format = "current"
        self.rows = []
        self.table_applied = False
        self.table_readable = True
        self.table_doc = None
        self._collect()
        self._revisions()
        if relationships:
            self.check_bases()

    def check_bases(self):
        for report in self.reports:
            inspect_available(self.base, report)

    def _read_report(self, path):
        if is_review_candidate(path.name):
            self.reviews.append(path)
            return
        if not self.result.check("C3.file_type", file_kind(path, self.result) == "file", "report must be a regular file", path):
            return
        name = report_name(path.name)
        if not self.result.check("C3.filename", name is not None, "supported report filename and revision number required", path):
            return
        stage, format_name, number = name
        try:
            doc = self.context.document(path)
        except CheckError:
            return
        valid = doc.has_frontmatter and doc.yaml_error is None and isinstance(doc.frontmatter, dict)
        self.result.check("C4.frontmatter", valid, doc.yaml_error or "YAML mapping frontmatter required", path, 1)
        if not valid:
            self.result.error("C4.metadata_dependency", "metadata cannot be inspected", path, 1)
        metadata = doc.frontmatter if valid else None
        scope = path.parent.name if format_name == "current" and path.parent != self.context.topic else None
        if metadata is not None:
            if format_name == "legacy":
                value = metadata.get("bundle")
                bundle_valid = "bundle" not in metadata or (isinstance(value, str) and BUNDLE_ID.fullmatch(value) is not None)
                self.result.check("C4.bundle", bundle_valid, "legacy bundle must be a lowercase identifier or omitted", path, 1)
                if not bundle_valid:
                    self.result.error("C4.scope_dependency", "legacy scope cannot be identified", path, 1)
                scope = value if bundle_valid else None
                if path.parent != self.context.topic:
                    self.result.check("C3.legacy_location", False, "legacy reports belong directly in task root", path)
            else:
                scope = path.parent.name if path.parent != self.context.topic else None
            status = metadata.get("status")
            self.result.check("C4.status", isinstance(status, str) and status in STATUS,
                              "status must be a supported string", path, 1)
            if format_name == "current" and status == "in_review":
                self.result.check("C4.in_review", stage == "design", "in_review is allowed only for design", path, 1)
            self.result.check("C4.base_type", "base_on" in metadata and
                              (metadata.get("base_on") is None or isinstance(metadata.get("base_on"), str)),
                              "base_on must be present and null or a string", path, 1)
            for field in ("revision", "previous", "once", "diff", "completion_type"):
                self.result.check("C4.forbidden_field", field not in metadata, f"forbidden field: {field}", path, 1)
        if self.manifest.stages is not None:
            self.result.check("C2.report_stage", stage in self.manifest.stages, "report stage must be registered in manifest", path)
        report = Report(path, stage, format_name, number, doc, metadata, scope)
        self.reports.append(report)
        self.by_path[resolve_path(path, self.result)] = report

    def _collect(self):
        root = list_directory(self.context.topic, self.result)
        for path in root:
            if report_candidate(path.name):
                inspect_available(self._read_report, path)
        detail_names = {report.path.stem for report in self.reports}
        # Read explicit bundle directory cells from common designs for collection only.
        hints = set()
        for report in self.reports:
            if report.stage != "design" or report.scope is not None:
                continue
            for section in report.doc.headings("작업 묶음표", 3):
                for table in report.doc.tables(section):
                    if not table:
                        continue
                    headers = [cell["text"] for cell in table[0]]
                    if "디렉토리" in headers:
                        column = headers.index("디렉토리")
                        for row in table[1:]:
                            if len(row) > column:
                                cell = row[column]
                                value = cell["text"].strip().rstrip("/")
                                if value != "미시작" and value and "/" not in value and "\\" not in value:
                                    hints.add(value)
                                for destination in cell["links"]:
                                    target = link_target(report.doc, destination, self.result, record=False)
                                    if target and target[0].parent == self.context.real_topic:
                                        hints.add(target[0].name)
        for path in root:
            if path.name == "deferred" or path.name in detail_names:
                continue
            by_name = re.match(r"^[0-9]+-", path.name) is not None or path.name in hints
            try:
                kind = file_kind(path, self.result)
            except CheckError:
                continue
            if kind != "directory":
                if by_name:
                    self.bundle_dirs.append(path)
                    self.result.check("C10.directory_type", False, "bundle scope must be a directory", path)
                continue
            if path.is_symlink():
                if by_name:
                    self.bundle_dirs.append(path)
                    self.result.error("runtime.directory", "bundle directory symlink is not traversed", path)
                continue
            try:
                children = list_directory(path, self.result)
            except CheckError:
                continue
            candidates = [child for child in children if report_candidate(child.name)]
            if by_name or candidates:
                self.bundle_dirs.append(path)
                for candidate in candidates:
                    inspect_available(self._read_report, candidate)

    def _revisions(self):
        formats = {report.format for report in self.reports}
        self.result.check("C3.format", len(formats) <= 1, "current and legacy report forms must not mix", self.context.topic)
        if len(formats) > 1:
            self.result.error("C3.format_dependency", "mixed report formats cannot define current scopes", self.context.topic)
        if formats == {"legacy"}:
            self.format = "legacy"
        groups = defaultdict(list)
        for report in self.reports:
            if report.format == "legacy" and (report.metadata is None or (
                "bundle" in report.metadata and not (isinstance(report.metadata["bundle"], str)
                                                      and BUNDLE_ID.fullmatch(report.metadata["bundle"]))
            )):
                self.result.error("C3.scope_dependency", "current legacy revision requires readable bundle metadata", report.path)
                continue
            key = (report.scope, report.stage)
            groups[key].append(report)
        for key, group in groups.items():
            numbers = [report.number for report in group]
            self.result.check("C3.revision_unique", len(numbers) == len(set(numbers)), "revision numbers must be unique in scope/stage", group[0].path.parent)
            maximum = max(numbers)
            latest = [report for report in group if report.number == maximum]
            if len(latest) == 1:
                if latest[0].status != "superseded":
                    self.current[key] = latest[0]
            else:
                self.result.error("C3.current_dependency", "current revision is ambiguous", group[0].path.parent)
            for report in group:
                if report.number < maximum:
                    self.result.check("C3.superseded", report.status == "superseded", "older revision must be superseded", report.path, 1)

    def lookup(self, path):
        return self.by_path.get(resolve_path(path, self.result))

    def predecessor_key(self, scope, stage):
        stages = self.manifest.stages
        if stages is None or stage not in stages:
            return None
        if scope is None:
            index = stages.index(stage)
            return None if index == 0 else (None, stages[index - 1])
        if stage == "design":
            return (None, "discussion" if self.format == "legacy" else "design")
        if stage == "implementation":
            return (scope if (scope, "design") in self.current else None, "design")
        if stage in ("verification", "qa"):
            return (scope, stages[stages.index(stage) - 1]) if stages.index(stage) else None
        return None

    def base_path(self, report):
        value = report.metadata.get("base_on") if report.metadata is not None else None
        if not isinstance(value, str) or not value:
            return None
        try:
            uri = urlsplit(value)
            valid = not (uri.scheme or uri.netloc or uri.query or uri.fragment or "?" in value or "#" in value)
        except ValueError:
            valid = False
        valid = valid and not Path(value).is_absolute() and "\\" not in value and "\x00" not in value
        if self.format == "legacy":
            valid = valid and Path(value).name == value
        if not self.result.check("C5.path", valid, "base_on must be a literal relative report path without URI/query/fragment", report.path, 1):
            return None
        path = resolve_path(report.path.parent / value, self.result)
        if not self.result.check("C5.scope", within(path, self.context.real_topic), "base_on must remain inside selected task", report.path, 1):
            return None
        return path

    def base(self, report):
        if report.metadata is None or self.manifest.stages is None:
            self.result.error("C5.dependency", "predecessor cannot be inspected without metadata/stages", report.path)
            return
        if not isinstance(report.status, str) or report.status not in STATUS:
            self.result.error("C5.state_dependency", "predecessor rules require a valid report status", report.path, 1)
            return
        if "base_on" not in report.metadata or not (
            report.metadata["base_on"] is None or isinstance(report.metadata["base_on"], str)
        ):
            self.result.error("C5.dependency", "predecessor requires a typed base_on field", report.path, 1)
            return
        key = self.predecessor_key(report.scope, report.stage)
        if key is None and report.scope is None and report.stage == "discussion":
            self.result.check("C5.initial", report.metadata.get("base_on") is None, "common discussion base_on must be null", report.path, 1)
            return
        if key is None:
            self.result.check("C5.relationship", False, "no supported predecessor for this report scope/stage", report.path, 1)
            return
        path = self.base_path(report)
        if path is None:
            self.result.check("C5.required", False, "required base_on path is absent or invalid", report.path, 1)
            return
        source = self.by_path.get(path)
        if not self.result.check("C5.target", source is not None, "base_on must resolve to a collected report", report.path, 1):
            return
        if not isinstance(source.status, str) or source.status not in STATUS:
            self.result.error("C5.source_state_dependency", "predecessor status cannot be interpreted", source.path, 1)
            return
        relationship = (source.scope, source.stage) == key
        if report.scope is not None and report.stage == "implementation" and source.stage == "design":
            historical = report.status in ("hold", "superseded")
            preserved = report.status == "completed" and source.scope is None and source.status in ("hold", "superseded")
            if historical or preserved:
                relationship = source.scope in (None, report.scope)
        self.result.check("C5.relationship", relationship,
                          f"expected predecessor scope/stage: {key}", report.path, 1)
        if report.status in ("hold", "superseded"):
            self.result.na("C5.source_status", "historical hold/superseded connection preserves previous source status", report.path)
            return
        allowed = source.status == "completed"
        if report.status == "completed" and report.scope is not None:
            common = source.scope is None
            allowed = allowed or (common and source.status == "superseded")
            allowed = allowed or (common and source.stage == "design" and source.status == "hold"
                                  and report.stage in ("design", "implementation"))
        self.result.check("C5.source_status", allowed, "source must be completed or a preserved completed-bundle exception", report.path, 1)

    def current_report(self, path):
        report = self.lookup(path)
        if report is None:
            self.result.error("input.report", "specified report could not be collected/parsed", path)
            raise CheckError
        return report

    def submission_target(self, report):
        return self.result.check("C3.submission_current", self.current.get((report.scope, report.stage)) is report
                                 and report.status != "superseded", "submission must select current non-superseded revision", report.path)

    def entry_input(self, args):
        from _check_runtime import lexical_path
        scope_path = lexical_path(args.scope_dir, self.result, "scope-dir")
        scope = None if scope_path == self.context.topic else scope_path.name
        valid = (scope_path == self.context.topic or scope_path.parent == self.context.topic)
        valid = valid and within(resolve_path(scope_path, self.result), self.context.real_topic)
        if not valid:
            self.result.error("input.scope_dir", "scope-dir must be task root or an immediate bundle path", scope_path)
            raise CheckError
        bundle_id = args.bundle_id
        if self.format == "legacy":
            if scope is not None or (bundle_id is not None and BUNDLE_ID.fullmatch(bundle_id) is None):
                self.result.error("input.bundle", "legacy scope requires task root and optional valid bundle-id", scope_path)
                raise CheckError
            scope = bundle_id
        elif bundle_id is not None or (scope is not None and not valid_bundle_name(scope)):
            self.result.error("input.bundle", "current scope requires bundle directory syntax and no bundle-id", scope_path)
            raise CheckError
        if args.stage not in STAGES or self.manifest.stages is None or args.stage not in self.manifest.stages:
            self.result.error("input.stage", "stage must be supported and registered in manifest", self.context.manifest_path)
            raise CheckError
        kind = file_kind(scope_path, self.result)
        if kind not in (None, "directory"):
            self.result.error("input.scope_dir", "scope-dir must be a directory or a new bundle path", scope_path)
            raise CheckError
        if kind == "directory" and scope_path.is_symlink():
            self.result.error("runtime.directory", "required scope directory symlink is not traversed", scope_path)
            raise CheckError
        target = self.current.get((scope, args.stage))
        if args.base_report == "none":
            if scope is not None or args.stage != "discussion":
                self.result.error("input.base_report", "none is allowed only for common discussion", scope_path)
                raise CheckError
            if target is not None and isinstance(target.status, str) and target.status in ACTIVE:
                self.result.check("C5.entry_matches", target.metadata.get("base_on") is None,
                                  "active common discussion must retain null base_on", target.path)
            self.result.na("C5.entry_source", "common discussion has no predecessor", scope_path)
            return scope, target, None
        if scope is None and args.stage == "discussion":
            self.result.error("input.base_report", "common discussion requires none", scope_path)
            raise CheckError
        source_path = self.context.argument_file(args.base_report, "base-report")
        source = self.current_report(source_path)
        key = self.predecessor_key(scope, args.stage)
        self.result.check("C5.entry_relationship", key is not None and (source.scope, source.stage) == key,
                          f"explicit entry predecessor must match {key}", source.path)
        self.result.check("C5.entry_source_status", source.status == "completed", "new entry source must be completed without historical exceptions", source.path, 1)
        if target is not None and isinstance(target.status, str) and target.status in ACTIVE:
            self.result.check("C5.entry_matches", self.base_path(target) == resolve_path(source.path, self.result),
                              "explicit source must match active report base_on", target.path, 1)
        return scope, target, source


def valid_bundle_name(name):
    match = BUNDLE_DIR.fullmatch(name)
    return match is not None and number_valid(match[1], 2)


def first_save(context):
    result = context.result
    for path in (context.root / "specs", context.topic.parent, context.topic):
        kind = file_kind(path, result)
        if present(path, result):
            result.check("C1.path", kind == "directory", "existing path component must be a directory", path)
        else:
            result.check("C1.path", True, "new path component is permitted", path)
    doc, selected = manifest_sections(context, first=True)
    result.check("C1.registration", not selected, "new task must not already be registered", context.manifest_path)
    if file_kind(context.topic, result) == "directory":
        entries = list_directory(context.topic, result)
        candidates = [path for path in entries if report_candidate(path.name)]
        for path in entries:
            if path.name == "deferred" or path.name.endswith("-report"):
                continue
            if file_kind(path, result) == "directory" and not path.is_symlink():
                candidates.extend(child for child in list_directory(path, result) if report_candidate(child.name))
        result.check("C1.existing_report", not candidates, "new task must not contain existing stage reports", context.topic)
    else:
        result.na("C1.existing_report", "topic directory not created yet", context.topic)
