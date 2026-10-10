# check_lifecycle_specification.py

[공통 가이드라인](../guidelines.md)에 따라 lifecycle 명세서, 단계 문서와 템플릿의 형식을 확인할 때 읽는다.
[검사 코드](../scripts/validation/check_lifecycle_specification.py)는 입력 파일을 읽기만 한다.

스킬 자체의 `SKILL.md` 검사는 [기본 구조 검사](check-structure.md)를 사용한다.

## 적용 대상과 시점

[표준 명세서 형식](../../.agents/skills/skill-lifecycle/references/specification.md)에 따라 작성한
명세서, lifecycle 단계 문서 구조 또는 단계 문서와 템플릿의 제목 대응을 확인한다.

- 명세서의 형식 확인이 필요하거나 단계 지침/템플릿을 변경했을 때 필요한 모드를 선택한다.
- 매 저장 자동 실행, 공유 자료 전체 검사와 기존 명세서 변환은 수행하지 않는다.
- 자체 수정에서 별도로 합의한 축약 명세서는 표준 본문 검사 대상이 아니다.

## 입력과 실행

Python과 의존성은 [공통 실행 조건](../guidelines.md#공통-실행-조건)을 따른다.
PyYAML과 markdown-it-py를 사용하며 추가 패키지는 필요하지 않다.

명세서 경로는 호출 위치 기준으로 해석하고 기준 지침은 도구가 속한 저장소에서 읽는다.

```bash
python3 -B tools/scripts/validation/check_lifecycle_specification.py /absolute/path/specification.md --json
python3 -B tools/scripts/validation/check_lifecycle_specification.py --check-template --json
python3 -B tools/scripts/validation/check_lifecycle_specification.py --check-stages --check-template --json
```

- 명세서 경로, `--check-template`과 `--check-stages`는 각각 단독 사용하거나 함께 지정할 수 있다.
  - 아무 대상이나 모드도 지정하지 않으면 입력 오류다.
- 다른 체크아웃이나 격리된 기준 자료를 사용하려면 `--lifecycle-directory`에
  해당 `skill-lifecycle` 디렉토리를 지정한다.

## 검사 범위와 근거

| 대상 | 확인하는 형식 | 근거 |
| --- | --- | --- |
| 명세서 프론트매터 | YAML 매핑, 다섯 필드의 누락/추가, 값 타입과 operation/current_stage 허용값, in_review boolean | [프론트매터](../../.agents/skills/skill-lifecycle/references/specification.md#프론트매터) |
| 명세서 본문 | 문서 제목, 단계 식별자/한글 제목과 순서, 공통 및 단계별 기록 제목의 누락/중복 | [전체 구성](../../.agents/skills/skill-lifecycle/references/specification.md#명세서의-전체-구성), [템플릿](../../.agents/skills/skill-lifecycle/references/specification.md#명세서-템플릿) |
| 템플릿 | 단계 순서와 단계별 기록 제목/순서의 대응 | [생명 주기 순서](../../.agents/skills/skill-lifecycle/references/lifecycle.md#생명-주기-순서)와 각 단계 문서의 명세서 기록 항목 |
| 단계 문서 (`--check-stages`) | 단계 목록과 파일/문서 제목 대응, 공통 구역과 운영 항목의 누락/중복/순서/제목 단계 | [단계 정의 공통 항목](../../.agents/skills/skill-lifecycle/references/lifecycle.md#단계-정의-공통-항목) |

- 단계 목록과 단계별 기록 제목은 기준 문서에서 읽으며 독립 목록을 도구에 복제하지 않는다.
- 일반 명세서에는 추가 설명 소제목과 관련 자료 절을 허용한다.
- 필수 기록 제목은 각 단계에 한 번씩 있어야 하며, 본문 내용은 원본 참조로 연결할 수 있다.
- 기록 항목 내부의 내용과 표를 채웠는지는 판정하지 않는다.

- `--check-stages`는 lifecycle 단계 지침 수정 시 사용한다.
  - `references/stages/` 바로 아래의 Markdown 파일 이름을 단계 목록과 대조하고 각 단계 문서를 검사한다.
  - 단계 목록과 운영 항목의 순서는 `lifecycle.md`의 해당 절 첫 최상위 목록에서 읽는다.
  - 운영 항목 안의 `####` 이하 추가 설명 제목은 허용한다.
- 단계별 기록 항목과 템플릿의 대응은 기존 `--check-template`이 담당한다.
- 새 옵션을 지정하지 않으면 기존 명세서/템플릿 검사 범위를 유지한다.

- YAML은 기존 구조 검사기의 안전한 파서와 중복 키 검출을 재사용한다.
- Markdown은 참조 검사기의 프론트매터 분리와 제목 텍스트 처리를 재사용한다.
- 코드 예시, HTML 주석과 인용문 안의 제목은 본문 단계/기록 항목으로 세지 않는다.
- 링크의 존재와 절 연결은 [참조 검사](check-references.md)에서 확인하며 이 도구에 중복 구현하지 않는다.

## 결과와 한계

JSON에는 검사 범위, 대상과 기준 디렉토리, 항목별 판정/근거/위치 및 한계를 담는다.
텍스트 출력과 JSON은 같은 판정을 사용한다.

- 종료 코드 `0`은 적용한 형식 검사 통과, `1`은 형식 위반, `2`는 입력/의존성/기준 자료의 실행 오류다.
  - 실행 오류와 형식 위반이 함께 있으면 종료 코드 `2`이며 개별 위반도 출력한다.
  - 단계 문서 검사에서 대상 파일 누락은 형식 위반이고, 파일 읽기/파싱이나 기준 목록 해석 실패는 실행 오류다.
- 여러 모드를 함께 실행하면 각 결과를 모아서 판정한다.
  - 누락된 단계 파일 때문에 다른 모드의 기록 기준을 읽을 수 없으면 해당 모드의 실행 오류도 함께 출력한다.
- 입력 명세서, 기준 문서와 템플릿 및 상태 필드는 수정하지 않는다.

- `name`과 `target_path`의 `null`은 형식으로 허용한다.
  - 기존 초기 명세서의 미정값인지, 새 명세서가 경로 확정 후 작성되었는지,
    이미 확정된 값을 되돌린 것인지와 요건 정의 완료 여부는 별도 의미 검토다.
- 실제 이름/경로의 일치, 승인, 필수 조건의 충족과 `current_stage`의 타당성을 자동 판정하지 않는다.
- `in_review`가 없는 기존 명세서는 누락으로 보고하고 자동 수정하지 않는다.
  재개할 때의 상태 확인과 갱신은 명세서 규격을 따른다.
- `in_review`의 boolean 형식만 검사하며 실제 검토, 커밋과 관문 통과 여부는 자동 판정하지 않는다.
- 검사 통과는 스킬의 완료 판정이나 다음 단계 진입 승인이 아니다.
- 단계 문서 검사도 본문 내용의 충분성이나 단계 이동 조건의 타당성을 판정하지 않는다.

- `--check-template`은 본문 대응만 검사한다.
- 템플릿의 `operation` 자리표시자는 실제 명세서의 허용값이 아니므로,
  템플릿 파일을 명세서 인수로 지정하면 해당 값의 형식 위반이 출력된다.
