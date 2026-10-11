# 실행 계약

이 문서는 실행기가 제공할 명령과 데이터 계약의 정본이다.

- 실행 준비: [환경과 호출](#실행-환경과-호출), [경로와 입력](#경로와-입력).
- 명령 수행: [응답과 오류](#응답과-오류), [입력 공통 규칙](#입력-객체의-공통-규칙), [명령과 상태](#명령과-실행-상태).
- 입력 작성: [시작](#시작-객체), [후보와 승인](#후보와-승인-객체), [상세 내용](#상세-객체와-렌더링).
- 결과 확인: [저장과 완료](#저장과-완료).

## 실행 환경과 호출

Linux에서 Python 3.10 이상과 Git을 사용한다.
Python 표준 라이브러리로 실행하며 별도 AI 서비스나 하네스 SDK에 의존하지 않는다.
파일 잠금, 심볼릭 링크를 따라가지 않는 디렉토리 핸들과 하드 링크를 이용해 파일을 저장한다.

스킬 디렉토리의 [실행기](../scripts/discovery.py)를 다음과 같이 호출한다.

```bash
python3 -B /absolute/skill/scripts/discovery.py inspect --target /absolute/material --output-root /absolute/git-root
python3 -B /absolute/skill/scripts/discovery.py start --input /absolute/control/start.json
python3 -B /absolute/skill/scripts/discovery.py read --run /absolute/run --file /absolute/material/file.md
python3 -B /absolute/skill/scripts/discovery.py propose --run /absolute/run --input /absolute/control/proposal.json
python3 -B /absolute/skill/scripts/discovery.py approve --run /absolute/run --input /absolute/control/approval.json
python3 -B /absolute/skill/scripts/discovery.py save-topic --run /absolute/run --input /absolute/control/topic.json
python3 -B /absolute/skill/scripts/discovery.py status --run /absolute/run
```

예시 경로는 사용자가 지정한 실제 경로와 `start`에서 반환한 `run`으로 바꾼다.

## 경로와 입력

### 공통 경로 기준

모든 경로 인자는 절대 경로로 전달한다.
상대 경로를 입력받았으면 사용자 대화에서 기준이 명확한 경우에만 해석하고,
기준이 모호하면 절대 경로나 기준 디렉토리를 확인한다.
사용자의 입력을 다른 저장소나 상위 경로로 자동 대체하지 않는다.

### 분석 대상

분석 대상은 하나 이상의 기존 읽기 가능한 일반 파일 또는 디렉토리다.
디렉토리의 내용을 읽기 전에는 파일명과 구조만 열거한다.
심볼릭 링크 대상을 분석 범위에 자동으로 포함하지 않는다.
대상이 링크이면 실제 위치를 알리고 포함 여부를 확인한 뒤 실제 경로를 명시 입력으로 사용한다.
FIFO, 장치와 소켓은 파일 분석 대상으로 받아들이지 않는다.

### 저장 기준 경로

저장 기준 경로는 기존의 쓰기 가능한 Git 작업 트리 루트다.
Git이 판정한 최상위 경로와 입력의 정규화된 실제 경로를 비교한다.
일반 디렉토리, bare 저장소, Git 하위 디렉토리, 존재하지 않는 경로는 거부한다.
`.git`이 파일인 worktree도 Git 판정에 따라 허용한다.
입력의 실제 루트를 진단으로 알려줄 수 있지만 그곳으로 자동 저장하지 않는다.
쓰기 가능 사전 검사가 통과해도 실제 저장 실패는 별도로 보고한다.

## 응답과 오류

명령은 UTF-8 JSON 하나를 표준 출력으로 반환한다.

- 성공: `ok: true`, `command`, `data`.
- 실패: `ok: false`, `command`, `error: {code, message}`.

진단 로그는 표준 오류에 기록하고, 예외 traceback만 남겨 정상 응답처럼 보이게 하지 않는다.

종료 코드는 성공 `0`, 입력이나 상태 계약 위반 `2`, 실제 읽기/쓰기 및 실행 실패 `3`이다.

오류 코드는 `MISSING_INPUT`, `INVALID_TARGET`, `INVALID_OUTPUT_ROOT`, `SCOPE_VIOLATION`,
`SOURCE_CHANGED`, `INVALID_PAYLOAD`, `INVALID_STATE`, `APPROVAL_MISMATCH`,
`TOPIC_CONFLICT`, `IO_ERROR`, `RECOVERY_REQUIRED`로 구분한다.
사용자가 입력을 고쳐야 하는 문제와 이미 저장된 결과를 명확히 구분하여 반환한다.

## 입력 객체의 공통 규칙

입력 JSON의 알 수 없는 키, 중복 키, 틀린 타입과 필요한 비어 있지 않은 값의 누락을 거부한다.
아래 객체는 명시된 키만 허용하며, 문자열 필드는 공백만으로 채울 수 없다.
예외적으로 `example.language`에는 빈 문자열을 허용한다.
빈 배열의 허용 여부는 각 객체에서 명시한다.

## 명령과 실행 상태

### 명령별 역할

| 명령 | 인자 | 입력과 결과 | 변경 범위 |
| --- | --- | --- | --- |
| inspect | `--target PATH` 반복, `--output-root PATH` | 필수 입력과 경로 검사, 대상 종류 및 디렉토리 구조 반환. 파일 본문은 읽지 않음 | 없음 |
| start | `--input JSON_PATH` | 아래 시작 객체 검사. 확정 파일 목록과 내용 해시를 고정하고 `run` 경로 반환 | 새 전용 임시 상태만 생성 |
| read | `--run PATH --file PATH` | 고정된 파일 목록과 해시를 확인한 뒤 UTF-8 본문 반환 | 없음 |
| propose | `--run PATH --input JSON_PATH` | 후보 목록을 등록하고 `proposal_digest` 반환 | 실행 상태 |
| approve | `--run PATH --input JSON_PATH` | 등록된 후보 목록에 대한 승인 ID 집합 고정 | 실행 상태 |
| save-topic | `--run PATH --input JSON_PATH` | 승인 주제 하나의 상세 내용을 검사하고 파일로 저장 | 실행 상태와 최종 후보 파일 |
| status | `--run PATH` | 단계, 저장 완료 파일, 실패/미처리 주제, 복구 필요 여부 반환 | 중단된 저장의 대조 결과만 갱신 가능 |

### 실행별 상태와 재개

모든 `JSON_PATH`는 실행별 임시 영역의 제어용 입력이다.
이를 최종 결과 디렉토리에 보관하지 않는다.
실행기는 `start`에서 새 전용 임시 디렉토리를 만들고 접근 권한을 사용자 전용으로 제한한다.
다른 실행의 상태를 자동 발견하거나 재사용하지 않는다.
같은 실행의 재개는 명시된 `run`으로만 한다.
임시 상태가 없으면 새 실행과 새 승인이 필요하다.

승인된 후보를 저장하는 기본 순서는 `start -> propose -> approve -> save-topic -> status`다.
`read`는 후보 추출 및 승인 후 상세 분석에서 사용한다.
`status`는 실행 생성 이후 언제든 조회할 수 있다.
실행 상태를 거슬러 후보나 승인 집합을 덮어쓰지 않는다.

## 시작 객체

| 키 | 타입과 의미 |
| --- | --- |
| targets | 비어 있지 않은 절대 경로 문자열 배열. 사용자 지정 분석 대상 |
| output_root | 사용자 지정 저장 기준 경로 |
| files | 확인된 범위의 일반 파일 절대 경로 배열. 디렉토리가 비었으면 빈 배열 허용 |
| scope_confirmation | 대상과 디렉토리 포함 범위를 명확히 한 사용자 입력 또는 확인 답변 |
| model | 아래 모델 확인 객체 |

`model`은 `name`, `effort`, `approval`, `verification`의 비어 있지 않은 문자열을 갖는다.
`verification`은 `runtime-confirmed` 또는 `user-confirmed`다.
기록에 값을 썼다는 사실만으로 실제 모델 설정이나 사용자 동의를 기계 검증했다고 해석하지 않는다.

`files`는 대상 파일 자체 또는 사용자 지정 대상 디렉토리 안에 실제로 존재하는 파일이어야 한다.
중복, 대상 밖 파일과 중간에 링크가 개입해 범위를 벗어나는 경로를 거부한다.
디렉토리의 모든 파일을 자동 추가하지 않는다.
고정 후 새로 생긴 파일도 자동으로 포함하지 않는다.
파일별 해시는 내부 상태에서만 관리하며 결과 문서에 원본 경로와 함께 내보내지 않는다.
분석 자료는 UTF-8 텍스트를 기본 지원하며 읽기/디코딩 실패는 조용히 생략하지 않고 알린다.

## 후보와 승인 객체

### 후보 목록

후보 입력은 `topics` 배열을 갖는다.

- 주제 객체: `id`, `title`, `candidates`.
- 후보 객체: `id`, `keyword`, `summary`.

`summary`는 1차 자연어 설명이며 상세 본문 키는 받지 않는다.
주제별 후보는 하나 이상이며, 전체 `topics: []`는 정상적인 후보 없음 결과다.

주제 ID는 `[a-z0-9]+(?:-[a-z0-9]+)*` 형태의 안전한 식별자이며 실행 안에서 유일하다.
후보 ID도 같은 형식으로 정하고 실행 전체에서 유일하게 한다.
사람에게 보여주는 제목과 키워드는 한국어 등 자연어를 허용한다.
주제 ID를 출력 파일명의 `<topic>` 값으로 사용한다.

### 일괄 승인

승인 입력은 `proposal_digest`, `selected_ids`, `user_response`를 갖는다.
`proposal_digest`는 등록된 목록의 식별값과 정확히 일치해야 한다.
`selected_ids`는 알려진 후보 ID의 중복 없는 배열이다.
빈 배열은 명시적 전체 제외이며 파일을 만들지 않고 종료한다.
`user_response`는 실제 선택 답변이다.
자연어의 의미와 실제 답변 여부는 에이전트가 확인하며 실행기는 문자열 존재와 ID 집합만 검사한다.

## 상세 객체와 렌더링

### 개념별 입력

상세 입력은 `topic_id`, `concepts`를 갖는다.
개념 객체는 `candidate_id`와 다음 선택 키를 갖는다.
해당 주제에서 승인된 후보를 빠짐없이 한 번씩 포함하고 다른 후보는 거부한다.

| 선택 키 | 값 | Markdown 소제목 |
| --- | --- | --- |
| explanation | 비어 있지 않은 설명 | 개념 설명 |
| usage | 비어 있지 않은 문법과 사용 설명 | 문법과 사용 형태 |
| behavior | 비어 있지 않은 동작, 조건 또는 제약 | 동작과 조건 |
| example | `language`, `text`를 갖는 객체. text는 비어 있지 않음, language는 빈 문자열 또는 안전한 코드 언어 식별자 | 최소 예시 |

각 개념은 선택 키를 하나 이상 가져야 한다.
설명을 채우기 위해 근거 없는 필드를 만들지 않는다.
후보가 상세 분석에서 적절하지 않다고 확인되면 임의 삭제하지 말고 해당 주제의 실패 이유를 보고한다.

### Markdown 구성

대제목은 후보 목록의 `keyword`로 정하고 개념마다 H1을 출력한다.
파일 전체를 대표하는 H1은 별도로 추가하지 않는다.
선택 키 순서는 표의 순서이며 존재하는 필드만 H2와 본문으로 렌더링한다.

필드 본문이 H1/H2를 추가해 구조를 바꾸지 못하도록 검사한다.
제목의 줄바꿈은 거부하고 Markdown 구조 문자는 이스케이프한다.
본문의 타입/태그 표기에서 꺾쇠 문자가 HTML로 사라지지 않도록 이스케이프한다.

인라인 코드 구간과 최소 예시 코드 블록의 원문은 유지한다.
예시 코드의 백틱이 코드 블록을 닫지 않도록,
본문에서 가장 길게 이어진 백틱보다 긴 구분자를 사용한다.

기계 입력에는 원본 경로, 행 번호와 출처 메타데이터 키를 두지 않는다.
설명 문자열에 출처나 프로젝트 고유 내용이 섞였는지는 별도 의미 검토 대상이다.

## 저장과 완료

### 파일명과 생성 시각

최종 경로는 `<output_root>/knowledge-candidate/YYYY-MM-DD/knowledge-YYYYMMDD-HHMMSS-<topic>.md`다.
파일을 생성하는 순간의 실행 환경 현지 시각 한 번으로 날짜와 파일 시각을 함께 정한다.
주제가 자정을 넘어 저장되면 각 파일의 생성 날짜를 따른다.
동일 파일명이 있으면 확장자 앞에 `-2`, `-3`처럼 구분자를 붙인다.
새 실행은 기존 파일에 누적하거나 덮어쓰지 않는다.

### 저장 조건과 기존 파일 보존

승인 후 유효한 주제 본문을 저장할 때만 결과 하위 디렉토리를 만든다.
후보 없음, 전체 제외와 승인 대기에는 빈 결과 파일이나 날짜 디렉토리를 만들지 않는다.
내용 없는 파일과 미승인 후보 파일을 만들지 않는다.
저장 직전에도 Git 루트와 경로를 재검사하고 결과 경로의 링크 우회를 거부한다.
다른 실행과 이름이 충돌해도 기존 파일을 보존하며 완성 본문만 최종 이름으로 공개한다.

### 재요청과 중단 복구

같은 실행에서 이미 저장한 주제의 동일한 요청은 저장 경로를 반환하며 중복 파일을 만들지 않는다.
내용이 다른 재요청은 충돌 오류이며 기존 파일을 수정하지 않는다.
중단으로 상태와 파일의 일치 여부가 불명확하면 복구 필요로 보고하고 새 파일을 무조건 만들지 않는다.
