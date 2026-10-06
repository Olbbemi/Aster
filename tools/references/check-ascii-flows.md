# check_ascii_flows.py

[공통 가이드라인](../guidelines.md)에 따라 작성한 도식의 문자 형식을 확인할 때 읽는다.
[검사 코드](../scripts/validation/check_ascii_flows.py)는 입력을 읽기만 한다.

## 적용 대상과 실행

[ASCII 도식의 기계 판정](../../standards/skills/skill-validation.md#ascii-도식의-기계-판정)에 따라
명시적으로 지정한 Markdown의 `text ascii-flow` fenced code block만 검사한다.
도식의 정본 파일을 전달하며 여러 파일을 지정할 수 있다.
같은 실제 파일은 한 번만 읽고 링크를 따라 범위를 확장하지 않는다.

```bash
python3 -B tools/scripts/validation/check_ascii_flows.py /absolute/path/design.md /absolute/path/details.md --json
```

markdown-it-py가 필요하며 Python과 의존성 범위는 공통 가이드라인을 따른다.
표시 없는 도식과 일반 코드 및 주석 안의 예시는 검사하지 않는다.
목록/인용문 안에서도 실제 도식으로 표시한 fenced code block은 검사한다.

## 검사 결과와 한계

닫는 구분자와 문자 형식은 위 규격을 적용한다.

- 탭이나 NUL 등이 파서에서 치환되기 전의 원문을 확인한다.
- 한글을 허용하며 고정 줄 폭이나 연결선 정렬을 자동 판정하지 않는다.

JSON에는 `files`, `diagrams_checked`, `status`, `exit_code`, `checks`와 검사 한계를 담는다.

- 문자 위반은 원문 파일의 행, 문자 위치와 Unicode 코드값을 출력한다.
  - 문자 위치는 화면의 표시 폭이나 바이트 위치가 아니다.

- 도식이 없으면 `diagrams_checked: 0`과 `diagram.none: SKIP`을 표시한다.
  - 오류가 없다면 종료 코드는 `0`이지만 실제 도식을 확인한 결과는 아니다.
  - 도식 누락 자체가 문제인지는 해당 설계 내용을 검토하여 판단한다.
- 형식 위반은 `1`, 읽기/파싱/입력 오류는 `2`이며 오류가 있으면 개별 위반도 함께 확인한다.

문자 검사 통과는 연결선 끝점, 분기 의미, 글꼴/뷰어에서의 실제 표시와 가독성 통과가 아니다.

실제 표시 확인은 해당 설계 절차에서 수행한다.
