---
name: code-development
target_path: plugins/Camellia/skills/code-development
operation: update
current_stage: completed
---

# 설계 산출물과 순차 묶음 개선 명세서

## problem-definition (문제 정의)

### 진입 조건 확인

기존 스킬과 Flax/Rosemary report를 대조하여 설계 정의, 승인 범위와 묶음별 개정의 개선 필요성을 확인했다.

### 스킬을 통해 해결해야 할 문제

큰 설계에서 구현용 정의와 승인 범위가 긴 설명에 묻히고 뼈대와 상세 논의가 분리되지 않았다.
같은 주제의 순차 묶음은 기존 단계별 최신 report 규칙과 충돌했다.

### 스킬을 사용하는 주체와 스킬이 사용되는 상황

Codex/Claude 개발 에이전트와 설계 및 QA를 확인하는 사용자가 설계 작성, 구현 인계와 작업 재개에 사용한다.

### 문제가 해결되었을 때 기대하는 결과

구현 계약과 검증 기준을 설계에서 찾고, 묶음별 승인과 전체 작업 완료를 구분한다.

### 요청한 스킬의 생성, 변경, 통합 또는 폐기가 필요한지에 대한 판단과 근거

기존 설계/분할/기록 책임의 개선이므로 기존 스킬을 변경했다.
새 스킬은 만들지 않았다.

### 스킬이 수행할 범위와 제외할 범위

설계 산출물, 논의 그룹별 상세 분리, 뼈대 우선 진행, 분할 판단, 묶음 기록과 승인 압축을 반영했다.
전용 검사의 기능 확장과 역할별 분할을 포함한다.
다른 프로젝트 문서와 전역 설정 변경은 제외했다.

Claude의 남은 설치본 검증은 사용자 확인으로 이관했다.
상세 범위와 완료 기준은 요건 정의의 지원 CLI 항목을 따른다.

### 후속 단계에서 확인할 사항

기계 검사, 동작 시나리오와 교차 검증은 완료했다.
설치본 검증의 남은 범위는 [설치본 호환성](validation.md#설치본-호환성)에 사용자 확인 대상으로 명시했다.

### 완료 조건 확인

문제, 사용 상황과 변경 범위를 정의했고 요건 및 검증 결과로 연결했다.

### 단계 이동 기록

최초 기록에서 선행 문제와 범위를 확인했다.
과거에 수행하지 않은 단계 이동은 만들지 않았다.

## requirements-definition (요건 정의)

### 진입 조건 확인

설계 및 순차 묶음의 개선 범위와 기존 계약을 유지할 조건을 확인했다.

### 스킬의 사용 형태(내부용 또는 플러그인 배포용)

Camellia 플러그인 배포형이며 기존 스킬 경로와 호출 조건을 유지한다.

### 지원 대상 CLI와 각 CLI에 적용할 호환성 요건

Codex/Claude 공통 Markdown과 Python 검사기를 사용한다.
기존 단일 플로우의 입력, 상태, 번호와 참조 계약을 유지한다.
설치본의 K1~K4 기준과 CLI별 관찰은 [호환성 결과](validation.md#설치본-호환성)를 따른다.

2026-10-07 사용자가 Claude의 남은 검증을 사용자 확인으로 이관하도록 요청했다.
Codex C1의 K1~K4와 Claude C2의 K1/K2 확인은 유지한다.
C2의 K3/K4는 사용자 확인으로 보류하고 이번 에이전트 작업의 필수 완료 범위에서 제외한다.
추가 자동 호출은 수행하지 않는다.
이 조정은 검증 담당과 완료 범위의 변경이며, Claude 지원 요건의 삭제나 미판정의 통과 전환이 아니다.
실제 관찰과 남은 확인 기준은 [설치본 호환성](validation.md#설치본-호환성)에 보존한다.

### 스킬 호출 조건과 호출 제외 조건

[SKILL.md](../../../../../plugins/Camellia/skills/code-development/SKILL.md)의 기존 호출 및 제외 조건을 유지했다.
요구사항과 설계 판단이 필요한 개발 및 기존 report를 이용한 재개에 적용하며, 명확한 국소 수정에는 자동 적용하지 않는다.

### 스킬 실행에 필요한 입력과 기대 결과

승인된 논의, 코드/설계와 현재 report를 입력으로 사용한다.
구현에 필요한 표/선언/도식, 상세 링크와 묶음별 결과를 남긴다.

### 반드시 수행해야 하는 동작과 에이전트가 재량으로 판단할 수 있는 동작

| 요건 | 수행 기준 |
| --- | --- |
| R1 | 최종 설계에 적용 대상의 인터페이스/데이터/DB/상태/흐름/검증 정의를 남김. 부가 설명은 허용 |
| R2 | 읽기 어려운 상세는 논의 그룹별 분리. 주 설계에 설명/링크. 흐름별 파일과 작은 설계의 강제 분리는 금지 |
| R3 | 큰 설계는 뼈대 -> 분할 -> 현재 묶음 상세 -> 구현/검증/QA. 후속 상세 미정과 현재 차단 사항 구분 |
| R4 | 항상 분할 재평가. 독립 목적은 신규 주제, 공통 목적은 같은 주제 순차 묶음. 시작 단계와 의존/완료 기준 기록 |
| R5 | 묶음별 상태/승인과 전체 완료 구분. 과거 완료를 다음 묶음 승인으로 승계하지 않음 |
| R6 | 승인 대상/판단/조건/근거로 압축. 중복 설명과 해결된 미정을 정리하되 이력 증거 보존 |
| R7 | 최종 제출 전 필요 도식 정리와 실제 표시 확인. 문자 검사로 표시를 대신하지 않음 |
| R8 | 읽기 전용 검사에서 묶음별 개정/선행 연결을 확인. 기존 단일 플로우 유지 |
| R9 | 현재 completed report의 체크리스트가 비어 있거나 미확인 항목이 남으면 실패. 체크된 항목의 현재 확인 근거 누락도 검사 |
| R10 | verification/qa의 완료 구분 누락/중복/단계별 허용값과 설명을 검사. 작성 중 미정은 허용하고 실제 결과의 타당성은 판단하지 않음 |
| R11 | 일괄 반영 기록의 식별자 중복, 대상 항목 누락과 실제 날짜/시각 형식을 검사. 기존 항목별 시각을 허용하고 승인 진위나 자연어 항목명의 의미 대응은 판정하지 않음 |
| R12 | 공통 설계의 묶음표 식별자 중복, 현재 묶음 report의 미등록 식별자와 결과 링크의 묶음/단계/작업 일치를 검사. 기존 비정형 표는 자동 변환하지 않고 미판정으로 보고 |
| R13 | 전용 검사기를 구조/연결, 완료/확인 기록, 묶음표, 문서 참조, 도식의 5개 역할로 분리. 개별 실행과 기존 전체 실행을 지원하고 단계/변경 영향에 따라 필요한 역할 선택. 파싱/입력/출력은 스킬 내부 공통 모듈을 공유 |

### 스킬 실행에 적용되는 제약, 실패 조건과 대응

SSOT/SDD와 기존 승인/회귀 경계를 유지한다.
필수 선행 조건이 부족하면 해당 묶음의 단계 진입을 대기한다.
기계 검사는 내용의 충분함, 승인 진위, 분할 타당성과 실제 도식 표시를 판정하지 않는다.

### 사용자 확인 및 승인 조건

- [x] 개선 범위와 구현 모델: 2026-10-06 사용자 확인에 따라 Astra/xhigh로 진행했다.
- [x] 검사 확장과 분할: 사용자가 R9~R12 추가 및 R13의 스킬 내부 역할별 분할을 요청했다.
- [x] 그룹별 Git 반영: 사용자가 그룹 1~10의 파일 전체 커밋과 이후 푸시 및 integrate/camellia 대상 PR 생성을 승인했다.
  PR #38 병합과 Garden 업데이트는 사용자가 별도로 진행했다.
- [x] 동작 시험: S1~S4를 Astra/xhigh로 각 1회/600초 실행하고, S2만 기존 결과를 재사용한 추가 1회/600초 확인을 승인했다.
  모의 선행 승인 범위만 적용했으며 새 설계, 도식 표시와 구현 착수 승인은 포함하지 않았다.
- [x] 교차 검증: 사용량을 고려하여 Claude Sonnet/high의 독립 검토를 승인했다.
- [x] 설치본 시험: C1/C2 각 1회/600초를 승인했다.
  실행 직전 사용자가 Codex의 Astra/high를 별도로 확정했고 Claude는 Sonnet/high로 실행했다.
- [x] 남은 Claude 확인의 이관: 추가 호출 생략 후 사용자가 K3/K4를 사용자 확인으로 넘겨 정리하도록 요청했다.
- [ ] Claude K3/K4의 실제 사용자 확인 결과: 아직 전달받지 않았다.
  담당 이관과 확인 완료를 구분한다.

위 기록은 이번 스킬 개발의 승인이다.
스킬을 사용하는 개별 작업의 묶음 종료, 설계 승인과 다음 단계 착수는 해당 report의 승인을 별도로 따른다.

### 각 요건의 충족 여부를 검증할 수 있는 기준

| 요건 | 최종 검증 근거와 범위 |
| --- | --- |
| R1~R4, R6 | 지침/템플릿 대조, S1~S3의 설계 작성과 분할 판단, 독립 교차 검토 |
| R5, R8 | 77개 회귀 시험에 포함된 묶음 개정/선행/과거 참조 경계, S2/S4의 승인 대기와 재개 판단 |
| R7 | 문자 검사 회귀와 지침의 실제 표시 구분, S2의 표시 미확인 보고 및 승인 대기. S2 표시 성공은 검증하지 못함 |
| R9~R12 | 정상/오류/작성 중/과거 형식 회귀, 실제 기존 자료 대조와 S4의 오류 4개 탐지 |
| R13 | 개별 역할 독립성/전체 결과 일치/파싱 오류의 회귀, 28파일 배포 대조, C1의 설치본 전체/개별 실행 |

명령, 실제 관찰과 한계는 [검증 기록](validation.md)을 따른다.

### 확인하지 못한 사항과 사용자의 판단이 필요한 사항

Claude K3/K4는 사용자 확인으로 이관했다.
실제 표시 미확인과 설치본 시험 한계는 [완료 시 잔여 사항](#완료-여부를-판단하는-시점에-남아-있는-미확인-사항과-위험)을 따른다.

### 완료 조건 확인

R1~R13의 수행 기준과 검증 근거를 대조했다.
완료 판단에는 사용자와 조정한 검증 범위를 적용하며 미판정은 그대로 보존한다.

### 단계 이동 기록

최초 선행 요건 정의 후 R9~R12 추가와 R13 분할을 반영했다.
최종 판단 전에 Claude K3/K4의 사용자 확인 이관을 완료 범위에 반영했다.

## existing-configuration-review (기존 구성 확인)

### 진입 조건 확인

기존 단일 플로우와 단계/승인 계약, 추가 정형 검사의 입력을 확인했다.

### 확인한 기존 구성과 실행 환경 목록

초기 기준은 Camellia 3.0.0의 d8e48eb이며 최종 변경 대조 기준은 1bc373a다.
구현 결과는 Camellia 3.1.0의 baef202이다.
검토 중 임시 작업 트리에 있던 소스는 사용자 요청으로 본 저장소에 옮겼고 최종 변경은 본 저장소에 반영했다.

### 기존 구성과 제품 동작을 확인하는 데 사용한 직접적인 근거

기준 소스, 이전 보존 명세와 사용자 제공 Flax/Rosemary report를 읽기 전용으로 대조했다.
Flax는 PASS 139/SKIP 9/도식 0, Rosemary는 PASS 261/SKIP 13/도식 65였다.
이는 기존 자료 호환성의 근거이며 새 묶음 절차를 에이전트가 수행한 근거는 아니다.

### 정의된 요건과 기존 구성 사이의 중복, 차이, 충돌 및 의존 관계

기존 분할 재평가와 ASCII 표시 확인을 보강했다.
단계 전체의 이전 report를 superseded로 요구하던 계약을 묶음별 현재 개정 판단으로 확장했다.
완료 체크리스트, 완료 구분, 반영 기록과 묶음표의 정형 대조를 추가했다.

### 기존 구성의 재사용, 수정, 분리, 통합, 제거 또는 신규 생성에 대한 판단과 근거

기존 report 경로와 상태를 재사용하고 bundle 필드를 선택형으로 추가했다.
설계/묶음 규칙은 전용 참고 문서로 분리했으며 기존 단일 작업을 자동 변환하지 않는다.

### 확인하지 못한 사항과 확인할 단계

새 지침의 실제 준수는 동작 검증으로 확인했다.
설치본의 Claude 검사 실행은 사용자 확인으로 남았다.

### 완료 조건 확인

재사용할 계약, 변경할 개정 단위와 검사 확장 범위를 구분하여 최종 설계에 반영했다.

### 단계 이동 기록

최초 구조 설계의 선행 조건을 확인했고, 검사 확장 및 분할 시 기존 파서와 실제 자료를 다시 대조했다.

## structure-design (구조 설계)

### 진입 조건 확인

기준 소스와 기존 실행 근거를 R1~R13에 대조하여 구조를 정했다.

### 작업 대상 스킬과 지원 파일 및 디렉토리의 구조

기존 스킬 디렉토리 안에 전용 지침과 Python 검사기를 둔다.
개발 시험은 저장소 tools/tests에 두며 배포하지 않는다.
최종 구조의 정본은 [설계 산출물](../../../../../plugins/Camellia/skills/code-development/references/design-artifacts.md), [작업 묶음](../../../../../plugins/Camellia/skills/code-development/references/work-bundles.md), [report 규칙](../../../../../plugins/Camellia/skills/code-development/references/guidelines.md), [검사 계약](../../../../../plugins/Camellia/skills/code-development/references/report-checks.md)다.

### 각 파일과 자료가 담당할 역할

설계/묶음 지침, 단계별 템플릿, 역할별 검사기와 개발 회귀 시험으로 나눈다.
검사기 7파일의 역할은 [구현과 실행 구조](validation.md#구현과-실행-구조)를 따른다.

### 스킬을 구성하는 파일과 자료 사이의 참조 방향 및 의존 관계

SKILL/workflow -> 현재 단계/묶음 -> 설계 산출물/템플릿/검사 계약 순서로 참조한다.
guidelines는 공통 기록/승인을 담당하고 묶음 예외는 work-bundles를 참조한다.
검사기는 스킬 내부 공통 모듈을 사용하며 Aster 개발 도구에 의존하지 않는다.

### 작업 대상 스킬 전용 자료

design-artifacts는 구현용 정의와 상세 분리, work-bundles는 뼈대/분할/묶음 계약을 담당한다.
report-checks와 scripts는 스킬 전용 읽기 전용 검사를 담당한다.
정본 링크는 위 구조 항목을 따른다.

### 내부 스킬 공용 자료

없음. 내부 lifecycle의 공용 구성은 이번 스킬 변경 대상이 아니다.

### 플러그인 단위 자료와 플러그인 내부 공용 자료

기존 Camellia manifest의 버전을 3.1.0으로 변경했다.
다른 스킬에 적용할 새 플러그인 공용 지침은 추가하지 않았다.

### 개발 전용 자료와 스킬 사용 자료의 구분

배포물은 manifest 1개, Markdown 19개, Python 7개와 requirements 1개로 총 28파일이다.
개발 시험, 작업 명세와 검증 기록은 배포 범위에서 제외한다.

### 지원 CLI에서 함께 사용하는 공용 구성

Codex/Claude 공통 SKILL, Markdown, Python 3.10 이상과 스킬 requirements를 사용한다.

### 특정 지원 CLI에서만 사용하는 전용 구성

없음. 실제 비호환을 근거로 별도 하네스 전용 파일을 추가한 사항은 없다.

### 동작 검증 시나리오 초안

S1 작은 설계, S2 뼈대/묶음 상세, S3 독립 목적 분리, S4 재개/오류 차단을 확정하여 실행했다.
선행 조건과 기대 결과 및 실제 판정은 [동작 시나리오](validation.md#동작-시나리오)에 보존했다.

### 구조 설계에 영향을 주는 미확인 사항과 확인 단계

구조 설계를 막는 미확인 사항은 없다.
실제 CLI의 관찰 한계는 검증 단계의 결과로 구분했다.

### 완료 조건 확인

선택 bundle, 단계별 전역 번호와 묶음별 개정/선행, 5개 역할 및 내부 공통 모듈의 책임을 확정했다.
기존 입력과 승인/회귀 계약을 유지하는 조건은 구현과 회귀 시험으로 대조했다.

### 단계 이동 기록

최초 진입 단계는 structure-design이었다.
검사 확장 R9~R12와 역할 분할 R13의 사용자 요청 때 mechanical-validation에서 구조 설계로 복귀했다.
각 계약을 정의한 뒤 구현과 영향받는 기계 검사를 다시 수행했다.

## implementation (구현)

### 진입 조건 확인

확정한 파일 역할, 묶음/검사 계약과 사용자 승인 범위를 기준으로 구현했다.

### 새로 만들거나 수정, 이동 또는 제거한 파일과 디렉토리

기준 1bc373a 대비 baef202의 변경은 다음 24파일이다.
선택형 묶음과 호환성을 유지하는 확장이므로 minor 3.1.0을 적용했다.

- [plugins/Camellia/.claude-plugin/plugin.json](../../../../../plugins/Camellia/.claude-plugin/plugin.json)
- [plugins/Camellia/skills/code-development/SKILL.md](../../../../../plugins/Camellia/skills/code-development/SKILL.md)
- [plugins/Camellia/skills/code-development/assets/stage_reports/design-template.md](../../../../../plugins/Camellia/skills/code-development/assets/stage_reports/design-template.md)
- [plugins/Camellia/skills/code-development/assets/stage_reports/discussion-template.md](../../../../../plugins/Camellia/skills/code-development/assets/stage_reports/discussion-template.md)
- [plugins/Camellia/skills/code-development/assets/stage_reports/implementation-template.md](../../../../../plugins/Camellia/skills/code-development/assets/stage_reports/implementation-template.md)
- [plugins/Camellia/skills/code-development/assets/stage_reports/qa-template.md](../../../../../plugins/Camellia/skills/code-development/assets/stage_reports/qa-template.md)
- [plugins/Camellia/skills/code-development/assets/stage_reports/verification-template.md](../../../../../plugins/Camellia/skills/code-development/assets/stage_reports/verification-template.md)
- [plugins/Camellia/skills/code-development/references/design-artifacts.md](../../../../../plugins/Camellia/skills/code-development/references/design-artifacts.md)
- [plugins/Camellia/skills/code-development/references/guidelines.md](../../../../../plugins/Camellia/skills/code-development/references/guidelines.md)
- [plugins/Camellia/skills/code-development/references/report-checks.md](../../../../../plugins/Camellia/skills/code-development/references/report-checks.md)
- [plugins/Camellia/skills/code-development/references/stages/design.md](../../../../../plugins/Camellia/skills/code-development/references/stages/design.md)
- [plugins/Camellia/skills/code-development/references/stages/implementation.md](../../../../../plugins/Camellia/skills/code-development/references/stages/implementation.md)
- [plugins/Camellia/skills/code-development/references/stages/qa.md](../../../../../plugins/Camellia/skills/code-development/references/stages/qa.md)
- [plugins/Camellia/skills/code-development/references/stages/verification.md](../../../../../plugins/Camellia/skills/code-development/references/stages/verification.md)
- [plugins/Camellia/skills/code-development/references/work-bundles.md](../../../../../plugins/Camellia/skills/code-development/references/work-bundles.md)
- [plugins/Camellia/skills/code-development/references/workflow.md](../../../../../plugins/Camellia/skills/code-development/references/workflow.md)
- [plugins/Camellia/skills/code-development/scripts/check_completion_records.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_completion_records.py)
- [plugins/Camellia/skills/code-development/scripts/check_report_diagrams.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_report_diagrams.py)
- [plugins/Camellia/skills/code-development/scripts/check_report_links.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_report_links.py)
- [plugins/Camellia/skills/code-development/scripts/check_report_structure.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_report_structure.py)
- [plugins/Camellia/skills/code-development/scripts/check_reports.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_reports.py)
- [plugins/Camellia/skills/code-development/scripts/check_work_bundles.py](../../../../../plugins/Camellia/skills/code-development/scripts/check_work_bundles.py)
- [plugins/Camellia/skills/code-development/scripts/report_common.py](../../../../../plugins/Camellia/skills/code-development/scripts/report_common.py)
- [tools/tests/validation/test_code_development_reports.py](../../../../../tools/tests/validation/test_code_development_reports.py)

### 구현하지 못한 요건과 구현하지 못한 이유 및 보완할 단계

구현 대상 누락은 없다.
Claude 설치본 K3/K4의 미확인은 구현 누락과 구분한다.

### 완료 조건 확인

설계/템플릿/지침에 R1~R8, 정형 대조에 R9~R12, 역할별 실행과 전체 실행에 R13을 반영했다.
미시작 report를 만들거나 기존 작업을 자동 변환하지 않고 스킬 사용 기록을 읽기만 한다.

### 단계 이동 기록

각 구현 이후 mechanical-validation에서 회귀, 기존 자료 호환 및 배포를 확인했다.
그룹 검토에서 발견한 과거 참조와 도식 구분자 오류는 보완 후 영향 검사를 다시 수행했다.

## mechanical-validation (기계 검사)

### 진입 조건 확인

구현 대상과 적용 규격 및 필수 검사 범위를 확인했다.

### 작업 대상 스킬의 기계 검사 항목과 적용 여부

검사기 회귀, 스킬 구조/참조/배포, 명세서 형식과 기존 report 호환을 적용했다.
승인 진위, 설계 충분함과 실제 CLI 동작은 의미 판단 및 후속 검증으로 구분했다.

### 기계 검사에 사용한 명령과 각 명령의 적용 대상

[기계 검사](validation.md#기계-검사)에 대상, 재현 명령과 최종 결과를 기록했다.

### 기계 검사별 통과 또는 실패 결과

전체 회귀 77개, 구조 7 PASS, 로컬 참조 295 PASS/외부 URL 2 SKIP, 배포 23 PASS 및 기대 28파일 일치를 확인했다.
최종 변경의 영향 범위와 소스 동일성을 확인하여 유효한 기존 결과를 재사용했다.

### 검사 실패가 발생한 위치와 위반한 개발 규격

[주요 실패와 보완](validation.md#주요-실패와-보완)에 과거 공통 참조 오판과 도식 닫는 구분자 오판의 재현/수정/회귀 결과를 보존했다.
최종 미해결 기계 실패는 없다.

### 실행하지 못한 검사와 실행했지만 결과를 판정하지 못한 항목

선정한 필수 기계 검사에 미실행/미판정은 없다.
외부 URL 2건은 로컬 참조 검사 대상 밖이며 외부 페이지의 유효성을 확인한 뜻이 아니다.

### 의미 판단이 필요한 항목과 그 이유 및 확인할 후속 단계

스킬 지침의 도식 1개는 Chrome 표시와 원문을 대조했다.
S2에서 생성한 별도 시험 도식의 표시 성공을 대신하는 근거는 아니다.
실제 지침 준수와 설치 실행은 이후 단계에서 별도로 확인했다.

### 완료 조건 확인

필수 기계 검사와 보완 후 회귀를 통과했다.
기계 검사 통과를 실제 승인이나 전체 설치 호환성 완료로 확대하지 않는다.

### 단계 이동 기록

2026-10-07 기계 검사와 시험 실행 조건의 사용자 확인을 마치고 behavioral-validation으로 이동했다.

## behavioral-validation (동작 검증)

### 진입 조건 확인

baef202의 기계 검사 통과와 S1~S4의 사용자 확정을 근거로 진입했다.
정상 선행 입력과 오류 변형 4개의 의도한 검사 결과를 실행 전에 대조했다.

### 확정한 시나리오와 실행 조건

Astra/xhigh, S1~S4 각 1회/600초로 실행했다.
S2는 최초 timeout 후 사용자 승인으로 추가 1회/600초의 최종 확인을 수행했다.
모의 선행 승인은 새 설계/표시/구현 승인으로 확장하지 않았다.

### 동작 검증을 수행한 사용 사례와 입력

[동작 시나리오](validation.md#동작-시나리오)의 사전 조건, 입력과 기대 결과를 사용했다.

### 동작 검증에 사용한 CLI와 실행 환경

Codex CLI 0.160.1, gpt-6-astra/xhigh를 각 세션의 turn_context에서 확인했다.
baef202의 배포 28파일 사본을 사용한 격리 프로젝트이며 실제 설치본 시험과 구분한다.

### 작업 대상 스킬의 인식 여부와 호출 결과

네 사례 모두 명시한 사본의 SKILL과 관련 지침/템플릿/검사기를 사용했다.
자동 선택이나 전역 설치본 인식의 근거로 확대하지 않는다.

### 요건별 동작 검증 결과와 판정 근거

S1~S4 모두 통과했다.
요건별 적용은 [요건 검증 대응](#각-요건의-충족-여부를-검증할-수-있는-기준), 관찰은 [동작 시나리오](validation.md#동작-시나리오)를 따른다.

### 이전 단계에서 넘긴 미확인 사항과 의미 판단 항목의 확인 결과 및 근거

단일 설계 유지, 공통 뼈대와 상세 분리, 독립 목적 분리 제안 및 선행 오류 차단을 확인했다.
S2는 표시 미확인을 보고하고 승인 대기에 머물렀다.
실제 도식 표시 완료와 새 설계 승인을 얻었다는 뜻은 아니다.

### 동작 검증에서 발견한 실패와 재현 조건

작성 중 빈 반영 기록의 형식 오류는 해당 실행 안에서 보완됐다.
S2는 Firefox snap 권한 오류로 렌더링을 확인하지 못했고 최초 실행이 시간 상한에 도달했다.
후속 확인은 기존 결과와 승인 상태를 바꾸지 않고 최종 응답과 정상 종료를 확보했다.

### 실행하지 못한 사용 사례와 결과를 판정하지 못한 동작

미실행 사례는 없다.
S2 최초 timeout은 유지하고 후속 성공과 결합하여 선정한 동작을 판정했다.
S2 도식의 실제 표시 성공은 미확인이다.

### 완료 조건 확인

선정한 4개 사례의 명시 호출, 기대 동작, 승인/중단 경계와 변경 범위 보존을 확인했다.
실제 설치 호환성은 이 단계 판정에 포함하지 않는다.

### 단계 이동 기록

2026-10-07 S2 후속 확인으로 behavioral-validation을 완료하고 cross-validation으로 이동했다.

## cross-validation (교차 검증)

### 진입 조건 확인

동작 시나리오 4개와 실제 근거가 현재 대상에 유효함을 확인했다.

### 교차 검증의 수행 여부와 판단 근거

사용자 요청으로 Claude의 독립 검토를 수행하고 Codex가 지적을 실제 대상과 원시 근거에 대조했다.

### 교차 검증 대상과 검증에 포함한 파일 및 변경 내용

기준 1bc373a -> baef202의 변경 24파일과 관련 계약을 검토했다.
검토 전후 HEAD 및 배포 소스/시험 29파일의 해시가 일치했다.

### 교차 검증의 판정 기준과 제외 범위

R1~R13과 기존 승인/회귀 계약, 스킬 개발 규격을 기준으로 했다.
실제 설치/업데이트, 새 CLI 동작 시험과 Git 반영은 교차 검토 범위에서 제외했다.

### 교차 검증 요청, 검토 결과와 후속 판단 기록

[교차 검증](validation.md#교차-검증)에 Claude 원문과 Codex 후속 판단을 작성자별로 요약했다.
대상 식별자는 source-and-evidence, 마지막 회차는 round-001이다.
검토 대상은 baef202이며 실제 CLI 2.1.283/claude-sonnet-5를 상위 실행 로그로 확인했다.
high는 호출 옵션 근거다.

### 교차 검증에서 제시된 각 지적에 대한 수용, 반박 또는 재검증 판단과 그 근거

[지적별 처리](validation.md#교차-검증)의 수용/반박/재검증 판단을 따른다.
확정 결함은 없으며 최신 공통 설계의 superseded 경계는 기존 검사로 탐지됨을 재검증했다.

### 이전 단계에서 넘긴 사항의 확인 결과와 교차 검증에서 남은 미확인 사항

S2 최초 timeout과 후속 성공 및 표시 미확인을 보존했다.
Claude의 회귀 재실행/대용량 로그 전수 열람/해시 재계산 한계는 Codex의 원문 대조와 별개로 기록했다.

### 수용한 지적에 따른 재검토와 수정 및 이후 재검증 결과

소스 수정은 없다.
기존 경계 시험과 입력 두 변형을 재검증했고 기존 기계/동작 근거를 무효화하는 결함은 없었다.

### 교차 검증을 수행하지 않은 사실이 완료 판단에 미치는 영향

해당 없음. 독립 교차 검증을 수행했다.

### 완료 조건 확인

검토 대상 동일성, 독립 검토와 항목별 후속 판단을 확인했다.
미해결 교차 검증 결함은 없다.

### 단계 이동 기록

2026-10-07 cross-validation 완료 후 compatibility-validation으로 이동했다.

## compatibility-validation (호환성 검증)

### 진입 조건 확인

PR #38의 integrate/camellia 병합과 Garden 업데이트 후 두 CLI의 3.1.0 설치/활성 및 각 28파일 동일성을 확인했다.
검증 소스 baef202와 병합 커밋 0beebac의 플러그인/등록 내용은 동일하다.

### 지원 대상 CLI와 호환성 요건 및 검증 기준의 명세서 위치

요건 정의의 지원 CLI 조건과 [설치본 호환성](validation.md#설치본-호환성)의 K1~K4를 적용했다.
최종 완료 범위는 요건 정의에 명시한 사용자 확인 이관을 따른다.

### 각 CLI의 실행 환경과 호환성 검증 결과

C1 Codex Astra/high는 K1~K4 통과다.
C2 Claude Sonnet/high는 K1/K2를 확인했고 K3/K4는 미판정이다.
실제 출력과 실행 한계는 [설치본 호환성](validation.md#설치본-호환성)에 보존했다.

### 지원 CLI의 공용 구성과 동작 확인 결과

두 CLI 모두 설치된 스킬과 관련 Markdown/템플릿에 접근했다.
각 프로젝트 11파일과 각 설치본 28파일은 시험 전후 동일했다.
공용 검사기의 실제 정상/오류 실행은 Codex에서 확인했다.

### 명세서에서 허용한 CLI별 차이와 각 차이의 근거

하네스 전용 소스나 형식 예외는 정의하지 않았다.
Claude K3/K4의 담당 이관은 지원 계약의 예외가 아니라 이번 검증 범위의 조정이다.

### 명세서의 허용 범위를 벗어난 CLI별 동작 또는 구성의 차이와 그 영향

Claude가 허용한 검사 명령 뒤에 echo를 추가하여 Bash 호출이 거부됐다.
Python 검사는 실행되지 않았다.
앞선 읽기용 ls/find는 실행됐으므로 Bash 전체 차단이나 설치본 결함으로 단정하지 않는다.

### 이전 단계에서 넘긴 미확인 사항과 의미 판단 항목의 확인 결과 및 근거

실제 설치 반영, 두 CLI의 새 세션 호출과 자료 접근 및 Codex 검사 실행을 확인했다.
Claude 검사 실행/재개 판단과 S2 표시 성공은 별도 미확인 사항으로 보존했다.

### 지원 대상 CLI별로 실행하지 못한 호환성 검증 항목과 결과를 판정하지 못한 항목 및 그 이유

C2 K3/K4는 권한 거부로 판정하지 못했고 사용자는 추가 호출을 생략한 뒤 사용자 확인으로 이관하도록 요청했다.
실제 사용량 제한 도달은 확인하지 않았다.
사용자 확인에 필요한 입력과 최초 실행 근거는 로컬에 유지한다.

### 완료 조건 확인

사용자와 조정한 이번 에이전트 검증 범위는 완료했다.
C1 K1~K4와 C2 K1/K2의 근거를 확인하고 C2 K3/K4를 사용자 확인으로 이관했다.
전체 CLI 호환성이 통과했다고 판단하지 않는다.

### 단계 이동 기록

2026-10-07 사용자 확인 이관에 맞춰 요건/검증 범위/완료 기준을 갱신한 뒤 completed로 이동했다.
기존 C2 미판정은 변경하지 않았다.

## completed (완료)

### 진입 조건 확인

기계/동작/교차 검증과 범위 조정 후 설치본 검증의 근거를 최종 대조했다.
이번 에이전트 범위 안에서 다시 실행할 검증은 없고 Claude K3/K4는 사용자에게 이관했다.

### 생명 주기의 완료 여부에 대한 판단

사용자와 조정한 범위의 생명 주기 작업을 완료했다.
Claude K3/K4의 실제 사용자 확인은 남아 있으며 전체 CLI 호환성 통과를 뜻하지 않는다.
보존 기록 작성과 커밋은 별개이며 이 완료 기록은 아직 커밋하지 않았다.

### 생명 주기의 완료 여부를 판단한 근거

최종 정본은 이 명세서와 [검증 기록](validation.md)이다.
문제/요건/설계/실제 변경/검증을 전체 대조하고, 승인 목록의 범위와 미확인을 보존했다.
R1~R13 대응은 요건 정의의 검증 표, 주요 실패와 보완은 검증 기록에 통합했다.
필수 단계와 기록 제목을 유지하면서 대화 순서, 반복 보고와 효력이 끝난 계획을 제거했다.

현재 작업 자료 360파일을 선별했다.
설계 초안, 그룹 검토, history와 기계/동작 결과의 유효한 내용을 두 보존 파일에 통합했다.
보존본의 형식/참조 및 내용 대조 후 중복 원본과 역할이 끝난 시험 사본/로그 292파일을 정리했다.
Claude 사용자 확인에 필요한 호환성 입력/근거와 독립 교차 검토 원문/근거는 로컬에 유지한다.
보존본은 이 로컬 자료나 개인 절대 경로 없이도 최종 판단을 이해할 수 있도록 작성했다.

원본과 필수 단계/기록 제목 및 R1~R13 표의 일치를 대조했다.
명세서 형식 검사와 완료 보고서 참조 검사(로컬 48 PASS, PR URL 1 SKIP)를 통과했다.
승인 범위, 주요 실패/보완과 미판정을 직접 대조하여 이관 누락과 모순이 없음을 확인했다.
사용자 확인용 자료와 교차 검토 원문/근거 68파일 및 보관 안내 1개만 로컬에 유지한다.
C2 입력/원시 근거와 다른 작성자의 검토 원문은 바이트 단위 동일성을 확인했다.
역할이 끝난 이번 작업의 시험 준비 및 기록 이관용 일회성 스크립트도 정리했다.
이번 이관으로 커밋할 파일은 이 명세서와 validation.md의 2개이며 아직 미추적 상태다.

### 완료 여부를 판단하는 시점에 남아 있는 미확인 사항과 위험

- Claude 설치본의 검사 실행과 결과에 따른 재개/차단 판단(K3/K4)은 미판정이다.
  사용자가 담당을 이관받았으므로 이번 에이전트 완료 범위에서 제외했다.
  전체 호환성 통과를 주장하려면 실제 사용자 확인 근거가 추가로 필요하다.
- S2 시험 도식의 실제 표시는 환경 제약으로 미확인이다.
  해당 시나리오는 미확인을 알리고 승인 대기에 머무는 동작을 확인했으며 표시 성공을 요구한 시험이 아니다.
  이 한계는 교차 검토 및 완료 판정에서도 유지한다.
- 외부 URL 2건은 기계 참조 검사에서 SKIP했다.
  로컬 참조 통과를 외부 링크 확인으로 확대하지 않는다.

범위 조정과 실제 미판정을 구분했으며 완료 기록의 별도 Git 반영은 아직 남아 있다.

### 완료 조건 확인

보존본의 형식/참조 및 의미 대조와 역할이 끝난 시험 자료의 정리를 마쳤다.
합의한 에이전트 완료 범위에 남은 필수 미충족 사항은 없다.
검증 범위 밖으로 이관한 Claude 확인을 통과로 바꾸지 않는다.

### 단계 이동 기록

2026-10-07 compatibility-validation -> completed.
사용자 확인 이관과 최종 기록 정리 범위를 근거로 이동했다.
