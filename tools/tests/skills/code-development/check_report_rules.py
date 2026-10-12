#!/usr/bin/env python3
"""Check C1-C14 and execution scopes with independently authored report fixtures."""

import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import expect, require, run_check, snapshot, tree_state


def check(repository, results):
    with snapshot(repository) as harness:
        def case(identifier, function, **options):
            variants = [(identifier, options)]
            if identifier.startswith(("D13.", "D14.", "D15.", "D16.", "D17.", "D18.", "D22.", "D23.", "D24.", "D25.", "D27.")) and "legacy" not in options:
                variants.append((identifier + ".legacy", {**options, "legacy": True}))
            for name, settings in variants:
                def execute(configuration=settings):
                    with harness.fixture(**configuration) as fixture:
                        function(fixture)
                results.case(name, execute)

        def submit(f, report=None, code=0, category=None, forbidden=(), rules=()):
            return expect(harness.invoke("check_report_submission", f.args("check_report_submission", report=report)),
                          code, category, forbidden=forbidden, rules=rules)

        def mutant(identifier, mutate, code=1, category=None, **options):
            def run(f):
                submit(f)
                selected = mutate(f)
                submit(f, report=selected if isinstance(selected, Path) else None, code=code, category=category)
            case(identifier, run, **options)

        def entry(f, *, stage="design", scope=None, base=None, bundle=None, code=0, category=None):
            argv = f.args("check_stage_entry", stage=stage, scope=scope,
                          base=base if base is not None else f.reports["discussion"], bundle=bundle)
            return expect(harness.invoke("check_stage_entry", argv), code, category)

        def final(f, report=None, code=0, category=None):
            return expect(harness.invoke("check_task_completion", f.args("check_task_completion", report=report)), code, category)

        def prepare_final(f):
            f.section(f.reports["qa"], "완료 구분", "all_passed\n고정 시험 결과\n", 3)

        def start(f, mode):
            topic = f.topic.with_name("새 작업")
            if mode == "collision":
                topic.write_text("충돌", encoding="utf-8")
            elif mode == "registered":
                f.manifest.write_text(f.manifest.read_text() + "\n## [새 작업](새%20작업/)\n", encoding="utf-8")
            elif mode == "report":
                f.report("discussion", scope=topic)
            before = tree_state(f.root)
            argv = ["--project-root", f.root, "--topic-dir", topic]
            expect(harness.invoke("check_task_start", argv), 0 if mode == "new" else 1,
                   None if mode == "new" else "C1")
            require(tree_state(f.root) == before, "first-save checker created or changed input")
        for mode in ("new", "collision", "registered", "report"):
            case("D01." + mode, lambda f, selected=mode: start(f, selected))
        def no_manifest(f):
            f.manifest.unlink()
            topic = f.topic.with_name("미생성")
            expect(harness.invoke("check_task_start", ["--project-root", f.root, "--topic-dir", topic]))
        case("D01.no_manifest", no_manifest)
        def parent_collision(f):
            project = f.root / "new-project"
            project.mkdir()
            (project / "specs").write_text("경로 충돌", encoding="utf-8")
            expect(harness.invoke("check_task_start", ["--project-root", project,
                   "--topic-dir", project / "specs" / "group" / "topic"]), 1, "C1")
        case("D01.parent_collision", parent_collision)
        def reference_only_start(f):
            f.manifest.write_text(f.manifest.read_text() + "\n## [다른 작업](other/)\n\n"
                                 "- reference_reports:\n  - [참고](새%20작업/)\n", encoding="utf-8")
            start(f, "new")
        case("D01.reference_only", reference_only_start)
        def reference_only_selected(f):
            f.manifest.write_text(f.manifest.read_text() + "\n## [다른 작업](other/)\n\n"
                                 "- reference_reports:\n  - [참고](로그인%20작업/)\n", encoding="utf-8")
            submit(f)
        case("D02.reference_only", reference_only_selected)
        def title_image(f):
            f.replace(f.manifest, "## [로그인 작업]", "## ![로그인 작업]")
            submit(f, code=2, category="C2", rules=("C2.registration",))
        case("D02.title_image", title_image)

        for label, before, after, code in (
            ("duplicate_task", "## [로그인 작업](로그인%20작업/)", "## [로그인 작업](로그인%20작업/)\n\n## [중복](로그인%20작업/)", 2),
            ("missing_stages", "- stages:", "- other:", 2),
            ("duplicate_stages", "- stages:", "- stages: [discussion]\n- stages:", 2),
            ("missing_references", "- reference_reports:", "- other:", 1),
            ("duplicate_references", "- reference_reports: 없음", "- reference_reports: 없음\n- reference_reports: 없음", 1),
            ("duplicate_stage", "discussion, design", "discussion, discussion, design", 2),
            ("unsupported", "discussion, design", "unsupported, discussion, design", 2)):
            mutant("D02." + label, lambda f, old=before, new=after: f.replace(f.manifest, old, new), code, "C2" if label != "unsupported" else None)
        for stages in (("discussion", "design"), ("discussion", "verification", "design")):
            case("D03.order." + "-".join(stages), lambda f: submit(f), stages=stages)
        mutant("D03.wrong_predecessor", lambda f: f.replace(f.reports["design"],
               'base_on: "discussion-report.md"', 'base_on: "design-report.md"'), category="C5")

        for legacy in (False, True):
            tag = "legacy" if legacy else "current"
            case("D04.normal." + tag, lambda f: submit(f), legacy=legacy)
            def revision(f):
                old = f.reports["design"]
                f.replace(old, "status: in_progress", "status: superseded")
                path = f.report("design", revision=1000, base=f.reports["discussion"])
                submit(f, path)
                f.replace(old, "status: superseded", "status: in_progress")
                submit(f, path, 1, "C3")
            case("D04.revisions." + tag, revision, legacy=legacy)
            for suffix in ("000", "1", "0001", "01000"):
                def filename(f, bad=suffix):
                    stem = "design-report-" if f.legacy else "design-report-rev-"
                    (f.topic / (stem + bad + ".md")).write_text(f.reports["design"].read_text(), encoding="utf-8")
                    submit(f, code=1, category="C3")
                case("D04.filename." + tag + "." + suffix, filename, legacy=legacy)
        def mixed(f):
            (f.topic / "design-report-001.md").write_text(f.reports["design"].read_text(), encoding="utf-8")
            submit(f, code=2, category="C3")
        case("D04.mixed", mixed)

        mutant("D05.extra_fields", lambda f: f.replace(f.reports["design"], "status: in_progress", "status: in_progress\ncustom: permitted"), 0)
        for field in ("revision", "previous", "once", "diff", "completion_type"):
            mutant("D05.forbidden." + field, lambda f, name=field: f.replace(f.reports["design"],
                   "status: in_progress", "status: in_progress\n" + name + ": value"), category="C4")
        for name, before, after in (("status_type", "status: in_progress", "status: true"),
                                    ("status_unknown", "status: in_progress", "status: unsupported"),
                                    ("base_type", 'base_on: "discussion-report.md"', "base_on: 1"),
                                    ("missing_base", 'base_on: "discussion-report.md"', "other: value"),
                                    ("duplicate_key", "status: in_progress", "status: in_progress\nstatus: in_progress"),
                                    ("invalid_yaml", "status: in_progress", "status: [")):
            mutant("D05." + name, lambda f, old=before, new=after: f.replace(f.reports["design"], old, new), 2, "C4")
        def invalid_source_status(f):
            f.replace(f.reports["discussion"], "status: completed", "status: unsupported")
            data = submit(f, code=2, category="C4")
            require(any(item["id"] == "C5.source_state_dependency" and item["status"] == "error"
                        for item in data["items"]), "invalid source status did not block predecessor judgment")
        case("D05.source_status", invalid_source_status)
        def invalid_other_status(f):
            records = f.bundles()
            other = records["02-store"]["implementation"]
            f.replace(other, "status: in_progress", "status: unsupported")
            data = submit(f, records["01-api"]["implementation"], 2, "C4")
            require(any(item["id"] == "C5.state_dependency" and item["status"] == "error"
                        and item["path"] == str(other) for item in data["items"]),
                    "invalid non-submitted status did not block predecessor judgment")
        case("D05.other_status", invalid_other_status)
        mutant("D06.design_review", lambda f: f.replace(f.reports["design"], "status: in_progress", "status: in_review"), 0)
        def other_review(f):
            path = f.report("implementation", base=f.reports["design"], status="in_review")
            f.replace(f.reports["design"], "status: in_progress", "status: completed")
            f.section(f.reports["design"], "완료 체크리스트", f.checked())
            submit(f, path, 1, "C4")
        case("D06.other_review", other_review)
        mutant("D06.legacy_review", lambda f: f.replace(f.reports["design"], "status: in_progress", "status: in_review"), 0, legacy=True)
        mutant("D06.invalid_legacy_bundle", lambda f: f.replace(f.reports["design"], "status: in_progress",
               'status: in_progress\nbundle: "Invalid!"'), 2, "C4", legacy=True)

        case("D07.entry", lambda f: entry(f))
        case("D07.new_report", lambda f: (f.reports["design"].unlink(), entry(f)))
        case("D07.discussion_none", lambda f: entry(f, stage="discussion", base="none"))
        for status in ("hold", "superseded", "in_progress"):
            def bad_source(f, state=status):
                f.replace(f.reports["discussion"], "status: completed", "status: " + state)
                entry(f, code=1, category="C5")
            case("D07.source." + status, bad_source)
        case("D07.wrong_stage", lambda f: entry(f, base=f.reports["design"], code=1, category="C5"))
        case("D07.missing_explicit_base", lambda f: entry(f, base=f.topic / "missing-report.md", code=2))
        def resume(f):
            old = f.reports["discussion"]
            f.replace(old, "status: completed", "status: superseded")
            source = f.report("discussion", revision=2, status="completed")
            f.replace(f.reports["design"], "status: in_progress", "status: hold")
            entry(f, base=source)
        case("D08.hold_resume", resume)
        def mismatch(f):
            source = f.report("discussion", revision=2, status="completed")
            f.replace(f.reports["discussion"], "status: completed", "status: superseded")
            # Historical source is not a completed input; only the mismatch can be relied on as C5.
            data = entry(f, base=source, code=1, category="C5")
            require(any(item["id"] == "C5.entry_matches" and item["status"] == "fail" for item in data["items"]),
                    "explicit predecessor mismatch was not judged")
        case("D08.mismatch", mismatch)

        for legacy in (False, True):
            for own in (False, True):
                def normal_bundle(f, detailed=own):
                    records = f.bundles(own_design=detailed)
                    submit(f, records["01-api"]["implementation"])
                case(f"D09-D10.bundle.{legacy}.{own}", normal_bundle, legacy=legacy)
        def bypass(f):
            records = f.bundles(own_design=True)
            path = records["01-api"]["implementation"]
            f.replace(path, 'base_on: "design-report.md"', 'base_on: "../design-report.md"')
            submit(f, path, 1, "C5")
        case("D09.own_design_bypass", bypass)
        def foreign_bundle(f):
            records = f.bundles(completed=True)
            path = records["01-api"]["verification"]
            f.replace(path, 'base_on: "implementation-report.md"', 'base_on: "../02-store/implementation-report.md"')
            submit(f, path, 1, "C5")
        case("D09.foreign_bundle", foreign_bundle)
        def legacy_source(f):
            records = f.bundles(own_design=True)
            path = records["01-api"]["design"]
            f.replace(path, 'base_on: "discussion-report-001.md"', 'base_on: "design-report-001.md"')
            submit(f, path, 1, "C5")
        case("D10.legacy_design_source", legacy_source, legacy=True)
        def legacy_foreign_bundle(f):
            records = f.bundles(completed=True)
            path = records["01-api"]["verification"]
            other = records["02-store"]["implementation"]
            f.replace(path, records["01-api"]["implementation"].name, other.name)
            submit(f, path, 1, "C5", rules=("C5.relationship",))
        case("D10.legacy_foreign_bundle", legacy_foreign_bundle, legacy=True)

        for own in (False, True):
            def preserved_hold(f, detailed=own):
                records = f.bundles(own_design=detailed, completed=True)
                f.replace(f.reports["design"], "status: completed", "status: hold")
                submit(f, records["01-api"]["implementation"])
                entry(f, stage="design" if detailed else "implementation", scope=f.topic / "01-api",
                      base=f.reports["design"], code=1, category="C5")
            case("D11.hold_common." + str(own), preserved_hold)
        def preserved_superseded(f):
            records = f.bundles(completed=True)
            common = f.reports["design"]
            content = common.read_text()
            replacement = common.with_name("design-report-rev-002.md")
            replacement.write_text(content, encoding="utf-8")
            f.replace(common, "status: completed", "status: superseded")
            submit(f, records["01-api"]["implementation"])
        case("D11.superseded_common", preserved_superseded)
        def same_bundle_hold(f):
            records = f.bundles(own_design=True, completed=True)
            f.replace(records["01-api"]["design"], "status: completed", "status: hold")
            submit(f, records["01-api"]["implementation"], 1, "C5")
        case("D11.same_bundle_hold", same_bundle_hold)
        mutant("D11.single_hold", lambda f: f.replace(f.reports["discussion"], "status: completed", "status: hold"), category="C5")
        for suffix in ("#anchor", "?query", "https://example.invalid/source", "../../outside.md"):
            value = "discussion-report.md" + suffix if suffix.startswith(("#", "?")) else suffix
            mutant("D12.path." + suffix, lambda f, target=value: f.replace(f.reports["design"],
                   'base_on: "discussion-report.md"', "base_on: " + json.dumps(target)), category="C5")
        def source_link(f):
            outside = f.root / "outside.md"
            outside.write_text(f.reports["discussion"].read_text(), encoding="utf-8")
            link = f.topic / "discussion-report-rev-002.md"
            link.symlink_to(outside)
            f.replace(f.reports["discussion"], "status: completed", "status: superseded")
            f.replace(f.reports["design"], 'base_on: "discussion-report.md"', 'base_on: "discussion-report-rev-002.md"')
            submit(f, code=1, category="C5")
        case("D12.symlink_escape", source_link)

        for name in ("단계 결과", "인계 사항", "완료 체크리스트", "사용자 승인"):
            mutant("D13.missing." + name, lambda f, heading=name: f.replace(f.reports["design"], "## " + heading, "## replacement"), category="C6")
            mutant("D13.duplicate." + name, lambda f, heading=name: f.replace(f.reports["design"], "## " + heading, "## " + heading + "\n\n## " + heading), category="C6")
        for name in ("사용자 판단", "보완 요청과 처리 결과", "남은 사항과 인계 조건"):
            mutant("D13.approval." + name, lambda f, heading=name: f.replace(f.reports["design"], "### " + heading, "#### " + heading), category="C6")
        for wrapper in ("```text\n## 인계 사항\n```", "<!--\n## 인계 사항\n-->", "> ## 인계 사항"):
            mutant("D13.example." + wrapper[:8], lambda f, text=wrapper: f.replace(f.reports["design"], "## 인계 사항", text), category="C6")
        mutant("D13.extra", lambda f: f.section(f.reports["design"], "단계 결과", "### 추가 상세\n내용"), 0)

        for legacy in (False, True):
            for state in ("in_progress", "awaiting_approval", "completed"):
                case(f"D14.allowed.{legacy}.{state}", lambda f: submit(f), legacy=legacy, target_status=state)
            for content in ("", "- [ ] 미확인", "- [x] 확인\n  - 확인 근거: ", "- [x] 확인\n  - 확인 근거: <!-- 주석 -->"):
                mutant("D14.empty." + str(legacy) + "." + str(len(content)),
                       lambda f, body=content: f.section(f.reports["design"], "완료 체크리스트", body),
                       category="C7", legacy=legacy, target_status="completed")
        def prior_only(f):
            body = "- [x] 확인\n  - 이전 확인 기록:\n    - 확인 근거: 과거 근거\n\n### 일괄 반영 기록" + f.checked().split("### 일괄 반영 기록", 1)[1]
            f.section(f.reports["design"], "완료 체크리스트", body)
            submit(f, code=1, category="C7")
        case("D14.previous_only", prior_only)
        for label, evidence in (("link", "LINK"), ("inline", "`자료형 정의`"),
                                ("continuation", "현재 확인\n    추가 설명"), ("empty_code", "``")):
            mutant("D15.evidence." + label, lambda f, value=evidence: f.section(f.reports["design"],
                   "완료 체크리스트", f.checked("[근거](" + f.reports["discussion"].name + ")" if value == "LINK" else value)), 1 if label == "empty_code" else 0,
                   "C7" if label == "empty_code" else None)
        def fenced_evidence(f):
            body = "- [x] 확인\n  - 확인 근거:\n\n    ```text\n    nonempty evidence\n    ```\n\n" + f.checked().split("### 일괄 반영 기록", 1)[1]
            # Keep the real batch heading; code text only fills the already-present evidence field.
            body = f.replace_text(body, "\n\n| 묶음", "\n\n### 일괄 반영 기록\n\n| 묶음", 1)
            f.section(f.reports["design"], "완료 체크리스트", body)
            submit(f)
        case("D15.fenced_evidence", fenced_evidence)
        def example_label(f):
            body = f.replace_text(f.checked(), "  - 확인 근거: 고정 시험 근거",
                                  "\n  ```text\n  확인 근거: 예시\n  ```")
            f.section(f.reports["design"], "완료 체크리스트", body)
            submit(f, code=1, category="C7", rules=("C7.evidence",))
        case("D15.example_label", example_label)

        for label, timestamp in (("bad_date", "2023-02-29 12:34:56 (KST)"), ("hour", "2024-02-29 24:00:00 (KST)"),
                                 ("minute", "2024-02-29 12:60:00 (KST)"), ("second", "2024-02-29 12:00:60 (KST)")):
            mutant("D16." + label, lambda f, value=timestamp: f.section(f.reports["design"], "완료 체크리스트", f.checked(timestamp=value)), category="C8")
        for label, old, new, code in (("duplicate_id", "| B1 |", "| B1 |", 1),
                                     ("zero_id", "| B1 |", "| B0 |", 1),
                                     ("empty_target", "| 대상 확인 |", "| |", 1),
                                     ("missing_column", "| 대상 항목 |", "| 다른 열 |", 2)):
            def batch(f, selected=label, before=old, after=new, expected=code):
                body = f.checked()
                if selected == "duplicate_id":
                    body += "| B1 | 두 번째 | 2024-02-29 12:34:56 (KST) |\n"
                else:
                    body = f.replace_text(body, before, after)
                f.section(f.reports["design"], "완료 체크리스트", body)
                submit(f, code=expected, category="C8")
            case("D16." + label, batch)
        def legacy_timestamp(f):
            f.section(f.reports["design"], "완료 체크리스트", "- [x] 확인\n  - 확인 근거: 자료\n  - 확인 완료 시각: 2024-02-29 12:34:56 (KST).\n")
            submit(f)
        case("D16.legacy_item_time", legacy_timestamp, legacy=True)
        def legacy_batch(f):
            f.section(f.reports["design"], "완료 체크리스트", "- [x] 확인\n  - 확인 근거: 자료\n\n### 일괄 반영 기록\n\n- B1: 확인\n  - 반영 시각: 2024-02-29 12:34:56 (KST).\n")
            submit(f)
        case("D16.legacy_list", legacy_batch)
        def reordered_batch(f):
            body = "- [x] 확인\n  - 확인 근거: 자료\n\n### 일괄 반영 기록\n\n" \
                   "| 반영 시각 | 묶음 | 대상 항목 |\n| --- | --- | --- |\n" \
                   "| 2024-02-29 12:34:56 (KST) | B1 | 확인 |\n"
            f.section(f.reports["design"], "완료 체크리스트", body)
            submit(f)
        case("D16.reordered_columns", reordered_batch)
        for record in ("B1", "B9"):
            def previous(f, identifier=record):
                body = f.checked() + "\n### 이전 확인 기록\n\n- 반영 기록: " + identifier + "\n"
                f.section(f.reports["design"], "완료 체크리스트", body)
                submit(f, code=0 if identifier == "B1" else 1, category=None if identifier == "B1" else "C8")
            case("D17.reference." + record, previous)
        mutant("D17.batch_absent", lambda f: f.section(f.reports["design"], "완료 체크리스트", "- [x] 확인\n  - 확인 근거: 자료"), category="C8")

        for stage in ("verification", "qa"):
            for state in ("in_progress", "awaiting_approval", "completed"):
                for value in ("미정", "all_passed\n근거", "all_passed", "unknown\n근거", "handoff\n근거"):
                    def outcome(f, target=stage, status=state, content=value):
                        path = f.reports[target]
                        f.section(path, "완료 구분", content, 3)
                        valid = content == "all_passed\n근거" or (content == "미정" and status == "in_progress") \
                                or (content == "handoff\n근거" and target == "verification" and not f.legacy)
                        submit(f, path, 0 if valid else 1, None if valid else "C9")
                    case(f"D18.{stage}.{state}.{value.splitlines()[0]}.{len(value)}", outcome, through=stage, target_status=state)

        def empty_table_heading(f):
            f.section(f.reports["design"], "단계 결과", "### 작업 묶음표\n<!-- 선택 사항 -->")
            submit(f)
        case("D19.optional_heading", empty_table_heading)
        case("D19.unstarted", lambda f: submit(f, f.bundles(unstarted=True)["01-api"]["implementation"]))
        def reordered_bundle(f):
            records = f.bundles()
            path = f.reports["design"]
            lines = path.read_text().splitlines()
            reordered = []
            for line in lines:
                if line.startswith("|"):
                    cells = line.strip("|").split("|")
                    line = "|" + "|".join(reversed(cells)) + "|"
                reordered.append(line)
            f.transform(path, lambda text: "\n".join(reordered) + "\n")
            submit(f, records["01-api"]["implementation"])
        case("D19.reordered_columns", reordered_bundle)
        for label, before, after in (("missing_column", "범위/완료 기준", "다른 열"),
                                     ("empty_cell", "| 범위 |", "| |"),
                                     ("duplicate_name", "| 02-store | 범위 |", "| 01-api | 범위 |")):
            def table(f, old=before, new=after):
                records = f.bundles()
                f.replace(f.reports["design"], old, new)
                submit(f, records["01-api"]["implementation"], 1, "C10",
                       rules=("C10.bundle_unique",) if old.startswith("| 02-store") else ())
            case("D19." + label, table)
        def unregistered(f):
            records = f.bundles()
            f.transform(f.reports["design"], lambda content: "\n".join(
                line for line in content.splitlines() if not line.startswith("| 02-store |")) + "\n")
            submit(f, records["01-api"]["implementation"], 1, "C10")
        case("D19.unregistered", unregistered)
        for label, before, after in (("foreign_result", "01-api/implementation-report.md", "02-store/implementation-report.md"),
                                     ("wrong_stage", "01-api/implementation-report.md", "design-report.md")):
            def result_link(f, old=before, new=after):
                records = f.bundles()
                f.replace(f.reports["design"], old, new)
                submit(f, records["01-api"]["implementation"], 1, "C10")
            case("D20." + label, result_link)
        for name in ("01-extra", "001-extra", "00-extra", "03-Upper"):
            def directory(f, extra=name):
                records = f.bundles()
                (f.topic / extra).mkdir()
                # Registration is valid so it cannot mask name/ordinal failures.
                common = f.reports["design"]
                body = common.read_text(encoding="utf-8").split("## 단계 결과\n", 1)[1].split("## 인계 사항\n", 1)[0]
                f.section(common, "단계 결과", body.rstrip() + f"\n| extra | 범위 | 구현부터 | 공통 설계 | {extra} | 미시작 |\n")
                data = submit(f, records["01-api"]["implementation"], 1, "C10")
                if extra == "01-extra":
                    require(any(item["id"] == "C10.number_unique" and item["status"] == "fail" for item in data["items"]),
                            "duplicate bundle ordinal was not judged")
                else:
                    failures = [item for item in data["items"] if item["status"] in ("fail", "error")]
                    require(failures and all(item["id"] == "C10.directory_name" for item in failures),
                            "directory-name case was masked by another rule")
            case("D20.directory." + name, directory)
        def root_mix(f):
            records = f.bundles()
            f.report("implementation", base=f.reports["design"])
            submit(f, records["01-api"]["implementation"], 1, "C10")
        case("D20.root_mix", root_mix)
        def expanded_number(f):
            records = f.bundles()
            scope = f.topic / "02-store"
            scope.rename(f.topic / "100-store")
            f.replace(f.reports["design"], "02-store", "100-store")
            submit(f, records["01-api"]["implementation"])
        case("D20.expanded_number", expanded_number)
        def missing_table(f):
            records = f.bundles()
            f.section(f.reports["design"], "단계 결과", "")
            submit(f, records["01-api"]["implementation"], 1, "C10")
        case("D21.missing_table", missing_table)
        def old_nonformal(f):
            records = f.bundles()
            f.section(f.reports["design"], "단계 결과", "### 작업 묶음표\n\n기존 비정형 자료")
            submit(f, records["01-api"]["implementation"], 2)
        case("D21.old_nonformal", old_nonformal, legacy=True)
        def superseded_scope(f):
            records = f.bundles()
            old = records["02-store"]["implementation"]
            f.replace(old, "status: in_progress", "status: superseded")
            common = f.reports["design"]
            f.transform(common, lambda content: "\n".join(
                line for line in content.splitlines() if not line.startswith("| 02-store |")) + "\n")
            submit(f, records["01-api"]["implementation"])
        case("D21.superseded_scope", superseded_scope)

        def good_links(f):
            linked = f.topic / "자료 문서.md"
            linked.write_text("# 자료 제목\n\n# 자료 제목\n\n## 자료 제목-1\n\n<a id='custom'></a>\n", encoding="utf-8")
            f.section(f.reports["design"], "단계 결과", "[자료](자료%20문서.md#자료-제목)\n![그림](자료%20문서.md)\n[참조][x]\n\n[x]: 자료%20문서.md#자료-제목-1\n\n[명시](자료%20문서.md#custom)")
            submit(f)
        case("D22.links", good_links)
        for link in ("missing.md", "discussion-report.md#missing", "bad%ZZ.md", "bad%FF.md", "bad%00.md"):
            mutant("D22.broken." + link, lambda f, value=link: f.section(f.reports["design"], "단계 결과", "[근거](" + value.replace("discussion-report.md", f.reports["discussion"].name) + ")"), category="C11")
        def nonmarkdown(f):
            (f.topic / "source.txt").write_text("자료", encoding="utf-8")
            f.section(f.reports["design"], "단계 결과", "[근거](source.txt#section)")
            submit(f, code=2)
        case("D22.nonmarkdown_fragment", nonmarkdown)
        def excluded(f):
            body = "```md\n[예시](missing.md)\n```\n<!-- [예시](missing.md) -->\n> [예시](missing.md)\n\n[외부](https://example.invalid/)"
            f.section(f.reports["design"], "단계 결과", body)
            submit(f)
        case("D23.examples", excluded)
        def external_local(f):
            source = f.root / "outside.md"
            source.write_text("# 자료\n\n[재귀 검사 제외](missing.md)\n", encoding="utf-8")
            f.section(f.reports["design"], "단계 결과", "[근거](" + str(source) + "#자료)")
            submit(f)
        case("D23.explicit_external_local", external_local)
        def details(f, linked=True):
            path = f.reports["design"]
            folder = path.with_suffix("")
            folder.mkdir()
            (folder / "group.md").write_text("# 정의\n\n```text ascii-flow\nstart -> end\n```\n", encoding="utf-8")
            if linked:
                f.section(path, "단계 결과", "[정의](" + folder.name + "/group.md)")
            submit(f, code=0 if linked else 1, category=None if linked else "C11")
        case("D24.details", details)
        case("D24.unlinked", lambda f: details(f, False))
        def ordinary_code(f):
            (f.topic / "code.py").write_text("pass\n", encoding="utf-8")
            f.section(f.reports["design"], "단계 결과", "[코드](code.py)")
            submit(f)
        case("D24.ordinary_code", ordinary_code)
        for terminated in (False, True):
            def unclosed_at_eof(f, newline=terminated):
                folder = f.reports["design"].with_suffix("")
                folder.mkdir()
                (folder / "group.md").write_text("# 정의\n\n```text ascii-flow\na -> b" + ("\n" if newline else ""), encoding="utf-8")
                f.section(f.reports["design"], "단계 결과", "[정의](design-report/group.md)")
                submit(f, code=1, category="C12", rules=("C12.fence",))
            case("D25.unclosed_eof." + str(terminated), unclosed_at_eof)
        for label, body, code in (("ascii", "```text ascii-flow\n시작 -> 종료\n```", 0),
                                  ("unicode_separator", "```text ascii-flow\nA\u2028B\n```", 0),
                                  ("unmarked", "```text\n└─ →\n```", 0),
                                  ("empty", "```text ascii-flow\n```", 0),
                                  ("list", "- 흐름\n\n  ```text ascii-flow\n  a -> b\n  ```", 0),
                                  ("unclosed", "```text ascii-flow\na -> b", 1),
                                  ("tab", "```text ascii-flow\na\t-> b\n```", 1),
                                  ("box", "```text ascii-flow\n└─\n```", 1),
                                  ("arrow", "```text ascii-flow\na → b\n```", 1),
                                  ("dash", "```text ascii-flow\na — b\n```", 1),
                                  ("fullwidth", "```text ascii-flow\na ＋ b\n```", 1),
                                  ("control", "```text ascii-flow\na\x01b\n```", 1)):
            mutant("D25." + label, lambda f, text=body: f.section(f.reports["design"], "단계 결과", text), code, "C12" if code else None)

        def review_case(f, change=None, code=0):
            path = f.review()
            if change:
                replacement = change(f, path)
                if isinstance(replacement, Path):
                    path = replacement
            expect(harness.invoke("check_review_receipt", f.args("check_review_receipt", review=path)), code,
                   "C13" if code == 1 else None)
        case("D26.review", review_case)
        for label, before, after in (("target", "검토 대상: design-report.md", "검토 대상: discussion-report.md"),
                                     ("empty", "검토자: fixture", "검토자:"),
                                     ("duplicate", "검토자: fixture", "검토자: fixture\n- 검토자: duplicate"),
                                     ("section", "## 종합 의견", "## 다른 영역")):
            case("D26." + label, lambda f, old=before, new=after: review_case(f, lambda fixture, path: fixture.replace(path, old, new), 1))
        def rename_review(f, path):
            destination = path.with_name("review.md")
            path.rename(destination)
            return destination
        case("D26.filename", lambda f: review_case(f, rename_review, 1))
        case("D26.missing", lambda f: expect(harness.invoke("check_review_receipt", f.args("check_review_receipt", review=f.topic / "missing.md")), 2))
        def review_elsewhere(f):
            origin = f.reports["design"]
            path = f.review(origin)
            scope = f.topic / "01-other"
            scope.mkdir()
            destination = scope / path.name
            path.rename(destination)
            expect(harness.invoke("check_review_receipt", f.args("check_review_receipt", review=destination)), 2)
        case("D26.wrong_input_location", review_elsewhere)

        case("D27.allowed", lambda f: (f.deferred(), submit(f)))
        for label in ("missing", "empty", "nonmarkdown", "nested"):
            def deferred_bad(f, selected=label):
                path = f.deferred()
                if selected == "missing":
                    f.replace(path, "## 필요한 작업", "## 다른 영역")
                elif selected == "empty":
                    f.section(path, "필요한 작업", "<!-- 빈 내용 -->")
                elif selected == "nonmarkdown":
                    path.rename(path.with_suffix(".txt"))
                else:
                    (path.parent / "nested").mkdir()
                submit(f, code=1, category="C14")
            case("D27." + label, deferred_bad)

        for state in ("in_progress", "awaiting_approval", "completed"):
            case("D28.final." + state, lambda f: (prepare_final(f), final(f)), through="qa", target_status=state)
        def earlier_unfinished(f):
            prepare_final(f)
            f.replace(f.reports["verification"], "status: completed", "status: in_progress")
            final(f, code=1, category="C7")
        case("D28.prior_unfinished", earlier_unfinished, through="qa")
        def missing_required(f):
            prepare_final(f)
            f.reports["implementation"].unlink()
            final(f, code=1, category="C3")
        case("D28.missing_required", missing_required, through="qa")
        def handoff(f):
            prepare_final(f)
            f.section(f.reports["qa"], "완료 구분", "handoff\n인계 근거", 3)
            final(f, code=1, category="C9")
        case("D28.final_handoff", handoff, through="qa")
        def bundle_final(f, unstarted=False):
            records = f.bundles(completed=True, unstarted=unstarted)
            first, last = records["01-api"]["qa"], records["02-store"]["qa"]
            f.section(first, "완료 구분", "handoff\n후속 인계", 3)
            final(f, last, 1 if unstarted else 0, "C10" if unstarted else None)
        case("D28.unstarted_final", lambda f: bundle_final(f, True))
        case("D29.previous_handoff", bundle_final)
        def legacy_final(f):
            f.section(f.reports["qa"], "완료 구분", "next_cycle_handoff\n기존 인계", 3)
            final(f)
        case("D29.legacy_final", legacy_final, legacy=True, through="qa")
        for state in ("hold", "superseded"):
            def invalid_final(f, status=state):
                prepare_final(f)
                f.replace(f.reports["qa"], "status: in_progress", "status: " + status)
                final(f, code=1, category="C9")
            case("D29.final_state." + state, invalid_final, through="qa")
        def explicit_last(f):
            records = f.bundles(completed=True)
            # The selected last QA need not have the largest bundle number.
            selected = records["01-api"]["qa"]
            f.replace(selected, "status: completed", "status: in_progress")
            final(f, selected)
        case("D29.explicit_last", explicit_last)
        def current_reviews(f, bad=False):
            prepare_final(f)
            path = f.review(f.reports["verification"])
            if bad:
                f.replace(path, "## 종합 의견", "## 다른 영역")
            final(f, code=1 if bad else 0, category="C13" if bad else None)
        case("D30.current_review", current_reviews, through="qa")
        case("D30.bad_review", lambda f: current_reviews(f, True), through="qa")
        for mode in ("empty", "content", "file", "broken_link"):
            def leftover(f, kind=mode):
                prepare_final(f)
                path = f.topic / "deferred"
                if kind == "content":
                    f.deferred()
                elif kind == "file":
                    path.write_text("잔존", encoding="utf-8")
                elif kind == "broken_link":
                    path.symlink_to(f.topic / "absent")
                else:
                    path.mkdir()
                final(f, code=1, category="C14")
            case("D30.deferred." + mode, leftover, through="qa")

        def other_topic(f):
            f.manifest.write_text(f.manifest.read_text() + "\n## [other](other/)\n- stages: [unknown]\n", encoding="utf-8")
            other = f.topic.with_name("other")
            other.mkdir()
            (other / "design-report.md").write_bytes(b"\xff")
            submit(f)
            start(f, "new")
        case("D31.other_topic", other_topic)
        def other_bundle_body(f):
            records = f.bundles()
            other = records["02-store"]["implementation"]
            f.replace(other, "## 단계 결과", "## 다른 영역")
            f.section(records["01-api"]["implementation"], "단계 결과", "```text ascii-flow\n→\n```")
            entry(f, stage="implementation", scope=f.topic / "01-api", base=f.reports["design"])
        case("D32.other_bundle_body", other_bundle_body)
        def old_submission(f):
            old = f.reports["design"]
            f.replace(old, "status: in_progress", "status: superseded")
            current = f.report("design", revision=2, base=f.reports["discussion"])
            submit(f, old, 1, "C3")
            f.replace(old, "## 사용자 승인", "## 과거 영역")
            submit(f, current)
        case("D33.old_submission", old_submission)
        def old_review(f):
            original = f.reports["design"]
            f.replace(original, "status: in_progress", "status: superseded")
            f.replace(original, "## 단계 결과", "## 과거 영역")
            f.manifest.unlink()
            review_case(f)
        case("D34.old_review", old_review)
        def overall_scope(f):
            records = f.bundles(completed=True)
            other = records["01-api"]["implementation"]
            f.replace(other, "## 단계 결과", "## 다른 영역")
            final(f, records["02-store"]["qa"], 1, "C6")
        case("D35.all_current", overall_scope)
        def historical_review(f):
            prepare_final(f)
            old = f.reports["design"]
            current = old.with_name("design-report-rev-002.md")
            current.write_text(old.read_text(), encoding="utf-8")
            f.replace(old, "status: completed", "status: superseded")
            f.replace(f.reports["implementation"], 'base_on: "design-report.md"', 'base_on: "design-report-rev-002.md"')
            review = f.review(old)
            f.replace(review, "## 종합 의견", "## 과거 영역")
            final(f)
        case("D35.old_review_ignored", historical_review, through="qa")
        def new_bundle(f):
            f.bundles(unstarted=True)
            scope = f.topic / "03-new"
            before = tree_state(f.root)
            entry(f, stage="implementation", scope=scope, base=f.reports["design"])
            require(tree_state(f.root) == before and not scope.exists(), "entry created an unstarted bundle")
            path = f.report("implementation", scope=scope, base=f.reports["design"])
            submit(f, path, 1, "C10")
        case("D36.new_bundle", new_bundle)


if __name__ == "__main__":
    raise SystemExit(run_check(check))
