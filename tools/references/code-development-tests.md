# Code Development 푸시 전 검사

## 목적과 제공 상태

code-development 자체의 파일과 내부 실행기의 동작 계약을 검사하여 기능 안정성을 확인한다.
기계적으로 판정 가능한 조건만 검사하며 등록된 검사 하나라도 실패하거나 실행할 수 없으면 푸시를 차단한다.
소비자 프로젝트의 실제 작업 기록이나 자연어 지침의 타당성을 대신 판정하지 않는다.

개발용 실행기는 아래 5개이며 `checks.json`에서 호출 대상을 관리한다.
공통 지원 모듈은 실행기의 준비와 결과 처리를 담당한다.
실제 AI 대화와 설치본 호환성은 별도이며 구현 또는 정형 검사 통과로 대신하지 않는다.

## 호출과 대상

변경 스킬 선택과 푸시 차단은 [Git 운영 규칙](../../.github/git-workflow.md#스킬-파일의-pre-push-검사),
등록과 공통 호출은 [스킬 푸시 전 검사](skill-pre-push.md)를 따른다.
`plugins/Camellia/skills/code-development/`의 변경이 선택되면
`tools/tests/skills/code-development/checks.json`에 등록한 검사 전체를 실행한다.
변경된 파일만이 아니라 전송할 커밋의 전체 대상 스킬을 검사한다.

스킬 경로 밖의 개발용 검사나 작업 기록만 바꾼 경우에는 이 자동 호출 조건에 포함되지 않는다.
그 경우에도 필요한 수동 검사를 수행할 수 있다.
등록 파일에는 5개 실행기만 연결한다.
보조 모듈은 등록하지 않고 목적 선택 옵션을 받는 통합 실행기를 만들지 않는다.

## 검사별 책임과 정본

스킬 루트는 `plugins/Camellia/skills/code-development/`다.
아래 파일은 모두 `tools/tests/skills/code-development/` 바로 아래에 둔다.

| 파일 | 필수 검사 범위 | 판정 근거 |
| --- | --- | --- |
| `check_skill_structure.py` | SKILL.md 메타데이터, 계약에 명시한 실행 자료, 스킬 내부 Python 구문과 의존성 선언 | [기본 형식](../../standards/skills/skill-content.md#skillmd-frontmatter), [구조 검증](../../standards/skills/skill-validation.md#구조-검증), [실행 환경과 파일 계약](../../plugins/Camellia/skills/code-development/references/report-check-contract.md) |
| `check_skill_references.py` | 배포 문서의 실제 로컬 링크/이미지/절과 배포 경계 | [배치 규격](../../standards/skills/skill-layout.md#배치-기준), [절 링크 정책](../../standards/skills/skill-validation.md#로컬-markdown-절-링크의-기계-판정) |
| `check_report_templates.py` | 기본 단계 목록과 지침/템플릿 대응, 템플릿의 필수 메타데이터/제목/기록란 | [단계 목록](../../plugins/Camellia/skills/code-development/references/workflow.md#단계-순서와-지침), [report 계약](../../plugins/Camellia/skills/code-development/references/report-check-contract.md), 단계별 작성 지침과 실제 연결된 템플릿 |
| `check_runtime_contract.py` | 내부 실행기 5개의 CLI, 출력/종료 코드, 실행 환경, 비변경성과 재현성 | [실행 계약](../../plugins/Camellia/skills/code-development/references/report-check-contract.md), [호출 안내](../../plugins/Camellia/skills/code-development/references/report-checks.md) |
| `check_report_rules.py` | 시험용 자료를 사용한 C1-C14, 실행 시점별 범위, 신구 형식/번들/회귀/전체 완료의 정상 및 위반 판정 | [판정 및 적용 범위 계약](../../plugins/Camellia/skills/code-development/references/report-check-contract.md) |

구조 검사는 필수 `name`/`description`의 타입, 비어 있지 않은 값과 디렉토리명 대응을 확인한다.
YAML은 안전하게 읽으며 중복 키를 허용하지 않는다.
내용의 적절성, 선택 필드의 하네스별 지원과 임의의 길이 제한은 이 검사에서 추정하지 않는다.
실행기 파일은 계약상의 5개를 요구하되 내부 보조 파일명, 전체 파일 수와 소스 문자열을 고정하지 않는다.
Python 구문 검사는 스킬 코드를 실행하거나 바이트코드 캐시를 생성하지 않는다.

참조 검사는 스킬 안의 Markdown을 출발 범위로 한다.
실제 Markdown 링크와 이미지를 읽고 코드/주석과 일반 문장의 경로를 링크로 추정하지 않는다.
외부 URI는 접속하지 않고 제외 사유를 표시한다.
로컬 필수 자료는 Camellia 배포 경계 안에서 같은 대상 버전으로 존재해야 한다.
연결 문서는 절 확인에 필요한 만큼만 읽고 링크를 따라 다른 문서 전체를 재귀 검사하지 않는다.
비Markdown 대상의 비어 있지 않은 fragment 등 정본에서 미판정으로 정한 항목은 통과로 바꾸지 않는다.
소비자 report의 C11은 프로젝트 밖의 명시적 근거도 허용하므로 이 배포 경계와 혼동하지 않는다.

템플릿 검사는 작성 전 원본을 대상으로 한다.
`status: in_progress`, `base_on: null`, 미체크 항목, 비어 있는 근거/반영 시각/승인 내용은 허용한다.
필수 필드와 고정 영역 및 단계별 템플릿 연결을 확인하며 완성된 report의 조건을 원본에 적용하지 않는다.
단계별 상세 제목 전체, 문구와 체크 항목 개수를 고정하지 않는다.
자연어 지침끼리 의미가 일치하는지는 별도 검토한다.

동작 검사는 정상 자료와 해당 조건을 바꾼 위반/오류 자료를 준비하고 실제 실행 결과를 비교한다.
원본 실행기의 내부 상수나 판정 함수를 기대값 생성에 재사용하지 않는다.
고정 시험 입력/시각은 재현용이며 실제 사용자 승인이나 현재 시각 조회를 뜻하지 않는다.
테스트 대상이 올바르게 위반을 반환한 경우에는 개발용 검사가 통과할 수 있다.
대상 실행기의 종료 코드와 개발용 검사 자체의 종료 코드를 구분한다.
위반 사례는 확인하려는 조건 외의 입력을 유효하게 유지하고 세부 규칙 ID와 상태를 대조한다.
같은 C 범주의 다른 실패가 의도한 위반의 검출을 대신하지 않도록 한다.
자료 변형에 필요한 문자열이나 영역이 없어 시험 입력을 준비하지 못하면 검사 준비 오류다.
기대 결과와 실제 동작을 비교한 뒤 확인한 불일치와 구분한다.

## 입력과 사용 방법

Linux, Python 3.10 이상과 Git을 사용한다.
파서 의존성은 [저장소 도구 의존성](../requirements.txt)으로 준비하고,
대상 실행기의 [의존성 선언](../../plugins/Camellia/skills/code-development/scripts/requirements.txt)과 호환되어야 한다.
의존성을 자동 설치하지 않으며 Python 격리 모드에서 읽을 수 없으면 실행 오류다.

각 개발용 실행기는 다음 인터페이스를 사용한다.
아래 명령은 호출 형식이며 현재 실행 성공을 뜻하지 않는다.

```sh
python3 -I -B tools/tests/skills/code-development/check_report_rules.py \
  --repository-root /absolute/Aster --revision HEAD --json
```

pre-push에서는 HEAD 대신 실제 전송할 커밋 SHA를 받는다.
커밋 전 수동 검사에는 `--revision` 대신 `--working-tree`를 명시한다.
둘은 함께 사용할 수 없고 하나는 반드시 필요하다.
`--repository-root`를 생략하면 검사 파일이 있는 Aster 루트를 사용하며 cwd로 대상을 추측하지 않는다.
이 기본값은 개발용 검사 전용이며, 모든 경로를 명시해야 하는 스킬 내부 실행기에 적용하지 않는다.

```sh
python3 -I -B tools/tests/skills/code-development/check_skill_structure.py \
  --working-tree --json
```

다른 검사도 표의 파일명으로 각각 호출한다.
알 수 없는 옵션, 축약/중복 옵션, 모순된 대상 선택과 잘못된 저장소/커밋은 오류다.
`--help` 단독 호출은 검사를 수행하지 않고 사용법만 표시한다.

## 대상 읽기와 시험 격리

검사 코드와 등록은 현재 체크아웃에서 실행한다.
`--revision`에서는 스킬, 배포 안의 참조와 동작 시험에 사용할 코드 모두 지정 커밋에서 읽는다.
작업 트리, 인덱스, 설치 캐시나 다른 커밋의 파일로 누락을 보충하지 않는다.
`--working-tree`에서는 대상 경로의 현재 파일을 읽으며 새 미추적 스킬 파일도 포함한다.
읽는 중 대상이 바뀌지 않은 상태에서 사용하며 동시 변경 잠금은 제공하지 않는다.

동작 시험은 선택한 스킬 자료를 임시 위치에 복사한 뒤 시험용 소비자 프로젝트를 만들어 실행한다.
사용자의 실제 specs, report와 승인 기록은 입력으로 사용하지 않는다.
대상 저장소, 인덱스, 커밋과 플러그인 설치본은 변경하지 않는다.
Git 조회는 기존 객체만 사용하며 checkout, fetch, commit과 push를 실행하지 않는다.

Git 조회 시 훅이 전달한 `GIT_*`, 자식 Python 호출 시 `PYTHONPATH`/`PYTHONHOME`의 영향을 제거한다.
다른 스킬의 검사 모듈이나 검사 대상의 판정 코드를 개발용 판정의 의존성으로 가져오지 않는다.
네트워크, AI CLI와 패키지 설치는 필요하지 않다.
임시 자료는 각 검사 종료 시 정리하며 다음 실행이 이전 시험 상태에 의존하지 않게 한다.

각 Git 조회와 시험용 자식 호출은 최대 10초로 제한하고,
공통 훅의 검사 파일별 60초 제한을 유지한다.
시간이 부족하다는 이유로 필수 사례를 생략하거나 실패를 무시하지 않는다.
환경/자료/코드가 바뀌면 현재 대상에 맞는 실행 근거를 다시 확보한다.

## 결과와 푸시 차단

JSON 출력은 객체 하나이며 개발용 공통 결과는 다음 구조를 사용한다.
아래는 선언이고 실행 결과가 아니다.

```text
Result = {
  passed: boolean,
  checks: [{
    id: string,
    passed: boolean,
    issues: [{
      kind: "violation" | "error",
      path: string | null,
      line: integer | null,
      message: string
    }]
  }],
  excluded: [{path: string, reason: string}]
}
```

`excluded`는 외부 URI처럼 규격이 제외한 대상을 설명하는 용도다.
필수 검사를 실행하지 못한 경우에는 제외 목록으로 넘기지 않고 `checks`에 오류를 남긴다.
모든 필수 검사가 수행되어 통과한 경우에만 전체 `passed`가 true다.
항목별 ID와 위치/이유를 안정적으로 정렬하고 JSON에 로그나 traceback을 섞지 않는다.
기본 텍스트 출력도 같은 판정, 항목 ID, 위치와 실패/오류 원인을 제공한다.

| 종료 코드 | 개발용 검사 결과 |
| --- | --- |
| 0 | `passed: true`. 적용 대상 필수 검사 모두 통과 |
| 1 | `passed: false`. 구조/참조/템플릿 위반 또는 대상 동작이 계약의 기대 결과와 다름 |
| 2 | `passed: false`. 입력/Git 조회/파일 읽기/검사 준비/의존성/시간 초과 등으로 필요한 판정을 수행하지 못함 |

오류와 위반이 함께 있으면 둘 다 보존하고 2를 반환한다.
실패한 항목 뒤에도 독립적으로 수행 가능한 항목은 확인하며, 종속 검사 불가를 통과로 처리하지 않는다.
대상 CLI가 계약과 다른 JSON이나 종료 코드를 내는 현상은 동작 위반이다.
검사 자체가 시작하지 못하거나 JSON을 반환하지 못하면 공통 훅이 실행 오류로 차단한다.
정상 예외 사례는 기대한 결과와 비교하여 통과시킬 수 있지만 skip/expected-failure로 필수 범위를 줄이지 않는다.

## 해석 범위

통과는 명시한 정형 조건과 시험 사례가 충족되었다는 뜻이다.
자연어 지침의 충분함, 실제 사용자 승인, 구현 결과의 업무 적합성과 전체 개발 완료를 뜻하지 않는다.
실제 Codex/Claude의 지침 준수, 모델 선택, 외부 명령 동작과 설치/배포 호환성은 별도 검증한다.
개발용 검사는 Camellia 배포물에 넣지 않으며 스킬 사용 중 호출하는 실행기와 구분한다.
