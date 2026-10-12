# code-development M1-M5 독립 교차 검증 요청

## 작성자

Codex. 2026-10-12 사용자의 "클로드 교차검증까지 진행해줘" 요청에 따라 작성했다.
검토자는 Claude Opus/high이며 새 CLI 호출의 실제 모델 식별자는 반환 메타데이터로 별도 확인한다.

## 검증 대상과 대상 상태

저장소는 /home/olbbemi/Project/Aster다.
브랜치는 work/camellia/workflow-and-script-rework, 기준 HEAD는 f6a22877d15ab2af662e900209f7251224c4d0d4다.
대상은 이 HEAD에 대한 미커밋 수정/삭제와 미추적 신규 파일을 포함한 현재 작업 트리다.
기존 outline-first-development 브랜치나 그 명세는 이번 확정 근거로 승계하지 않는다.

요건과 실제 작업의 입구는 [명세서](../../../specification.md)다.
보조 근거는 [M5 설계](../../../structure-design/developer-checks.md),
[정형 및 지침 대조](../../../validation.md), [실제 AI 시험](../../../behavioral-validation.md)다.
이 문서의 기존 판정을 정답으로 취급하지 말고 독립적으로 실제 파일과 증거를 대조하십시오.
명세서의 current_stage는 problem-definition으로 남아 있다.
사용자가 순서별 부분 구현/검증을 승인했고 전체 생명 주기의 선행 조건/단계 표시 정리는 남아 있다.
이 기록 상태와 제품 결함, 후속 완료 관문을 구분하여 지적하십시오.

## 검증 항목과 판정 기준

1. M1: Claude 자동 메모리 비활성화가 호출 한정인지, 명령/권한/기록과 실제 관찰 구분이 일관되는지 확인하십시오.
2. M2: 혼합 대화, 뼈대 우선 질문, 현재 필수 결정과 후속 상세, 번들 후보/확정/진입 및 기존 승인 경계가 충돌하지 않는지 확인하십시오.
3. M3: 중간 저장/번들 진입/회귀/마지막 QA의 문서 완결성과 도식/타입/구현 대응, 과거 승인 본문 보존 및 전체 대조가 일관되는지 확인하십시오.
4. M4: 독립 실행기 5개와 공통 모듈의 CLI/입력/수집 범위/C1-C14 판정/예외/0,1,2 출력/읽기 전용 계약을 코드에 대조하십시오.
   파일 이름이나 현재 상태만으로 의미/승인을 추정하거나 위반을 놓치는 사례, 실행 오류의 오분류와 호환 형식 회귀를 특히 확인하십시오.
5. M5: 독립 개발용 검사 5개/지원 모듈/등록이 명세의 기대값을 검증하는지 확인하십시오.
   대상 코드를 판정 오라클로 재사용하거나 검사 범위가 빠지는지, revision과 작업 트리 격리,
   오류/시간 제한/JSON 계약과 변경 스킬 선택의 기존 pre-push 연결을 대조하십시오.
6. 검증 기록 1-4번의 근거가 결론을 실제로 뒷받침하는지 확인하십시오.
   최초 실패, fixture 준비 결함, B06의 자식 네트워크 실패와 승인된 상위 대리 호출을 구분하십시오.
   불확실한 의심은 확정 결함과 구분하고 필요한 최소 재현 방법을 적으십시오.

우선 기준은 명세서의 확정 M1-M5 및 배포용 report-check-contract.md와 개발용 code-development-tests.md다.
standards/skills/skill-content.md, skill-layout.md, skill-validation.md와 repository-layout.md,
work-data.md 및 .github/git-workflow.md의 관련 범위도 대조하십시오.
계약에 없는 새 제품 요구사항을 검사 코드나 리뷰만으로 강제하지 마십시오.

## 검증 범위와 제외 범위

다음 경로의 현재 내용 전체와 관련 변경을 검토하십시오. 상대 경로 기준은 저장소 루트입니다.

- plugins/Camellia/skills/code-development/ 전체. 신규 Python 9개와 문서/템플릿, 이전 Python 7개 삭제 포함.
- tools/tests/skills/code-development/ 전체. 개발용 Python 7개, checks.json과 이전 unittest 파일 삭제 포함.
- tools/references/code-development-tests.md, tools/references/skill-pre-push.md 및 README.md의 관련 변경.
- records/plugins/Camellia/code-development/workflow-and-script-rework/의 명세/설계/검증 기록.
- 연결 확인용 tools/scripts/git/pre-push 및 operations의 스킬 검사 호출 코드와 tools/tests/git/test_check_push.py.
  이 공용 코드는 이번 제품 변경이 아니므로 관련 연결의 회귀 여부만 확인하십시오.

원시 근거는 data/cargo/work/plugins/Camellia/code-development/workflow-and-script-rework/의
validation/과 behavioral-validation/ 아래에 있습니다.
원시 이벤트는 길 수 있으므로 필요한 사례/파일을 골라 기록의 진위를 확인하십시오.
검토 시점 파일 목록/해시와 tracked diff는 같은 로컬 자료 루트의 cross-validation/round-001/에
target-state.json과 tracked.patch로 보존합니다. 신규 파일은 목록의 실제 현재 파일을 읽으십시오.
대상 소스/명세는 리뷰가 끝날 때까지 요청자가 변경하지 않습니다.

이번 범위는 독립 소스/근거 검토이며 테스트 재실행, 추가 AI 호출, 설치/배포, Git 변경과 전역 설정 수정은 제외합니다.
실제 재현이 필요하면 명령/최소 입력/기대값과 의심 결과를 적어 요청자에게 전달하십시오.
설치본 호환성은 후속 검증이며 이 리뷰로 완료 처리하지 마십시오.
현재 대화는 부분 검증 5번의 수행 승인입니다. 커밋 전 검토/버전 결정/커밋과 단계 최종 마감은 별도입니다.

## 검토자의 실행과 산출물

사용자가 승인한 직접 Claude 호출입니다. 자동 메모리 환경 변수는 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1입니다.
옵션은 -p, --model opus, --effort high, --tools Read,Write,
범위별 Read와 지정 리뷰 한 파일의 Edit 권한, --permission-mode dontAsk,
--no-session-persistence, --disable-slash-commands, --strict-mcp-config,
--setting-sources project, --output-format json입니다.
검토자에게 전달된 옵션과 직접 확인한 동작을 구분하고 종료 코드는 미리 적지 마십시오.

유일한 쓰기 대상은 이 요청과 같은 디렉토리의 review.md입니다.
원본 소스/기록/이 요청/설정/메모리를 수정하지 마십시오. 리뷰 작성 후 Read로 확인하십시오.
assets/work-records/cross-validation-review-template.md의 필수 정보를 갖춰 한국어로 작성하십시오.
작성자/확인 가능한 실제 모델, 전체 및 항목별 판정, 심각도와 지적 ID, 파일/행/근거/재현/영향,
개선 방향과 확인하지 못한 사항을 포함하십시오. 지적이 없으면 실제 확인 범위와 한계를 적으십시오.
Git에 보존할 리뷰의 로컬 링크는 리뷰 파일 기준 상대 경로로 쓰십시오.
