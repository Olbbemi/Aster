# 검사 호출 매핑

이 파일은 호출 스킬별로 사용할 검사 스크립트, 개별 가이드와 실행 시점을 정하는 지침을 연결한다.
호출 스킬의 지침에서는 [가이드라인](guidelines.md)을 통해 이 파일에 접근한다.
실행 절차와 결과 처리는 가이드라인을 따르며, 아래 링크는 이 파일이 있는 디렉토리 기준이다.
등록된 검사기의 일괄 실행 목록이나 자동 실행 설정으로 사용하지 않는다.

## skill-lifecycle

기계 검사 단계의 검사 대상, 적용 조건과 완료 판단은
[기계 검사 단계](../.agents/skills/skill-lifecycle/references/stages/mechanical-validation.md)를 따른다.
그 밖의 자료 검사는 아래 실행 시점의 정본을 따른다.
구체적인 조건은 각 정본에서 관리하며 이 목록에 별도로 정의하지 않는다.

| 용도 | 스크립트 | 개별 가이드 | 실행 시점의 정본 |
| --- | --- | --- | --- |
| 기본 구조와 형식 | [check_structure.py](scripts/validation/check_structure.py) | [check-structure.md](references/check-structure.md) | [기계 검사](../.agents/skills/skill-lifecycle/references/stages/mechanical-validation.md#검사-대상과-적용-조건) |
| 표준 lifecycle 명세서 형식, 단계 문서 구조 또는 템플릿 대응 확인 | [check_lifecycle_specification.py](scripts/validation/check_lifecycle_specification.py) | [check-lifecycle-specification.md](references/check-lifecycle-specification.md) | [명세서 형식 확인](../.agents/skills/skill-lifecycle/references/specification.md#최소-형식-검사), [단계 지침 변경](../.agents/skills/skill-lifecycle/references/lifecycle.md#단계-정의-공통-항목) |
| 스킬 참조 연결 또는 완료 보고서의 로컬 참조 검사 | [check_references.py](scripts/validation/check_references.py) | [check-references.md](references/check-references.md) | 일반 모드: [기계 검사](../.agents/skills/skill-lifecycle/references/stages/mechanical-validation.md#검사-대상과-적용-조건). 완료 보고서 모드: [정리와 이관](../.agents/skills/skill-lifecycle/references/completion-records.md#정리와-이관) |
| 시나리오 요건/계획/현재 결과의 기록 대조 | [check_scenario_records.py](scripts/validation/check_scenario_records.py) | [check-scenario-records.md](references/check-scenario-records.md) | `plan`: [사용자 확정 전](../.agents/skills/skill-lifecycle/references/scenario-validation.md#사용자-검토와-확정). `results`: [결과 대조](../.agents/skills/skill-lifecycle/references/scenario-validation.md#결과-대조와-완료-판단) |
| 작성하거나 수정한 ASCII 도식의 문자 형식 | [check_ascii_flows.py](scripts/validation/check_ascii_flows.py) | [check-ascii-flows.md](references/check-ascii-flows.md) | [도식 작성과 수정](../.agents/skills/skill-lifecycle/references/design-artifacts.md#도식-정리와-표시-확인) |
| 배포 구성 | [check_distribution.py](scripts/validation/check_distribution.py) | [check-distribution.md](references/check-distribution.md) | [기계 검사](../.agents/skills/skill-lifecycle/references/stages/mechanical-validation.md#검사-대상과-적용-조건) |
