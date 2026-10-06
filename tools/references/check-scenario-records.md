# check_scenario_records.py

[공통 가이드라인](../guidelines.md)에 따라 요건/계획/현재 결과의 대응을 확인할 때 읽는다.
[검사 코드](../scripts/validation/check_scenario_records.py)는 입력을 읽기만 하며 시나리오를 실행하지 않는다.

## 적용 대상과 입력

[시나리오 기록 대조 형식](../../standards/skills/scenario-records.md)의 표시와 열을 가진 Markdown 표를 검사한다.

- 명세서 또는 연결된 정본 문서의 실제 경로를 전달한다.
- 한 호출에는 한 시나리오 묶음의 요건/계획과 필요한 결과 표만 포함한다.
  - 여러 파일을 전달할 수 있고 같은 실제 파일은 한 번만 읽는다.
- 링크 대상, 실행기 로그나 다른 작업을 자동으로 찾아 입력에 포함하지 않는다.

markdown-it-py가 필요하며 Python과 의존성 범위는 공통 가이드라인을 따른다.

- 표시 없는 기존 기록은 자동 변환하지 않는다.
- 필요한 표를 찾지 못하면 실패이며 파일 읽기/파싱 실패는 실행 오류다.

## 실행

실행 전 계획을 확인할 때는 `plan`, 실행 후 현재 결과를 대조할 때는 `results`를 지정한다.

아래 경로는 해당 작업의 실제 정본 파일로 바꾼다.
세 표가 한 문서에 있으면 그 파일만 전달한다.

```bash
python3 -B tools/scripts/validation/check_scenario_records.py /absolute/path/plan.md --phase plan --json
python3 -B tools/scripts/validation/check_scenario_records.py /absolute/path/plan.md /absolute/path/results.md --phase results --json
```

- `plan`은 결과 표가 없어도 실행하며 결과 표의 내용을 검사하지 않는다.
- `results`는 계획에 있는 제외/보류 사례까지 현재 결과가 있는지 대조한다.

필수 열, 값과 범위 변경/재시험 기록의 기준은 위 규격을 따른다.

## 출력과 한계

JSON의 `status`, `exit_code`, `checks`는 기록 형식과 대응의 판정이다.

- 위반 위치는 파일과 행 번호로 출력하며 종료 코드는 공통 가이드라인을 따른다.
  - 오류와 형식 위반이 함께 있으면 종료 코드 `2`와 개별 위반을 모두 출력한다.

실제 시험 상태는 `execution`에서 구분한다.

| 필드 | 의미 |
| --- | --- |
| `checked` | 결과 표를 검사했는지. `plan`은 false |
| `counts` | 등록된 사례의 현재 결과 상태별 수 |
| `required_cases_not_passed` | 현재 대상인 필수 사례 중 결과가 통과가 아닌 ID. 누락된 결과도 포함 |

- 입력 기록이 잘못되었거나 읽기에 실패하면 상태 요약도 부분 결과일 수 있다.
- `PASS`와 빈 미통과 목록만으로 실제 시험 통과, 요건별 충족이나 단계 완료를 확정하지 않는다.
- 설명/근거의 비어 있음은 검사하지만 내용의 충분성, 진위와 실제 사용자 승인은 확인하지 않는다.
- 상세 링크의 존재와 절은 [참조 검사](check-references.md)로 확인한다.
