# 커밋 관문 검토와 반영 결과

## 목적과 현재 상태

첫 관문은 code-development M1-M5를 실제 설치할 Camellia 5.0.0 커밋으로 고정했다.
57개 파일의 기능 커밋과 상태/근거 마감 커밋을 승인받아 각각 반영했다.
이후 사용자 승인으로 푸시와 PR #58을 만들었고 사용자가 병합 및 Garden 업데이트를 완료했다.
설치본 K01-K04도 통과했다.

아래 첫 관문의 파일 목록과 검증은 당시 대상/승인 근거다.
설치본 결과를 포함한 최종 기록 정리는 마지막 [최종 관문](#최종-기록-커밋-검토)에서 구분한다.

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

첫 관문 마감은 specification.md와 이 기록의 상태/근거를 반영한
`dabd374ece13ee010516a3e4812555410ad49c38`이다.
기능 소스/검사 코드는 바뀌지 않았으며 실제 마감 커밋과 당시 in_review: false를 확인했다.
이후 최종 기록 관문에 진입하면서 in_review를 true로 다시 열었다.

## 다음 검증의 선행 조건

첫 관문의 실제 커밋, 배포 ref 반영과 설치 일치를 확인한 뒤 K01-K04를 수행했다.
검토 전 사본이나 4.0.0 결과를 새 설치본의 근거로 사용하지 않았다.
전역 설치/설정 변경은 Garden에서 수행했고 Aster는 결과를 읽어 대조했다.

### 배포와 설치 준비

| 항목 | 실제 결과 |
| --- | --- |
| 배포 소스 | https://github.com/Olbbemi/Aster.git, git-subdir, ref integrate/camellia, path plugins/Camellia |
| 기능/마감 커밋 | dddda1429905a91cb579603848cffe529fb27165 / dabd374ece13ee010516a3e4812555410ad49c38 |
| 원격 반영 | 승인받은 푸시의 버전 검사 및 등록 검사 5개 통과 후 PR #58 생성 |
| 병합 | 사용자가 병합. integrate/camellia의 868fcb15c7622de24f66b88b1601e7658dd204df |
| 배포 파일 | Camellia 5.0.0, 34개. plugin tree 7a047fee6f12ad4f67d63b455a66c988dc3eed31 |
| 실제 설치 | Garden에서 양 CLI 업데이트/활성화. Aster에서 병합 커밋과 34개 파일 내용/모드 재대조 |
| 호환성 | K01/K02 발견/자료 접근, K03/K04 실제 설치본 실행/판정 통과 |

구체적 세션/명령/관찰과 최초 실패 및 재시험은 [호환성 기록](compatibility-validation.md)에 보존했다.
Syringa 등 비대상 플러그인 보존도 Garden의 업데이트 결과에서 확인했다.

## 최종 기록 커밋 검토

### 목적과 처리 순서

설치본 검증 결과를 보존하고 명세서 및 관련 기록을 최종 보고서로 정리한다.
제품 소스/검사/등록/배포 구성 변경은 없다.
서로 참조하는 명세/설계/검증/관문 기록을 하나의 기록 그룹으로 묶는다.
그룹 커밋 이후 실제 해시와 완료 판단을 기록하고 in_review: false로 닫는 마감 커밋을 별도로 만든다.
마감 자신의 해시를 같은 파일에 기록하는 순환은 만들지 않는다.

PR #58이 병합된 작업 브랜치는 새 커밋에 재사용하지 않는다.
최신 origin/integrate/camellia의 868fcb15c7622de24f66b88b1601e7658dd204df에서
`work/camellia/finalize-workflow-records`를 생성했다.
승인 범위의 최초 푸시와 upstream 연결을 마쳤으며 생성 시 로컬/원격이 같은 커밋이었다.
실제 pre-push는 변경 플러그인과 선택된 스킬이 없음을 확인하여 통과했다.
이 최초 등록에는 아래 최종 기록 커밋을 포함하지 않는다.

### 포함 파일과 기존 보존 자료

아래 경로는 이 기록 루트 기준이며 12개 전체가 최종 보존 묶음이다.
수정/신규 6개를 기록 그룹에 포함하고, 나머지 6개는 기존 기능 커밋의 내용/모드가 같아 그대로 재사용한다.

| 처리 | 경로 | 목적 |
| --- | --- | --- |
| 수정 | specification.md | 최종 요건/결과, 승인 체크리스트, 보존 선별과 완료 관문 |
| 수정 | commit-review.md | 첫 관문 실제 결과와 최종 포함/제외/재사용 근거 |
| 수정 | validation.md | 초기/보완/커밋 검증 시점과 현재 판정 분리 |
| 수정 | behavioral-validation.md | 최초 실패/검증 한계 보존 및 후속 결과/한시 보존 연결 |
| 신규 | compatibility-validation.md | 설치본 K01-K04의 입력, 실제 결과와 실패/복구 |
| 수정 | structure-design/developer-checks.md | 완료한 설계/구현의 경과 정리와 검증 정본 연결 |
| 기존 유지 | cross-validation/change-review/round-001/request.md | 독립 검토의 원래 대상/기준/권한 |
| 기존 유지 | cross-validation/change-review/round-001/review.md | Claude 1차 검토 원문 |
| 기존 유지 | cross-validation/change-review/round-001/resolution.md | 지적별 수용/반박/보완 근거 |
| 기존 유지 | cross-validation/change-review/round-002/request.md | 수정 영향 재검토의 대상/기준 |
| 기존 유지 | cross-validation/change-review/round-002/review.md | Claude 2차 검토 원문 |
| 기존 유지 | cross-validation/change-review/round-002/resolution.md | N1-N3의 재현/보완 및 독립 검토 한계 |

마감 커밋의 범위는 specification.md와 commit-review.md의 실제 그룹 해시, 승인/완료 근거와 상태다.
빈 커밋은 만들지 않으며 다른 제품/문서 변경을 추가하지 않는다.

### 제외 범위와 재사용 근거

- Camellia 소스/manifest, 개발용 검사/등록과 지속 사용 안내 및 README는 이번 기록 수정 대상이 아니다.
  기능 커밋 dddda14 이후 내용/모드가 동일하므로 첫 관문 검토와 869개 정형 검증을 재사용한다.
- 위 교차 검토 6개는 dddda14와 내용/모드가 동일하다.
  원문 판정과 이후 작성자 보완을 구분하며 새로운 독립 리뷰로 표현하지 않는다.
- 로컬 원시 로그/시험 사본과 일회성 하네스는 Git에서 제외한다.
  한시 보존 및 정리 조건은 명세서 완료 근거를 따른다.
- 다른 작업 자료, todo, Garden 파일과 전역 설치 캐시 및 기존 두 작업 브랜치 삭제는 제외한다.
- 새 기록 커밋의 푸시/PR 및 main 통합은 이번 커밋 범위와 구분한다.

### 검토와 승인 상태

M1-M5의 요건, 파일 역할과 실제 결과의 대응을 정리했다.
완료된 설치 대기/미작성 항목을 실제 결과로 바꾸고 승인 범위와 예외를 보존했다.
이전 reviewer 원문과 실행 실패/미검증 범위는 변경하지 않았다.
명세서 형식 21개, 보존 문서 12개의 로컬 참조 118개가 통과했다.
외부 URL 3개는 범위 밖 SKIP이며 실패/오류/미판정은 없었다.
두 시나리오 결과 표는 각각 통과 7개/4개, 현재 필수 미통과 0개로 기록 검사를 통과했다.
변경 공백 검사와 Markdown 구조를 확인했고 실제 변경 6개가 위 수정/신규 목록과 일치했다.
참조 검사가 식별한 미추적 compatibility-validation.md도 포함했다.
제품 변경이 없으므로 새 AI 호출이나 전체 정형 회귀는 실행하지 않는다.

사용자가 문서 6개의 기록 그룹과 specification.md/commit-review.md 마감 변경,
새 브랜치 생성 및 최초 원격 등록을 승인했다.
앞선 기능 커밋의 승인과 구분하여 이번 구체적 목록에 대한 승인을 받았다.
그룹 및 마감 커밋을 실제 확인하기 전까지 in_review: true를 유지한다.
