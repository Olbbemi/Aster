# 스킬 푸시 전 검사

## 목적과 호출 관계

변경된 스킬의 검사를 Git `pre-push`에서 실행하여 실패하면 푸시를 차단한다.
대상 선택과 판정 기준의 정본은 [Git 운영 규칙](../../.github/git-workflow.md#스킬-파일의-pre-push-검사)이다.

[프로젝트 훅](../scripts/git/pre-push)은 Git 인자를
[운영 스크립트](../scripts/git/operations/check_push.py)에 전달한다.
운영 스크립트는 표준 입력을 한 번 읽어 플러그인 버전 검사와 스킬 검사에 같은 ref 정보를 전달한다.
게시 이력 경계의 조회와 판정은 기존 [버전 검사기](../scripts/git/operations/check_plugin_versions.py)를 사용한다.
파일이나 인덱스 변경, checkout, 자동 커밋과 fetch를 수행하지 않는다.

## 스킬 검사 등록과 입력

검사를 적용할 스킬은 `tools/tests/skills/<스킬명>/checks.json`에 실행할 파일을 등록한다.
검사 파일과 등록 파일은 스킬명 디렉토리 바로 아래에 둔다.
별도 하위 디렉토리나 플러그인 이름으로 구분하지 않는다.

```json
{"scripts": ["check_skill_lifecycle.py"]}
```

`scripts`는 중복이 없는, 비어 있지 않은 Python 파일명 목록이다.
경로 구분자, 스킬명 디렉토리 밖의 파일과 심볼릭 링크는 허용하지 않는다.
등록 파일에는 `scripts`만 정의하며 JSON 중복 키도 허용하지 않는다.

등록한 파일은 다음 입력 계약을 지원해야 한다.

```sh
python3 -I -B tools/tests/skills/<스킬명>/<검사 파일>.py \
  --repository-root <저장소 루트> --revision <전송할 커밋 SHA> --json
```

표준 출력은 전체 판정 `passed`가 boolean인 JSON 객체다.
통과는 `passed: true`와 종료 코드 `0`을 함께 반환한다.
실패와 실행 오류는 `passed: false`와 비정상 종료 코드를 반환한다.
실패 위치와 원인은 `checks`의 각 항목 안 `issues` 목록으로 제공할 수 있다.
기존 lifecycle 검사기는 항목별 `id`, `passed`, `issues`를 제공한다.

입력 계약을 지원하지 않는 기존 회귀 테스트는 등록하지 않는다.
현재 등록된 스킬은 [skill-lifecycle](skill-lifecycle-validation.md)과
[knowledge-discovery](knowledge-discovery-tests.md)다.
다른 스킬의 기존 테스트는 해당 스킬 작업에서 기준과 입력 계약을 정한 뒤 등록한다.

검사 구현과 등록은 현재 체크아웃의 파일을 사용한다.
검사 대상 스킬과 그 로컬 참조는 `--revision`에 전달한 커밋에서 읽어야 한다.
훅은 검사 파일마다 최대 60초를 허용하며, 시간 초과를 통과로 처리하지 않는다.
Python 격리 모드에서 실행하므로 사용자 site-packages와 `PYTHONPATH`에 의존하지 않는다.
의존성은 훅에서 사용하는 Python의 가상 환경 또는 격리 모드에서 접근 가능한 환경에 준비한다.

## 수동 실행과 결과

Git이 전달하는 입력 형식은 한 줄마다
`<local-ref> <local-oid> <remote-ref> <remote-oid>`다.
수동 검사도 같은 운영 스크립트에 해당 입력을 전달한다.
새 ref와 삭제는 Git이 전달하는 객체 ID 길이의 영(0)으로 표시한다.

```sh
python3 -I -B tools/scripts/git/operations/check_push.py origin <원격 주소> < <푸시 입력 파일>
```

일반 작업 중 스킬만 검사하는 명령은 각 스킬의 안내를 따른다.
스킬만 수동 검사한 결과가 원격 상태와 플러그인 버전을 포함한 전체 푸시 검사 결과는 아니다.

- `0`: 적용한 검사 모두 통과. 등록된 검사가 없는 변경은 생략 사유를 알린다.
- `1`: 검사 기준 위반.
- `2`: 입력, 등록, Git 조회 또는 검사 실행 오류.

출력에는 비교 대상 ref와 커밋, 스킬명과 검사 파일, 판정 및 실패 이유를 남긴다.
스킬 검사 하나가 실패해도 다른 등록 검사를 실행하여 결과를 함께 보고한다.
입력이나 Git 조회에 실패하여 대상을 정할 수 없으면 오류로 중단한다.
파일을 수정해야 하는 위반은 해당 수정을 커밋에 포함한 뒤 다시 푸시한다.

## 연결과 한계

공통 훅의 설치와 호출 계약은 [버전 검사기의 훅 연결 안내](check-plugin-versions.md#훅-연결과-갱신)를 따른다.
Aster는 프로젝트 훅과 운영 구현을 관리하며 `.git/hooks/`와 전역 설정을 변경하지 않는다.
연결된 공통 훅이 현재 체크아웃의 프로젝트 훅을 호출해야 실제 푸시 차단이 적용된다.
`--no-verify`와 훅 설정 변경, 훅이 연결되지 않은 CI 및 GitHub 웹 병합에서는 자동 적용되지 않는다.

변경된 스킬과 대응하는 등록이 있을 때만 스킬 검사를 적용한다.
등록이 없다는 출력은 그 스킬의 검증을 통과했다는 뜻이 아니다.
이 검사는 실제 작업 기록, 다른 스킬의 동작과 설치 호환성을 대신 검증하지 않는다.

## Git 운영 구현의 검사

호출 선택과 실제 푸시 차단은 로컬 시험용 Git 저장소와 bare 원격으로 확인한다.
Aster의 실제 원격에 시험용 커밋을 보내지 않는다.

```sh
python3 -I -B -m unittest discover -s tools/tests/git -p 'test_check_push.py' -v
```
