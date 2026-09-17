---
name: code-development
description: |
  신규 코드 개발, 기존 기능 개선/변경, 버그 수정과 리팩터링 요청에 사용한다.
  개발 요청을 구체화하고 설계, 코드와 테스트 작성, 검증 및 사용자 참여 QA를 단계별 report로 연결한다.
  기존 작업의 선행 report와 승인 근거를 확인하여 필요한 단계부터 시작하거나 진행 중인 개발 작업을 재개할 때도 사용한다.
---

# Code Development

## 목적과 적용 범위

신규 개발, 기존 기능 개선/변경, 버그 수정과 리팩터링을 논의부터 사용자 참여 QA까지 연결한다.
이번 개발에 필요한 분석과 TDD 테스트 작성은 포함하며, 코드 분석만 수행하거나 기존 테스트만 별도로 보강하는 작업은 구분한다.

다른 스킬이나 분석 자료를 필수로 요구하지 않으며, 언어와 저장소 구성 및 빌드 도구는 프로젝트의 요구와 기존 환경에 맞게 정한다.
Codex와 Claude에서 같은 절차를 사용하며 실행 도구의 차이는 허용한다.

## 입력과 산출물

- 개발 요청, 대상 프로젝트와 현재 코드/테스트를 확인한다. 중간 단계부터 시작하거나 재개하려면 필요한 선행 report와 승인 근거가 있어야 한다.
- 호출 시점 cwd의 `.code-dev-registry.json`에서 주제와 report 저장 루트를 확인한다. 입력 부족, 선택 유지와 오류 처리는 [등록 지침](references/guidelines.md#스킬-호출-시-등록-정보-확인)을 따른다. 필요한 입력과 경로를 확인하기 전에는 이에 의존하는 report 작업을 진행하지 않는다.
- 코드와 테스트는 개발 대상에, report와 `freight-manifest.md`는 선택한 주제의 등록 루트 아래에 남긴다. 실제 결과, 근거, 미확인 범위와 다음 작업에 필요한 내용을 연결한다.

## 시작과 진행

1. [workflow](references/workflow.md)를 읽고 등록 정보와 기존 기록을 확인하여 사용자와 회차 및 현재 단계를 정한다. 필요한 선행 report나 승인 근거가 없으면 [진입 확인](references/guidelines.md#다음-단계-진입-시-선행-report-확인)에 따라 해당 단계 작업을 차단한다.
2. workflow에서 연결한 현재 단계 지침과 작업 조건에 해당하는 상세 지침을 읽고 수행한다. 실제 적용할 단계 목록과 순서는 해당 회차 manifest의 `stages`로 확인한다.
3. 연결된 템플릿으로 report를 작성하고 결과와 인계 사항을 정리한다. workflow의 흐름에 따라 필요한 교차 검증, 완료 확인과 사용자 승인을 거친 뒤 다음 단계나 종료로 연결한다.

## 항상 지킬 경계

- [상호 확인 규칙](references/guidelines.md#상호-확인과-체크리스트-갱신)에 따라 항목별 사용자 확인과 근거 대조 후에만 체크한다. 포괄 위임, 무응답이나 에이전트 판단을 승인으로 간주하지 않는다.
- 작성과 검증의 내부 작업은 에이전트가 수행하고 QA는 사용자와 함께 진행한다. 단계 종료, 합의 변경과 리뷰 지적 처리는 해당 사용자 확인 절차를 따른다.
- [SDD 경계](references/guidelines.md#sdd와-설계-및-구현의-경계)에 따라 명세를 기준으로 구현하고 검증한다. 명세 변경이 필요하면 해당 선행 단계에서 합의하고 먼저 갱신한다.
- [테스트 작성 기준](references/stages/implementation.md#코드와-테스트-작성-기준)과 [실행 기준](references/guidelines.md#테스트-실행과-재검증)을 따른다. TDD 수행이나 테스트 통과만으로 품질과 확인 범위가 충분하다고 판단하지 않으며, 실패/미실행/판정 불가와 제외를 구분한다.
- 필수 규칙과 충돌하는 요청은 [규칙 위반 대응](references/guidelines.md#공통-규칙-위반-대응)에 따라 설명하고 처리하며, 정해진 중단 조건을 적용한다.
- 커밋, 푸시, 배포는 별도 요청 없이는 제안하거나 실행하지 않는다. [변경 권한](references/guidelines.md#승인-대기-중-보완과-변경-권한)과 단계 승인을 구분한다.

## 자료를 읽는 기준

이 파일의 상대 경로는 SKILL.md가 있는 디렉토리를 기준으로 한다.

| 자료 | 읽거나 사용하는 조건 |
| --- | --- |
| [references/workflow.md](references/workflow.md) | 시작/재개 시 진행 흐름과 필요한 지침의 연결을 읽는다. 기본 단계 목록은 이 문서에서 관리한다. |
| [references/guidelines.md](references/guidelines.md) | 공통 적용과 자료 사용 기준을 확인하고, 등록/기록/승인/회귀 등 현재 작업에 해당하는 절을 읽는다. |
| [references/ai_agents/model-selection.md](references/ai_agents/model-selection.md) | 설계에서 구현용 권장 조합을 논의하거나 교차 검증의 모델을 선택할 때 읽는다. 구현 중 권장 조합의 조정이 필요할 때도 참조한다. |
| [references/ai_agents/review-execution.md](references/ai_agents/review-execution.md) | 교차 검증을 수행하기로 한 경우 상대 CLI의 호출과 결과 확인에 사용한다. |
| references/stages/ | 현재 단계 지침을 읽는다. 다른 단계는 필요한 입력이나 기준을 확인할 때만 참조한다. |
| assets/stage_reports/ | 해당 단계 report를 작성할 때 연결된 템플릿을 사용한다. 실제 결과는 원본 템플릿에 기록하지 않는다. |
| [assets/review_reports/review-template.md](assets/review_reports/review-template.md) | 교차 검증을 수행하는 검토자가 결과 파일을 작성할 때 사용한다. 수행 조건과 절차는 guidelines의 교차 검증 지침을 따른다. |
