# Knowledge Discovery 푸시 전 검사

## 목적과 호출

knowledge-discovery 자체의 파일과 실행 계약을 지속적으로 검사한다.
각 검사는 boolean 판정과 종료 코드를 반환하며 실패하면 pre-push가 푸시를 차단한다.
스킬 사용에 필요한 실행기는 플러그인 내부 scripts/에 있고 이 검사는 배포 밖의 개발 자료다.
실제 분석 자료의 지식 정확성, 작업 명세서와 승인 기록, AI 모델 및 설치본 동작은 검사하지 않는다.

대상 선택과 판정 규칙은 [스킬 푸시 전 검사](skill-pre-push.md)를 따른다.
[checks.json](../tests/skills/knowledge-discovery/checks.json)에 아래 6개 파일을 각각 등록한다.
통합 실행기를 두지 않으며 공통 훅이 모든 등록 파일을 호출한다.

## 기능별 검사와 기준

판정 기준은 [실행 계약](../../plugins/Syringa/skills/knowledge-discovery/references/execution.md),
[스킬 기본 형식](../../standards/skills/skill-content.md#skillmd-frontmatter)과
[로컬 참조 및 구조 검증](../../standards/skills/skill-validation.md)이 정본이다.

| 파일 | 반복해서 검사하는 조건 |
| --- | --- |
| [check_skill_structure.py](../tests/skills/knowledge-discovery/check_skill_structure.py) | SKILL.md의 YAML/필수 값/이름, 로컬 링크와 Markdown 절, 스킬 내부 Python 구문 |
| [check_input_scope.py](../tests/skills/knowledge-discovery/check_input_scope.py) | 구조 열거 전 본문 미읽기, 정상/오류 Git 루트, 범위 밖/링크/특수 파일 거부, JSON 입력과 소스 변경 |
| [check_candidate_approval.py](../tests/skills/knowledge-discovery/check_candidate_approval.py) | 승인 전 저장 금지, 목록 digest/ID 대조, 상태 전이, 빈 결과/전체 제외 및 승인 개념만 저장 |
| [check_markdown_output.py](../tests/skills/knowledge-discovery/check_markdown_output.py) | 지원 필드와 제목, 코드 구분자, 타입/태그 표시, 빈 내용과 출처 메타데이터 거부 |
| [check_topic_storage.py](../tests/skills/knowledge-discovery/check_topic_storage.py) | 출력 링크 거부, 시간 경로, 기존 파일 보존, 반복 호출, 잠금과 경쟁, 부분 실패 및 공개 전후 중단/복구 |
| [check_cli_execution.py](../tests/skills/knowledge-discovery/check_cli_execution.py) | 필수 인자 오류, JSON/종료 코드, 불완전한 상태 처리 및 다른 작업 디렉토리에서 직접 호출 |

검사 수, 현재 배포 파일 개수와 버전을 통과 조건으로 고정하지 않는다.
정해진 날짜, 예시 자료와 장애 주입은 지속적인 동작 계약을 재현하기 위한 fixture다.
특정 변경의 함수 본체 동일성이나 과거 버전 마이그레이션 확인은 이 검사에 포함하지 않는다.
실행 계약이 변경되면 해당 기능의 검사 기준도 함께 갱신한다.

## 입력과 실행 방법

Linux, Python 3.10 이상과 Git을 사용한다.
PyYAML과 markdown-it-py는 [도구 의존성](../requirements.txt)에 지정된 버전을 사용한다.
훅의 Python 격리 모드에서 접근할 수 있는 환경에 준비한다.

각 검사 파일은 다음 입력을 지원한다.

```sh
python3 -I -B tools/tests/skills/knowledge-discovery/check_input_scope.py \
  --repository-root /absolute/Aster --revision HEAD --json
```

위 파일명은 표의 다른 검사 파일로 바꿀 수 있다.
pre-push는 HEAD 문자열 대신 실제 전송할 커밋 SHA를 전달한다.
개발 중인 파일을 수동 검사할 때는 --revision 대신 --working-tree를 명시한다.
두 옵션은 함께 사용할 수 없고 둘 중 하나는 반드시 필요하다.

```sh
python3 -I -B tools/tests/skills/knowledge-discovery/check_skill_structure.py --working-tree --json
```

기본 저장소는 검사 파일이 놓인 Aster 루트이며 --repository-root로 다른 저장소를 지정할 수 있다.
등록된 검사 코드는 현재 체크아웃에서 실행하되 스킬 파일과 로컬 참조는 지정한 커밋에서 읽는다.
미커밋 변경, 미추적 스킬 파일과 인덱스 상태를 커밋 검사에 섞지 않는다.

## 검사 방식과 격리

[repository_support.py](../tests/skills/knowledge-discovery/repository_support.py)는
Git 객체와 명시 작업 트리를 읽고 Markdown 기본 형식을 해석한다.
[check_support.py](../tests/skills/knowledge-discovery/check_support.py)는
시험용 사본/자료, 제한 시간과 공통 결과 출력을 관리한다.
보조 모듈은 checks.json에 등록하지 않는다.

구조 검사는 스킬 코드를 실행하지 않는다.
나머지 검사는 스킬 파일을 임시 사본에 읽어 넣고 독립 Git fixture에서 모의 입력으로 실행 계약을 확인한다.
실행용 사본의 심볼릭 링크와 하위 저장소는 전체 검사 보장을 할 수 없으므로 오류로 반환한다.
로컬 참조는 저장소 경계 안에서 같은 커밋의 대상만 확인하고 외부 URL은 접속하지 않는다.

Git fixture와 명시 저장소 읽기는 훅이 전달한 GIT_* 환경변수를 제거하고,
자식 실행은 PYTHONPATH/PYTHONHOME도 제거한다.
검사 대상의 파일, 인덱스와 커밋은 변경하지 않으며 fixture와 실행 상태는 종료 시 정리한다.
임시 위치를 지정하려면 TMPDIR을 사용하며 검사 준비 시 실제 절대 경로로 해석한다.
각 Git 및 자식 호출에는 10초 제한을 적용하고 공통 훅은 검사 파일마다 최대 60초를 허용한다.
시간 초과와 의존성 누락을 통과로 처리하지 않는다.

## 결과와 실패 처리

--json 출력은 전체 passed가 boolean인 JSON 객체다.
checks에 검사별 id, passed 및 issues의 실패 종류/경로/이유를 제공한다.
기본 수동 출력은 첫 줄의 true/false와 이후 검사별 실패 원인이다.

- passed: true와 종료 코드 0이면 통과한다.
- 형식, 참조, 구문과 동작 계약 위반은 passed: false와 종료 코드 1이다.
- 입력, Git 조회, 읽기, import, 의존성과 시간 초과 등 검사 오류는 passed: false와 종료 코드 2다.
- 필수 검사를 생략하거나 expected-failure로 처리하여 통과시키지 않는다.

등록 파일/검사 코드 자체가 깨져 JSON을 반환하지 못한 경우에도 공통 훅이 검사 오류로 푸시를 차단한다.
사용자 승인 의미, 자료 해석의 정확성, 실제 Codex/Claude 설치와 외부 서비스 연결은 이 판정 범위 밖이다.
