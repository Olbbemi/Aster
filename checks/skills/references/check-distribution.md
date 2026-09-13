# check_distribution.py

[공통 가이드라인](../guidelines.md)에 따라 배포 구성 검사 스크립트를 실행할 때 읽는 개별 안내다.
[검사 코드](../scripts/check_distribution.py)는 Aster의 두 marketplace를 사용하는 로컬 플러그인 구성을 검사한다.
두 marketplace 중 하나만 사용하는 구성, 원격 배포나 다른 manifest 형식을 모두 검증하는 도구는 아니다.
검증이 필요하지만 이 범위에 맞지 않는 구성은 공통 가이드라인에 따라 미확인 사항으로 알린다.

## 적용 대상

생성하거나 유지하는 플러그인을 대상으로 하며, 플러그인별로 실행한다.
같은 플러그인의 동일 구성은 중복 검사할 필요가 없다. 플러그인을 유지하면서 일부 스킬만
제거한 경우에는 남은 플러그인 구성에 적용한다.
플러그인 배포 대상이 없는 내부용 스킬의 작업은 적용 대상이 없다고 알린다.
제거할 플러그인의 제거 여부와 남은 등록은 호출 스킬에서 별도로 확인한다.

## 입력과 실행

Python 표준 라이브러리만 사용한다. 플러그인 경로, 두 marketplace가 위치한 저장소 루트,
작업 명세에서 정한 기대 배포 구성 JSON을 입력한다. `plugin_directory`, `repository_root`,
`expected_files`에 각각 해당 디렉토리/파일의 절대 경로를 설정한다. 공통 경로/실행 기준은
[공통 가이드라인](../guidelines.md)을 따른다. 플러그인은 지정 저장소 경계 안에 있어야 한다.

```bash
python3 checks/skills/scripts/check_distribution.py "$plugin_directory" \
  --repository-root "$repository_root" \
  --expected-files "$expected_files" --json
```

기대 구성은 다음 형식이며 파일 경로는
플러그인 루트 기준이다. 실제 파일을 스캔해 기대값으로 자동 채우지 않고 합의된 배치에서 작성한다.

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
기대 목록은 검사 입력이며 플러그인에 배포하지 않는다. 작업 명세/기대 목록의 변경은
해당 작업에서 합의한 뒤 반영한다. 검사기는 파일을 추가/삭제하거나 목록을 수정하지 않는다.

## 검사 범위와 한계

기본 manifest 검사는 `name`, 선택 `version`/`description`의 문자열 형식과 `skills`의
경로 문자열/배열을 다룬다. `skills`가 없으면 기본 `./skills/`를 사용하며, 추가 경로는
기본 경로에 더해 대조한다. 기대 `SKILL.md`가 스킬 경로 안에 배치됐는지를 확인하며,
실제 하네스의 발견/호출을 재현하지 않는다. 나머지 manifest 필드는 `UNCHECKED`다.

두 catalog는 `.agents/plugins/marketplace.json` 및 `.claude-plugin/marketplace.json`이다.
기본 `name`/`plugins`, Claude `owner.name`, 대상의 단일 등록과 로컬 source 경로를 확인한다.
Codex 대상 항목의 `policy.installation`, `policy.authentication`, `category`는 비공백 문자열인지
확인하며 정책 값의 전체 열거형 검증은 하지 않는다. 다른 플러그인의 source를 실제 탐색하지 않는다.
대상 source가 원격 형식이면 `UNCHECKED`다. 별도 bare-name/pluginRoot 해석도 지원하지 않으며
현재 Aster에서 사용하는 `./` 로컬 경로 형식을 대상으로 한다.

2026-09-13 확인한 [Codex 배포 문서](https://developers.openai.com/plugins/build/plugins),
[Claude manifest 문서](https://code.claude.com/docs/en/plugins-reference)와
[Claude marketplace 문서](https://code.claude.com/docs/en/plugin-marketplaces)의 해당 형식 및
Aster의 [배포 경계](../../../standards/repository-layout.md)를 적용한다. 제품 전체 스키마,
설치된 배포물의 구성, 실제 Codex/Claude의 manifest 수용 여부는 검사 범위 밖이다.
승인된 manifest 형식을 다른 배포 형식으로 자동 전환하지 않는다.

종료 코드와 공통 해석은 [공통 가이드라인](../guidelines.md)을 따른다. JSON에는 대상/기대 구성 경로,
기대/실제 파일 목록과 항목별 판정/근거를 담는다. 숨김 파일도 목록에 포함한다.
파일 집합의 누락/추가와 경계 밖 파일 링크는 실패한다. 내부 디렉토리 링크는 재귀 수집하지 않고
`UNCHECKED`로 보고하며, 목록을 전부 읽지 못한 경우 정확한 집합 대조를 완료했다고 처리하지 않는다.
