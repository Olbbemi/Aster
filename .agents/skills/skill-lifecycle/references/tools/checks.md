# 검사 스크립트 사용 가이드라인

skill-lifecycle에서 사용하는 검사기의 실행 지침이다.
에이전트가 아래 검사기 목록과 개별 안내를 읽어 실행하며, 별도 자동 실행기는 사용하지 않는다.

검사 스크립트는 대상을 읽기만 하며 대상 스킬을 실행하지 않는다.
검사 대상은 개별 안내에 따라 스킬 디렉토리 또는 작업 명세서 등으로 구분한다.
이 검사기와 안내는 내부 스킬인 skill-lifecycle의 실행 자료이며 플러그인 배포물에는 포함하지 않는다.
문서 링크는 각 문서가 있는 디렉토리를 기준으로 해석한다.

## 검사기와 적용 시점

기계 검사 단계의 검사 대상, 적용 조건과 완료 판단은
[기계 검사 단계](../stages/mechanical-validation.md)를 따른다.
그 밖의 자료 검사는 아래 실행 시점의 정본을 따른다.
구체적인 조건은 각 정본에서 관리하며 이 목록에 별도로 정의하지 않는다.

| 용도 | 스크립트 | 개별 가이드 | 실행 시점의 정본 |
| --- | --- | --- | --- |
| 기본 구조와 형식 | [check_structure.py](../../scripts/check_structure.py) | [check-structure.md](check-structure.md) | [기계 검사](../stages/mechanical-validation.md#검사-대상과-적용-조건) |
| 표준 lifecycle 명세서 형식, 단계 문서 구조 또는 템플릿 대응 확인 | [check_lifecycle_specification.py](../../scripts/check_lifecycle_specification.py) | [check-lifecycle-specification.md](check-lifecycle-specification.md) | [명세서 형식 확인](../records/specification.md#최소-형식-검사), [단계 지침 변경](../lifecycle.md#단계-정의-공통-항목) |
| 스킬 참조 연결 또는 완료 보고서의 로컬 참조 검사 | [check_references.py](../../scripts/check_references.py) | [check-references.md](check-references.md) | 일반 모드: [기계 검사](../stages/mechanical-validation.md#검사-대상과-적용-조건). 완료 보고서 모드: [정리와 보존](../records/completion-records.md#정리와-보존) |
| 시나리오 요건/계획/현재 결과의 기록 대조 | [check_scenario_records.py](../../scripts/check_scenario_records.py) | [check-scenario-records.md](check-scenario-records.md) | `plan`: [사용자 확정 전](../procedures/scenario-validation.md#사용자-검토와-확정). `results`: [결과 대조](../procedures/scenario-validation.md#결과-대조와-완료-판단) |
| 작성하거나 수정한 ASCII 도식의 문자 형식 | [check_ascii_flows.py](../../scripts/check_ascii_flows.py) | [check-ascii-flows.md](check-ascii-flows.md) | [도식 작성과 수정](../procedures/design-artifacts.md#도식-정리와-표시-확인) |
| 배포 구성 | [check_distribution.py](../../scripts/check_distribution.py) | [check-distribution.md](check-distribution.md) | [기계 검사](../stages/mechanical-validation.md#검사-대상과-적용-조건) |

## 사용 순서

1. 호출 스킬의 이름과 현재 단계 또는 검사 요청의 대상 및 범위를 확인한다.
2. [검사기와 적용 시점](#검사기와-적용-시점)에서 검사기와 적용 시점을 정하는 지침을 찾는다.
   해당 지침에 따라 이번에 확인할 항목을 선정하며 등록된 검사기 전부를 일괄 실행하지 않는다.
3. 선정한 검사기의 개별 안내를 읽고 입력, 명령과 판정 범위를 확인한다.
   호출 지침이 기존 결과 재사용을 허용하면 그 조건을 충족하는 근거를 연결하고, 나머지는 실행 대상으로 정한다.
4. 실행 대상은 개별 안내에 따라 검사하고 종료 코드와 출력 결과를 확보한다.
   여러 대상이 있으면 대상별 결과를 구분한다.
5. 아래 결과 제공 기준에 따라 이번 실행, 기존 결과 재사용 및 미실행 내역을 호출 스킬의 지침으로 전달한다.

검사기 목록과 개별 안내는 준비된 구성을 사용한다.
각 도구의 준비 여부를 별도 사전 점검 목록으로 다시 확인할 필요는 없다.
실행 중 입력 부족, 의존성 부재나 파일 누락 등이 확인되면 해당 실행의 문제로 보고하고 통과로 처리하지 않는다.

## 공통 실행 조건

Python 3.10 이상을 사용한다.
각 안내의 명령은 Aster 저장소 루트 기준이다.
다른 작업 디렉토리에서는 스크립트의 절대 경로를 사용한다.
입력 상대 경로는 호출 위치 기준이므로,
대상 경로는 절대 경로로 준비한다.
명령의 셸 변수는 설명한 실제 경로로 설정한 뒤 실행한다.

검사별 의존성은 상세 안내에서, 허용 버전은 [requirements.txt](../../scripts/requirements.txt)에서 확인한다.
필요한 라이브러리가 없으면 프로젝트의 Python 환경에 다음 명령으로 준비한다.

```bash
python3 -m pip install -r .agents/skills/skill-lifecycle/scripts/requirements.txt
```

## 결과 해석과 제공

명령의 `--json`은 대상, 검사 범위와 항목별 판정/근거를 출력한다.
생략하면 텍스트로 출력한다.
종료 코드는 `0` 적용 항목 통과, `1` 위반 발견, `2` 실행 오류/잘못된 호출/미판정이다.
오류나 미판정이 위반과 함께 있으면 `2`를 반환하므로 개별 `FAIL`도 확인한다.

- 스크립트와 대상별로 사용한 입력/명령, 실제 종료 코드, 항목별 결과와 근거를 제공한다.
  실행하지 않았으면 이유를 제공하고, stdout/stderr 등 별도 근거 자료가 있으면 그 위치를 연결한다.
- 기존 결과를 재사용했다면 원래 실행 근거와 현재도 유효하다고 판단한 이유를 제공한다.
  이번 실행과 구분하고, 호출 지침의 재사용 조건을 확인하지 못하면 검사 통과로 처리하지 않는다.
- 대상이 검사 범위에 해당하지 않는 경우와 필요한 입력/의존성이 없어 실행할 수 없는 경우를 구분한다.
- 필요한 기계 검증을 수행할 스크립트가 없거나 기존 스크립트의 검사 범위로 충족할 수 없으면, 해당 검증 항목과 부족한 내용을 확인한 시점에 사용자에게 알린다.
  - 기존 검사기의 보완 또는 새 검사기의 별도 개발이 필요함을 설명하고, 호출 스킬의 지침에 따라 후속 작업으로 정리한다.
  - 해당 검증을 통과나 검증 불필요로 처리하지 않는다.
- `SKIP`은 해당 항목의 유효성을 확인했다는 뜻이 아니다.
  `UNCHECKED`와 `ERROR`도 통과로 처리하지 않는다.
  개별 가이드의 범위와 한계를 함께 제공한다.
- 이번 호출에 적용하는 검사 항목과 실행/재사용/미실행 내역을 대조하여 빠진 대상이 없는지 확인한다.
  다른 시점에 적용할 검사기를 현재 미실행이라는 이유만으로 실패 처리하지 않는다.
- 검사 결과의 기록 위치와 형식, 작업 완료 여부, 후속 작업 및 사용자 승인은 호출 스킬의 지침을 따른다.
  스크립트의 종료 코드만으로 호출 스킬의 작업 완료를 결정하지 않는다.

통과는 각 검사기의 범위에 한정된다.
목록의 검사가 요청한 모든 검증을 대신하지 않으며,
도구가 다루지 못한 대상과 의미 판단, 실제 실행 및 설치 호환성은 호출 스킬에서 후속 판단한다.

## 관리 기준

규칙의 정본은 [스킬 내용 작성 규격](../../../../../standards/skills/skill-content.md)과
[스킬 검증 규격](../../../../../standards/skills/skill-validation.md)이다.
검사기 목록과 검사 코드는 이를 구현한다.
