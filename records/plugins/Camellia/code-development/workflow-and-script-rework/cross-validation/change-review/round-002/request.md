# code-development 계약/코드 보완 독립 재검토 요청

## 작성자와 대상

Codex. 사용자의 "마저 진행하자" 요청으로 수정 후 Claude 독립 재검토를 진행한다.
검토 모델은 기존 승인한 Claude Opus/high이며 호출 별칭과 반환 실제 모델은 구분한다.
대상은 work/camellia/workflow-and-script-rework의 현재 미커밋 코드/문서다.
기준 HEAD와 실제 읽을 파일 해시는 로컬 cross-validation/round-002/target-state.json에 기록한다.
검토가 끝나기 전 대상 파일은 변경하지 않는다.

## 범위와 기준

1. plugins/Camellia/skills/code-development/scripts/의 Python 9개 전체와 requirements.txt를 읽고
   report-check-contract.md, report-checks.md 및 guidelines.md의 manifest 규칙에 대조하십시오.
2. tools/tests/skills/code-development/의 Python 7개 전체와 checks.json을 읽고
   tools/references/code-development-tests.md 및 [검사 설계](../../../structure-design/developer-checks.md)에 대조하십시오.
3. [1차 원문 리뷰](../round-001/review.md)의 F1/F2/F3/F4/F5/F8/F9/I2에 관해
   현재 구현과 자연어 계약의 대응, 보호 사례의 검출력 및 수정으로 생긴 회귀를 독립 판정하십시오.
   이전 작성자 판정은 정답이 아니며 현재 코드/정본 계약을 먼저 대조하십시오.
4. [정형 결과](../../../validation.md)의 마지막 절을
   로컬 validation/cross-review-fixes의 실행 JSON, execution.json과 mutations.json에 대조하십시오.
   테스트 통과만으로 코드가 모든 입력을 보장한다고 판단하지 마십시오.
5. 기존 리뷰에서 채택되지 않은 F6/F7/I1/I3는 새 근거로 확정할 결함이 있을 때만 다루십시오.
   계약에 없는 새 요구사항을 임의로 강제하지 마십시오.

특히 초기 공통 모듈 로딩 오류의 텍스트/JSON/명시 인자 보존, 옵션 중복,
H2 제목 링크만 사용하는 신규 등록/선택, 위반 1과 종속 오류 2,
fixture 준비 실패 2와 대상 기대값 불일치 1, CommonMark 도식 닫힘,
C10 이름/디렉토리명 사례의 독립 검출을 확인하십시오.
실제로 읽은 전문과 diff만 읽은 범위, 원시 근거를 읽지 못한 항목을 구분하십시오.

명세서와 이전 M1-M3 및 AI 결과는 맥락을 확인할 때 읽으십시오.
이 회차는 수정 영향에 집중하며 M1-M3의 전체 재검토나 실제 AI 시나리오 재실행을 요구하지 않습니다.
적용 규격은 standards/skills/skill-content.md, skill-layout.md, skill-validation.md,
standards/repository-layout.md와 관련 Git/작업 데이터 규격입니다.

## 제외와 수행 제한

테스트 실행, 추가 AI 호출, 설치, 커밋/푸시/브랜치 변경과 전역 설정 변경은 제외합니다.
재현이 필요하면 최소 입력/명령/기대값/의심 결과를 기록하여 요청자에게 전달하십시오.
전체 lifecycle 단계/커밋 관문과 설치본 호환성은 후속이며 이 리뷰로 통과 처리하지 마십시오.

CLAUDE_CODE_DISABLE_AUTO_MEMORY=1을 이 직접 호출에만 전달합니다.
--model opus --effort high, Read/Write, 지정 경로 읽기와 review.md 한 파일 쓰기를 허용합니다.
--permission-mode dontAsk --no-session-persistence --disable-slash-commands
--strict-mcp-config --setting-sources project --output-format json으로 실행합니다.

유일한 쓰기 대상은 이 요청과 같은 디렉토리의 review.md입니다.
이전 리뷰, 소스, 계약, 요청과 전역/프로젝트 설정은 수정하지 마십시오.
assets/work-records/cross-validation-review-template.md의 필수 정보에 맞춰 한국어 리뷰를 작성하고 다시 읽어 확인하십시오.
전체 및 항목별 판정, 심각도/지적 ID, 파일/행/근거/최소 재현/영향과 미확인 사항을 기록하십시오.
확인 가능한 실제 모델과 전달받은 호출 정보, 직접 확인한 결과를 구분하십시오.
호출 종료 코드를 미리 기록하지 마십시오. 로컬 링크는 리뷰 위치 기준 상대 경로를 사용하십시오.
