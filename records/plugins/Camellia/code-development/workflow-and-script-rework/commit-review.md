# 호환성 검증 전 커밋 검토

## 목적과 현재 상태

code-development의 M1-M5 개편과 지적 보완을 실제 설치할 커밋으로 고정한다.
현재 단계는 cross-validation이며 기능 커밋과 커밋 대상 검증을 마쳤다.
in_review를 false로 바꾸는 이 마감 변경은 실제 커밋 성공 후 관문 통과 근거가 된다.
사용자가 전체 목록 설명 후 "이견없음"과 후속 준비 진행을 요청하여 기능/관문 마감 커밋 범위를 승인했다.
기능 커밋은 수행했으며 푸시/설치/배포는 수행하지 않았다.

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

아래 상태는 기능 커밋 직전 작업 트리 기준이다. M은 수정, D는 삭제, ??는 신규다.

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

승인받은 57개 파일과 실제 스테이징 목록이 일치함을 확인하고 기능 커밋 `dddda1429905a91cb579603848cffe529fb27165`를 만들었다.
신규 파일은 100644이며 의도하지 않은 실행 권한 변경은 없다.
스테이징 버전 검사는 origin/work/camellia/workflow-and-script-rework의 f6a2287을 기준으로
Camellia 4.0.0 -> 5.0.0을 통과했다.

기능 커밋 SHA를 --revision으로 명시하여 5개 등록 검사를 다시 실행했다.
검사 순서별 20/383/14/115/337개, 합계 869개가 모두 종료 0/true였다.
R/D는 각각 9.659초/10.785초로 60초 제한 이내였다.
원시 결과와 명령/대상 SHA/종료/시간은 로컬 자료 validation/committed-revision에 보존한다.
이 확인은 실제 커밋의 스킬을 검사한 근거이며 설치본 시험을 대신하지 않는다.

마감 변경은 specification.md와 이 기록의 상태/근거 및 후속 준비를 정리한다.
소스/검사 코드는 기능 커밋 이후 바꾸지 않아 해당 검증 결과를 재사용한다.
마감 커밋 자신의 해시를 같은 파일에 다시 적지 않으며 실제 성공 여부는 Git 이력에서 확인한다.
마감 커밋 실패 시 in_review를 true로 복구한다.

## 다음 검증의 선행 조건

호환성 검증은 승인한 커밋의 Camellia 5.0.0을 Codex/Claude에 실제 반영한 뒤 수행한다.
설치본의 소스/버전/파일을 대조하고 스킬 호출, 상대 자료 접근과 새 실행기의 정상/위반 결과를 최소 사례로 확인한다.
전역 설치/설정 변경이 필요한 경우에는 Garden 작업 경계를 따르며 Aster에서 전역 구성을 수정하지 않는다.
검토 전 사본이나 기존 4.0.0의 결과를 새 설치본의 통과 근거로 사용하지 않는다.

### 배포와 설치 준비

두 marketplace catalog의 Camellia 소스는 아래와 같다.
작업 브랜치에 커밋했다는 사실만으로 이 배포 ref에 반영되었다고 판단하지 않는다.

| 항목 | 대상과 확인 기준 |
| --- | --- |
| 저장소 | https://github.com/Olbbemi/Aster.git |
| 배포 소스 | git-subdir, ref integrate/camellia, path plugins/Camellia |
| 설치 대상 | 기능 커밋의 Camellia 5.0.0, 배포 파일 34개 |
| 현재 원격 상태 | fetch 후 origin/integrate/camellia는 f6a22877d15ab2af662e900209f7251224c4d0d4, manifest 4.0.0 |
| Aster 선행 작업 | 작업 브랜치 푸시와 integrate/camellia 대상 PR/병합을 승인 범위에서 수행하고 원격 배포 파일을 대조 |
| Garden 선행 작업 | 배포 반영 후 실제 Codex/Claude 설치 업데이트와 활성화 및 설치 파일 일치 확인 |

기존 사용자 설치를 바꾸는 작업은 Garden 세션에서 진행한다.
업데이트 요청을 인계할 때는 실제 게시된 커밋/버전/파일 집합을 특정하고,
각 CLI의 설치 경로와 실제 읽힌 버전, 호출 여부 및 상대 자료 접근 결과를 되돌려 받는다.
Syringa의 설치 상태와 파일이 유지되는지도 확인한다.
아직 배포되지 않았으므로 기존 설치본 업데이트 요청을 실행 가능한 상태로 전달하지 않았다.

설치 반영 뒤에는 양 CLI의 새 세션에서 스킬 발견/명시 호출과
참조 문서/템플릿/내부 실행기 접근을 확인하는 최소 호환성 사례를 확정한다.
내부 실행기의 정상/위반/오류 판정은 설치 경로에서 실행하고 해당 커밋의 기대 결과와 대조한다.
전체 B01-B07을 기계적으로 반복하지 않고 설치 경로와 호출 환경의 변경 영향을 기준으로 선정한다.
사례별 입력/종료 조건, 호출 수, 모델과 생성물 정리 범위를 사용자와 확정하기 전 실제 AI 시험은 시작하지 않는다.
이 절은 설치 및 시나리오 준비 사항이며 실행 승인이나 호환성 통과 기록이 아니다.
