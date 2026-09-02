# 저장소 뼈대 초안

이 문서는 Aster 저장소의 개발 영역과 실제 플러그인 배포 영역에 관해 현재까지
합의한 내용을 기록한다. `drafts/`는 설계가 확정되기 전까지만 사용하는 임시
공간이며, 최종 문서 위치와 파일 분할은 아직 확정하지 않았다.

## 전체 구조

```text
Aster/
|-- AGENTS.md
|-- CLAUDE.md
|-- drafts/
|   |-- repository-layout.md
|   `-- shared-data.md
|-- standards/
|   `-- skills/
|-- checks/
|   `-- skills/
|-- .agents/
|   `-- plugins/
|       `-- marketplace.json
|-- .claude-plugin/
|   `-- marketplace.json
`-- plugins/
    `-- <plugin-name>/
        |-- .codex-plugin/
        |   `-- plugin.json
        |-- .claude-plugin/
        |   `-- plugin.json
        |-- skills/
        |   `-- <skill-name>/
        |       |-- SKILL.md
        |       |-- references/
        |       |-- scripts/
        |       `-- assets/
        `-- shared/
            |-- references/
            |-- scripts/
            `-- assets/
```

표시된 선택 디렉토리는 실제 필요가 확인될 때만 만든다. 빈 디렉토리나 자리 표시용
파일을 미리 만들지 않는다.

## 개발 영역

### `AGENTS.md`

Aster 저장소를 Codex로 개발할 때 항상 적용하는 운영 규칙의 정본이다. 개별 플러그인
소스 경계 밖에 있으므로 플러그인 배포물에는 포함하지 않는다.

### `CLAUDE.md`

Aster 저장소를 Claude로 개발할 때 적용하는 운영 규칙이다. 가능한 경우
`AGENTS.md`와 같은 정본을 공유하되, 두 하네스가 실제로 읽는 경로와 형식을 확인한
뒤 방식을 확정한다. 개별 플러그인 배포물에는 포함하지 않는다.

### `drafts/`

설계 논의 중인 초안을 임시로 저장한다. 설계가 확정되면 내용을 정본 위치로 옮기고
초안은 제거한다. 플러그인 배포물에는 포함하지 않는다.

### `standards/`

스킬과 플러그인을 개발하고 검토할 때 적용하는 규격을 둔다. 설치된 스킬이 실행 중
읽어야 하는 자료와 구분하며, 플러그인 배포물에는 포함하지 않는다.

### `checks/`

저장소 산출물이 `standards/`의 기계 판정 가능한 규칙을 만족하는지 검사하는 코드를
둔다. 검사 코드 자체를 규칙의 정본으로 삼지 않는다. 플러그인 배포물에는 포함하지
않는다.

## 마켓플레이스 영역

### `.agents/plugins/marketplace.json`

Codex 마켓플레이스에서 개별 플러그인의 소스 디렉토리를 가리킨다. 플러그인 소스는
저장소 루트가 아니라 `plugins/<plugin-name>/`으로 지정한다.

### `.claude-plugin/marketplace.json`

Claude 마켓플레이스에서 개별 플러그인의 소스 디렉토리를 가리킨다. Codex와 동일한
플러그인 경계를 사용하되, 매니페스트 형식은 하네스별로 유지한다.

## 플러그인 배포 영역

### `plugins/<plugin-name>/`

개별 플러그인의 배포 경계다. 이 디렉토리 안의 파일만 해당 플러그인 배포물에
포함한다. 설치, 갱신, 인증, 장애 및 배포 주기가 다를 때 별도 플러그인으로 나눈다.
구성 요소 종류만으로 플러그인을 분리하지 않는다.

### `.codex-plugin/plugin.json`

Codex 플러그인 매니페스트다. Codex에 등록할 스킬 경로를 `./skills/`로 지정한다.

```json
{
  "name": "<plugin-name>",
  "skills": "./skills/"
}
```

실제 매니페스트를 만들 때는 현재 Codex가 요구하는 필수 필드와 허용 필드를 다시
확인한다.

### `.claude-plugin/plugin.json`

Claude 플러그인 매니페스트다. Codex 매니페스트와 이름 및 버전처럼 공통으로 유지할
값은 일치시킨다. 하네스별로 다른 필드는 각 매니페스트에서 독립적으로 관리한다.

### `skills/`

사용자에게 스킬로 등록되는 구성 요소를 둔다. 스킬 하나의 최소 필수 파일은
`SKILL.md`다.

```text
skills/
`-- <skill-name>/
    |-- SKILL.md
    |-- references/
    |-- scripts/
    `-- assets/
```

- `references/`는 해당 스킬만 사용하는 상세 지침이 있을 때만 만든다.
- `scripts/`는 해당 스킬만 사용하는 반복 작업이나 결정적 처리가 있을 때만 만든다.
- `assets/`는 해당 스킬이 결과물에 사용하는 자료가 있을 때만 만든다.
- `agents/openai.yaml`은 필수가 아니며 UI 메타데이터나 호출 정책이 필요할 때만
  추가한다.

Codex와 Claude에서 공용 `SKILL.md`를 우선 사용한다. 실제 비호환 사항이 확인된
경우에만 하네스 전용 구성을 추가한다.

### `shared/`

같은 플러그인의 여러 스킬이 실행 중 함께 사용하는 자료를 둔다. 플러그인과 함께
배포되지만 별도 스킬로 등록되지는 않는다.

- `shared/references/`는 여러 스킬이 읽는 공용 실행 지침을 둔다.
- `shared/scripts/`는 여러 스킬이 실행하는 공용 코드를 둔다.
- `shared/assets/`는 여러 스킬이 결과물에 사용하는 공용 자료를 둔다.

공용 내용은 `shared/`에 한 번만 기록한다. 각 `SKILL.md`에는 필요한 공용 파일을
읽으라는 짧은 참조 지시를 둔다. 참조 지시는 여러 `SKILL.md`에 반복될 수 있지만,
공용 규칙의 내용은 복제하지 않는다.

```markdown
[공용 워크플로](../../shared/references/common-workflow.md)를 읽고 적용한다.
```

각 스킬이 필수 공용 자료를 참조하는지는 나중에 기계 검사 대상으로 삼는다.

## 배포 경계

마켓플레이스는 `plugins/<plugin-name>/`을 개별 플러그인 소스로 지정한다.

배포되는 항목:

- 하네스별 플러그인 매니페스트
- `skills/`
- 실행에 필요한 `shared/`
- 이후 해당 플러그인에 추가되는 MCP, 훅 및 다른 런타임 구성 요소

배포되지 않는 항목:

- 저장소 루트의 `AGENTS.md`와 `CLAUDE.md`
- `drafts/`
- 개발용 `standards/`
- 개발용 `checks/`
- 다른 플러그인의 디렉토리

플러그인 내부에 `AGENTS.md`를 넣으면 파일 자체는 배포될 수 있지만, 플러그인 설치만으로
사용자 프로젝트의 지침으로 자동 적용된다고 가정하지 않는다. 설치된 스킬이 반드시
적용해야 하는 지침은 `SKILL.md` 또는 그 파일이 명시적으로 참조하는 배포 대상 파일에
둔다.

## 저장소 외부 공유 데이터

Codex와 Claude의 작업 기록 및 교차 검증 이력은 저장소와 별도로 관리한다.

```text
~/.local/share/aster/
|-- INDEX.md
|-- pending/
|-- work/
|   |-- codex/
|   `-- claude/
`-- verifications/
```

상세 구조와 현재 합의는 [공유 작업 데이터 구조 초안](shared-data.md)에 둔다.

## 미결 사항

- 첫 번째 시험용 플러그인의 이름과 범위
- Codex와 Claude 매니페스트의 실제 필드
- 저장소 `AGENTS.md`와 `CLAUDE.md`의 정본 공유 방식
- 개발 규격과 검사의 상세 분류
- 여러 플러그인이 같은 실행 자료를 필요로 할 때의 배포 방식
- MCP와 훅이 추가될 때의 플러그인 경계
