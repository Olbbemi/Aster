# Aster

스킬, 훅, MCP, 에이전트 실행 보조 도구와 플러그인을 개발하고 관리하는 저장소다.

## 디렉토리 안내

아래는 [저장소 배치 규격](standards/repository-layout.md)에 따른 각 영역의 역할이다.
파일을 추가하거나 옮길 때 적용할 기준은 해당 규격에서 확인한다.

| 디렉토리 | 역할 |
| --- | --- |
| [.agents/](.agents) | 저장소 내부용 스킬과 Codex용 플러그인 목록 |
| [.claude-plugin/](.claude-plugin) | Claude용 플러그인 목록 |
| [.codex/](.codex) | 저장소에 적용하는 Codex 설정과 실행 허용 규칙 |
| [.github/](.github) | Git 운영 규칙, PR과 GitHub 자동화 |
| [assets/](assets/) | 일반 작업과 내부 스킬의 공용 기본 양식 |
| `data/` | Git에서 제외하는 진행 중 자료와 로컬 기록. 공용 경로로 접근 |
| [records/](records/) | 완료 시 선별/정리하여 Git에 보존할 작업 기록 |
| [plugins/](plugins) | 배포할 플러그인의 소스와 실행 자료 |
| [shared/](shared/) | 내부 스킬과 설치된 플러그인이 함께 참조하는 공용 자료 |
| [standards/](standards) | 구성 요소의 개발 규격과 저장소 배치 기준 |
| [tools/](tools/) | 검사기, Git 자동화와 시나리오 실행기, 공용 테스트와 사용 안내 |

## 작업 안내

### 작업 규칙과 자료 관리

- 작업 절차와 권한은 [AGENTS.md](AGENTS.md)를 따른다. `CLAUDE.md`는 같은 규칙을 읽는 진입점이다.
- 파일을 추가하거나 옮길 때는 [저장소 배치 규격](standards/repository-layout.md)을 확인한다.
- 작업 기록과 시험 결과의 저장 위치는 [공유 작업 데이터 접근](AGENTS.md#공유-작업-데이터-접근)에서 확인한다.
- 공용 기록 규격과 선택 가능한 양식은 [작업 데이터 규격](standards/work-data.md)에서 확인한다.
- 최초 clone과 명시적 초기화의 경로 준비는 [Aster 작업 경로 준비](tools/references/prepare-todo.md)를 따른다.

### Git과 GitHub 운영

- 브랜치, 커밋과 PR 작업은 [Git 운영 규칙](.github/git-workflow.md)을 따른다.
- PR 본문은 [PR 양식](.github/pull_request_template.md)을 사용한다.
- 플러그인 변경의 사전 검사와 푸시 차단 설정은 [플러그인 버전 확인](.github/git-workflow.md#플러그인-버전-확인)에서 확인한다.
- main 병합 후 통합 브랜치로 변경을 전파하는 자동화의 동작과 검사 방법은 [main 변경 자동 전파](tools/references/main-propagation.md)에서 확인한다.

### 스킬 개발과 검사

- 스킬을 만들거나 수정할 때는 [스킬 내부 배치](standards/skills/skill-layout.md), [내용 작성](standards/skills/skill-content.md), [검증](standards/skills/skill-validation.md) 규격을 확인한다.
- 기계 검사 실행 방법은 [검사 스크립트 사용 가이드라인](tools/guidelines.md)을 따른다.
- 표준 lifecycle 명세서 형식과 단계/템플릿 대응은 [명세서 형식 검사](tools/references/check-lifecycle-specification.md)로 확인할 수 있다.
- 시나리오 계획/결과의 누락은 [시나리오 기록 대조](tools/references/check-scenario-records.md), 도식의 문자 형식은 [ASCII 도식 검사](tools/references/check-ascii-flows.md)로 확인한다.
- 검사기 자체를 수정하거나 실행 환경의 영향을 확인할 때는 [검사 스크립트의 개발과 자체 검증](tools/guidelines.md#검사-스크립트의-개발과-자체-검증)을 확인한다.

### 공용 모델 선택

스킬에서 작업 성격에 맞는 모델과 추론 강도를 제안할 때는
[공용 모델 선택 기준](shared/model-selection.md)을 참조한다.
승인과 실제 적용 절차는 각 스킬의 지침을 따른다.

### 시나리오 실행

사용자가 승인한 시나리오를 별도 Codex CLI로 자동 수행할 때는
[시나리오 공통 실행기](tools/references/scenario-runner.md)의 사용 계약과 실행 방법을 확인한다.
