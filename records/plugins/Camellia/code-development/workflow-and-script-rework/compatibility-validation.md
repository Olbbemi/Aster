# Camellia 5.0.0 설치본 호환성 검증

## 대상과 현재 상태

대상은 PR #58의 병합 커밋 `868fcb15c7622de24f66b88b1601e7658dd204df`에 있는 Camellia 5.0.0이다.
플러그인 tree는 `7a047fee6f12ad4f67d63b455a66c988dc3eed31`이며 기능 커밋 dddda14의 배포 파일과 같다.
기능/관문 마감 커밋과 실제 병합을 확인했으며 호환성 진입 당시 in_review는 false였다.

설치와 인식/자료 접근은 Garden의 실제 근거를 수신하여 대조했다.
2026-10-12 제시한 K03/K04 범위와 모델/호출 수/격리 및 정리 조건을 사용자에게 승인받았다.
승인한 추가 실행을 마쳤으며 K01-K04는 현재 모두 통과다.
Claude의 최초 시도는 명령 형식에 따른 권한 거부로 미실행이었고 같은 조건의 재시험에서 통과했다.
이 문서의 계획 검사 통과를 실제 실행 승인이나 호환성 완료로 처리하지 않는다.

## 요건과 사례

요건의 정본은 [명세서](specification.md)의 지원 CLI, M4 실행 계약과 검증 기준이다.
이 표는 그중 설치/하네스 차이로 확인할 범위를 연결한다.
M1-M3의 내용 및 대화 흐름은 기존 [동작 검증](behavioral-validation.md)을 재사용한다.
M5는 배포하지 않는 개발용 검사이므로 설치본에서 실행할 항목이 아니다.

<!-- lifecycle-check:requirements -->

| 요건 ID | 필수 여부 | 범위 | 사유 |
| --- | --- | --- | --- |
| K-R1 | 필수 | 대상 | Codex/Claude가 실제 Camellia 5.0.0 설치본을 발견하고 명시 호출하며 공용 자료에 접근한다 |
| K-R2 | 필수 | 대상 | 양 CLI에서 설치된 내부 실행기 5개를 호출하고 의존성 로딩 및 정상 판정을 확인한다 |
| K-R3 | 필수 | 대상 | 양 CLI가 설치본의 대표 위반/오류와 종료 코드 및 JSON 판정을 구분한다 |

<!-- lifecycle-check:scenarios -->

| 사례 ID | 대응 요건 | 필수 여부 | 범위 | 기대 결과 | 사유 |
| --- | --- | --- | --- | --- | --- |
| K01 | K-R1 | 필수 | 대상 | Codex 새 세션이 5.0.0 스킬을 발견/명시 호출하고 해당 경로의 자료를 읽는다 | Garden 실제 실행 근거 재사용 |
| K02 | K-R1 | 필수 | 대상 | Claude 새 세션이 5.0.0 스킬을 발견/명시 호출하고 해당 경로의 자료를 읽는다 | Garden 실제 실행 근거 재사용 |
| K03 | K-R2, K-R3 | 필수 | 대상 | Codex가 설치본의 5개 정상 호출 및 대표 위반 1개/오류 1개를 실행하고 결과를 정확히 보고하며 입력과 설치본을 보존한다 | 사례 선정 당시 설치본 실행 및 결과 해석이 미확인 |
| K04 | K-R2, K-R3 | 필수 | 대상 | Claude가 설치본의 5개 정상 호출 및 대표 위반 1개/오류 1개를 실행하고 결과를 정확히 보고하며 입력과 설치본을 보존한다 | Codex의 결과를 Claude의 통과 근거로 대신하지 않음 |

## 재사용 근거와 대조

Garden이 실제 실행한 CLI는 Codex 0.162.1과 Claude Code 2.1.283이다.
소스 주입이나 --plugin-dir 없이 등록된 플러그인을 선택했다.
업데이트와 세션 실행 근거의 원시 자료는 공용 Garden 자료 경로의
`validation/20261012-camellia-5-installed-update.json`에서 확인했다.
이후 Aster에서도 두 설치본의 전체 경로 집합, 내용과 실행 권한을 Git 객체에 직접 대조했으며 각각 34개가 일치했다.

| 사례 | 실제 세션 및 관찰 | 한계 |
| --- | --- | --- |
| K01 | Codex 세션 01a12f08-e228-7162-afaa-11c9a508e670. CLI 종료 0 및 turn.completed. 5.0.0 SKILL.md/manifest와 지정 자료 읽기 명령 종료 0 | 실행기를 실행하지 않았다 |
| K02 | Claude 세션 ed2302f7-43e4-4110-bc42-9f3b401f6d3a. init 목록, Skill 호출의 설치 경로와 자료 읽기 성공. CLI 종료 0, result.is_error=false, 권한 거부 없음 | 실행기를 실행하지 않았다 |

읽은 자료는 workflow/report-checks/report-check-contract, discussion/review 템플릿,
실행기 5개/보조 모듈 4개/requirements의 15개다.
각 첫 12줄과 짧은 requirements 전체를 읽은 확인이며 모든 문서의 의미나 실제 실행까지 검증한 것은 아니다.
이번 두 설치본의 파일이 위 실행 대상과 같으므로 발견/명시 호출/자료 접근을 반복하지 않는다.

## 추가 실행의 입력과 판정

K03/K04는 각각 독립된 시험 프로젝트를 사용한다.
상위 세션이 기존 개발용 검사 fixture 형식을 재사용하여 고정 입력을 준비하고 경로/내용을 대조한다.
모의 report/리뷰/완료 기록은 시험 입력이며 사용자 승인이나 실제 업무 완료 근거가 아니다.
자식 에이전트에 새 단계 승인이나 사용자 역할의 모의 응답을 전달하지 않는다.

| 호출 | 입력 조건 | 기대 결과 |
| --- | --- | --- |
| check_task_start | 실제 존재하는 시험 프로젝트와 아직 등록/생성되지 않은 신규 주제의 명시 경로 | 종료 0, outcome=pass |
| check_stage_entry | 유효한 stages와 완료된 discussion, design 진입의 scope/base-report를 명시 | 종료 0, outcome=pass |
| check_report_submission | 유효한 design report와 manifest | 종료 0, outcome=pass |
| check_review_receipt | 같은 design report를 대상으로 하는 정상 review를 명시 | 종료 0, outcome=pass |
| check_task_completion | 전체 필수 단계와 승인 기록을 갖춘 별도 고정 fixture의 완료 QA report를 명시 | 종료 0, outcome=pass |
| check_report_submission 위반 | 정상 design 입력의 사본에서 manifest의 reference_reports 필드만 제거 | 종료 1, outcome=fail, C2 위반 |
| check_report_submission 오류 | 별도 정상 사본에서 manifest의 stages 필드만 제거 | 종료 2, outcome=error, C2 오류 |

각 명령은 실제 발견한 설치본 scripts 경로에 python3 -B로 실행하며 모든 경로/인자를 명시한다.
시험 입력에는 project-root/topic-dir/report/review/base-report의 실제 출처를 제공한다.
--json 출력의 checker/inputs/outcome/exit_code 및 필수 필드를 확인하고 실제 프로세스 종료 코드와 대조한다.
위반/오류를 시험 성공으로 해석하는 이유는 입력 조건과 기대 결과가 일치하기 때문이며 제품 입력 자체의 통과로 보고하지 않는다.

상위 세션은 호출 로그의 실제 명령/경로/종료/원시 JSON과 자식의 해석을 대조한다.
설치본 파일, 시험 fixture와 report의 전후 해시가 같아야 한다.
실제 설치본 대신 저장소 사본이나 복사한 실행기를 사용하면 해당 사례는 통과로 판정하지 않는다.

## 승인 당시 환경, 호출 계획과 중단 조건

- 설치 경로: Codex는 ~/.codex/plugins/cache/aster/camellia/5.0.0,
  Claude는 ~/.claude/plugins/cache/aster/camellia/5.0.0을 실제 선택한 경로와 대조한다.
- 최초 AI 호출 계획은 CLI별 새 세션 1회, 합계 2회였다. 각 세션에서 내부 실행기 7회, 총 14회를 호출한다.
- 모델은 기존 작업의 Codex Astra/high와 Claude Opus/high로 확정했다.
  실행기의 실제 선택 모델은 세션 근거로 확인하며 사용자 진술과 구분한다.
- Codex는 lifecycle scenario_runner를 사용하고 Claude는 직접 CLI로 실행한다.
  Claude 호출에는 자동 메모리 비활성화를 적용하고 Read/Skill/Bash 중 필요한 권한만 허용한다.
- 쓰기 대상은 공용 Camellia 로컬 자료의 workflow-and-script-rework/compatibility-validation 아래 시험 프로젝트/로그다.
  설치 캐시, 전역 설정, 실제 사용자 프로젝트와 승인 기록은 수정하지 않는다.
- 소요 시간은 모델 응답과 도구 실행에 따라 달라지며 두 AI 호출에 수 분 이상 걸릴 수 있다.
  전체 B01-B07이나 정형 회귀 869개를 반복하는 계획이 아니다.
- 의존성을 자동 설치하지 않는다. 경로/권한/환경 문제, 예상 밖 파일 변경 또는 판정 불일치가 있으면 원인을 확인하고 해당 사례를 중단한다.
  실패를 자동 승인/무조건 재시도로 덮지 않으며 재시험 조건 변경은 사용자와 확인한다.
- 원시 결과와 시험 입력은 판정 및 필요한 후속 확인까지 보관한다.
  최종 근거를 기록한 뒤 이 시험에서 만든 자료만 정리한다.

<!-- lifecycle-check:results -->

| 사례 ID | 상태 | 근거/사유 |
| --- | --- | --- |
| K01 | 통과 | Garden의 실제 Codex 세션 근거와 현재 설치본 34개 대조 |
| K02 | 통과 | Garden의 실제 Claude 세션 근거와 현재 설치본 34개 대조 |
| K03 | 통과 | 실제 설치본 7개 호출과 원시 결과/종료 코드 및 파일 보존을 상위 세션에서 대조 |
| K04 | 통과 | 최초 명령 거부를 보존하고 동일 조건 재시험의 7개 호출 및 파일 보존을 대조 |

## 추가 실행 결과

| 항목 | K03 Codex | K04 Claude |
| --- | --- | --- |
| 실제 모델 | gpt-6-astra/high. 세션 turn_context에서 확인 | claude-opus-5-5, --effort high. result의 modelUsage와 호출 인자에서 확인 |
| 세션 | 01a12f13-a357-7f71-a6f3-38ed55d312f6 | 재시험 91e56ea4-52d4-4ab7-a4e2-d7d328325256 |
| CLI 전달 | 종료 0, runner success=true, turn.completed 확인 | 종료 0, is_error=false, permission_denials=[] |
| 실제 검사기 실행 | 7회, 모두 기대 일치 | 7회, 모두 기대 일치 |
| 실행 환경 | Python 3.12.3, PyYAML 6.0.1, markdown-it-py 3.0.0 | Python 3.12.3, PyYAML 6.0.1, markdown-it-py 3.0.0 |
| 입력/설치본 보존 | 사전 파일과 SHA-256/모드 동일 | 최초 시도 및 재시험 이후 사전 파일과 SHA-256/모드 동일 |
| 생성 파일 | results 안의 원시 JSON/stderr/calls.json 15개 | results 안의 원시 JSON/stderr/calls.json 15개 |

양쪽 모두 정상 실행기 5개는 각각 종료 0/outcome=pass였다.
reference_reports 누락은 종료 1/outcome=fail, C2.reference_reports fail이었다.
stages 누락은 종료 2/outcome=error, C2.stages fail과 C2.stage_dependency/C5.dependency error를 함께 반환했다.
확인 가능한 위반과 종속 판정 불가를 동시에 보존하는 계약과 일치했다.

상위 세션에서 각 원시 JSON의 필수 스키마, checker, 실제 argv와 inputs의 일치,
프로세스/JSON 종료 코드, outcome과 기대값 및 C2 세부 규칙을 직접 대조했다.
stderr는 14개 모두 비어 있었다.
두 자식의 최종 응답도 정상/위반/오류를 구분했으며 모의 완료 기록을 실제 업무 완료로 해석하지 않았다.
사례 판정은 전달 성공만이 아니라 원시 결과와 전후 파일 대조에 근거한다.

### Claude 최초 시도와 복구

최초 세션 cb9d9874-08a5-4cb3-b855-b1246e21a06d는 종료 0/is_error=false였지만 시험은 미실행이었다.
지정 driver 명령 뒤에 `; echo "DRIVER_EXIT=$?"`를 덧붙여 제한한 Bash 허용 명령과 맞지 않았고,
permission_denials에 그 명령이 남았다. driver와 7개 검사기는 실행되지 않았으며 results도 없었다.
이를 CLI 정상 종료만으로 통과 처리하지 않았다.

상위 세션이 실패 원인과 미실행 상태를 확인한 뒤 단일 명령만 전달하도록 입력의 명령 안내를 보완했다.
Read/Skill/Bash의 허용 범위, dontAsk 모드, fixture, 설치 대상과 기대값을 유지했다.
권한을 넓히거나 상위 세션에서 검사를 대리 실행하지 않았다.
같은 목적/조건의 명령 구성 오류 수정에 해당하여 시나리오 절차에 따라 추가 범위 승인 없이 한 번 재시험했다.
재시험에서는 명령 한 번으로 7개 호출을 마쳤고 권한 거부가 없었다.

AI 호출은 계획된 2회에 Claude 복구 1회를 더한 총 3회였다.
실제 설치본 검사기 호출은 최초 Claude에서 실행되지 않아 계획한 총 14회다.
최초 미실행 로그와 재시험 로그는 별도로 보존한다.

## 판정과 보존

K01-K04와 대응 필수 요건은 모두 통과했다.
배포 소스와 설치본의 동일성, 양 CLI의 발견/명시 호출/자료 접근 및 실제 실행/판정과 비변경성을 확인했다.
현재 범위의 미실행/미판정 필수 호환성 항목과 제품 수정 사항은 없다.
전체 업무 유형을 다시 검증한 것은 아니며 기존 동작/정형 검증은 동일 소스 및 변경 영향 대조에 따라 재사용한다.

원시 자료는 공용 Camellia 작업 자료의 workflow-and-script-rework/compatibility-validation 아래에 둔다.
K03의 inputs/turns/project, K04의 inputs/events/retry-01-events/project와 baseline,
adjudication.json 및 created-materials.json은 최종 사용자 검토와 필요한 이의 재현까지 한시 보존한다.
정리 조건은 [명세서 완료 근거](specification.md#생명-주기의-완료-여부를-판단한-근거)를 따른다.
시험 자료만 정리하며 설치 캐시와 Garden의 원시 자료는 Aster에서 변경하거나 삭제하지 않는다.
호환성 완료와 전체 생명 주기 완료를 구분하며 최종 커밋 관문은 명세서에서 관리한다.
