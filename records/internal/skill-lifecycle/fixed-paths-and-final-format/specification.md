---
status: completed
in_review: false
name: skill-lifecycle
target_path: .agents/skills/skill-lifecycle/
operation: update
---

# 스킬 산출물 경로 확정과 커밋 전 문서 검토

## 목적과 범위

초안을 만들 때마다 저장 위치를 따로 정하는 문제를 해결한다.
스킬의 용도와 이름을 논의할 때 소스와 기록 경로를 함께 확정하고,
명세서와 설계 및 검증 문서는 처음부터 `records/`의 같은 정본에서 갱신한다.

명세서와 해당 시점의 스킬을 함께 읽어 작업의 목적, 실제 변경과 기대 산출물을 파악할 수 있게 한다.
커밋 전에는 스킬 본문과 지원 문서 및 명세서를 의미에 맞게 정리하고 서로 대조한다.
프로젝트 이름보다 해결할 문제와 변경 결과가 드러나는 작업명과 문서 제목을 사용한다.

[skill-lifecycle](../../../../.agents/skills/skill-lifecycle/SKILL.md) 자체 수정에 합의한 제한된 절차를 적용한다.
이 문서는 요건, 구현과 검증을 연결하는 축약 명세서다.
전체 생명 주기나 독립 에이전트의 동작 시험을 수행했다는 기록은 아니다.
이번 작업의 완료 검토에도 그룹별 검토와 커밋 절차를 적용한다.

## 승인과 작업 기준

- [x] 용도 논의 시 소스와 기록 경로를 함께 확정하고 명세서 및 부가 문서를 처음부터 `records/`에 작성한다.
- [x] 스킬 본문과 지원 문서까지 가독성과 의미를 검토한다.
  플러그인은 호환성 검증 전과 최종 완료 시, 내부용은 최종 완료 시 검토한다.
- [x] 프론트매터의 `in_review`와 그룹별 검토 및 커밋 근거로 관문을 관리한다.
  중복 파일을 각 그룹에 나열하고 동일한 커밋 내용을 재사용하며 추가 변경은 다시 검토한다.
- [x] 명세서와 실제 스킬의 대응 및 목적 중심 명명 기준을 포함한다.
  `specification.md` 파일명은 유지한다.
- [x] 위 범위를 정리하고 스킬 개선을 진행한다.
  사용자가 추가 논의 없이 구현을 진행하도록 요청했다.
- [x] GPT-6 Astra/high로 지침 수정과 관련 검증을 수행한다.
  실제 모델 적용은 사용자의 변경 완료 확인을 근거로 하며 독립 실행 상태 검증은 하지 않았다.
- [x] 아래 25개 파일과 최종 상태 기록의 커밋.
  대상 목록과 브랜치 생성 기준을 확인한 뒤 사용자가 커밋을 요청했다.

기준 커밋은 `c761a80`, 대상은 이 커밋 위의 이번 변경이다.
로컬 작업 브랜치는 `work/common/lifecycle-paths-and-final-format`이다.
명세서 경로는 최초 확정한 위치를 유지하며 이번 문서 제목은 목적에 맞게 정리했다.

## 요건과 구현 결과

| 요건 | 기대 동작과 산출물 | 구현 정본 |
| --- | --- | --- |
| 용도와 경로 동시 확정 | 새 스킬의 내부용/플러그인용 여부와 이름을 논의할 때 소스 및 기록 경로를 확정한다. 미정이면 파일을 만들지 않고 논의를 이어간다. | [경로 확정](../../../../.agents/skills/skill-lifecycle/references/work-data.md#경로-확정), [소스 배치](../../../../standards/repository-layout.md#스킬-배치) |
| 정본에서 초안 작성 | 소스는 실제 배치 위치, 명세서와 설계 및 검증 문서는 records 작업 루트에서 시작한다. 완료 시 제자리에서 정리한다. | [작업 자료 배치](../../../../.agents/skills/skill-lifecycle/references/work-data.md), [완료 정리](../../../../.agents/skills/skill-lifecycle/references/completion-records.md) |
| 기존 자료와 로컬 자료 | 기존 작업은 현재 정본에서 재개하고 필요한 경우에만 대조하여 이관한다. 원시 로그와 시험용 사본은 대응하는 공용 로컬 자료 루트에 둔다. | 같은 작업 자료 배치 및 완료 정리 문서 |
| 두 검토 관문 | 플러그인은 cross-validation에서 호환성 검증용 커밋 전 검토를, 모든 스킬은 completed에서 최종 검토를 수행한다. 검토 중에는 다음 관문 통과나 완료 선언을 막는다. | [공통 검토 절차](../../../../.agents/skills/skill-lifecycle/references/commit-review.md), [생명 주기](../../../../.agents/skills/skill-lifecycle/references/lifecycle.md#커밋-전-검토-관문) |
| 검토 상태 | 표준 프론트매터는 in_review boolean을 포함한다. 기존 누락은 재개 시 근거에 따라 갱신하며 자동 완료로 읽지 않는다. | [명세서 형식](../../../../.agents/skills/skill-lifecycle/references/specification.md#프론트매터), [템플릿](../../../../.agents/skills/skill-lifecycle/assets/lifecycle-template.md) |
| 그룹별 처리 | 목적별 그룹의 포함/제외 파일을 명시하고 정리, 검토, 커밋한다. 중복 파일은 선행 검토 커밋과 현재 내용 및 모드가 같을 때만 파일 검토를 재사용한다. 추가 변경과 각 그룹의 요건 충족 여부는 확인한다. | 공통 검토 절차의 그룹 구성과 처리 |
| 검토 마감 | 모든 그룹 커밋 후 결과와 in_review false 변경을 검토하여 마감 커밋한다. 실패하면 true로 복구한다. 자신의 커밋 해시를 반복 기록하지 않는다. | 공통 검토 절차의 그룹별 처리 |
| 가독성과 의미 보존 | 문장 단위 개행, 논점별 문단, 병렬/순서 목록과 종속 설명의 들여쓰기를 정리한다. 범위, 조건, 예외, 의무와 승인/검증 상태를 보존한다. | 공통 검토 절차의 개행과 목록 구조 정리 |
| 명세서 가치와 명명 | 작업명과 제목은 목적과 변경 결과를 나타낸다. 명세의 입력/조건, 동작, 산출물과 종료 기준을 실제 구현 및 검증에 연결한다. | [작업명과 제목](../../../../.agents/skills/skill-lifecycle/references/specification.md#작업명과-제목), 공통 검토 절차의 대응 확인 |
| 기계 검사 | in_review 누락과 잘못된 타입을 보고한다. boolean 값으로 실제 검토나 완료를 추정하지 않는다. | [검사 안내](../../../../tools/references/check-lifecycle-specification.md), [검사기](../../../../tools/scripts/validation/check_lifecycle_specification.py), [테스트](../../../../tools/tests/validation/test_lifecycle_specification.py) |

공용 작업 데이터 규격, 저장소 배치, AGENTS와 README 및 검사 안내의 기존 이관 전제를 함께 조정했다.
다른 작업에 lifecycle의 필수 단계를 적용하거나 기존 기록을 일괄 이동하지 않았다.
명세서와 함께 보관할 부가 파일의 종류와 상세 정리 방식은 후속 논의로 남겼다.

## 검증 결과와 한계

검증일은 2026-10-10이다.
명령은 저장소 루트에서 Python 3로 실행했으며 검사 대상은 절대 경로로 전달했다.

| 검사 | 명령 또는 범위 | 결과 |
| --- | --- | --- |
| 검사기 단위 및 CLI 회귀 | `python3 -B -m unittest discover -s tools/tests/validation -p test_lifecycle_specification.py -q` | 47개 통과. boolean 두 값, 잘못된 타입, 중복/누락, 기존 형식 회귀와 읽기 전용 CLI 포함 |
| 기본 구조 | `check_structure.py .agents/skills/skill-lifecycle --json` | PASS 7, 종료 0 |
| 단계와 템플릿 | `check_lifecycle_specification.py --check-stages --check-template --json` | PASS 43, 종료 0 |
| lifecycle 로컬 참조 | `check_references.py .agents/skills/skill-lifecycle --json` | 19개 문서, PASS 227, 종료 0 |
| 개발 규격 참조 | 같은 참조 검사기에 `standards/` 지정 | 6개 문서, PASS 38, 외부 링크 SKIP 1 |
| 도구 안내 참조 | 같은 참조 검사기에 `tools/` 지정 | 12개 문서, PASS 89, 외부 링크 SKIP 13 |
| 루트 문서 참조 | 참조 검사 모듈의 링크 추출과 대상/절 확인으로 AGENTS 및 README 검사 | PASS 38 |

표의 검사기 파일은 `tools/scripts/validation/` 아래에 있다.
이 축약 명세서는 표준 단계별 본문 검사 대상이 아니며 단계/템플릿 검사를 별도로 수행했다.
원시 JSON은 공용 경로의 `cargo/work/internal/skill-lifecycle/fixed-paths-and-final-format/mechanical-validation/`에 있다.
커밋 검토와 오류 조사 동안 유지하며 최종 판단에 필요한 결과는 이 명세서에 포함한다.

문서 내용 대조에서는 다음 흐름을 확인했다.

- 신규 내부용 및 플러그인용 작업은 각각의 확정 소스와 records 경로에 작성한다.
  경로가 미정이면 임의 위치에 생성하지 않는다.
- 플러그인은 교차 검증 수행 여부 판단 후 첫 검토 관문을 거친다.
  아직 수행하지 않은 호환성 결과를 완료로 쓰지 않으며, 설치 대상 변경 시 검토와 필요한 검증으로 복귀한다.
- 내부용은 첫 관문을 적용하지 않고 완료 단계에서 소스와 기록을 함께 검토한다.
- 선행 그룹의 커밋 내용과 같은 파일만 재사용하고 이후 변경은 다시 검토한다.
  파일 검토를 재사용해도 해당 그룹의 요건 충족은 별도로 확인한다.
- 검토 중 보완과 이전 단계 복귀는 허용하되 관문 통과와 최종 완료를 막는다.
  승인 부재나 커밋 실패를 완료로 바꾸지 않고 마감 실패는 true로 복구한다.
- 명세의 기대 산출물과 실제 관찰 및 미검증 범위를 구분하며,
  형식 검사 통과를 의미 검토나 실제 에이전트 동작의 증명으로 사용하지 않는다.

독립 에이전트의 지침 준수 시험, 교차 검토 및 설치 호환성 시험은 이번 축약 범위에서 수행하지 않았다.
검증은 지침의 정적 대조와 검사기 회귀 범위다.
외부 URL의 유효성과 그래픽 UI 표시는 검증하지 않는다.
최종 Markdown 구조, 기록 참조 및 공백 검사는 아래 검토 결과에 기록한다.

## 최종 커밋 검토

### 그룹과 대상

G1: 스킬 산출물 경로 확정과 커밋 전 명세/문서 검토.

두 개선이 같은 명세서 규격과 템플릿 및 단계 지침을 수정하고 서로 연결되므로 하나의 그룹으로 처리한다.
분리된 중간 커밋에 새 필드와 검사 또는 문서 참조의 불일치가 생기는 것을 피한다.
그룹별 중복 파일 재사용은 이번 단일 그룹에서는 해당하지 않는다.

포함 대상은 아래 25개 파일이며, 명세서의 마지막 상태 기록 커밋도 같은 승인 범위에 포함한다.

```text
.agents/skills/skill-lifecycle/SKILL.md
.agents/skills/skill-lifecycle/assets/lifecycle-template.md
.agents/skills/skill-lifecycle/references/commit-review.md
.agents/skills/skill-lifecycle/references/completion-records.md
.agents/skills/skill-lifecycle/references/design-artifacts.md
.agents/skills/skill-lifecycle/references/lifecycle.md
.agents/skills/skill-lifecycle/references/scenario-validation.md
.agents/skills/skill-lifecycle/references/specification.md
.agents/skills/skill-lifecycle/references/stages/compatibility-validation.md
.agents/skills/skill-lifecycle/references/stages/completed.md
.agents/skills/skill-lifecycle/references/stages/cross-validation.md
.agents/skills/skill-lifecycle/references/stages/implementation.md
.agents/skills/skill-lifecycle/references/stages/requirements-definition.md
.agents/skills/skill-lifecycle/references/work-data.md
AGENTS.md
README.md
standards/repository-layout.md
standards/skills/skill-validation.md
standards/work-data.md
tools/mappings.md
tools/references/check-lifecycle-specification.md
tools/references/check-references.md
tools/scripts/validation/check_lifecycle_specification.py
tools/tests/validation/test_lifecycle_specification.py
records/internal/skill-lifecycle/fixed-paths-and-final-format/specification.md
```

제외 대상은 Git에서 제외되는 공용 로컬 검사 출력과 후속 논의 todo다.
이번 작업 외의 기존 todo와 다른 작업 자료는 변경하거나 커밋하지 않는다.

### 검토 결과와 완료 판단

구현과 위 검증을 마쳤다.
명세의 각 요건과 실제 지침 및 검사기를 대조했다.
변경된 Markdown 23개를 CommonMark/표 파서로 확인했으며 의도하지 않은 들여쓰기 코드 블록은 없었다.
공통 검토 절차와 이 명세서는 렌더러의 HTML도 원문과 대조하여 문단, 목록과 표의 구분을 확인했다.
커밋 전 완료 기록 참조 검사는 PASS 13, 종료 0이었다.
당시 미추적 보존 대상이었던 새 공통 검토 문서와 이 명세서도 G1 커밋에 포함했다.
`git diff --check`는 출력 없이 종료 0이다.

승인된 25개 파일과 실제 스테이징 대상을 대조한 뒤
G1을 `ad75819` (Define lifecycle artifact paths and commit review gates)로 커밋했다.
합의한 구현과 정적 검증 범위를 충족했으며 이번 개선의 남은 구현 작업은 없다.
이 명세서의 승인, 커밋 근거와 완료 상태를 대조하여 `in_review: false`로 마감한다.
마감 커밋은 이 파일의 Git 이력으로 확인하며 자신의 해시를 본문에 반복 기록하지 않는다.
푸시는 이번 요청 범위에 포함하지 않는다.

## 후속 논의

이번 개선 완료 후 명세서와 함께 저장할 파일의 종류 및 정리 방법을 사용자와 논의한다.
공용 todo의 `20261010-lifecycle-supporting-records.md`에 재개 조건과 범위를 남겼다.
현재 개선의 미구현 요건이나 부가 파일 삭제 승인으로 해석하지 않는다.
