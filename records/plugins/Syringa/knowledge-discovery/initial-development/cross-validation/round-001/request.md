# 1차 독립 검토의 대상과 기준

## 실행과 식별

요청자는 Codex이며 사용자가 Claude Sonnet / high의 읽기 전용 검토를 승인했다.
이 요청의 회차는 round-001이다.
0.1.0 미커밋 구현을 기준 커밋 `111946e4ce0698def89f797eda3410d167e9e7b7` 위에서 검토했다.
후속 문장 정리와 0.1.1 지침을 이 회차에서 다시 검토한 것은 아니다.

대상은 다음 15개 파일이다.
경로는 현재 위치로 표시하며 기록 디렉토리는 사용자 승인에 따라 initial-development로 변경됐다.

- 배포 파일 5개: plugin.json, SKILL.md, references/execution.md, references/model-selection.md, scripts/discovery.py.
- 저장소 연결 4개: .agents/plugins/marketplace.json, .claude-plugin/marketplace.json, README.md, .codex/config.toml.
- 개발 기록 4개: [명세서](../../specification.md), [설계](../../structure-design/script-design.md),
  [배포 기대 목록](../../mechanical-validation/expected-files.json), [검증 기록](../../behavioral-validation/plan.md).
- 검사 자료 2개: tools/tests/runtime/test_knowledge_discovery.py, tools/references/knowledge-discovery-tests.md.

배포 파일의 기준 경로는 plugins/Syringa/이며 manifest는 .claude-plugin/,
나머지는 skills/knowledge-discovery/ 하위다.
당시 discovery.py의 SHA-256은 다음과 같으며 0.1.1에서도 동일하다.

```text
5503e0053fd317ceefba1330c54ea7c34012cac785ffca387650ff5d1dd8a997
```

요청자는 검토 전후 15개 파일의 해시 일치를 확인했다.
이것은 검토자의 독립 해시 검증이 아니며 현재 문서가 당시와 같은 바이트라는 뜻도 아니다.
일회성 전체 해시 목록은 대상 식별에 필요한 위 정보로 통합했다.

## 검토 기준과 제외

[Aster 작업 규칙](../../../../../../../AGENTS.md),
[스킬 내용 규격](../../../../../../../standards/skills/skill-content.md),
[스킬 검증 규격](../../../../../../../standards/skills/skill-validation.md)과 명세 요건을 기준으로 삼았다.
검토 항목은 입력/범위와 일괄 승인, 의미 판단과 스크립트 책임 경계,
Git 루트/링크, 렌더링, 충돌/잠금/원자적 저장/복구, 시험 근거와 배포 경계다.
명세에 없는 요구를 새 필수 요건으로 삼지 않으며 확정 결함과 미확정 의심을 구분하도록 요청했다.

대상 파일과 전역 설정 변경, 새 AI 시나리오, 설치 및 실제 CLI 호출은 제외했다.
브랜치/커밋/원격 변경, 게시와 모델 성능 비교도 범위 밖이었다.
기존 시험 로그와 산출물은 읽기 근거로만 사용했다.

## 실행 실패와 재개

초기 API 실행 중단에 이어 OAuth 인증 만료로 검토가 시작되지 못했다.
핵심 오류는 "OAuth session expired and could not be refreshed"였다.
이 인증 실패 호출은 대상 읽기나 판정 근거로 계산하지 않았다.
사용자 인증 갱신 후 재개하여 정상 결과를 받았다.

[검토 결과 요약](review.md)은 Claude의 원래 판단을,
[후속 판단](resolution.md)은 Codex의 재현과 수용/반박을 구분한다.
사용자의 원문 축약 요청에 따라 핵심 내용을 이 세 문서에 남기고 인증 로그와 중복 원문은 정리했다.
