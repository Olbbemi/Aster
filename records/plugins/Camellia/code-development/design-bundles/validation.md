# 설계 산출물과 순차 묶음 개선 검증

## 대상과 최종 판정

2026-10-07 Codex가 구현 및 최종 판단을 수행했고 Claude가 독립 교차 검토를 수행했다.
아래 기록은 실제 실행 근거를 최종 결과 중심으로 통합한 것이다.

| 항목 | 식별 또는 결과 |
| --- | --- |
| 변경 기준 | `1bc373a4ea684697d35587b96fd0fe5aec843a93` |
| 검증 소스 | `baef202a9b29230950c64791d24a0aab9458bee5`, Camellia 3.1.0 |
| 변경 규모 | 24파일, 사용자 검토 그룹 1~10의 10커밋 |
| integrate/camellia 반영 | [PR #38](https://github.com/Olbbemi/Aster/pull/38), 병합 커밋 `0beebac5ef6d359fd720618040cb553459e83ac1` |
| 설치 기준 | 검증 소스와 병합본의 플러그인/등록 내용 동일, Codex/Claude 각 28파일 해시 일치 |
| 기계 검사 | 회귀 77개 및 구조/참조/배포 통과 |
| 동작 검증 | S1~S4 통과. S2 최초 timeout과 후속 성공을 구분 |
| 독립 교차 검증 | 완료. 미해결 결함 없음 |
| Codex 설치본 C1 | K1~K4 통과 |
| Claude 설치본 C2 | K1/K2 확인, K3/K4 미판정 및 사용자 확인으로 이관 |

사용자는 추가 Claude 호출을 생략한 뒤 남은 검증을 사용자 확인으로 넘기도록 요청했다.
이에 따라 K3/K4를 이번 에이전트 작업의 필수 완료 범위에서 제외하고 실제 미판정은 유지한다.
사용자 확인 완료나 전체 CLI 호환성 통과로 기록하지 않는다.
완료 범위와 승인 정본은 [명세서](specification.md)를 따른다.

## 구현과 실행 구조

스킬 전용 Python 파일은 7개다.
전체 진입점, 5개 역할 실행기와 내부 공통 모듈을 같은 스킬의 `scripts/`에서 관리한다.

| 파일 | 역할 |
| --- | --- |
| `check_reports.py` | 같은 입력 컨텍스트에서 5개 역할을 실행하는 전체 진입점 |
| `check_report_structure.py` | 파일명/메타데이터/필수 영역, 현재 개정과 선행 연결 및 묶음 범위 |
| `check_completion_records.py` | 완료 체크리스트와 근거, verification/qa 완료 구분, 반영 기록 |
| `check_work_bundles.py` | 공통 설계의 묶음표, 현재 report 등록과 결과 연결 |
| `check_report_links.py` | 선택 manifest, 현재 report와 설계 상세의 로컬 링크 및 절 |
| `check_report_diagrams.py` | 현재 report와 설계 상세의 ASCII 문자 형식 |
| `report_common.py` | 입력, YAML/Markdown 파싱, 현재 report/상세 자료 수집과 공통 출력 |

각 실행기는 작업 경로와 `--json`을 받는다.
다른 역할을 실행한 뒤 결과만 숨기는 방식이 아니라 필요한 역할의 검사만 수행한다.
공통 입력 파싱 오류는 개별 실행에서도 보고한다.
전체 실행은 파싱/순회 결과를 재사용한다.
종료 코드는 통과 0, 위반 1, 오류 또는 미판정 2다.
사용 기록을 수정하거나 로그/캐시를 생성하지 않는다.

최종 역할 선택과 검사 한계는 [검사 계약](../../../../../plugins/Camellia/skills/code-development/references/report-checks.md)에 있다.
승인 제출에는 필요한 역할 전체를 확인하며 재개에는 구조/완료 및 해당 묶음표를 기본으로 확인한다.
변경된 자료의 영향에 따라 참조/도식 등 필요한 역할을 다시 실행하고 영향이 불명확하면 전체 실행을 사용한다.

공통 discussion/design은 bundle을 생략하고 묶음별 design/implementation/verification/qa는 선택 bundle을 사용한다.
번호는 단계 전체에서 증가하며 현재 개정은 `(단계, bundle)`별로 판단한다.
다른 묶음의 완료를 superseded로 바꾸지 않는다.
묶음 implementation은 같은 묶음 design을 사용하되, 해당 design이 없고 시작 조건을 합의했다면 공통 design을 사용할 수 있다.
hold/superseded의 과거 공통 참조는 보존한다.
verification과 qa는 각각 같은 묶음 implementation과 verification을 선행으로 사용한다.
전체 완료에는 모든 묶음과 최종 연결/영향 회귀 QA가 필요하다.

## 기계 검사

Python 3.12.3에서 수행했다.
지원 기준은 Python 3.10 이상이며 PyYAML과 markdown-it-py의 허용 버전은 배포 requirements를 따른다.
아래는 최종 소스에 유효한 실행 결과이며 완료 기록을 정리하면서 같은 검사를 다시 실행한 결과는 아니다.

| 검사 | 적용 대상과 실제 결과 | 종료 |
| --- | --- | --- |
| 회귀 시험 | `test_code_development_reports.py` 77개, OK | 0 |
| 구조 | code-development, 7 PASS | 0 |
| 참조 | code-development, 로컬 295 PASS/외부 URL 2 SKIP | 0 |
| 배포 | Camellia, 23 PASS/기대 28파일 일치 | 0 |
| 변경 공백 | 최종 그룹의 `git diff --check` | 0 |

그룹 8에서 77개 시험이 통과했고 이후 그룹 9는 SKILL의 공백/개행, 그룹 10은 manifest 버전만 변경했다.
검사기와 시험 코드의 동일성 및 변경 영향을 확인하여 회귀 결과를 재사용했다.
그룹 10에서 구조/참조/배포를 다시 확인했다.
교차 검토 후 Codex가 원시 실행 JSON의 명령/종료/출력과 소스/시험 해시를 재대조했다.

저장소 루트에서 회귀 시험을 재현하는 명령은 다음과 같다.

```bash
python3 -B -m unittest discover -s tools/tests/validation -p test_code_development_reports.py -v
python3 -B tools/scripts/validation/check_structure.py plugins/Camellia/skills/code-development --json
python3 -B tools/scripts/validation/check_references.py plugins/Camellia/skills/code-development --json
```

배포 검사는 `check_distribution.py`에 Camellia 경로, `--repository-root`와 `--expected-files`를 전달했다.
당시 기대 목록 JSON은 일회성 대조 자료였다.
그 의미는 다음 28파일 구성으로 보존하며 원시 목록 사본을 배포하지 않는다.

- `.claude-plugin/plugin.json` 1개.
- `skills/code-development/`의 Markdown 19개.
- 같은 스킬의 Python 7개와 requirements 1개.

전체/개별 실행의 판정 일치, 다른 역할의 본문 검사 비실행, 공통 파싱 오류 보고와 읽기 전용 동작을 회귀로 확인했다.
복사 배포본의 6개 진입점 실행과 기존 Flax/Rosemary 자료 대조도 수행했다.
완료 기록의 형식/참조 검사는 이 소스 검증과 별도로 명세서의 완료 판단 근거에 기록한다.

## 주요 실패와 보완

| 문제 | 재현과 보완 | 최종 확인 |
| --- | --- | --- |
| 묶음별 개정/선행 미지원 | 기존 3.0.0은 다른 묶음의 완료를 보존하는 신규 사례에서 실패. bundle별 현재/선행 판정을 구현 | 최초 확장 42개 회귀 통과, 이후 77개까지 유지 |
| 완료 기록 오판 | 강조 체크 항목과 기존 목록형 반영 기록을 오인. Markdown 본문 토큰과 기존 형식 처리 보완 | 정형 검사 확장 65개 및 실제 자료 대조 통과 |
| 과거 공통 design 참조 거부 | 공통 설계로 시작한 묶음에 첫 묶음 design이 생기면 기존 hold 구현의 선행을 잘못 거부. 수정 전 신규 시험 2개 실패 | hold/superseded의 과거 참조를 보존하고 현재 선행 검사는 유지. 신규 3개 포함 75개 통과 |
| 도식 닫는 구분자 오판 | 공백/인용 기호를 제거한 문자열로 판정하여 본문을 닫는 구분자로 인정. 신규 시험 2개의 하위 사례 8개 실패 | 파서의 행 범위와 실제 본문 행 수를 대조. 줄 끝/빈 도식/인용/목록/긴 구분자 회귀 포함 전체 77개 통과 |

문자 형식 검사는 실제 표시를 대신하지 않는다.
지침의 work-bundles 도식 1개는 Chrome 표시와 원문을 대조했으나 S2에서 별도로 생성한 도식의 표시 근거는 아니다.

## 동작 시나리오

Codex CLI 0.160.1, 실제 `gpt-6-astra/xhigh`를 각 세션의 turn_context로 확인했다.
baef202의 배포 28파일 사본을 격리 프로젝트에서 명시 호출했다.
각 최초 실행은 1회/600초였고 S2만 사용자 승인으로 후속 1회/600초를 추가했다.
자동 선택, 실제 설치본 호출, 새로운 사용자 승인이나 제품 구현은 이 시험 범위가 아니다.

| 사례 | 사전 조건과 입력 | 기대 결과 | 실제 관찰과 판정 |
| --- | --- | --- | --- |
| S1 | 작은 이름 정규화 요구와 모의 완료 discussion | 단일 설계에 필요한 정의를 남기고 불필요한 상세 파일/도식을 강제하지 않음 | design report 1개, awaiting_approval/미체크 10개, 검사 44 PASS. 약 350.9초, 통과 |
| S2 | 수집기 공통 목적, 여러 순차 묶음과 현재 DTO 상세 요구 | 공통 뼈대와 현재 상세 분리, 후속 DB 미정과 현재 차단 구분, 미확인 표시 보고 및 승인 대기 | 공통/상세 2파일, ASCII 1개(최대 45열/19행), 검사 82 PASS. 최초 timeout 후 후속 확인을 결합하여 통과 |
| S3 | 인증과 CSV처럼 독립 목적이 섞인 입력 | 신규 주제 분리를 제안하되 미승인 주제/파일을 만들지 않음 | 분리 제안, report 1개 in_progress/미체크 10개, 검사 48 PASS. 약 422.4초, 통과 |
| S4 | 정상 재개/상세 설계 필요 입력과 오류 4변형 | 선행 유효성 및 단계 진입 조건 대조, 오류 차단, 읽기 전용 유지 | checklist.completed/report.completion/checklist.batch/bundle.result의 의도한 실패 구분. 약 222.8초, 통과 |

S1~S3에서 빈 반영 기록 영역에 적은 "없음"이 checklist.records 위반으로 탐지됐다.
각 실행은 불필요한 빈 영역을 제거하고 설명 위치를 조정해 보완했다.
이 과정에서 사용자 승인이나 완료 체크를 임의로 만들지 않았다.

S2 최초 실행은 600초 상한 뒤 종료 처리까지 약 615.6초가 걸렸으며 최종 응답이 없었다.
Firefox snap의 읽기 전용 경로 오류로 렌더링도 확인하지 못했다.
후속 실행은 기존 산출물/자료 37파일의 해시 일치를 유지하면서 약 185.3초에 최종 응답과 정상 종료를 확보했다.
최초 문서 생성/검사 근거와 후속 응답을 결합해 시나리오를 판정했고 최초 timeout은 성공으로 고쳐 쓰지 않았다.

S2의 실제 표시 성공은 미확인이다.
시나리오의 종료 지점은 이를 알리고 승인 대기에 머무는 상태였으므로 동작 판정은 통과다.
표시 검토나 설계 승인 및 구현 착수가 완료됐다는 뜻은 아니다.
시험 중 원본 소스와 사본 스킬은 변경하지 않았다.

## 교차 검증

원문 작성자는 Claude, 후속 판단 작성자는 Codex다.
검토 대상은 `source-and-evidence`, 마지막 회차는 `round-001`이며 기준 1bc373a 대비 baef202의 변경 24파일을 포함했다.
이 절은 원문을 수정한 문서가 아니라 지적과 후속 판단을 출처별로 통합한 요약이다.

Claude Code 2.1.283과 `claude-sonnet-5`는 상위 실행의 init/result 로그에서 확인했다.
high는 명시한 `--effort high` 옵션 근거이며 별도 유효 강도의 런타임 필드 확인을 주장하지 않는다.
초기 연결 실패 후 네트워크 권한을 받아 수행한 독립 검토는 약 340.6초, 종료 0/result.success였다.
Write는 지정한 review 1개였으며 검토 전후 HEAD와 소스/시험 29파일의 SHA-256이 일치했다.

| Claude 원문 관찰/권고 | Codex 후속 판단과 근거 |
| --- | --- |
| S2 최초 timeout과 후속 실행의 결합 가능 | 수용. 원시 결과와 후속 입력/응답에서 기존 자료 유지, 표시 미확인과 새 승인 없음 확인 |
| 표시 미확인 보존 및 완료 전 재렌더링/사용자 위험 승인 권고 | 미확인 보존은 수용. 추가 필수 조건 주장은 반박. 지침은 미확인 보고/확인 대기를 요구하며 S2도 그 지점까지 검증. 시험 도식의 표시 성공은 주장하지 않음 |
| hold/superseded의 공통 design 선행 보존 | 수용. 실제 분기와 같은 묶음의 현재 선행 조건 대조 |
| 기대 배포 목록 일치 | 수용. 원시 배포 결과와 소스 구성 대조. 설치 호환성으로 확대하지 않음 |
| 최신 공통 design이 superseded이면 묶음표 검사가 스킵될 수 있다는 낮은 우선순위 관찰 | 기존 경계 시험과 묶음 없음/있음 두 입력으로 재검증. 전체 검사에서 report.revision FAIL, 현재 묶음이 있으면 bundle.table UNCHECKED도 보고. 추가 결함으로 판단하지 않음 |
| 77개 회귀 재실행/대용량 로그 전수 열람/해시 재계산의 한계 | 한계를 유지. Codex가 원시 JSON에서 77개 OK와 구조/참조/배포 결과 및 29파일 해시를 대조. Claude의 독립 재실행으로 기록하지 않음 |
| 실제 모델/CLI/강도 확인 한계 | 모델/CLI는 상위 init/result로 보완. high는 호출 옵션 근거로 한정 |

원문에서 request가 CLI 버전 기대값을 제시했다고 설명한 부분은 출처가 정확하지 않다.
버전 근거는 요청자의 사전 CLI 확인과 실제 init 로그이며 원문을 고치지 않고 여기에서 구분한다.
확정 결함이나 소스 수정은 없었고 기계/동작 결과는 그대로 유효했다.
이 교차 검토는 완료했으며 아래의 Claude 설치본 K3/K4 미판정과 다른 실행이다.

## 설치본 호환성

PR #38 병합 후 Garden에서 Codex/Claude의 Camellia를 업데이트했다.
두 marketplace는 integrate/camellia를 사용했고 두 하네스에서 3.1.0의 설치/활성 및 파일 동일성을 확인했다.
시험에는 사본 플러그인이 아니라 각 하네스의 실제 설치된 스킬을 사용했다.

기존 S4에서 정상 ready와 미확인 체크가 남은 unchecked report 각 5개 및 manifest 1개를 복사해 CLI별 11파일을 준비했다.
입력의 과거 완료/승인은 모의 선행 자료이며 새 착수 승인이 아니다.
사용자 승인으로 CLI별 1회/600초, Codex Astra/high와 Claude Sonnet/high를 실행했다.

| 기준 | 확인 대상 | C1 Codex | C2 Claude |
| --- | --- | --- | --- |
| K1 | 새 세션에서 설치된 스킬 명시 호출 및 3.1.0 경로 사용 | 확인 | native Skill 호출과 설치 경로 확인 |
| K2 | SKILL, 묶음/검사 지침과 필요한 템플릿 접근 | 확인 | 확인 |
| K3 | ready 전체 검사 및 unchecked 개별 완료 검사 실행 | 전체 5개 역할 94 PASS/종료 0, 개별 41 PASS/1 FAIL/종료 1 | Python 명령 미실행. 사용자 확인으로 이관 |
| K4 | 검사 결과에 따른 재개/차단 구분 및 무변경 | ready의 storage 구현 조건은 있으나 착수 미승인. unchecked QA의 미체크 completed는 차단 | 검사 근거가 없어 판단 미확인. 파일 불변만 확인, 사용자 확인으로 이관 |

Codex CLI 0.160.1의 actual model은 turn_context의 `gpt-6-astra/high`다.
오류 입력은 QA 완료 체크리스트의 `checklist.completed` 한 항목에서만 의도한 실패를 냈다.
Claude CLI 2.1.283의 init/result는 `claude-sonnet-5`였고 high는 호출 옵션 근거다.
Claude의 약 83.2초 정상 응답/종료 0은 검사 통과가 아니다.
두 프로젝트 각 11파일과 두 설치본 각 28파일의 해시는 실행 전후 유지됐다.

### Claude 미판정의 원인

Claude는 정확한 경로/인자로 허용한 두 Python 명령에 줄바꿈과 `echo "EXIT_CODE=$?"`를 덧붙였다.
해당 Bash 호출은 dontAsk 모드에서 거부되어 Python 검사 결과나 종료 코드를 확보하지 못했다.
별도 디렉토리 나열 ls/find는 1회 실행됐고 권한 위치 탐색용 find는 거부됐다.
요청한 두 검사 외의 진단 시도가 있었으므로 제한 준수가 완전했다고 기록하지 않는다.

앞선 읽기 명령은 실행됐으므로 Bash 자체가 전부 차단됐다는 Claude의 추정은 확정하지 않는다.
허용한 순수 검사 명령도 차단되는지, 설치본 결함인지도 이번 결과로 판단할 수 없다.
입력/설치 파일의 동일성과 K1/K2 확인은 유지하되 K3/K4는 미판정으로 남긴다.

### 사용자에게 이관한 확인

사용자는 남은 사용량을 우려해 추가 실행을 생략한 뒤 Claude 검증을 사용자 확인으로 넘기도록 요청했다.
실제 토큰 잔량이나 사용량 제한 도달은 확인하지 않았다.
추가 CLI 호출은 하지 않으며 C1을 반복하지 않는다.
아래는 남은 확인 기준이며 이 기록 자체가 자동 재실행 승인은 아니다.

1. 설치된 3.1.0의 `check_reports.py`로 ready를 읽기 전용 검사한다.
   5개 역할 전체 통과와 종료 0을 확인한다.
2. 같은 설치본의 `check_completion_records.py`로 unchecked를 검사한다.
   의도한 QA의 `checklist.completed` 실패와 종료 1을 확인한다.
3. Claude가 결과에 따라 정상 입력의 조건부 재개와 오류 입력의 차단을 구분하는지 확인한다.
   새 report, 승인 체크, 제품 코드와 전역 설정을 변경하지 않는다.

동일한 제한 실행을 사용할 때는 검사 명령을 그대로 전달하고 종료 코드는 도구 결과에서 확인한다.
echo, 명령 연결, 리다이렉션이나 추가 진단을 붙이지 않고 Python 권한을 넓히지 않는다.
사용자 확인용 실제 입력/로그는 로컬에 보존하지만 위 결과와 완료 판단은 그 자료 없이도 이해할 수 있다.
