# 교차 검증 결과

## 작성자

- 검토자: Claude (Claude Agent SDK 기반 단일 세션)
- 모델명/버전: 확인 불가.
  세션 시스템 정보에는 `claude-opus-5-5`로 표시되지만 응답 메타데이터로 직접 확인하지 못했다.
- 검토 요청: [요청](request.md)
- 검토 대상: 기준 HEAD `f6a22877d15ab2af662e900209f7251224c4d0d4`의
  `work/camellia/workflow-and-script-rework` 현재 작업 트리(미커밋 수정/삭제와 미추적 신규 파일 포함)
- 이전 회차: [1차 원문 리뷰](../round-001/review.md), [1차 후속 판단](../round-001/resolution.md)

### 전달받은 호출 정보와 직접 확인한 내용

요청 43-46행의 호출 정보는 다음과 같다.
이 값은 전달받은 정보이며 검토자가 직접 관찰한 동작이 아니다.

- 이 호출에만 적용한 환경 변수 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`
- `--model opus`, `--effort high`, Read/Write, 지정 경로 읽기와 이 리뷰 한 파일 쓰기
- `--permission-mode dontAsk`, `--no-session-persistence`, `--disable-slash-commands`
- `--strict-mcp-config`, `--setting-sources project`, `--output-format json`

직접 확인한 내용은 다음과 같다.

- 이 세션에서 사용할 수 있는 도구는 Read와 Write뿐이었다.
  명령 실행, 테스트/검사기 재실행과 추가 AI 호출은 하지 않았다.
- 원본 소스, 계약, 이전 리뷰, 요청과 설정은 수정하지 않았다.
  쓰기는 이 `review.md` 한 파일에만 했고 작성 후 Read로 다시 확인했다.
- 공용 접근 경로 `~/.local/share/aster/` 아래의 원시 자료 읽기는 권한 설정으로 거부되었다.
  [작업 데이터 규격](../../../../../../../../standards/work-data.md)상 그 링크의 대상인 저장소 `data/` 경로로 같은 파일을 읽었다.
  로컬 `target-state.json`도 원시 자료를 `data/cargo/...` 경로로 기록한다.
- 컨텍스트에서 자동 메모리 내용으로 보이는 자료는 보지 못했다.
  이것은 차단 시험이 아니므로 환경 변수 효과의 근거로 쓰지 않는다.
- CLI 종료 코드는 호출이 끝난 뒤에만 알 수 있으므로 이 리뷰에 적지 않는다.

## 전체 판정과 항목별 결과

전체 판정은 **조건부 적합**이다.

1차 지적 F1/F3/F8은 현재 계약과 구현이 대응하며 보호 사례도 지적한 경로를 직접 확인한다.
F2/F4/F5/F9는 지적한 핵심은 해소되었고 잔여 사항은 낮음/참고 수준이다.
I2의 U+2028 오판정은 해소되었다.
다만 같은 수정이 파일 끝 LF가 없는 미닫힘 도식을 닫힌 것으로 판정하는 새 거짓 통과(N1, 중간)를 만든다.

| 항목 | 판정 | 요약 |
| --- | --- | --- |
| 1. M4 Python 9개와 requirements.txt | 조건부 적합 | 부트스트랩, 옵션 중복, 제목 링크 선택은 계약과 일치한다. N1(중간)과 N2(낮음)가 있다 |
| 2. M5 Python 7개와 checks.json | 대체로 적합 | 등록은 5개 실행기만 연결한다. C10/R09/R13 보호 사례는 지적 경로를 검출한다. N3(낮음)과 참고 P1이 있다 |
| 3. 1차 지적 F1-F9/I2 | 아래 표 | 이전 판정은 정답으로 쓰지 않았고 현재 코드와 정본을 먼저 대조했다 |
| 4. 정형 결과 마지막 절 | 확인한 범위에서 일치 | 항목 수, 통과, 19개 조합과 변이 결과는 원시 JSON과 일치한다. 실행 시간, 실행 옵션과 변이 내용은 원시 근거가 없다 |
| 5. F6/F7/I1/I3 | 새로 확정한 결함 없음 | 새 근거가 없어 다시 판정하지 않았다 |

### 1차 지적별 독립 판정

| ID | 현재 판정 | 근거 요약 |
| --- | --- | --- |
| F1 | 해소 | 계약 19-22행은 `-I`/`-P`/`PYTHONSAFEPATH` 지원을 계약 밖으로 둔다. 308-312행은 첫 공통 모듈 로딩 실패도 종료 2와 정형 결과로 정한다. 5개 진입점 8-43행의 비상 출력이 이를 구현한다. 명시 인자, 텍스트/JSON, null 버전을 보존한다. R09.internal 19개가 실제 프로세스로 확인한다. 잔여는 참고 P2/P3 |
| F2 | 해소, 참고 잔여 | D19.duplicate_name은 첫 셀만 바꾸고 `C10.bundle_unique` fail을 직접 요구한다. D20.directory.*는 정형 표에 등록하므로 `C10.registration`이 실패를 대신하지 못한다. 01-extra는 `C10.number_unique`를 요구하고, 나머지는 모든 실패가 `C10.directory_name`이어야 한다. 같은 ID의 두 방출 위치 중 하나만 제거한 변이는 구분하지 못한다(P1) |
| F3 | 해소 | 계약 48-49행이 값 있는 옵션의 같은 값 반복과 `--json`/`--help` 반복의 거부를 명시한다. 구현 `_check_runtime.py` 261-278행과 R02 사례가 일치한다 |
| F4 | 대체로 해소, N2 잔여 | 계약 320-342행에 fail/error 경계표가 생겼다. 상세 설계 D02/D05(226, 229행)와 사례 기대값의 종료 코드가 정렬되었다. C6 누락에 따른 C7/C9 fail은 336행과 일치한다. status 위반 report의 C5 종속 판정은 경계표 334행과 어긋날 수 있다(N2) |
| F5 | 부분 해소, N3 잔여 | `PreparationError`(check_support.py 31-32행)는 `Results.case`에서 error/2가 된다. `Fixture.replace`/`section` 경로는 R13으로 확인했다. 헬퍼를 거치지 않는 직접 문자열 치환/줄 필터 사례는 준비 실패를 감지하지 못한다(N3) |
| F8 | 해소 | `_check_records.py` 84-96행은 H2 제목 inline의 `link_open`만 읽는다. 본문 링크와 제목 이미지는 등록으로 세지 않는다. 첫 저장 `first_save`(481-482행)도 같은 함수를 사용한다. 계약 72-76, 141-142행과 guidelines 204-205행이 일치하며 D01.reference_only/registered, D02.reference_only/title_image가 보호한다 |
| F9 | 해소, 참고 잔여 | report-checks.md "제공 상태"와 계약 머리말에 개발 이력이 없다. tools 안내에도 일회성 실행 결과가 없다. [저장소 배치 규격](../../../../../../../../standards/repository-layout.md) 150-155행과 맞는다. 배포 문서의 개발용 검사기 언급은 참고 P5 |
| I2 | U+2028은 해소, N1 회귀 | `_check_content.py` 218행이 LF 개수를 사용하므로 U+2028은 줄로 세지 않는다. D25.unicode_separator가 보호한다. 같은 식이 파일 끝 LF 없는 미닫힘 fence를 닫힌 것으로 판정한다(N1) |

## 발견한 문제와 확인 가능한 근거

심각도 기준은 1차 리뷰와 같다.

| 심각도 | 기준 |
| --- | --- |
| 높음 | 계약 위반으로 기본 사용 경로에서 잘못된 통과/차단이 발생 |
| 중간 | 현실적인 조건에서 오분류/검출 누락이 발생하거나 완료 관문을 막음 |
| 낮음 | 경계 조건, 문서/기록 정합성, 커버리지 공백 |
| 참고 | 조치 필요성 낮음 |

경로는 저장소 루트 기준이며 행 번호는 검토 시점 파일 기준이다.
아래 재현은 제안이며 직접 실행하지 않았다.

### N1 (중간, 제품, 회귀 가능성) 파일 끝 LF가 없는 미닫힘 `text ascii-flow`를 닫힌 도식으로 판정함

#### 위치와 근거

- 위치: [_check_content.py](../../../../../../../../plugins/Camellia/skills/code-development/scripts/_check_content.py) 218행

  ```text
  closing = token.map is not None and token.map[1] - token.map[0] == token.content.count("\n") + 2
  ```

- markdown-it-py의 fence 규칙은 닫는 구분자가 없으면 문서 끝에서 블록을 자동으로 닫는다.
  이때 `map`은 `[시작 줄, 문서 끝 줄]`이고 content는 `getLines(..., keepLastLF=True)`로 만든다.
  마지막 물리 줄에 LF가 없으면 그 줄의 content에는 LF가 붙지 않는다.
- 내용 n줄의 미닫힘 fence가 LF 없이 파일 끝에서 끝나는 경우를 계산하면 다음과 같다.
  - `map` 차이: 여는 줄 1 + 내용 n = n + 1
  - `content.count("\n")`: n - 1
  - 판정식 우변: (n - 1) + 2 = n + 1이므로 `closing`이 참이 된다.
- 닫힌 fence(n + 2 = n + 2)와 LF로 끝나는 미닫힘(n + 1 ≠ n + 2)은 올바르게 구분된다.
  빈 내용의 미닫힘(1 ≠ 2)도 올바르다.
- 1차 리뷰는 이전 구현이 `str.splitlines()` 줄 수를 사용한다고 기록했다.
  그 식이 "splitlines 개수 + 2"였다면 LF 없는 마지막 줄도 한 줄로 세어 이 입력을 미닫힘으로 판정했을 것이다.
  이전 소스는 이번에 직접 읽지 않았으므로 회귀 여부는 추정이다.

#### 계약과 영향

- [실행 계약](../../../../../../../../plugins/Camellia/skills/code-development/references/report-check-contract.md) 218-219행은
  "파서 기준의 닫는 구분자 존재"를 C12 참 조건으로 둔다.
  파서는 이 입력을 닫는 구분자 없이 자동 종료한 블록으로 해석하므로 C12.fence는 거짓이어야 한다.
- 미닫힘 fence는 항상 문서 끝이나 컨테이너 끝까지 이어진다.
  따라서 최상위 미닫힘 도식은 "파일이 LF로 끝나지 않음"이라는 조건 하나만 더해지면 거짓 통과가 된다.
- 특히 설계 상세 `<report stem>/<그룹>.md`는 C6 등 다른 필수 영역이 없다.
  도식 하나로 끝나는 파일에서는 다른 실패 없이 종료 0이 될 수 있다.
- 개발용 [D25](../../../../../../../../tools/tests/skills/code-development/check_report_rules.py) 460-472행의 unclosed 사례는
  fixture의 후속 제목과 LF가 뒤따르므로 이 경로를 검사하지 않는다.

#### 최소 재현(제안)

1. 정상 현행 단일 fixture(through=design)에서 `<topic>/design-report/group.md`를 만든다.
   내용은 아래와 같으며 마지막 `a -> b` 뒤에 LF와 닫는 구분자를 두지 않는다.

   ````text
   # 정의

   ```text ascii-flow
   a -> b
   ````

2. `design-report.md`의 단계 결과에 `[정의](design-report/group.md)`를 추가한다.
3. 다음을 실행한다.

   ```sh
   python3 -B <skill>/scripts/check_report_submission.py --project-root <root> \
     --topic-dir <topic> --report <topic>/design-report.md --json; echo $?
   ```

4. 기대 결과는 `C12.fence` fail과 종료 1이다.
   의심 결과는 `C12.fence` pass와 종료 0이다.

파서 동작만 따로 확인하려면 다음 한 줄로 `map`과 content를 볼 수 있다.
기대 관찰은 `[0, 2] 'a -> b'`이다.

```sh
python3 -c 'from markdown_it import MarkdownIt; t=[x for x in MarkdownIt("commonmark").parse("```text ascii-flow\na -> b") if x.type=="fence"][0]; print(t.map, repr(t.content))'
```

#### 개선 방향

- 줄 수를 `content.count("\n") + (1 if content and not content.endswith("\n") else 0)`처럼 LF 기준 물리 줄로 계산한다.
  또는 `map[1] - 1` 줄이 실제 닫는 구분자인지 원문으로 확인하는 방식을 쓸 수 있다.
  어느 방식이든 U+2028 사례를 유지해야 한다.
- D25에 "파일 끝 LF 없는 미닫힘" 사례를 추가한다.
  report 본문 끝 또는 설계 상세 파일에서 확인할 수 있다.

### N2 (낮음, 제품/계약 정합) status 위반 report의 C5 판정이 종속 error 없이 pass/fail로 끝나 종료 1이 될 수 있음

#### 위치와 근거

- 위치: [_check_records.py](../../../../../../../../plugins/Camellia/skills/code-development/scripts/_check_records.py)
  222-224행(C4.status), 362-402행(`base`), 186-188행(`check_bases`)
- `base()`는 metadata와 base_on 타입만 종속 조건으로 확인한다(363-370행).
  status가 허용값이 아니어도 `report.status in ("hold", "superseded")`가 거짓이므로 진행용 조건을 적용한다(393-402행).
  source의 status가 허용값이 아니면 `source.status == "completed"`가 거짓이 되어 `C5.source_status` fail만 낸다.
- `check_bases`는 선택 작업의 모든 수집 report에 C5를 적용한다.
  본문을 검사하는 대상 report는 `C7.state_dependency` error(`_check_content.py` 105-106행)로 종료 2가 된다.
  본문을 검사하지 않는 선행 report나 다른 번들 report는 그 error가 생기지 않는다.

#### 계약과의 차이

- 계약 334행은 "status 누락/타입/허용값 위반"을 "C4 fail.
  상태별 본문 또는 선행 연결을 검사해야 하면 종속 error도 반환하여 종료 2"로 정한다.
- 379행은 종속 항목을 통과로 만들지 않도록 정한다.
- 반면 322행은 읽은 자료로 불충족을 확정할 수 있으면 fail로 둔다.
  "허용값이 아닌 source status는 completed가 아니다"를 확정 가능한 fail로 읽을 여지가 있어 해석이 갈린다.
- 개발용 D05(`check_report_rules.py` 129-135행)는 제출 대상 report 자체만 바꾼다.
  그래서 C7 종속 error가 종료 2를 만들고 이 경로는 검사하지 않는다.

#### 최소 재현(제안)

- 변형 A: 정상 단일 fixture에서 discussion의 `status: completed`를 `status: unsupported`로 바꾸고 design을 제출한다.
  계약 334행을 문자 그대로 읽은 기대 결과는 C4.status fail, 종속 error와 종료 2다.
  의심 결과는 C4.status fail, C5.source_status fail과 종료 1이다.
- 변형 B: `bundles()` fixture에서 `02-store/implementation-report.md`의 status를 `unsupported`로 바꾸고 `01-api/implementation-report.md`를 제출한다.
  의심 결과는 02-store의 C4.status fail과 `C5.source_status` pass, 종료 1이다.
  status를 해석하지 못한 report의 종속 항목이 pass가 되는 사례다.

#### 영향과 개선 방향

- 두 결과 모두 통과가 아니므로 차단 여부는 같다.
  하지만 1과 2를 다르게 해석하는 호출자에게 분류가 달라진다.
- 계약에서 "status를 해석할 수 없는 report와 그 report를 source로 쓰는 C5는 error"인지,
  "다른 값으로 불충족이 확정되면 fail"인지 정한 뒤 구현과 D 사례를 맞춘다.
  계약을 먼저 갱신한다.

### N3 (낮음, 개발용 검사) 준비 실패 분류가 두 헬퍼에만 적용되어 직접 치환/필터 사례는 준비 실패를 감지하지 못함

#### 위치와 근거

- 분류 구현: [check_support.py](../../../../../../../../tools/tests/skills/code-development/check_support.py) 379-395행.
  대상 문자열이 없을 때 `Fixture.replace`/`section`만 `PreparationError`를 낸다.
- [check_report_rules.py](../../../../../../../../tools/tests/skills/code-development/check_report_rules.py)의 다음 사례는 헬퍼를 거치지 않고 직접 변형한다.
  대상이 없을 때도 조용히 아무것도 바꾸지 않는다.

| 사례 | 행 | 변형 방식 | 대상 부재 시 결과 |
| --- | --- | --- | --- |
| D19.reordered_columns | 337-349 | 표 행으로 시작하는 줄의 셀 순서 반전 | 기대값 0이라 변형 없이 통과 |
| D21.superseded_scope | 411-419 | 02-store 묶음 행 줄 제거 | 기대값 0이라 변형 없이 통과 |
| D19.unregistered | 359-364 | 같은 줄 제거 | violation/1로 분류 |
| D15.fenced_evidence, D15.example_label | 268-280 | `str.replace` | violation/1로 분류 |
| D16 batch | 289-297 | `str.replace` | violation/1로 분류 |

#### 기준과 영향

- [개발용 검사 안내](../../../../../../../../tools/references/code-development-tests.md) 66-67행은
  "자료 변형에 필요한 문자열이나 영역이 없어 시험 입력을 준비하지 못하면 검사 준비 오류"로 정한다.
  [상세 설계](../../../structure-design/developer-checks.md) 205행의 R13도 같은 분류를 요구한다.
- 현재 fixture 문자열은 같은 파일에서 만들어 일치하므로 지금 통과 결과가 틀렸다는 근거는 아니다.
  fixture 형식이 바뀌면 기대값 0 사례는 보호 목적을 잃은 채 통과하고, 나머지는 준비 문제가 대상 위반으로 보고된다.
- [정형 결과](../../../validation.md) 265-266행의 디렉토리명 fixture 첫 실패도 준비 결함이 대상 기대값 불일치로 나타난 사례다.
  이 경우는 문자열이 있었으므로 R13 분류로 막을 수 없는 종류다.

#### 최소 재현(사고 실험)과 개선 방향

- 임시 사본에서 `check_support.py` 455행의 묶음 행 형식을 셀 경계 공백 없이 바꾼 뒤 `check_report_rules.py`를 실행한다.
- 기대 결과는 해당 사례들의 error/준비 오류다.
  의심 결과는 D21.superseded_scope와 D19.reordered_columns 통과, D19.unregistered violation이다.
- 개선 방향: 직접 변형도 `Fixture.replace`나 "변형 전후가 달라야 함" 확인을 거치게 한다.

### 참고 (조치 선택)

- P1. `C10.directory_name`은 표 행(`_check_content.py` 345-346행)과 수집 디렉토리(362-366행) 두 곳에서 같은 ID로 나온다.
  `C10.registration`도 디렉토리(368-371행)와 report scope(376-377행) 두 곳에서 나온다.
  - D20.directory.*는 ID 단위로 검출하므로 두 위치를 모두 무력화한 변이는 잡는다.
  - 한 위치만 제거하면 다른 위치가 같은 ID를 내서 통과한다.
  - 미등록 잘못된 이름 디렉토리나 디렉토리 없는 scope 사례가 없어 각 위치를 따로 보호하지 않는다.
  - 원시 `mutations.json`과 정형 결과 262행도 "두 곳"을 함께 바꾼 변이만 기록한다.
  - 관찰 가능한 종료 코드는 대개 같으므로 결함으로 확정하지 않는다.
- P2. `_check_runtime.py`가 없을 때 `--help` 단독 호출도 비상 출력의 오류 2가 된다(각 진입점 8-43행).
  계약 50행(help 단독은 0)과 309-310행(로딩 실패는 2)이 겹치는 경우는 정해져 있지 않다.
  계약 공백이며 현재 동작을 결함으로 보지 않는다.
- P3. 비상 출력의 inputs는 `--json`/`--help` 이외의 모든 `--옵션 값`을 기록하므로 알 수 없는 옵션도 포함한다.
  정상 경로 `_check_runtime.py` 261-274행은 알려진 옵션만 기록한다.
  같은 argv의 inputs가 경로에 따라 다를 수 있다.
  계약 352행과 369행의 "전달된 명시적 인자" 범위 안이어서 위반으로 보지 않는다.
- P4. `C13.location`(`_check_content.py` 390-391행)은 현재 두 호출 경로 모두에서 거짓이 될 수 없다.
  `check_review_receipt.py` 51-53행이 먼저 입력 오류로 끝내고,
  `check_task_completion.py` 58-59행은 같은 디렉토리의 리뷰만 수집한다.
  1차 후속 판단의 F4 비채택 이유(공존 가능)와 충돌하는 새 거짓 통과 근거는 찾지 못했다.
- P5. 배포 문서인 계약 22행("개발용 검사기의 격리 모드 호출 계약과 구분한다")과
  report-checks.md 31행은 Aster 개발용 검사의 존재를 언급한다.
  개발 이력이나 시험 결과는 아니므로 F9 미해소로 보지 않는다.

### 정형 결과 마지막 절 대조 (요청 항목 4)

[정형 결과](../../../validation.md) 239-268행을 로컬
`cargo/work/plugins/Camellia/code-development/workflow-and-script-rework/validation/cross-review-fixes/`의 원시 자료와 대조했다.

| 기록 내용 | 원시 근거 | 대조 결과 |
| --- | --- | --- |
| 5개 검사 20/383/14/115/331, 합계 863, 모두 0/true | `execution.json`의 checks | 일치. 합계도 863이다 |
| R/D 실패/미판정 없음 | `check_runtime_contract.json` 115개, `check_report_rules.json` 331개 | 모든 항목 `passed: true`, issues 빈 목록, `excluded: []` |
| 내부 모듈 누락 19개 조합 | `check_runtime_contract.json`의 R09.internal | 4개 진입점 x 4 모듈 + check_task_start 3 모듈 = 19개 확인. 코드 82-100행과 일치 |
| 수정 후 소스 | `execution.json`의 source_sha256 16개 | 로컬 `round-002/target-state.json`의 같은 16개 파일 해시와 모두 일치 |
| 이름 판정 무력화는 D19.duplicate_name에서만 실패 | `mutations.json`의 bundle_name | exit 1, checks 331, 실패는 D19.duplicate_name 하나(기대 1, 실제 0) |
| 디렉토리명 판정 무력화는 D20 세 사례에서만 실패 | `mutations.json`의 directory_name | exit 1, checks 331, 실패는 D20.directory.00-extra/001-extra/03-Upper |
| 1차 리뷰 해시 | `execution.json`의 review_sha256 | 1차 후속 판단 25행과 같은 값 |

원시 근거로 확인하지 못한 기록은 다음과 같다.

- 실행 시간 9.41초/10.53초와 60초 이내 종료: `execution.json`에 시간 필드가 없다.
- 모든 호출의 `-I -B --working-tree --json` 사용: 실행 명령이 원시 자료에 없다.
- 변이 사본의 실제 변경 위치("한 곳", "두 곳")와 변이 사본 해시: `mutations.json`에 소스 변경 내용이 없다.
- 디렉토리명 fixture의 최초 준비 실패 3개: 해당 원시 로그는 확인하지 않았다.
- Python 16개 구문, 명세서 형식, 보존 참조, `git diff --check`: 원시 결과를 읽지 않았다.
- 구조/참조/템플릿 검사의 원시 JSON 3개와 stderr 5개: 읽지 않았다.
  stderr 5개는 target-state.json에서 0바이트로 기록되어 있다.

결론은 다음과 같이 한정한다.

- 기록된 정형 결과는 확인한 원시 자료와 모순되지 않는다.
- 하지만 N1처럼 D25가 다루지 않는 입력에서 C12 거짓 통과가 남아 있다.
  "331개 통과"를 C12 닫힘 판정의 모든 입력 보장으로 확대할 수 없다.
- 변이 시험은 "두 방출 위치 동시 무력화"만 확인했으므로 P1의 단일 위치 보호는 증명하지 않는다.

### 후속 관문 (결함 아님, 이 리뷰로 통과 처리하지 않음)

- 1차 리뷰의 G1(플러그인 버전), G2(outline-first-development 기록), G3(설치본 호환성/커밋 전 검토)은 이번 범위 밖이다.
  요청 41행에 따라 lifecycle 단계/커밋 관문과 설치본 호환성을 통과 처리하지 않는다.
- N1-N3의 수용/반박과 재검증은 원본 작성자가 사용자와 합의해 처리한다.

## 확인하지 못한 사항

### 전문을 읽은 범위

#### 요청과 기록

- 이번 [요청](request.md) 전체, [1차 원문 리뷰](../round-001/review.md) 전체, [1차 후속 판단](../round-001/resolution.md) 전체
- [정형 결과](../../../validation.md) 전체, [검사 상세 설계](../../../structure-design/developer-checks.md) 전체
- 로컬 `cross-validation/round-002/target-state.json` 전체

#### M4 배포 자료

- `scripts/`의 Python 9개 전체와 requirements.txt
  - `_check_runtime.py`, `_check_records.py`, `_check_content.py`, `_check_markdown.py`
  - `check_task_start.py`, `check_stage_entry.py`, `check_report_submission.py`, `check_review_receipt.py`, `check_task_completion.py`
- report-check-contract.md, report-checks.md 전체
- guidelines.md는 1-622행만 읽었다(전체 813행).
  manifest 규칙(193-273행)은 이 범위에 포함된다.

#### M5 개발 자료

- `tools/tests/skills/code-development/`의 Python 7개 전체와 checks.json
  - `check_support.py`, `repository_support.py`
  - `check_skill_structure.py`, `check_skill_references.py`, `check_report_templates.py`
  - `check_runtime_contract.py`, `check_report_rules.py`
- tools/references/code-development-tests.md 전체

#### 규격과 원시 근거

- standards/work-data.md, standards/repository-layout.md 전체
- 로컬 `validation/cross-review-fixes/`의 `execution.json`, `mutations.json`,
  `check_runtime_contract.json`, `check_report_rules.json`

### 읽지 않았거나 diff로도 대조하지 않은 범위

- 이번 회차에서는 diff를 별도로 읽지 않았다.
  모든 판단은 현재 파일 전문과 위 원시 근거 기준이다.
- 이전 구현 소스(수정 전 `_check_content.py` 등)는 읽지 않았다.
  N1의 회귀 여부는 1차 리뷰의 기술에 근거한 추정이다.
- 명세서, behavioral-validation.md, M1-M3 관련 단계 지침/템플릿과 이전 AI 결과는 읽지 않았다.
  요청 32-33행에 따라 맥락 확인용이며 이번 수정 영향 판단에는 필요하지 않다고 보았다.
- guidelines.md 623-813행은 읽지 않았다.
- standards/skills/skill-content.md, skill-layout.md, skill-validation.md와 `.github/git-workflow.md`는 이번에 읽지 않았다.
  해당 규격에 근거한 S/L/T 검사의 세부 대조는 수행하지 않았다.
- 로컬 원시 자료 중 `check_skill_structure.json`, `check_skill_references.json`, `check_report_templates.json`과
  stderr 파일, 1차 회차의 `reproductions.json`과 재현 하네스는 읽지 않았다.
- `~/.local/share/aster/` 경로 직접 읽기는 권한 설정으로 거부되었다.
  같은 링크 대상인 저장소 `data/` 경로로 읽었다.

### 수행하지 않은 확인

- 테스트, 검사기, 변이 시험과 pre-push는 요청 39행에 따라 실행하지 않았다.
  N1-N3의 실제 결과는 미확인이며 위 최소 재현으로 확인해야 한다.
- N1의 파서 동작은 markdown-it-py 3.x의 fence/getLines 구현에 대한 검토자의 이해에 근거한다.
  설치된 실제 버전에서 `map`/content 값을 직접 관찰하지 않았다.
- 설치본 호환성, 실제 메모리 차단, 외부 URL과 실제 AI 시나리오는 확인하지 않았다.
- 원시 자료의 파일 해시를 다시 계산하지 않았다.
  target-state.json과 execution.json에 적힌 값끼리만 대조했다.
