# Aster 할 일 경로 준비

## 목적과 동작 기준

프로젝트별 할 일 보관에 관한 전역 공통 지침에 따라
`~/.local/share/aster/todo/`를 준비한다.
공유 자료 접근과 관리 기준은 [Aster 작업 규칙](../../AGENTS.md#공유-작업-데이터-접근)을 따른다.

[post-checkout](../scripts/git/post-checkout)은 Git이 전달하는
`OLD_HEAD NEW_HEAD BRANCH_FLAG` 세 인자를 받는다.
`BRANCH_FLAG`가 `1`인 clone, 브랜치 checkout/switch와 worktree 생성 때 경로를 준비한다.
파일 checkout인 `0`은 아무 작업 없이 종료한다.
인자 개수나 flag가 잘못되면 오류로 종료한다.

- 저장소 폴더 이름과 worktree 이름에 관계없이 같은 `aster/todo/`를 사용한다.
- 경로가 없으면 필요한 상위 디렉토리와 `todo/`를 생성한다.
- 기존 디렉토리와 정상적인 디렉토리 링크 및 내부 자료는 유지한다.
  새 심볼릭 링크를 만들거나 기존 링크를 변경하지 않는다.
- 경로에 일반 파일이나 끊어진 링크가 있거나 쓰기 권한이 없으면 오류를 알린다.
  충돌 대상을 교체하거나 삭제하지 않는다.
- `cargo/pending/`의 기존 기록을 이동하거나 공유 자료의 안내 파일을 생성하지 않는다.
- 세션 시작 시 할 일을 읽고 사용자에게 확인하는 작업은 에이전트가 수행한다.

## 연결과 수동 실행

- 공통 훅의 설치, 호출 계약과 갱신은 [Hortulanus README](https://github.com/Olbbemi/Hortulanus#readme)를 따른다.
- 프로젝트 훅은 실행 권한을 포함하여 Git으로 관리해야 한다.
- 공통 `post-checkout`이 이미 설치되어 있으면 프로젝트 훅 추가 후 재설치는 필요 없다.
- 훅이 포함되지 않은 브랜치나 공통 훅이 없는 clone에서는 자동 준비되지 않는다.

기존 체크아웃에서 Git 작업 없이 준비하려면 Aster 루트에서 실행한다.

```sh
tools/scripts/git/post-checkout HEAD HEAD 1
```

- 성공하거나 파일 checkout을 건너뛰면 출력 없이 종료 코드 `0`을 반환한다.
- 잘못된 인자와 경로 준비 실패는 표준 오류에 원인을 출력하고 `1`을 반환한다.
  충돌 또는 권한 문제를 해결한 뒤 수동 명령으로 다시 준비한다.
- Git checkout 이후 실행되는 훅이므로 오류가 나도 이미 수행한 checkout을 되돌리지 않는다.

## 검증

- 임시 홈과 로컬 Git 저장소로 경로 생성, 반복 실행, 기존 자료와 링크 보존, 충돌, 파일 checkout 제외, clone/checkout/worktree 호출을 확인한다.
- 공통 설치기의 검증은 Hortulanus에서 관리하며 이 테스트는 프로젝트 훅을 검증한다.

```sh
python3 -I -B -m unittest discover -s tools/tests/git -p 'test_prepare_todo.py' -v
```
