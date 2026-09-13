# 검사기 자체 시험

`tests/`는 `scripts/`의 검사 코드가 규격에 맞는 대상을 검사하고 올바르게 판정하는지 확인한다.
검사기를 새로 만들거나 수정한 경우, 또는 실행 환경의 변경 영향을 확인할 때 사용한다.
스킬이 기존 검사기를 사용하는 일반 실행 절차에는 이 문서 읽기와 자체 테스트를 포함하지 않는다.

## 테스트 파일별 목적과 범위

| 테스트 파일 | 검사 코드 | 대표 검증 범위 |
| --- | --- | --- |
| [test_structure.py](test_structure.py) | [check_structure.py](../scripts/check_structure.py) | 기본 구조와 프론트매터의 정상/오류 판정 |
| [test_references.py](test_references.py) | [check_references.py](../scripts/check_references.py) | 링크 추출, 경로 해석과 검사 제외 처리 |
| [test_distribution.py](test_distribution.py) | [check_distribution.py](../scripts/check_distribution.py) | 배포 JSON, 등록 경로와 기대 파일 목록 대조 |

공통으로 실제 CLI 호출의 출력과 종료 코드가 기대값과 일치하는지, 검사 대상이 변경되지 않는지 확인한다.
개별 사례와 기대값은 각 테스트 코드에서 관리한다.

## 실행

Python과 의존성 준비는 [공통 가이드라인](../guidelines.md)을 따른다. 전체 시험에는
[requirements.txt](../requirements.txt)의 라이브러리가 필요하다. unittest는 Python 표준 라이브러리다.

Aster 저장소 루트에서 전체 시험을 실행한다.

```bash
python3 -B -m unittest discover -s checks/skills/tests -p 'test_*.py' -v
```

영향 범위가 특정 검사기에 한정되면 `-p`에 해당 테스트 파일명을 지정할 수 있다.
테스트는 임시 파일/디렉토리의 정상/오류 사례, 검사기 import와 실제 CLI 호출을 확인한다.

시험 통과는 검사기의 동작을 확인한 결과다. 실제 스킬의 검사 통과를 대신하지 않는다.
명령, 적용 범위와 결과는 해당 개발 작업 기록에 남기고 원시 결과는 공유 작업 데이터에 보관한다.
