# main 변경 자동 전파

운영 규칙과 판정 기준의 정본은 [Git 운영 규칙](../standards/git-workflow.md#main-변경의-전파)이다.
`.github/workflows/sync-integrate.yml`이 `tools/sync_integrate_branches.py`를 실행한다.

## 실행 환경과 동작

Python 3.9 이상과 `git merge-tree --write-tree`를 지원하는 Git 2.38 이상을 사용한다.
GitHub 표준 Ubuntu 러너에서 기본 `GITHUB_TOKEN`의 `contents: write` 권한으로 실행한다.
`actions/checkout`이 구성한 `origin` 인증을 사용하며 별도 비밀값을 소스에 저장하지 않는다.

워크플로는 병합된 `main`을 체크아웃하고 임시 Git 원격을 사용하는 회귀 검사를 수행한다.
검사 통과 후 전파 도구가 최신 원격 커밋과 통합 브랜치 목록을 조회한다.
`merge-tree`와 `commit-tree`를 사용하므로 통합 브랜치를 체크아웃하지 않으며 그 안의 코드를 실행하지 않는다.
새 merge 커밋의 작성자와 커미터는 `github-actions[bot]`이고 메시지는 영어다.
Git 설정 파일, 현재 로컬 브랜치, 작업 파일과 스테이징 내용을 변경하지 않는다.
fetch로 원격 추적 참조를 갱신하고, merge에 필요한 Git 객체를 만들며, 실제 원격 통합 브랜치를 푸시한다.

각 브랜치의 기존/결과 커밋, 처리 방식, 성공 여부와 실패 원인을 JSON으로 출력하고
Actions 실행의 Summary에도 기록한다. 모든 대상이 성공하면 종료 코드 0, 하나라도 실패하면 1이다.
조회된 통합 브랜치가 없으면 빈 결과를 보고하고 성공 종료한다.
푸시 후 검증에서 실패하면 원격에 이미 반영되었을 가능성이 있으므로 원격 상태를 먼저 확인한다.

전파 중 통합 브랜치에 다른 변경이 푸시되어 일반 푸시가 거부되면 해당 실행은 실패로 남긴다.
실행 중 브랜치 삭제를 병행하지 않는다. 삭제 확인과 푸시 사이의 경합을 Git 일반 푸시로 원자적으로 차단하지는 않는다.
충돌과 권한 문제를 해결한 후 GitHub Actions에서 해당 실행을 재실행하면 최신 원격 상태를 다시 조회한다.
브랜치 보호 정책이 변경되면 기본 토큰의 푸시 가능 여부도 다시 확인한다.

## 로컬 검사

```bash
python3 -I -B -m unittest discover -s tools/tests -p test_sync_integrate_branches.py -v
```

검사는 임시 디렉토리에 실제 Git 저장소와 bare 원격을 만들고 종료 후 정리한다.
Aster 원격에 푸시하지 않으며 GitHub 인증과 이벤트 전달은 검사하지 않는다.

전파 도구를 직접 실행하는 다음 명령은 검사 명령이 아니다.
지정 저장소의 실제 `origin/integrate/*`를 갱신하므로 Git 운영 규칙의 원격 변경 권한을 확인한 뒤 사용한다.

```bash
python3 -I -B tools/sync_integrate_branches.py --repo /path/to/repository
```

## 최초 GitHub 검증

1. 이 변경을 공용 작업 브랜치에서 `integrate/common` 대상으로 Draft PR을 만든다.
2. 사용자가 Ready 전환과 병합을 수행한 뒤 공용 통합 결과를 검증한다.
3. `integrate/common -> main` Draft PR을 만들고 사용자가 Ready 전환과 병합을 수행한다.
4. 자동 생성된 `Propagate main to integration branches` 실행과 Summary를 확인한다.
5. 원격을 fetch하고 Summary의 `main` 커밋이 `origin/integrate/common`과 `origin/integrate/camellia`의 조상인지 확인한다.
6. 양쪽에 전파 파일이 반영되고, 작업 브랜치에 자동 전파되지 않았는지 확인한다.

이 검증은 브랜치 전파에 대한 확인이며 Camellia의 기능이나 버전 훅 실행을 검증하는 절차가 아니다.

## 공식 동작 근거

- [GitHub의 PR 병합 이벤트](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#running-your-pull_request-workflow-when-a-pull-request-merges)
- [Actions checkout과 기본 토큰 사용](https://github.com/actions/checkout)
- [Actions 동시 실행 제어](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [Git merge-tree](https://git-scm.com/docs/git-merge-tree)
- [Git commit-tree](https://git-scm.com/docs/git-commit-tree)
