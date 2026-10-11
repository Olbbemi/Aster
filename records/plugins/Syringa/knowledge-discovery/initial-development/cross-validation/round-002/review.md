# Knowledge Discovery 분리본 독립 검토 결과 (round-002)

## 작성자

Claude Sonnet / high. Codex가 작성한 분리본에 대한 독립 읽기 전용 검토이며, round-001(이전 단일 구현 기준)과는 별개의 판단이다.

## 전체 판정

**확정 결함 없음.** 검토 범위에서 실제로 읽고 대조한 코드·지침·검사·동작 증거 사이에 요건(R1-R11) 위반이나 저장/승인/경로 안전성 결함을 발견하지 못했다. 아래 "미확인 사항과 검증 한계"에 적은 범위 밖 항목을 제외하면 보고할 지적이 없다.

## 확인 범위

- **스킬 전체**: `SKILL.md`, `references/workflow.md`, `references/execution.md`, `references/model-selection.md`, `references/stages/{preparation,candidate-proposal,approval,analysis-and-save,completion}.md`을 전부 읽었고, `SKILL.md → workflow.md → stages/*.md`의 호출 시점·인계 조건이 서로 모순 없이 연결됨을 확인했다. 직접 호출 스크립트 7개(`inspect_inputs.py, start_run.py, read_source.py, propose_candidates.py, approve_candidates.py, save_topic.py, run_status.py`)와 공통 모듈 4개(`runtime_common.py, source_access.py, run_state.py, storage_recovery.py`)의 import 그래프를 전부 추적했다. 7개 스크립트는 서로를 import/호출하지 않고 공통 모듈만 의존하며, 공통 모듈 간 의존 방향(`runtime_common ← source_access ← run_state ← storage_recovery`)도 `structure-design/script-design.md`의 표와 정확히 일치한다. `execution.md`에 나열된 오류 코드 11개(`MISSING_INPUT, INVALID_TARGET, INVALID_OUTPUT_ROOT, SCOPE_VIOLATION, SOURCE_CHANGED, INVALID_PAYLOAD, INVALID_STATE, APPROVAL_MISMATCH, TOPIC_CONFLICT, IO_ERROR, RECOVERY_REQUIRED`)를 코드 전체에서 `grep`으로 대조한 결과 미문서화 코드는 없었다.
- **검사 코드**: `tools/tests/skills/knowledge-discovery/`의 6개 등록 검사 파일과 보조 모듈 2개(`repository_support.py`, `check_support.py`), `checks.json`, `tools/references/knowledge-discovery-tests.md`를 전부 읽었다. 커밋 스냅샷 격리(`Repository.resolve`/`files`가 심볼릭 링크·하위 저장소를 오류로 거부), `snapshot()`의 임시 사본 검증, `run_check()`의 boolean `passed`/종료 코드(0/1/2) 매핑을 코드 레벨에서 확인했다. 6개 파일의 테스트 메서드 수를 직접 세어 3+9+4+4+9+4=33개로, 명세서가 기록한 "33개 항목"과 정확히 일치함을 확인했다. 일회성 마이그레이션 검사나 명세서/다른 스킬을 강제하는 검사는 발견하지 못했다.
- **README.md / skill-pre-push.md**: 이번 변경은 각각 한 줄 안내 추가(README 표 항목, skill-pre-push.md의 등록 스킬 목록)로 한정되어 있었다. `tools/scripts/git/operations/check_push.py`는 읽기만 했으며(수정하지 않음), `SKILL_PATH` 정규식이 `plugins/Syringa/skills/knowledge-discovery`를 올바르게 캡처하고, `registered_scripts()`가 `checks.json`의 `scripts` 목록·심볼릭 링크 금지·정규 파일 요구를 검증하는 것을 확인했다. 이 호출 계약은 `tools/references/skill-pre-push.md`와 `.github/git-workflow.md`의 서술과 일치한다.
- **명세서 대조**: `specification.md`(전체 893행), `structure-design/script-design.md`, `mechanical-validation/expected-files.json`, `behavioral-validation/plan.md`를 전부 읽고 R1-R11 각 항목을 실제 파일 경로·코드와 1:1로 대조했다. `expected-files.json`의 21개 파일 목록이 실제 `plugins/Syringa/` 디렉토리 구성과 정확히 일치함을 확인했다.
- **적용 기준**: `standards/skills/skill-content.md`, `skill-layout.md`, `skill-validation.md`, `.github/git-workflow.md`의 "스킬 파일의 pre-push 검사" 절을 읽고 SKILL.md frontmatter(`name: knowledge-discovery`가 디렉토리명과 일치, 소문자/하이픈 규칙 충족), 단계적 공개 원칙, 구조 검증 항목과의 부합을 확인했다.
- **실제 동작 증거**: `data/cargo/.../behavioral-validation/split-flow-retry-20261012/`의 `normal-flow`/`invalid-output-root` 두 사례에서 `state.json`, `turns/02-response.md`, `turns/03-response.md`, `turns/04-response.md`, 최종 저장 파일(`knowledge-20261012-020439-rust.md`), `invalid-output-root/turns/01-response.md`를 직접 읽었다. 디렉토리 구조만 먼저 제시하고 범위를 재질문한 것, 자료에서 Rust 3개/PostgreSQL 2개 후보를 제시하고 승인 대기에서 멈춘 것, PostgreSQL 제외 후 Rust 3개만 한 파일에 저장되고 `phase: completed`가 된 것, `Option<T>`가 `Option\<T\>`로 이스케이프되어 보존된 것, 잘못된 하위 경로 출력 루트가 `INVALID_OUTPUT_ROOT`로 거부되고 자동 대체 없이 종료된 것을 각각 기록과 대조해 확인했다. `round-002/baseline.json`에 적힌 36개 파일 경로 목록이 실제 git status의 변경 파일 범위와 부합함도 확인했다.

## 지적

없음. 심각도를 매길 확정 결함이나 재현 가능한 위반을 찾지 못했다.

## 참고로 남기는 경미한 관찰 (결함 아님, 추정)

- `save_topic.py`의 파일명 접미사 재시도 루프(`while True: ... suffix += 1`)에는 상한이 없다. 명세서도 상한을 요구하지 않고 "다음 접미사로 시도한다"고만 규정하므로 이는 명세 위반이 아니며, 현실적인 충돌 빈도에서 문제가 될 가능성도 낮다고 판단한다. 필수 결함으로 제시하지 않는다.
- `read_source.py`의 `read_file()`은 `Path(args.file).resolve()`를 `strict=True` 없이 호출한다. `state["files"]`의 키는 `start_run.py`에서 `resolve(strict=True)`로 고정되므로 실제로는 항상 일치해야 하는 경로만 키 조회에 성공하고, 존재하지 않는 경로는 `regular_bytes`의 `SOURCE_CHANGED`에서 걸러진다. 동작에 영향을 주는 차이를 찾지 못해 결함으로 보지 않는다.

## 미확인 사항과 검증 한계

- **해시 독립 재계산 불가**: 이번 세션에는 셸/해시 실행 도구가 제공되지 않아 `round-002/baseline.json`에 적힌 SHA-256 값을 직접 재계산해 대조하지 못했다. 파일 내용은 전부 읽어 명세·검사·기록과의 의미적 일치를 확인했지만, 바이트 단위 무결성 증명은 요청자가 제시한 해시 기록에 의존한다.
- **검사 실행 미수행**: 요청에 따라 새 검사 실행, 설치, Git 조작을 하지 않았으므로 6개 검사 파일과 2개 보조 모듈의 실제 통과 여부는 코드 읽기로만 판단했고, 이번 세션에서 재현 실행으로 재확인하지 않았다.
- **실제 AI 판단 재현 불가**: `split-flow-retry-20261012`의 D5.1/D5.2 응답은 과거 Codex 세션의 기록이며, 이번 검토는 그 기록을 읽고 명세·실제 자료와 대조했을 뿐 동일 시나리오를 독립적으로 재실행하지 않았다. 따라서 "일반 지식 선별이 모든 입력 조합에서 항상 올바르다"는 일반화된 보증은 할 수 없으며, 명세서 자신도 이를 동일하게 제한하고 있다.
- **원격 배포본/설치본 일치**: 명세서가 명시한 대로 이번 분리본은 아직 원격에 반영되지 않았고, 설치본 호환성 검증은 이번 요청 범위 밖이므로 다루지 않았다.
- **round-001과의 관계**: round-001은 이전 단일 구현(`discovery.py`) 기준이며 이번 분리본에는 그대로 적용되지 않는다는 명세서의 서술을 그대로 받아들였고, 이번 검토는 분리본 자체만을 독립적으로 재검토했다.
