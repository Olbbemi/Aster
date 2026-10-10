---
status: active
in_review: true
name: skill-lifecycle
target_path: .agents/skills/skill-lifecycle/
operation: update
---

# 명세서 중심의 부가 기록 관리와 스킬 문서 가독성 개선

## 목적과 범위

명세서에서 작업의 목적, 확정 요건, 핵심 설계, 실제 변경과 최종 판정을 이해할 수 있게 한다.
부가 파일은 독립적인 상세 정보나 재개에 필요한 경위가 있을 때만 생성한다.
파일별 역할, 커밋 대상 및 보존과 정리 조건을 단계 지침과 연결한다.

`skill-lifecycle`의 자체 수정에 합의한 축약 절차를 적용한다.
관련 지침 수정, 문맥 및 의미 대조, Markdown 구조/참조/단계 및 템플릿 검사를 수행한다.
스킬 전체의 개행과 들여쓰기를 검토하되 형식 정리로 내용, 범위, 의무, 조건과 예외를 바꾸지 않는다.
기존 완료 기록과 다른 작업의 파일을 재작성하거나 삭제하는 작업은 포함하지 않는다.

## 승인과 작업 기준

- [x] 기존 자료를 비교한 제안에 따라 필요한 부가 파일만 생성하고 기록 루트에서 관리한다.
  사용자는 제안에 이견이 없으며 생성한 보존 문서는 커밋 대상임을 확인했다.
- [x] history의 필수 생성을 완화하고 명세서와 부가 문서의 역할을 구분한다.
  각 단계와 관련 문서를 갱신하고 lifecycle 스킬 전체의 개행 및 들여쓰기를 의미 보존 조건으로 검토한다.
- [x] 기존 지침 수정 작업에서 승인한 GPT-6 Astra/high와 정적 검증 범위를 이어서 적용한다.
  실제 모델 적용 근거는 앞선 사용자 확인이며 별도 에이전트 실행은 포함하지 않는다.
- [x] 제시한 21개 파일과 마감 상태 기록의 커밋을 승인받았다.
  사용자는 독립적으로 나눌 수 있으면 그룹별로 커밋하고 푸시 및 PR 생성까지 진행하도록 요청했다.

기준은 PR #44 병합 후 `origin/integrate/common`의 `258f77f`다.
작업 브랜치는 `work/common/lifecycle-supporting-records`다.
기록 루트는 이 명세서의 디렉토리이며 소스는 위 target_path를 사용한다.
형식 대조와 검사 원시는 공용 경로의
`cargo/work/internal/skill-lifecycle/supporting-records-and-readability/`에 보관한다.

## 요건과 확인 기준

| ID | 요건 | 기대 결과와 확인 방법 |
| --- | --- | --- |
| R1 | 명세서 중심 기록 | 목적, 요건, 핵심 설계, 실제 변경, 요건별 최종 판정과 미확인을 명세서에서 이해한다. 상세 자료 링크만으로 결과를 대신하지 않는다. |
| R2 | 필요에 따른 파일 생성 | validation은 복잡한 검증 근거, 설계 상세는 독립 구현 정의, 교차 검증은 수행한 요청/원문/후속 판단, history는 명세서/Git에 없는 재개 경위에만 사용한다. 빈 파일이나 단계별 문서를 일괄 생성하지 않는다. |
| R3 | 역할과 상태의 분리 | 명세서는 현재 유효한 판단을 관리하고 부가 문서는 상세 근거를 관리한다. history의 과거 상태가 현재 상태로 읽히지 않게 한다. |
| R4 | 커밋과 완료 정리 | 기록 루트에서 필요하여 생성하고 유지하는 모든 문서는 커밋 대상이다. 중복 내용은 통합할 수 있으나 독립적인 근거를 무조건 합치지 않는다. 원본/참조 대조 후 정리한다. |
| R5 | 미해결 근거 보존 | 로컬 자료는 보존 이유와 정리 조건을 기록한다. 후속 검토나 재시험에 필요한 동안 유지하며 미해결을 통과로 바꾸지 않는다. 교차 검토 작성자와 원문 권한을 유지한다. |
| R6 | 단계 연결 | 문제/요건/설계/구현/검증/완료 단계, 공통 운영 규칙과 템플릿의 생성/기록 기준이 서로 일치한다. 기존 단계별 필수 내용과 제목은 유지한다. |
| R7 | 의미를 보존한 가독성 | 모든 lifecycle Markdown을 검토한다. 형식 수정은 단어와 링크, 코드, 표, 목록 계층 및 본문 내용을 보존하는지 전후 대조한다. 정책 변경은 형식 수정과 구분해 검토한다. |

## 근거로 검토한 기존 사례

- `fixed-paths-and-final-format`은 명세서 하나에 요건, 구현 위치, 검증과 커밋 근거를 담았다.
- Camellia `bundles-regressions-deferred`는 상세 검증 파일에 시나리오별 관찰과 요건 대응 및 실패/재시험을 보존했다.
- Camellia `design-bundles`는 미판정 사용자 확인에 필요한 로컬 자료를 정리 조건과 함께 유지했다.
- 기존 lifecycle `completion-records/history.md`에는 현재 커밋 완료 설명과 이전 미커밋 상태가 함께 남아 있었다.
  현재 판단과 과거 경위의 역할을 나눌 근거이며 기존 원문을 이번 작업에서 수정하지 않는다.

## 구현 결과와 요건 대조

| 요건 | 실제 반영과 근거 |
| --- | --- |
| R1 | [명세서 기록 기준](../../../../.agents/skills/skill-lifecycle/references/specification.md#작업-내용과-결과)에 핵심 결과와 요건별 판정 유지, 링크만으로 결과를 대신하지 않는 기준을 추가했다. |
| R2 | [기록 루트 안의 배치](../../../../.agents/skills/skill-lifecycle/references/work-data.md#기록-루트-안의-배치)에 문서별 생성 조건과 역할을 정의했다. history는 필요할 때만 생성하며 독립 시험 묶음의 표는 억지로 합치지 않는다. |
| R3 | 같은 배치 문서의 커밋과 역할 유지 및 [운영 규칙](../../../../.agents/skills/skill-lifecycle/references/lifecycle.md#작업-기록-갱신)에 현재 정본과 과거 경위의 구분을 반영했다. |
| R4 | [커밋 전 검토](../../../../.agents/skills/skill-lifecycle/references/commit-review.md#그룹-구성과-승인)와 [완료 정리](../../../../.agents/skills/skill-lifecycle/references/completion-records.md#보조-자료의-선별)에 유지하는 기록 전체의 커밋, 선택적 통합과 원본/참조 대조를 연결했다. |
| R5 | [시험 정리](../../../../.agents/skills/skill-lifecycle/references/scenario-validation.md#시험-생성물과-임시-기록-정리)와 완료 단계에서 용도가 끝난 자료만 정리하고 보존 이유와 조건을 남기도록 했다. 교차 검증의 원문/작성자 권한은 유지했다. |
| R6 | 단계 지침 10개의 산출물 절에 담당 기록의 역할과 공통 생성 기준을 연결했다. 템플릿과 [공용 작업 데이터 규격](../../../../standards/work-data.md#스킬별-작업-자료)을 갱신했다. history 없이 명세서에서 교차 검증 회차를 추적할 수 있다. |
| R7 | 스킬 Markdown 19개를 검토하여 12개에서 개행을 정리했다. 긴 조건절과 열거의 문맥을 대조하고 목록 본문에 맞춘 이어쓰기 들여쓰기를 유지했다. 형식 전후 파싱 결과로 본문/링크/코드/표/목록 구조와 프론트매터가 같음을 확인했다. |

정본 배치와 history 선택성은 work-data에서 관리하며 다른 단계에서는 필요한 역할과 정본을 연결한다.
별도 validation이나 history 파일을 만들지 않아도 이번 명세서에서 판단과 검사 결과를 이해할 수 있어 새 부가 기록은 만들지 않았다.
기존 완료 기록과 로컬 원문을 변경하거나 삭제하지 않았다.

## 검증 결과와 한계

검증일은 2026-10-10이다.
저장소 루트에서 Python 3로 다음 검사기를 실행했으며 대상 경로는 절대 경로로 전달했다.
검사기 경로는 `tools/scripts/validation/` 아래다.

| 검사 | 명령 또는 범위 | 결과 |
| --- | --- | --- |
| 스킬 기본 구조 | `check_structure.py .agents/skills/skill-lifecycle --json` | PASS 7, 종료 0 |
| 단계와 템플릿 | `check_lifecycle_specification.py --check-stages --check-template --json` | PASS 43, 종료 0 |
| 스킬 참조 | `check_references.py .agents/skills/skill-lifecycle --json` | 19개 문서, PASS 247, 종료 0 |
| 공용 규격 참조 | 같은 참조 검사기에 `standards/` 지정 | PASS 38, 외부 URL SKIP 1, 종료 0 |
| 작업 명세서의 보존 참조 | 같은 참조 검사기에 이 기록 디렉토리와 `--completion-report` 지정 | PASS 7, 종료 0. 새 명세서의 커밋 필요 상태 확인 |
| 형식 변경 전후 대조 | 정책 반영 후 형식 정리 전 사본과 최종 파일의 CommonMark/표 토큰 비교 | 19개 일치. 본문과 링크, 코드, 목록/표 계층 및 프론트매터 보존 |
| 들여쓰기와 렌더링 | 스킬 19개 문서의 파싱과 HTML 생성, 변경한 문단 및 목록과 원문 대조 | 의도하지 않은 들여쓰기 코드 블록 없음. 열거와 인용 항목명의 어색한 개행을 재정리 |
| 공백 | `git diff --check` | 출력 없음, 종료 0 |

형식 비교는 일반 개행에 따른 텍스트 공백만 정규화하고 나머지 본문, 링크 속성, 코드와 구조를 대조했다.
이 비교는 형식 변경의 보존 근거이며 의도한 기록 정책 변경까지 변경 없음으로 판정한 것이 아니다.
정책 변경은 위 R1~R6의 요건과 구현 정본 및 단계 연결을 별도로 대조했다.

작은 작업의 명세서 단독 기록, 상세 검증 분리, history 없이 교차 검증 회차 유지,
미판정 사용자 확인의 자료 보존, 중복 통합 후 참조 갱신과 커밋 대상을 문서상으로 확인했다.
검사기 코드는 변경하지 않아 검사기 단위 테스트는 재실행하지 않았다.
실제 스킬의 별도 에이전트 실행, 독립 교차 검토, 설치 호환성 시험과 그래픽 UI 표시는 수행하지 않았다.
외부 URL도 로컬 참조 검사의 확인 범위가 아니다.

형식 정리 전 사본, 대조 결과와 렌더링 및 검사 원시는 위 로컬 자료 루트에 있다.
검토와 커밋 시 의미 보존 및 대상 대조에 필요하여 유지한다.
커밋 검토를 마치고 재현에 필요한 결과가 이 명세서에 보존되었음을 확인하면 정리할 수 있다.
로컬 사본은 추가 정본이나 커밋 대상이 아니다.

## 최종 커밋 검토

G1: 명세서 중심의 부가 기록 관리와 lifecycle 문서 가독성.

기록 기준과 형식 정리가 같은 단계/운영 문서에 겹치므로 하나의 커밋 그룹으로 묶었다.
검토에서는 정책 변경과 형식 보존을 구분하고, 커밋은 검토한 파일 전체를 포함한다.
후속 그룹의 중복 파일 검토 재사용은 이번 단일 그룹에서 해당하지 않는다.

포함 대상은 다음 21개 파일이며 마지막 검토 상태 기록의 커밋도 함께 제시한다.

```text
.agents/skills/skill-lifecycle/SKILL.md
.agents/skills/skill-lifecycle/assets/lifecycle-template.md
.agents/skills/skill-lifecycle/references/commit-review.md
.agents/skills/skill-lifecycle/references/completion-records.md
.agents/skills/skill-lifecycle/references/design-artifacts.md
.agents/skills/skill-lifecycle/references/lifecycle.md
.agents/skills/skill-lifecycle/references/scenario-validation.md
.agents/skills/skill-lifecycle/references/specification.md
.agents/skills/skill-lifecycle/references/stages/behavioral-validation.md
.agents/skills/skill-lifecycle/references/stages/compatibility-validation.md
.agents/skills/skill-lifecycle/references/stages/completed.md
.agents/skills/skill-lifecycle/references/stages/cross-validation.md
.agents/skills/skill-lifecycle/references/stages/existing-configuration-review.md
.agents/skills/skill-lifecycle/references/stages/implementation.md
.agents/skills/skill-lifecycle/references/stages/mechanical-validation.md
.agents/skills/skill-lifecycle/references/stages/problem-definition.md
.agents/skills/skill-lifecycle/references/stages/requirements-definition.md
.agents/skills/skill-lifecycle/references/stages/structure-design.md
.agents/skills/skill-lifecycle/references/work-data.md
standards/work-data.md
records/internal/skill-lifecycle/supporting-records-and-readability/specification.md
```

제외 대상은 Git에서 제외되는 로컬 형식 대조 사본과 검사 출력 및 후속 todo다.
다른 작업의 자료와 기존 보존 기록은 포함하지 않는다.

구현과 정적 대조 및 커밋 대상 승인을 마쳤다.
승인 후 변경과 그룹 구성을 다시 확인했으며 동일 문서의 정책/형식 변경을 함께 검토하는 G1을 유지한다.
`in_review: true`를 유지하고 G1 커밋을 확인한 뒤 별도 마감 커밋으로 결과와 상태를 확정한다.
이후 같은 작업 브랜치에 푸시하고 `integrate/common` 대상 Draft PR을 생성한다.
