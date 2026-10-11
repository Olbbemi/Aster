# check_distribution.py

[공통 가이드라인](checks.md)에 따라 배포 구성 검사 스크립트를 실행할 때 읽는 개별 안내다.
[검사 코드](../../scripts/check_distribution.py)는 Aster의 두 marketplace에서
로컬 경로 또는 branch를 지정한 `git-subdir` 플러그인 구성을 검사한다.

두 marketplace 중 하나만 사용하는 구성과 모든 원격 소스/manifest 형식을 검증하는 도구는 아니다.
검증이 필요하지만 이 범위에 맞지 않는 구성은 공통 가이드라인에 따라 미확인 사항으로 알린다.

## 적용 대상

생성하거나 유지하는 플러그인을 대상으로 하며, 플러그인별로 실행한다.
같은 플러그인의 동일 구성은 중복 검사할 필요가 없다.
플러그인을 유지하면서 일부 스킬만 제거한 경우에는 남은 플러그인 구성에 적용한다.

플러그인 배포 대상이 없는 내부용 스킬의 작업은 적용 대상이 없다고 알린다.
제거할 플러그인의 제거 여부와 남은 등록은 호출 스킬에서 별도로 확인한다.

## 입력과 실행

Python 표준 라이브러리를 사용하며 원격 대조에는 Git과 원격 읽기 권한도 필요하다.
플러그인 경로, 두 marketplace가 위치한 저장소 루트와 작업 명세에서 정한 기대 배포 구성 JSON을 입력한다.
`plugin_directory`, `repository_root`, `expected_files`에 각각 해당 디렉토리나 파일의 절대 경로를 설정한다.
공통 경로와 실행 기준은 [공통 가이드라인](checks.md)을 따른다.

로컬 소스의 플러그인은 지정 저장소 경계 안에 있어야 한다.
`git-subdir`의 검사 대상 사본은 그 밖에 있어도 되며 원격 커밋의 해당 디렉토리와 대조한다.

```bash
python3 .agents/skills/skill-lifecycle/scripts/check_distribution.py "$plugin_directory" \
  --repository-root "$repository_root" \
  --expected-files "$expected_files" --json
```

기대 구성은 다음 형식이며 파일 경로는 플러그인 루트 기준이다.
실제 파일을 스캔해 기대값으로 자동 채우지 않고 합의된 배치에서 작성한다.

```json
{
  "plugin_name": "sample",
  "manifest": ".claude-plugin/plugin.json",
  "files": [
    ".claude-plugin/plugin.json",
    "skills/sample-skill/SKILL.md"
  ]
}
```

manifest는 `files`에 포함되어야 한다.
기대 목록은 검사 입력이며 플러그인에 배포하지 않는다.
작업 명세와 기대 목록의 변경은 해당 작업에서 합의한 뒤 반영한다.
검사기는 파일을 추가/삭제하거나 목록을 수정하지 않는다.

### git-subdir 입력과 원격 대조

위 기대 구성에 `source`를 추가한다.
두 catalog의 실제 항목에서 역으로 복사하지 않고 명세의 저장소, 브랜치와 경로를 입력한다.

```json
{
  "source": "git-subdir",
  "url": "https://github.com/Olbbemi/Aster.git",
  "path": "plugins/Syringa",
  "ref": "integrate/syringa"
}
```

이 객체는 기대 JSON 전체가 아니라 `source` 필드의 값이다.
`path`는 저장소 기준 상대 경로이며 앞의 `./` 유무를 정규화한다.
이 검사 범위의 `ref`는 브랜치 이름이다.
`sha`, 태그, SSH URL과 위에 없는 필드를 사용하는 소스는 검사 범위 밖이며 통과로 처리하지 않는다.

운영 소스는 HTTPS Git URL이고, 네트워크 없는 Git 회귀 검사에만 `file:///` URL도 허용한다.
로컬 시험 URL 지원을 CLI의 지원 범위로 해석하지 않는다.

```bash
python3 -B .agents/skills/skill-lifecycle/scripts/check_distribution.py "$plugin_directory" \
  --repository-root "$repository_root" --expected-files "$expected_files" \
  --source-repository "$git_object_repository" --verify-remote --json
```

`--source-repository`는 원격 커밋의 Git 객체가 준비된 로컬 저장소이며 생략하면 `--repository-root`다.
검사기는 `git ls-remote`로 브랜치 커밋을 한 번 확인하고, 그 커밋의 하위 경로에 있는
파일 집합, 일반 파일의 내용과 실행 권한을 기대 목록 및 검사 대상 사본과 대조한다.

이 검사에 필요한 객체가 없으면 사용자가 적절한 저장소에 fetch한 뒤 다시 실행한다.
검사기가 자동으로 fetch/checkout하거나 플러그인 코드를 실행하지 않는다.
Git 명령당 제한 시간은 30초이며 인증 입력을 기다리지 않는다.

원격 확인 옵션이 없으면 소스 정의는 대조하되 원격 확인은 `UNCHECKED`다.
원격 조회 실패와 객체 부재는 `ERROR`이며 어느 경우에도 전체 `PASS`가 아니다.
보고의 `remote_commit`은 조회 시점의 커밋이며 이후 브랜치가 가리키는 커밋이나 실제 설치 커밋을 보장하지 않는다.

## 검사 범위와 한계

기본 manifest 검사는 `name`, 선택 필드인 `version`과 `description`의 문자열 형식,
`skills`의 경로 문자열 또는 배열을 다룬다.
`skills`가 없으면 기본 `./skills/`를 사용하며, 추가 경로는 기본 경로에 더해 대조한다.
기대 `SKILL.md`가 스킬 경로 안에 배치됐는지를 확인하며 실제 하네스의 발견이나 호출을 재현하지 않는다.
나머지 manifest 필드는 `UNCHECKED`다.

두 catalog는 `.agents/plugins/marketplace.json` 및 `.claude-plugin/marketplace.json`이다.
기본 `name`/`plugins`, Claude `owner.name`, 대상의 단일 등록과 source를 확인한다.
Codex 대상 항목의 `policy.installation`, `policy.authentication`, `category`는 비공백 문자열인지
확인하며 정책 값의 전체 열거형 검증은 하지 않는다.
다른 플러그인의 source를 실제 탐색하지 않는다.

로컬 소스는 `./` 상대 경로를 확인한다.
`git-subdir`는 위 기대 소스가 있어야 검사하며 다른 원격 형식은 `UNCHECKED`다.
별도 bare-name/pluginRoot 해석은 지원하지 않는다.
원격 symlink/submodule은 미검사이며 일반 파일 검증과 구분한다.

2026-10-11 확인한 [Codex 소스 문서](https://learn.chatgpt.com/docs/enterprise/plugin-management),
[Claude manifest 문서](https://code.claude.com/docs/en/plugins-reference)와
[Claude marketplace 문서](https://code.claude.com/docs/en/plugins/marketplace-reference)의 해당 형식 및
Aster의 [배포 경계](../../../../../standards/repository-layout.md)를 적용한다.

제품 전체 스키마, 설치된 배포물의 구성과 실제 Codex/Claude의 manifest 수용 여부는 검사 범위 밖이다.
승인된 manifest 형식을 다른 배포 형식으로 자동 전환하지 않는다.

종료 코드와 공통 해석은 [공통 가이드라인](checks.md)을 따른다.
JSON에는 대상 및 기대 구성의 경로, 기대/실제 파일 목록과 항목별 판정 및 근거를 담는다.
숨김 파일도 목록에 포함한다.

파일 집합의 누락/추가와 경계 밖 파일 링크는 실패한다.
내부 디렉토리 링크는 재귀 수집하지 않고 `UNCHECKED`로 보고한다.
목록을 전부 읽지 못한 경우 정확한 집합 대조를 완료했다고 처리하지 않는다.
