# Aster 작업 경로 준비

## 목적과 동작 기준

[Aster 작업 데이터 규격](../../standards/work-data.md)에 따라 실제 기록 디렉토리와 공용 링크를 준비한다.
[post-checkout](../scripts/git/post-checkout)은 Hortulanus 공통 훅의
`OLD_HEAD NEW_HEAD BRANCH_FLAG` 호출 계약을 유지하고 초기 checkout 조건을 판별한다.

실제 준비는 [prepare_work_data.py](../scripts/git/operations/prepare_work_data.py)가 담당한다.
운영 스크립트는 주 작업 트리 여부를 확인한 뒤 경로와 링크를 준비한다.

- 최초 clone의 checkout에서 경로를 자동 준비한다.
  자동 준비 조건은 주 작업 트리, `BRANCH_FLAG=1`, 이전 HEAD가 null OID인 경우다.
- 일반 checkout/switch, 파일 checkout과 추가 worktree 생성에서는 아무 경로도 만들거나 바꾸지 않는다.
- 공용 경로가 없으면 주 작업 트리의 `data/todo/`, `data/cargo/`를 만들고
  `~/.local/share/aster`가 그 `data/`를 가리키게 한다.
  프로젝트 이름은 clone 이름에 의존하지 않는다.
- 기존의 정상 공용 링크는 대상을 유지하고 그 안의 `todo/`, `cargo/`만 필요한 경우 준비한다.
  다른 clone에서 실행해도 새로운 자료 루트를 만들거나 기존 연결을 바꾸지 않는다.
- 공용 경로의 일반 디렉토리/파일, 끊어진 링크와 하위 경로 충돌은 오류로 알리고 보존한다.
  새 자료 루트의 `data`는 실제 디렉토리여야 한다.
  기존 자료 내부의 정상 디렉토리 링크는 유지한다.
- 공용 링크로 여러 세션과 프로젝트가 같은 기록에 접근한다.
  자동 갱신이나 재연결은 하지 않으며 대상 이동/삭제로 링크가 끊기면 자료 접근도 실패한다.
- 데이터/링크의 자동 이관, 규격과 템플릿 복사, 세션 시작 질문은 수행하지 않는다.
  기존 경로의 이관은 별도 합의한 작업에서 목록과 내용 대조 후 수행한다.

## 연결과 수동 실행

공통 훅의 설치와 호출 계약은 Hortulanus에서 관리한다.
프로젝트 훅은 실행 권한을 포함해 Git으로 관리하며, 공통 훅이 설치된 환경에서 호출된다.
훅이 포함되지 않은 브랜치나 공통 훅이 없는 clone에서는 자동 준비되지 않는다.

훅은 자동 준비 조건을 충족하면 운영 스크립트를 `--checkout`으로 호출하고,
표준 입력/출력과 종료 코드를 전달한다.
`--checkout`은 훅에서 초기 checkout 조건을 확인한 뒤 사용하는 호출 모드다.

기존 주 작업 트리의 Aster 루트에서 명시적으로 초기화하려면 실행한다.

```sh
python3 -I -B tools/scripts/git/operations/prepare_work_data.py --initialize
```

기존 `tools/scripts/git/post-checkout --initialize`도 같은 운영 스크립트를 호출한다.
추가 worktree에서 명시적 초기화는 오류로 종료한다.
기존 공용 경로로 자료에 접근한다.
`HEAD HEAD 1`은 일반 checkout으로 분류하여 초기화하지 않는다.

성공하거나 자동 준비 대상이 아니면 출력 없이 `0`을 반환한다.
잘못된 인자, Git 경로 확인 또는 준비 실패는 표준 오류에 원인을 출력하고 `1`을 반환한다.
권한 오류가 나면 일부 빈 디렉토리가 이미 생성되었을 수 있다.

충돌과 권한 문제를 해결한 뒤 명시적 초기화를 다시 실행한다.
훅 오류는 이미 수행한 checkout을 되돌리지 않는다.

## 검증

임시 홈과 실제 로컬 Git 저장소에서 최초 clone, 운영 스크립트와 훅의 수동 초기화,
반복 초기화, 추가 clone/worktree, 일반 checkout, 충돌 및 기존 자료 보존을 확인한다.
Hortulanus 공통 설치기 자체의 검증은 해당 프로젝트에서 관리한다.

```sh
python3 -I -B -m unittest discover -s tools/tests/git -p 'test_prepare_todo.py' -v
```
