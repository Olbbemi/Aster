# 플러그인 버전 검사기

검사 단위와 판정 기준의 정본은 [Git 운영 규칙](../../standards/git-workflow.md#플러그인-버전-확인)이다.

[검사기](../scripts/validation/check_plugin_versions.py)는 Git의 커밋 또는 스테이징 상태를 읽고,
[pre-push 진입점](../scripts/git/pre-push)은 실제 전송할 ref 정보를 검사기에 전달한다.

공통 훅의 실행 환경은 [Hortulanus README](https://github.com/Olbbemi/Hortulanus#readme)의
지원 환경을 따른다.
검사기에 외부 Python 라이브러리는 필요하지 않다.

## 입력과 사전 검사

기준 ref는 실제 푸시할 대상의 최신 원격 추적 ref를 사용한다.
새 브랜치의 사전 검사는 분기한 통합 브랜치 등을 기준으로 하며 최종 원격 비교는 훅이 수행한다.

상향 수준과 판단 시점은 Git 운영 규칙의
[상향 수준과 호환성 판단](../../standards/git-workflow.md#상향-수준과-호환성-판단)과
[사전 검사와 pre-push](../../standards/git-workflow.md#사전-검사와-pre-push)를 따른다.
검사기는 버전 형식, 증가 여부와 예외 조건을 검사하며,
변경 의미에 맞는 major/minor/patch 선택은 자동 판정하지 않는다.

```bash
# 커밋 전: BASE_REF를 실제 비교 기준으로 바꾼다. 스테이징 내용만 검사한다.
python3 -I -B tools/scripts/validation/check_plugin_versions.py check --base BASE_REF --staged
# 커밋 후: TARGET_REF를 실제 푸시할 커밋/ref로 바꾼다.
python3 -I -B tools/scripts/validation/check_plugin_versions.py check --base BASE_REF --target TARGET_REF --remote origin
```

`--remote`는 이미 원격에 반영된 변경 전파를 확인할 때 사용한다.
지정하지 않으면 원격 조회 없이 두 상태만 비교하며 동일 버전의 변경을 실패로 판정한다.

`--staged` 검사에서는 `--remote`를 지정해도 동일 버전의 변경 전파 예외를 인정하지 않는다.
이 예외의 확인은 커밋 후 `--target`과 `--remote`를 함께 지정해 수행한다.

출력에는 비교 기준, 검사한 플러그인, 기존/반영 버전과 판정 이유를 남긴다.
종료 코드는 다음과 같다.

- `0`: 통과
- `1`: 기준 위반
- `2`: 실행/입력 오류

`tools/scripts/git/pre-push`는 매 푸시마다 같은 스크립트의 `pre-push` 모드에 Git이 전달한 원격과 ref 정보를 넘긴다.
실제 전송할 커밋을 검사하므로 작업 폴더나 스테이징 영역에만 있는 버전 수정은 인정하지 않는다.

여러 ref를 한 번에 보내면 모두 검사하고 하나라도 실패하면 푸시를 중단한다.

훅은 파일 수정, 자동 커밋, 버전 자동 증가나 원격 쓰기를 수행하지 않는다.

실패하면 출력된 원인에 따라 버전이나 manifest 오류, 원격 조회 실패, 필요한 Git 이력 부족 등을 해결한 뒤 다시 푸시한다.
버전 등 플러그인 파일을 수정했다면 해당 변경을 커밋에 포함한다.

## 훅 연결과 갱신

공통 훅의 설치, 호출 계약, 기존 체크아웃의 갱신과 설정 충돌 진단은
[Hortulanus README](https://github.com/Olbbemi/Hortulanus#readme)를 따른다.
공통 훅의 설치와 이관 검증도 Hortulanus에서 관리한다.

Aster는 `tools/scripts/git/pre-push`와 검사 로직을 관리한다.
공통 `pre-push`는 현재 작업 트리의 이 파일을 실행하며 원격 인자, 표준 입력과 종료 상태를 전달한다.
검사기는 `.git/`에 복사하지 않는다.

검사 코드 변경은 다음 호출부터 적용되므로 공통 설치본 갱신이 필요하지 않다.
현재 체크아웃의 검사 코드가 전송할 커밋을 판정한다는 구분은 유지한다.

프로젝트 훅이 없는 브랜치에서는 버전 검사가 실행되지 않으므로 Aster의 검사를 적용할
브랜치에는 `tools/scripts/git/pre-push`와 검사기를 유지해야 한다.
Aster 검사기는 사용자/로컬 Git 설정이나 공통 훅을 설치하지 않는다.

로컬 훅은 `--no-verify`나 훅 설정 변경으로 우회할 수 있고, GitHub 웹 병합이나 훅을 연결하지 않은
CI에는 자동 적용되지 않는다.
훅 실행 계약은 [Git pre-push 문서](https://git-scm.com/docs/githooks#_pre_push)를 따른다.

검사 통과는 설치나 기능 검증을 대신하지 않는다.

## 검사

검사기와 실제 훅 차단은 임시 로컬 Git 저장소와 bare 원격으로 검증한다.
Aster의 실제 원격에 시험용 커밋을 푸시하지 않는다.

```bash
python3 -I -B -m unittest discover -s tools/tests/validation -p 'test_check_plugin_versions.py' -v
```
