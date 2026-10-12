# 교차 검증 결과

## 작성자

- 검토자: Claude (Claude Agent SDK 기반 단일 세션)
- 모델명/버전: 확인 불가.
  세션 시스템 정보에는 `claude-opus-5-5`로 표시되지만 응답 메타데이터로 직접 확인하지 못했다.
- 검토 요청: [요청](request.md)
- 검토 대상: 기준 HEAD `f6a22877d15ab2af662e900209f7251224c4d0d4`에 대한
  `work/camellia/workflow-and-script-rework` 현재 작업 트리(미커밋 수정/삭제와 미추적 신규 파일 포함)

### 전달받은 실행 정보와 직접 확인한 내용

요청에 적힌 호출 정보는 다음과 같다.
이 값은 전달받은 정보이며 검토자가 직접 관찰한 동작이 아니다.

- 환경 변수 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
- `-p`, `--model opus`, `--effort high`, `--tools Read,Write`
- 범위별 Read와 이 리뷰 한 파일의 Edit 권한, `--permission-mode dontAsk`
- `--no-session-persistence`, `--disable-slash-commands`, `--strict-mcp-config`,
  `--setting-sources project`, `--output-format json`

직접 확인한 내용은 다음과 같다.

- 이 세션에서 사용할 수 있는 도구는 Read와 Write뿐이었다.
  명령 실행, 테스트 재실행과 추가 에이전트 호출은 하지 않았다.
- 원본 소스, 기록, 요청, 설정과 메모리는 수정하지 않았다.
  쓰기는 이 `review.md` 한 파일에만 했고, 작성 후 Read로 다시 확인했다.
- 컨텍스트에서 자동 메모리 내용으로 보이는 자료는 보지 못했다.
  다만 이것은 생성/로드 차단 시험이 아니므로 환경 변수의 효과를 확인한 근거로 쓰지 않는다.
- CLI 종료 코드는 호출이 끝난 뒤에만 알 수 있으므로 이 리뷰에 적지 않는다.

## 전체 판정과 항목별 결과

전체 판정은 **조건부 적합**이다.
현재 확정된 계약을 뒤집거나 기본 사용 경로를 막는 높은 심각도 결함은 찾지 못했다.
다만 처리를 권고하는 중간 심각도 지적이 세 건 있다.

- 제품 결함 한 건(F1)
- 개발용 검사 결함 한 건(F2)
- 작업 기록 상태 한 건(R1)

낮음/참고 지적과 후속 완료 관문은 아래에 따로 정리했다.
기존 판정을 정답으로 삼지 않았다.
대상 코드와 문서를 직접 읽어 계약과 대조했다.

| 항목 | 판정 | 요약 |
| --- | --- | --- |
| 1. M1 자동 메모리 | 적합, 지적 없음 | 환경 변수는 명령 접두로 호출에만 적용된다. 전역/프로젝트 설정과 export를 바꾸지 않는다. 권한 규칙과 함께 적용하고, 설정 전달과 실제 관찰을 report/리뷰 템플릿에서 구분한다 |
| 2. M2 대화와 번들 | 적합, 지적 없음 | 아래 "M2 근거" 참고 |
| 3. M3 문서 완결성 | 적합, 제품 지적 없음 | 아래 "M3 근거" 참고 |
| 4. M4 내부 실행기 | 조건부 적합 | 시점별 C1-C14 판정, 0/1/2 집계, 정렬, 읽기 전용성은 계약과 대체로 일치한다. 격리 모드 import 실패의 종료 1 오분류(F1, 중간)와 낮음 3건(F6-F8)이 있다 |
| 5. M5 개발용 검사 | 조건부 적합 | revision/작업 트리 분리, 대상 사본 실행, M4 모듈 비재사용, checks.json 연결은 적합하다. 일부 D 사례가 대상 규칙을 분리하지 못한다(F2, 중간). 그 밖에 낮음 4건(F3-F5, F9)이 있다 |
| 6. 검증 기록 근거 | 대체로 뒷받침됨 | 확인한 원시 근거는 기록과 일치한다. 최초 실패, fixture 결함, B06 대리 호출의 구분도 논리적으로 일관된다. 다만 F2 때문에 "D 전체 통과"가 일부 규칙 보호까지 증명하지는 않는다 |

### M2 근거

다음 연결이 있고 기존 승인 경계와 충돌하지 않는다.

- workflow의 "대화와 공식 단계"
- work-bundles의 "질문의 깊이와 후속 안건", "분할 판단과 방식 선택"
- discussion/design 단계 지침과 두 템플릿

후보 제안을 설계 완료나 번들 시작 승인으로 보지 않는다.
변경 전 work-bundles에 있던 "필수 미결정을 후속 상세로 넘기지 않음" 조건은 새 절에 보존되었다.

### M3 근거

다음 연결은 적합하다.

- guidelines의 "report 작성 기준", "report 본문 정리" 시점별 표, "전체 완료 시 문서와 결과 대조"
- design-artifacts 보강, 구현/검증/QA 연결

중간 정리를 전체 재작성으로 확대하지 않는다.
과거 승인본 보존과 미검증 통과 처리 금지도 유지된다.

### 기록 상태와 후속 관문

| 구분 | 판정 |
| --- | --- |
| 기록 상태(제품 결함 아님) | R1(중간) |
| 후속 완료 관문 | G1-G4. 이 리뷰로 완료 처리하지 않는다 |

## 발견한 문제와 확인 가능한 근거

심각도 기준은 다음과 같다.

| 심각도 | 기준 |
| --- | --- |
| 높음 | 계약 위반으로 기본 사용 경로에서 잘못된 통과/차단이 발생 |
| 중간 | 현실적인 조건에서 오분류/검출 누락이 발생하거나 완료 관문을 막음 |
| 낮음 | 경계 조건, 문서/기록 정합성, 커버리지 공백 |
| 참고 | 조치 필요성 낮음 |

경로는 저장소 루트 기준이며 행 번호는 검토 시점 파일 기준이다.

### F1 (중간, 제품) 격리 모드에서 내부 실행기의 import 실패가 종료 1로 나와 "규칙 위반"과 구분되지 않음

#### 위치와 근거

- 위치: 5개 실행기의 8행.
  [check_task_start.py](../../../../../../../../plugins/Camellia/skills/code-development/scripts/check_task_start.py),
  `check_stage_entry.py`, `check_report_submission.py`, `check_review_receipt.py`, `check_task_completion.py`
- 실행기 파일은 `from _check_runtime import ...`를 모듈 최상단에서 수행한다.
- 스크립트 디렉토리를 `sys.path`에 넣지 않으므로 표준 sys.path[0] 동작에만 의존한다.
- `python3 -I`(격리 모드)나 `PYTHONSAFEPATH=1` 환경에서는 sys.path에 스크립트 디렉토리가 들어가지 않는다.
  이 경우 `ModuleNotFoundError` traceback과 함께 종료 코드 1로 끝날 것으로 판단한다.
- 이 import는 [_check_runtime.py](../../../../../../../../plugins/Camellia/skills/code-development/scripts/_check_runtime.py)
  245-293행의 `command()` 예외 처리보다 먼저 실행되므로 `runtime.*` 오류 JSON도 나오지 않는다.
- 공통 모듈 4개 중 하나가 설치본에서 빠진 경우도 같은 경로로 종료 1이 된다.

#### 계약과 회귀 근거

- [실행 계약](../../../../../../../../plugins/Camellia/skills/code-development/references/report-check-contract.md)
  301-305행은 종료 1을 "하나 이상의 검사 결과가 거짓이며 오류는 없음"으로 정의한다.
- 299행은 JSON 미보장을 "Python 자체가 시작하지 못하거나 강제 종료된 경우"로만 한정한다.
- [실행 안내](../../../../../../../../plugins/Camellia/skills/code-development/references/report-checks.md)
  176-178행도 1을 규칙 위반으로 해석하도록 안내한다.
- 제거된 기존 실행기에는 "Keep sibling modules available for direct execution, including Python -I." 주석과
  `sys.path.insert`가 있었다.
  로컬 `tracked.patch`의 삭제된 `check_completion_records.py` 앞부분에서 확인했다.
  따라서 호환 동작의 회귀이기도 하다.

#### 재현 방법과 영향

- 최소 재현 명령은 아래와 같다.
  기대 결과는 JSON과 계약상 0/1/2이다.
  의심 결과는 stderr의 ModuleNotFoundError와 종료 1이다.

  ```sh
  python3 -I -B <skill>/scripts/check_task_start.py --project-root /tmp/p --topic-dir /tmp/p/specs/a/b --json; echo $?
  ```

- `PYTHONSAFEPATH=1 python3 -B ...`로도 같은 결과가 날 것으로 판단한다.
- 문서화된 기본 명령 `python3 -B`에서는 발생하지 않는다.
- 하지만 Aster 도구 관례(`python3 -I -B`)를 따르는 에이전트나 사용자 환경 변수가 있으면 실행 오류가 "규칙 위반"으로 읽힐 수 있다.
  report-checks.md는 종료 코드와 항목을 함께 읽게 하지만, 항목 JSON이 없는 1을 어떻게 처리할지는 정하지 않았다.
- M5 R 사례는 `-B`만 사용하고, in-process 호출은 sys.path에 스크립트 디렉토리를 직접 넣는다.
  그래서 이 경로를 검출하지 못한다.
  관련 위치는 [check_support.py](../../../../../../../../tools/tests/skills/code-development/check_support.py) 244, 255행이다.

#### 개선 방향

실행기 최상단에서 `Path(__file__).resolve().parent`를 sys.path에 넣어 기존 호환을 복원한다.
필요하면 import 실패도 종료 2로 바꾸는 최소 부트스트랩을 둔다.
R 사례에 `-I`와 공통 모듈 누락 사본을 추가한다.
계약을 바꾸지 않는다면 계약 299행의 "시작 실패" 범위에 import 실패의 종료 코드 해석을 명시하는 방법도 있다.
어느 쪽이든 계약을 먼저 갱신한다.

### F2 (중간, 개발용 검사) 일부 D 사례가 여러 C10 조건을 함께 바꿔 대상 규칙의 회귀를 검출하지 못함

#### D19.duplicate_name

- 위치: [check_report_rules.py](../../../../../../../../tools/tests/skills/code-development/check_report_rules.py) 321-328행
- fixture 행 형식은 `check_support.py` 446행의 `| {name} | ... | {name} | [결과](...) |`이다.
  묶음 이름과 디렉토리 셀에 같은 문자열이 들어간다.
- 따라서 `"| 02-store |" -> "| 01-api |"` 치환은 두 셀을 모두 바꾼다.
- 그 결과 `_check_content.py`의 다음 항목이 함께 실패한다.
  - `C10.bundle_unique`(331행)
  - `C10.directory_unique`(347행)
  - `C10.result_scope`(356행)
  - `C10.registration`(370행)
- 사례는 C10 범주의 fail만 요구한다.
  그래서 묶음 이름 중복 판정을 제거해도 통과한다.

#### D20.directory.{001-extra,00-extra,03-Upper}

- 위치: 같은 파일 342-355행
- 미등록 디렉토리라 `C10.registration`(370행)이 항상 실패한다.
- 따라서 `C10.directory_name`(363행)을 제거해도 통과한다.
- 01-extra만 등록한 뒤 `C10.number_unique`를 직접 확인한다.

#### 기준 위반과 개선 방향

- [상세 설계](../../../structure-design/developer-checks.md) 102행은 위반 사례를 "조건 하나 변경" 기준으로 둔다.
- 126-127행은 다른 규칙만 실패해 종료 1이 된 경우 통과하지 않아야 한다고 정의한다.
  위 사례는 이 기준에 맞지 않는다.
- 재현 방법(사고 실험): `_check_content.py` 331행을 항상 참으로 바꾸거나 363행을 제거한 뒤 `check_report_rules.py`를 실행한다.
  기대 결과는 D19.duplicate_name 또는 D20.directory.* 실패다.
  의심 결과는 통과다.
- 개선 방향: 이름만 바꾸는 치환(첫 셀만 대상)과 등록된 잘못된 디렉토리명 행을 사용한다.
  D20.directory.01-extra처럼 `C10.bundle_unique`, `C10.directory_name` 결과 ID를 직접 확인한다.

### F3 (낮음, 개발용 검사) R02.duplicate_json이 M4 계약에 없는 요구를 강제함

- 위치: [check_runtime_contract.py](../../../../../../../../tools/tests/skills/code-development/check_runtime_contract.py) 69-75행.
  특히 72행 `("duplicate_json", ["--json"])`가 해당한다.
- M4 계약 45행은 "같은 단일 값 옵션의 중복"만 입력 오류로 정한다.
- 상세 설계 194행 R02는 이를 "중복 옵션" 전체로 넓혀 적었다.
- 현재 M4 구현(`_check_runtime.py` 262-269행)은 `--json` 반복도 오류로 처리하므로 결과는 일치한다.
  하지만 근거가 계약이 아니라 검사 코드와 개발 설계에만 있다.
- 개선 방향: 계약에 "모든 옵션의 중복은 입력 오류"를 명시하거나 해당 사례를 제거한다.

### F4 (낮음, 계약/설계 정합) "종속 검사 불가"의 오류/위반 분류가 계약, 설계표와 코드 사이에서 일관되게 정의되지 않음

#### 설계표와 사례 기대값의 차이

- 상세 설계 223행 D02는 "같은 작업 중복 H2, 필수 필드 중복/누락, 중복 단계"를 F(C2)(종료 1)로 정의한다.
- 226행 D05는 "타입/상태 위반"을 F(C4)로 정의한다.
- 실제 사례(`check_report_rules.py` 75-83행, 115-121행)는 duplicate_task, missing_stages, duplicate_stages,
  duplicate_stage, status_type, status_unknown, base_type, missing_base에 종료 2를 기대한다.
- 코드는 `C2.stage_dependency`(`_check_records.py` 130-131행)와 `C7.state_dependency`/`C5.dependency`를 error로 낸다.

#### 코드 안의 분류 차이

- 같은 성격의 C6 영역 누락에 따른 `C7.section_dependency`/`C9.section_dependency`는 fail로 처리된다.
  위치는 `_check_content.py` 66-67행과 181-183행이다.
- 계약 108, 305, 338-340행은 "파싱 후 종속 검사 불가"를 오류로 두지만 어느 누락이 이에 해당하는지 정하지 않는다.

#### C13 위치 조건의 이중 정의

- 리뷰 위치는 계약 55-56행에서 입력 조건이고, 216행 C13에서는 규칙 조건이다.
- 수정 후 `check_review_receipt.py` 16-18행이 입력 오류로 먼저 중단한다.
  그래서 `_check_content.py` 389-390행의 `C13.location`은 수신 경로에서 거짓이 될 수 없다.

#### 영향과 개선 방향

- 두 분류 모두 푸시를 차단하므로 운영 영향은 작다.
- 하지만 같은 정본을 읽는 사람이 1과 2를 다르게 예상할 수 있다.
- 개선 방향: 계약에 "선택 manifest/stages/metadata를 해석할 수 없어 종속 검사를 못 하면 2, report 내부 고정 영역 누락은 1"처럼 경계를 명시한다.
  D02/D05 설계표와 C13 위치 조건의 정본을 한 곳으로 정리한다.

### F5 (낮음, 개발용 검사) fixture 준비 실패가 검사 준비 오류(2)가 아니라 대상 위반(1)으로 분류됨

- 위치: `check_support.py` 41-51행(`Results.case`), 78-80행(`require`), 373-386행(`Fixture.replace`/`section`)
- fixture 변형 대상 문자열이 없을 때 `require`가 AssertionError를 일으켜 kind "violation", 종료 1이 된다.
- [개발용 검사 안내](../../../../../../../../tools/references/code-development-tests.md) 150-154행은
  "검사 준비" 실패를 종료 2로 정의한다.
- 영향: 검사 문구나 fixture가 바뀐 경우를 대상 실행기의 계약 위반으로 오인할 수 있다.
  푸시 차단 여부는 같다.
- 개선 방향: fixture 준비 단계는 OSError 계열의 별도 예외로 올려 error로 분류한다.

### F6 (낮음, 제품, 불확실) 번호나 묶음표 힌트가 없는 심볼릭 링크 하위 디렉토리를 조용히 건너뜀

- 위치: [_check_records.py](../../../../../../../../plugins/Camellia/skills/code-development/scripts/_check_records.py) 274-278행
- `by_name`이 아닌 심볼릭 링크 디렉토리는 오류나 미적용 항목 없이 `continue`한다.
- 계약 84-85행은 "직접 단계 report 후보를 포함한 디렉토리"도 번들 후보로 둔다.
  92-93행은 "필수 범위가 그 경로에만 있어 확인하지 못하면 오류"로 정한다.
- 제거된 기존 report-checks.md 안내는 "하위 심볼릭 링크 디렉토리는 순회하지 않고 미판정으로 알린다"였다.
  로컬 `tracked.patch` 593행(report-checks.md의 삭제된 줄)에서 확인했다.
- 바로 아래 항목 열거는 재귀 순회가 아니므로 계약상 허용 범위인지 판단이 갈린다.
- 최소 재현 방법:
  1. 작업 루트에 `extra -> /tmp/x` 링크를 만든다(`/tmp/x/implementation-report.md` 포함).
  2. `check_report_submission.py`나 `check_task_completion.py`를 실행한다.
  3. 기대 결과는 오류(2) 또는 C10 위반이다.
     의심 결과는 해당 경로에 대한 항목 없이 링크 이외 결과만으로 판정되는 것이다.
- 개선 방향: 비번호 심볼릭 링크 디렉토리도 `runtime.directory` 오류나 명시적 미적용 항목으로 보고한다.
  어느 쪽으로 할지 계약에서 정한다.

### F7 (낮음, 계약 공백) `--help`를 다른 인자와 함께 주면 결과 없이 종료 0

- 위치: `_check_runtime.py` 257-259행, 281-283행
- 계약 43-46행은 `--help`만 준 경우만 정의한다.
- 현재 구현은 `--project-root ... --help --json`에서도 사용법 텍스트와 종료 0을 반환한다.
- report-checks.md 179행이 "help의 0은 통과가 아님"을 안내하지만, 종료 코드만 보는 호출자는 통과로 오인할 수 있다.
- 개발용 `check_support.py` 106-108행과 119-121행도 같은 형태다.
- 개선 방향: 혼합 사용을 입력 오류로 정하거나 현재 동작을 계약에 명시한다.

### F8 (낮음, 제품, 불확실) manifest 작업 식별이 제목 링크가 아니라 H2 절 전체 링크를 사용함

- 위치: `_check_records.py` 84-91행
- 선택 H2 절 본문 어디에든 작업 디렉토리 링크가 있으면 그 절을 선택 후보로 센다.
- guidelines 204행은 작업 주제 제목을 실제 디렉토리 링크로 정의한다.
- 계약 68-70행 "선택한 작업으로 연결되는 H2 항목"은 범위를 정하지 않았다.
- 재현 방법:
  1. 다른 작업 H2의 본문이나 reference_reports에 `[로그인 작업](로그인%20작업/)` 같은 디렉토리 링크를 넣는다.
  2. 기대 결과는 선택 작업의 정상 식별이다.
  3. 의심 결과는 `C2.registration` 실패와 `C2.selection` 오류, 종료 2다.
- reference_reports는 보통 파일을 링크하므로 실제 발생 가능성은 낮다.
- 개선 방향: 제목 inline 링크만 사용하도록 계약과 코드를 함께 정한다.

### F9 (낮음, 문서 배치) 배포 문서와 지속 안내에 개발 이력과 일회성 시험 결과가 섞임

배포 스킬 문서에 Aster 내부 작업 맥락이 남아 있다.

| 위치 | 남아 있는 내용 |
| --- | --- |
| report-checks.md 7-11행("제공 상태") | "기존 검사 스크립트를 제거하고 ... 새로 구현했다" |
| 계약 5-6행 | "실행 코드와 의존성 목록을 ... 구현했다" |
| 계약 344-346행 | "후속 구현을 확인할 기준이며 ... M5의 테스트 코드 설계가 아니다" |

소비자에게는 의미가 없는 Aster 내부 작업 맥락(M5, 후속 구현)이다.

개발용 지속 안내 code-development-tests.md에도 일회성 검증 결과가 들어 있다.

- 9-13행: "정적/실행 검사 ... 실제 로컬 pre-push 연결을 검증했다"
- 119행: "이번 개편 검증에서 각 실행기의 60초 이내 실행 ... 을 확인했다"

[저장소 배치 규격](../../../../../../../../standards/repository-layout.md) 150행과 154행은 tools 안내에
목적/입력/실행/해석/한계를 두고 실제 시험 결과와 작업 기록은 두지 않도록 정한다.

개선 방향: 제공 상태는 현재 사실(5개 실행기 제공)만 남기고 이력과 검증 결과는 records의 정본으로 옮긴다.

### R1 (중간, 작업 기록 상태, 제품 결함 아님) 명세서의 단계 표시와 완료 판정 문구가 실제 수행 기록과 충돌하고 낡은 문장이 남음

#### 위치와 근거

- 위치: [명세서](../../../specification.md)
- 프론트매터 `current_stage: problem-definition`(5행)이다.
- requirements-definition, existing-configuration-review, structure-design, implementation과 그 이후 절에는
  실제 요건 정의, 기존 구성 확인, 구조 설계와 구현/검증 결과가 상세히 기록되어 있다.
- 하지만 각 절의 완료 조건은 "미판정. 해당 단계 작업을 수행하지 않았다"이다(460, 541, 675행 등).
- 다음 문장들은 이후 기록과 어긋나는 낡은 서술이다.

| 행 | 낡은 서술 | 어긋나는 이후 기록 |
| --- | --- | --- |
| 449-450 | "M4의 코드 구현은 마쳤으며 실제 검증이 남아 있다" | 454행과 validation.md의 1-3번 통과 |
| 447-448 | M1 실제 시험과 M2/M3 시험 조건을 미정으로 둠 | B01-B07 수행 |
| 487 | "새 검사 통과를 주장하지 않는다" | 642행의 실행 검증 통과 |
| 571 | "검증 통과를 주장하지 않는다" | 642행의 실행 검증 통과 |
| 536 | "M1 적용은 동작 검증에서 확인할 사항" | B07 수행 |

#### 영향과 개선 방향

- 요청 19-21행의 설명대로 부분 구현/검증 승인 아래의 의도된 기록 상태다.
  제품 결함은 아니다.
- 하지만 생명 주기 단계 전이와 완료 기록 정리 전에 반드시 해소해야 하는 관문이다.
- 다른 세션이 이 명세만 보고 현재 상태를 판단하면 혼동할 수 있다.
- 개선 방향: 선행 단계 정리 때 각 절의 "완료 조건 확인"을 실제 수행/미수행으로 다시 쓴다.
  낡은 미확인 문장은 현재 결과와 링크로 갱신한다.
  단계 전이는 소급하지 않고 기록 규칙대로 처리한다.

### 참고 (조치 선택)

- I1. M4의 앵커 계산은 L 검사의 `aster-markdown-headings-v1` 정책(skill-validation.md 71-77행)과 세부적으로 다르다.
  - `_check_markdown.py` 249-270행은 명시 id를 제목 번호 계산 집합에 함께 넣는다.
  - 53-54행에서 Setext 제목 줄바꿈을 `\n`으로 남겨 단어가 붙는다.
  - 136-143행에서 인용문 안 제목의 앵커를 수집하지 않는다.
  - 소비자 C11은 계약 229-233행이 정본이고 그 문구가 이 경우들을 정하지 않으므로 결함으로 확정하지 않는다.
  - 두 정책을 맞출지는 계약에서 정한다.
- I2. C12 닫는 구분자 판정은 `_check_content.py` 217행에서 `str.splitlines()` 줄 수를 쓴다.
  - U+2028/U+2029가 도식 안에 있으면 닫힌 fence도 미닫힘으로 잘못 판정될 수 있다.
  - 실제 발생 가능성은 매우 낮다.
- I3. 비기본 stages 작업에 번호 디렉토리가 있으면 `overall`이 필수 단계를 공통 discussion/design으로 줄인다.
  - 근거: `_check_content.py` 283-286행과 456-465행
  - 단계 사슬이 끊기면 C5가 위반을 잡으므로 거짓 통과로 이어지는 경로는 찾지 못했다.

### 후속 완료 관문 (결함 아님, 이 리뷰로 완료 처리하지 않음)

- G1. Camellia 플러그인 소스가 바뀌었지만 `plugins/Camellia/.claude-plugin/plugin.json`은 변경 목록에 없다.
  - validation.md 126행은 pre-push 시험 fixture에서만 버전을 올려 버전 관문을 통과시켰다.
  - 실제 푸시 전에는 버전 결정이 필요할 것으로 보인다.
  - `check_plugin_versions.py`는 읽지 않았다.
- G2. 작업 트리에 미추적 `records/plugins/Camellia/code-development/outline-first-development/` 문서 3개가 있다.
  - 요청 13행상 승계 대상이 아니다.
  - 이번 커밋 범위에서 제외하거나 별도 처리할지를 커밋 전 검토에서 정해야 한다.
  - 내용은 읽지 않았다.
- G3. 설치본 호환성, 커밋 전 검토와 커밋은 요청 62-63행에 따라 별도다.
- G4. 위 F1-F9와 R1의 수용/반박과 재검증은 원본 작성자가 사용자와 합의해 처리한다.

### 검증 기록 1-4번 근거 대조 (요청 항목 6)

#### 최초 실패

로컬 `validation/check_report_rules-round-1.json`에서 실패 사례를 확인했다.

| 실패 사례 | 관찰 결과 |
| --- | --- |
| `D15.evidence.empty_code`(+legacy) | 기대 1, 실제 0 |
| `D26.wrong_input_location` | 기대 2, 실제 1 |

나머지 항목은 통과였고 최상위 `passed: false`였다.
`round-2.json`에서는 모든 항목과 최상위 결과가 `passed: true`였다.
validation.md 93-101행의 서술과 일치한다.
310개 항목 수는 직접 세지 않았다.

#### B06 상위 대리 호출

로컬 `behavioral-validation/B06/`의 세 파일을 확인했다.

- `parent-review-command.txt`: `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, Read/Edit 개별 경로, dontAsk 등이 명령에 있다.
- `parent-execution.json`: exit 0, 변경 파일이 리뷰 하나다.
- `parent-review.json`: `modelUsage`가 `claude-opus-5-5`, `permission_denials: []`, `is_error: false`다.

기록의 "상위 호출 성공, 실제 모델 확인"을 뒷받침한다.

확인하지 못한 부분은 다음과 같다.

- 자식의 EAI_AGAIN 실패 원문과 자식 명령의 동일성은 해당 파일을 읽지 않아 확인하지 못했다.
- 대리 호출 명령의 Read 경로는 `plugin/Camellia/...`(단수)다.
  사례 프로젝트 배치를 확인하지 못해 실제 템플릿 경로와 맞는지 판단하지 못했다.
- parent-review.json의 `duration_ms`는 약 113초, parent-execution.json의 시작~종료 관찰 간격은 약 180초다.
  두 값은 측정 대상이 달라 모순으로 보지 않았다.

#### 원시 자료를 읽지 않은 사례

B01 초기화 실패, B05 fixture 준비 결함과 B07 대조는 원시 자료를 읽지 않았다.
기록 안의 구분 자체는 다음 점에서 논리적으로 일관된다.

- 실패 case 보존
- 재시험 1회 한도
- 스킬 소스 미수정
- 대리 호출 승인의 별도 표기

#### 결론의 한정

정형 결과는 기록대로 통과다.
하지만 F2 때문에 "C1-C14 위반 검출 확인"은 C10의 묶음 이름 중복과 디렉토리명 규칙에 대해서는 증명되지 않는다.

다음 사례도 없다.

- D18의 handoff 분기
  - 단일 플로우 비최종 QA의 handoff 거부
  - verification handoff/기존 qa_handoff 허용
- D07의 base-report 파일 부재 E
- D10의 기존 형식 다른 bundle 선행 거부
- D15의 예시 속 라벨 오인

따라서 해당 분기는 코드 대조로만 판단했다.
코드는 계약과 일치한다고 보았다(`_check_content.py` 199-203행, `check_stage_entry.py`/`_check_runtime.py` 235-237행).

## 확인하지 못한 사항

### 실제로 읽은 범위

#### 요청과 기록

- 요청 전체, 로컬 `cross-validation/round-001/target-state.json` 전체
- `tracked.patch` 1-1049행. 삭제된 Python 본문 대부분은 읽지 않았다.
- 명세서 전체, 상세 설계 전체, validation.md 전체, behavioral-validation.md 전체

#### M4 배포 자료

- Python 9개 전체와 requirements.txt
- report-check-contract.md, report-checks.md, guidelines.md(1-812행), work-bundles.md, workflow.md, SKILL.md
- review-execution.md, legacy-records.md, deferred-work.md, stages/qa.md, stages/discussion.md
- review-template.md, deferred-item-template.md

#### M5 개발 자료

- Python 7개 전체와 checks.json
- code-development-tests.md, skill-pre-push.md

#### 공용 연결과 규격

- `tools/scripts/git/pre-push`, `operations/check_push.py`, `tools/tests/git/test_check_push.py`
- skill-content.md, skill-validation.md, repository-layout.md 전체
- `.github/git-workflow.md`는 1-80행만 읽었다.

#### 원시 근거

- `check_report_rules-round-1.json`, `check_report_rules-round-2.json`
- B06의 `parent-review-command.txt`, `parent-execution.json`, `parent-review.json`

### 읽지 않았거나 일부만 읽은 범위

#### 배포 스킬 자료

- stages/design.md, implementation.md, verification.md, design-artifacts.md는 변경 diff만 대조했고 전문은 읽지 않았다.
- discussion/design/implementation/verification/qa 템플릿 전문도 읽지 않았다.
- model-selection.md는 읽지 않았다.

#### 규격과 운영 자료

- skill-layout.md, work-data.md, git-workflow.md의 나머지(pre-push 절 포함)는 읽지 않았다.
- `check_plugin_versions.py`, `tools/requirements.txt`, 플러그인 manifest는 읽지 않았다.
- README.md는 변경 diff만 대조했다.

#### 원시 자료

- `check_runtime_contract` 원시 결과, `integration*.json`, `timeout-recheck.json`
- B01-B05, B07의 사례 디렉토리와 B06 자식 실행 원시 자료
- `generated-paths.json`, 감사 JSON

### 수행하지 않은 확인

- 테스트, 검사기와 pre-push 재실행은 요청 범위 밖이므로 하지 않았다.
  F1, F6, F8의 실제 결과와 F2의 사고 실험 결과는 미확인이며 위에 적은 최소 재현으로 확인해야 한다.
- 설치본 호환성과 실제 메모리 차단은 검토자가 직접 관찰하지 않았다.
- 외부 URL과 공식 문서의 현재 내용도 확인하지 않았다.
- 원시 이벤트의 해시 대조와 사례별 전후 스냅샷은 확인하지 않았다.
