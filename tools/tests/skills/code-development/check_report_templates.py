#!/usr/bin/env python3
"""Check stage/template correspondence and unfilled template structures."""

from collections import Counter
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_support import require, run_check
from repository_support import (APPROVAL_AREAS, DEFERRED_AREAS, REPORT_AREAS, REVIEW_AREAS,
                                Document, SKILL, STAGES, local_target)


def top_labels(doc):
    stop = min((h.start for h in doc.headings if h.level == 2), default=len(doc.tokens))
    depth, labels = 0, []
    for index, token in enumerate(doc.tokens[:stop]):
        if token.type == "list_item_open":
            depth += 1
        elif token.type == "list_item_close":
            depth -= 1
        elif token.type == "inline" and depth == 1 and index not in doc.quoted:
            from repository_support import inline_text
            match = re.match(r"^(검토자|모델명/버전|검토 대상):", inline_text(token).strip())
            if match:
                labels.append(match[1])
    return Counter(labels)


def check(repository, results):
    def stages():
        source = SKILL + "/references/workflow.md"
        doc = Document(repository.text(source))
        tables = doc.tables(doc.one("단계 순서와 지침", 2))
        require(len(tables) == 1 and bool(tables[0]), "missing unique default stage table")
        table = tables[0]
        headers = [cell[0] for cell in table[0]]
        require(headers.count("단계 식별자") == 1 and headers.count("단계 지침") == 1, "invalid workflow table columns")
        index, link_index = headers.index("단계 식별자"), headers.index("단계 지침")
        identifiers = [row[index][0] for row in table[1:]]
        require(tuple(identifiers) == STAGES, "default stages differ from the declared flow")
        for row in table[1:]:
            stage = row[index][0]
            stage_path = SKILL + "/references/stages/" + stage + ".md"
            require(len(row[link_index][1]) == 1 and local_target(repository, source, row[link_index][1][0])[0] == stage_path,
                    "stage instruction link does not identify its stage")
            stage_doc = Document(repository.text(stage_path))
            section = stage_doc.one("report 작성과 인계", 2)
            expected = SKILL + "/assets/stage_reports/" + stage + "-template.md"
            actual = [local_target(repository, stage_path, destination) for destination, _line in stage_doc.links(section)]
            require(any(target is not None and target[0] == expected for target in actual), "stage has no corresponding report template")
    results.case("T01.stage_correspondence", stages, SKILL + "/references/workflow.md")

    for stage in STAGES:
        path = SKILL + "/assets/stage_reports/" + stage + "-template.md"
        def structure(p=path):
            doc = Document(repository.text(p))
            require(doc.meta is not None, "template requires valid unique YAML frontmatter")
            require(doc.meta.get("status") == "in_progress" and "base_on" in doc.meta and doc.meta["base_on"] is None,
                    "unfilled template metadata differs from its initial contract")
            forbidden = {"revision", "previous", "once", "diff", "completion_type"}
            require(not forbidden.intersection(doc.meta), "template has a forbidden report field")
            for name in REPORT_AREAS:
                doc.one(name, 2)
            approval = doc.one("사용자 승인", 2)
            for name in APPROVAL_AREAS:
                doc.one(name, 3, approval)
        results.case("T02.report." + stage, structure, path)
        def recording(p=path, selected=stage):
            doc = Document(repository.text(p))
            doc.one("일괄 반영 기록", 3, doc.one("완료 체크리스트", 2))
            if selected in ("verification", "qa"):
                doc.one("완료 구분", 3, doc.one("사용자 승인", 2))
        results.case("T03.recording." + stage, recording, path)

    def review():
        doc = Document(repository.text(SKILL + "/assets/review_reports/review-template.md"))
        labels = top_labels(doc)
        require(all(labels[name] == 1 for name in ("검토자", "모델명/버전", "검토 대상")), "review template lacks unique top list labels")
        for name in REVIEW_AREAS:
            doc.one(name, 2)
    results.case("T04.review", review, SKILL + "/assets/review_reports/review-template.md")
    def deferred():
        doc = Document(repository.text(SKILL + "/assets/deferred-item-template.md"))
        for name in DEFERRED_AREAS:
            doc.one(name, 2)
    results.case("T04.deferred", deferred, SKILL + "/assets/deferred-item-template.md")


if __name__ == "__main__":
    raise SystemExit(run_check(check))
