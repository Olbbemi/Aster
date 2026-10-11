# 플러그인별 설치와 업데이트

배포 소스의 정본은 [플러그인별 배포 소스](../../standards/repository-layout.md#플러그인별-배포-소스)와
그 절에서 지정한 두 marketplace catalog다.
`aster`는 목록 이름이며 별도 설치 플러그인이 아니다.
목록은 플러그인의 위치를 알리고, 설치 코드는 각 항목의 Git 참조에서 가져온다.

## 목록과 코드의 갱신 범위

기존에 등록한 목록 참조에 변경된 두 catalog가 반영돼 있으면 그 참조를 유지할 수 있다.
공용 변경이 main에서 각 통합 브랜치로 전파된 뒤 실제 반영 여부를 확인한다.
목록 참조를 변경해야 하는 경우에는 Garden에서 사용자와 확정하여 등록한다.

목록을 읽을 브랜치를 바꾸는 것으로 개별 플러그인 소스 참조를 대신하지 않는다.
이미 등록된 `aster`와 소스가 충돌하면 기존 항목 삭제나 캐시 복사를 자동 대안으로 수행하지 않는다.

목록 갱신은 이름, 설명과 소스 정의를 새로 읽는 작업이다.
개별 플러그인 설치/업데이트는 지정한 항목의 코드를 가져오는 작업이다.
전체 marketplace 갱신과 모든 플러그인 업데이트를 같은 동작으로 취급하지 않는다.

CLI의 자동 업데이트가 켜져 있으면 다른 플러그인에 미치는 영향도 확인한다.

## Garden에서 수행할 절차

전역 marketplace 등록, 설치/활성화와 설정 변경은 전역 지침에 따라 Garden에서 시작한 세션에서 수행한다.
Aster에서는 catalog와 검사 도구를 준비하며 설치본을 직접 변경하지 않는다.

1. 설치 전 두 플러그인의 소스, 버전, 활성화 상태, 실제 설치 경로와 파일 해시를 기록한다.
2. 확정한 목록 참조에서 변경된 catalog를 가져오고, 각 소스의 URL, branch와 경로를 확인한다.
3. 설치/업데이트할 플러그인 하나만 지정하여 실행한다.
4. 대상의 실제 소스 커밋, manifest 버전과 설치 파일을 해당 branch의 배포물과 대조한다.
5. 비대상 플러그인의 소스, 버전, 활성화 및 파일 해시가 이전과 같은지 확인한다.
6. 필요한 재시작 후 실제 설치본 발견과 호출을 확인한다.

반대 플러그인을 갱신할 때도 같은 보존 조건을 적용한다.

버전 변경이 없는 설치 명령의 성공만으로 업데이트 독립성을 통과 처리하지 않는다.
새 버전이 준비되지 않았으면 설치 확인과 업데이트 시험의 미실행 범위를 구분한다.
시험만을 위해 운영 플러그인의 버전을 임의로 올리지 않는다.

## 명령과 확인 범위

2026-10-11 Codex CLI 0.162.1과 Claude Code 2.1.283의 `--help` 및 공식 문서를 확인했다.
아래 명령은 Garden에서 실행할 때 참고하며, 이번 소스 변경의 실제 설치 통과 근거는 아니다.
Syringa 예시이며 Camellia를 처리할 때는 해당 플러그인 이름만 지정한다.

| 목적 | Codex | Claude |
| --- | --- | --- |
| Aster 목록 갱신 | `codex plugin marketplace upgrade aster --json` | `claude plugin marketplace update aster` |
| 개별 신규 설치 | `codex plugin add syringa@aster --json` | `claude plugin install syringa@aster --scope user` |
| 개별 업데이트 | 별도 `update` 하위 명령 없음. 아래 미확인 사항 참조 | `claude plugin update syringa@aster --scope user --json` |

Codex의 `add`는 개별 설치 명령으로 문서화돼 있다.
기존 설치본에서 이를 재호출할 때의 업데이트 및 다른 플러그인 보존 동작은 Garden에서 확인해야 한다.
확인 전에는 신규 설치 지원만으로 개별 업데이트까지 검증했다고 처리하지 않는다.

CLI가 요구하는 권한 또는 동작이 확정 범위를 벗어나면 그 제한을 보고하고 범위를 다시 확인한다.

- [Codex CLI 명령](https://learn.chatgpt.com/docs/cli/reference)
- [Codex 플러그인 소스](https://learn.chatgpt.com/docs/enterprise/plugin-management)
- [Claude marketplace 소스](https://code.claude.com/docs/en/plugins/marketplace-reference)

## 배포 전 검사와 결과 인계

합의한 기대 소스와 파일 목록을 기준으로 확인한 배포 검사 결과를 인계한다.
로컬 JSON 형식, 원격 소스 대조, 실제 CLI 설치와 개별 업데이트를 각각 구분하여 기록한다.
원격 branch가 움직이면 보고의 커밋과 설치 시점 커밋을 다시 대조한다.

Garden 인계에는 반영된 catalog의 참조/커밋, 플러그인별 참조/커밋과 버전,
검사 결과, 설치/업데이트 명령의 확인 범위와 미검증 항목을 포함한다.
반영 전 로컬 catalog를 원격에서 설치 가능한 배포물로 안내하지 않는다.
