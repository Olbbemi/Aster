# 호환성 검증 전 커밋 검토

## 목적과 현재 상태

code-development의 M1-M5 개편과 지적 보완을 실제 설치할 커밋으로 고정한다.
현재 단계는 cross-validation, in_review는 true이며 승인한 커밋을 준비 중이다.
사용자가 전체 목록 설명 후 "이견없음"과 후속 준비 진행을 요청하여 기능/관문 마감 커밋 범위를 승인했다.
실제 커밋/푸시/설치/배포는 수행하지 않았다.

## 그룹과 검토 결과

소스, 실행 계약, 테스트 및 pre-push 등록이 함께 바뀌므로 하나의 기능 커밋으로 묶는다.
삭제된 CLI와 새 CLI, 계약과 검사 코드를 분리하면 중간 커밋의 호출/검증이 성립하지 않는다.
README와 공용 검사 안내 변경은 이 스킬 등록을 연결하는 범위다.

명세의 M1-M5와 실제 문서/실행 자료 및 검사 역할을 대조했다.
1차/2차 독립 리뷰의 작성자 판단과 보완 결과는 각 resolution을 따른다.
최종 5개 등록 검사는 20/383/14/115/337개, 합계 869개가 통과했다.
추가 도식 EOF, 상태 종속 오류와 fixture 준비 실패 사례 및 음성 변형 결과를 확인했다.
현재 플러그인 파일 집합은 기존 커밋 31개에서 구 CLI 7개를 빼고 새 Python 9개와 계약 문서를 더한 34개다.
실제 로컬 파일 집합이 이 목록과 일치하며 개발용 검사/기록은 배포 경계 밖이다.
원격 반영과 실제 설치본은 이 검토의 통과 근거가 아니다.

기존 공개 검사 CLI를 제거하고 실행 위치별 새 CLI/인자로 바꿨으므로 major 변경이다.
Git 운영 규칙의 플러그인 버전 기준으로 Camellia를 4.0.0 -> 5.0.0으로 반영했다.
기존 report 형식 지원을 유지했다는 사실만으로 삭제된 CLI의 호출 호환성을 주장하지 않는다.

## 포함 파일 전체

아래 상태는 Git 작업 트리 기준이다. M은 수정, D는 삭제, ??는 신규다.

| 상태 | 경로 |
| --- | --- |
| M | `README.md` |
| M | `plugins/Camellia/.claude-plugin/plugin.json` |
| M | `plugins/Camellia/skills/code-development/SKILL.md` |
| M | `plugins/Camellia/skills/code-development/assets/review_reports/review-template.md` |
| M | `plugins/Camellia/skills/code-development/assets/stage_reports/design-template.md` |
| M | `plugins/Camellia/skills/code-development/assets/stage_reports/discussion-template.md` |
| M | `plugins/Camellia/skills/code-development/assets/stage_reports/qa-template.md` |
| M | `plugins/Camellia/skills/code-development/references/ai_agents/review-execution.md` |
| M | `plugins/Camellia/skills/code-development/references/design-artifacts.md` |
| M | `plugins/Camellia/skills/code-development/references/guidelines.md` |
| ?? | `plugins/Camellia/skills/code-development/references/report-check-contract.md` |
| M | `plugins/Camellia/skills/code-development/references/report-checks.md` |
| M | `plugins/Camellia/skills/code-development/references/stages/design.md` |
| M | `plugins/Camellia/skills/code-development/references/stages/discussion.md` |
| M | `plugins/Camellia/skills/code-development/references/stages/implementation.md` |
| M | `plugins/Camellia/skills/code-development/references/stages/qa.md` |
| M | `plugins/Camellia/skills/code-development/references/stages/verification.md` |
| M | `plugins/Camellia/skills/code-development/references/work-bundles.md` |
| M | `plugins/Camellia/skills/code-development/references/workflow.md` |
| ?? | `plugins/Camellia/skills/code-development/scripts/_check_content.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/_check_markdown.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/_check_records.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/_check_runtime.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_completion_records.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_report_diagrams.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_report_links.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_report_structure.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/check_report_submission.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_reports.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/check_review_receipt.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/check_stage_entry.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/check_task_completion.py` |
| ?? | `plugins/Camellia/skills/code-development/scripts/check_task_start.py` |
| D | `plugins/Camellia/skills/code-development/scripts/check_work_bundles.py` |
| D | `plugins/Camellia/skills/code-development/scripts/report_common.py` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/behavioral-validation.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/commit-review.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-001/request.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-001/resolution.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-001/review.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-002/request.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-002/resolution.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/cross-validation/change-review/round-002/review.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/specification.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/structure-design/developer-checks.md` |
| ?? | `records/plugins/Camellia/code-development/workflow-and-script-rework/validation.md` |
| ?? | `tools/references/code-development-tests.md` |
| M | `tools/references/skill-pre-push.md` |
| ?? | `tools/tests/skills/code-development/check_report_rules.py` |
| ?? | `tools/tests/skills/code-development/check_report_templates.py` |
| ?? | `tools/tests/skills/code-development/check_runtime_contract.py` |
| ?? | `tools/tests/skills/code-development/check_skill_references.py` |
| ?? | `tools/tests/skills/code-development/check_skill_structure.py` |
| ?? | `tools/tests/skills/code-development/check_support.py` |
| ?? | `tools/tests/skills/code-development/checks.json` |
| ?? | `tools/tests/skills/code-development/repository_support.py` |
| D | `tools/tests/skills/code-development/test_code_development_reports.py` |

## 제외 대상

아래 이전 작업 명세 3개는 이번 작업의 근거로 승계하지 않는다.
사용자가 필요 없으면 삭제하도록 요청하여 현재 기록/근거에 의존하지 않는 것을 확인한 뒤 삭제했다.
미추적 파일이므로 이번 Git 삭제 변경에는 나타나지 않으며 기능 커밋에 포함하지 않는다.

- `records/plugins/Camellia/code-development/outline-first-development/followup-validation.md`
- `records/plugins/Camellia/code-development/outline-first-development/specification.md`
- `records/plugins/Camellia/code-development/outline-first-development/validation.md`

공용 data/cargo의 원시 로그/시험 사본과 /tmp 재현 자료는 로컬 자료이며 Git에서 제외한다.
기존 작업 브랜치 삭제, 원격 푸시와 배포도 이 커밋 승인 범위에 포함하지 않는다.

## 커밋과 관문 마감

승인받은 파일 전체를 스테이징한 뒤 목록/변경/실행 권한을 다시 대조한다.
첫 커밋에는 위 기능 묶음과 현재 기록을 포함한다.
그룹의 실제 커밋을 확인한 뒤 명세서와 이 기록에 결과를 반영하고 in_review를 false로 바꾸는 마감 커밋을 수행한다.
마감 커밋 자신의 해시를 같은 파일에 다시 적지 않는다.
이 두 커밋의 기록 갱신도 이번 승인 묶음에 포함한다.
실제 커밋이 확인되기 전 관문 완료나 호환성 검증 진입으로 처리하지 않는다.

## 다음 검증의 선행 조건

호환성 검증은 승인한 커밋의 Camellia 5.0.0을 Codex/Claude에 실제 반영한 뒤 수행한다.
설치본의 소스/버전/파일을 대조하고 스킬 호출, 상대 자료 접근과 새 실행기의 정상/위반 결과를 최소 사례로 확인한다.
전역 설치/설정 변경이 필요한 경우에는 Garden 작업 경계를 따르며 Aster에서 전역 구성을 수정하지 않는다.
검토 전 사본이나 기존 4.0.0의 결과를 새 설치본의 통과 근거로 사용하지 않는다.
