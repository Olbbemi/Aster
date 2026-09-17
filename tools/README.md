# Aster 시나리오 공통 실행기

## 목적과 역할

`scenario_runner.py`는 승인된 시험의 요청 한 건을 별도 Codex CLI에 전달하고 실행 근거를
회수한다. 시나리오마다 Python 하네스를 만들지 않고 같은 실행 명령을 재사용한다.
Linux, Python 3.11 이상과 현재 확인한 Codex CLI 0.154.0을 대상으로 한다.
Claude 실행기는 구현하지 않았다. 플러그인 배포물에 포함하지 않는다.

상위 세션은 사용자가 지정한 목표, 시나리오 범위, 모의 승인 허용과 종료 조건을 확인한다.
응답, 실제 파일 및 해당 시나리오의 판정 기준을 대조한 뒤 다음 입력을 작성하고 실행기를
반복 호출한다. 실행기는 승인 문구나 시나리오 통과 판정을 스스로 만들지 않는다.
모의 승인은 실제 사람의 독립 판단과 구분한다. 지정한 시나리오가 끝나면 종료한다.
예상 밖의 결과는 근거를 확인하고, 합의한 범위를 변경해야 할 때 사용자에게 확인한다.

## 입력과 출력 계약

호출 시 cwd는 Aster 저장소 또는 그 하위여야 한다. `--case`에는 이 저장소의
`.codex/config.toml`에 명시된 `sandbox_workspace_write.writable_roots` 중 한 곳의
하위 시험 디렉토리 절대 경로를 전달한다. 기본 cwd 쓰기 권한만으로 다른 디렉토리를
실행기 입력으로 허용하지 않는다. 공유 데이터의 심볼릭 링크 별칭은 실제 경로로 대조한다.
디렉토리의 생성과 자료 배치는 [공유 작업 데이터 접근](../AGENTS.md#공유-작업-데이터-접근)을 따른다.

| 경로 | 역할 |
| --- | --- |
| `project/` | 미리 준비한 시험 프로젝트. 자식 Codex의 cwd 및 작업 쓰기 범위 |
| `inputs/<step>.md` | 상위 세션이 작성한 UTF-8 요청 원문. 1 MiB 이하 |
| `turns/<step>/input.md` | 실제 전달한 입력 사본 |
| `turns/<step>/execution.json` | argv, cwd, 시각, 입력/실행기 해시, 시간 제한 |
| `turns/<step>/events.jsonl`, `stderr.txt`, `response.md` | CLI 원시 이벤트, 오류 출력, 최종 응답 |
| `turns/<step>/before.json`, `after.json` | 프로젝트의 실행 전후 파일 해시/내용 |
| `turns/<step>/outcome.json` | 종료 코드, 세션 ID, 전달 완료 여부, 오류, 변경 파일 |
| `session.json` | 성공한 마지막 요청의 세션 ID와 case/project 연결. 실행기가 관리 |
| `.runner.lock` | 동일 case 동시 실행 방지용 잠금 파일. 실행 후 빈 파일로 유지 |
| `blocked.json` | 실패 후 자동 재시도/후속 입력 차단. 실패가 발생한 경우만 생성 |

step은 영문자/숫자로 시작하는 1~80자의 영문자, 숫자, `_`, `-`다.
기존 turn 디렉토리는 덮어쓰지 않는다. 입력, 출력 디렉토리 또는 project가 링크를 통해
시험 경계를 벗어나면 실행 전에 차단한다. 코드나 셸 명령을 실행기 옵션으로 전달할 수 없다.

스냅샷은 `.git`, `.agents`, `.codex`, `__pycache__`를 제외한다.
도구가 삽입한 메타데이터 마운트를 호스트 구성으로 단정하지 않는다.
심볼릭 링크는 대상 경로만 기록하고 내용을 따라 읽지 않는다. 2 MiB 초과 파일과 바이너리는
해시/크기만 기록한다. 한 요청 안의 순간적인 중간 저장은 관측하지 않으므로 필수 중간 상태는
별도 요청의 종료 지점으로 나누어 확인한다. 출처/이전 시나리오/설치본 같은 프로젝트 밖의
보존 대상 대조와 내용의 의미 판단은 상위 세션이 담당한다.

## 호출

아래 `CASE_PATH`는 위 계약에 따라 준비한 실제 절대 경로로 바꾼다.
호출은 Aster에서 아래 명령 형태 그대로 실행한다. 앞에 셸 래퍼나 환경 변수 설정을 붙이거나
Python 경로/옵션 순서를 바꾸면 실행 허용 규칙과 일치하지 않을 수 있다.

```bash
/usr/bin/python3 -I /home/olbbemi/Project/Aster/tools/scenario_runner.py run --case CASE_PATH --step 01-entry
/usr/bin/python3 -I /home/olbbemi/Project/Aster/tools/scenario_runner.py run --case CASE_PATH --step 02-followup
```

최초 실행은 `codex exec`, 이후는 같은 case의 `session.json`에 저장된 ID로
`codex exec resume`을 실행한다. 임의 세션 ID나 `--last`는 받지 않는다.
모델과 effort는 Codex의 적용 설정을 따른다. 시험 시 실제 실행 모델/환경은 별도로 확인한다.
실행 제한은 기본 1800초이며 `--timeout`으로 1~7200초를 지정할 수 있다.
오래 걸리는 호출은 상위 세션 도구의 비동기 실행/폴링으로 상태를 확인한다.

성공은 CLI 종료 0, 동일한 유효 세션 ID, 정확히 한 번의 `turn.completed`, 비어 있지 않은
최종 응답과 오류 이벤트 없음이 모두 충족된 경우다. 이는 전달 성공이며 시나리오 통과와 다르다.
실행 실패는 종료 1, 입력/사전 조건 오류는 종료 2다. 시간 초과나 중단 시 자식 프로세스 그룹을
종료한다. 실패 후 무조건 재시도하거나 다음 승인을 전달하지 않는다.
상위 세션은 원시 로그와 실제 파일을 확인한 뒤 복구 범위를 판단한다. 불완전한 case의 기록을
삭제하여 성공한 것처럼 이어가지 않고, 재시험이 필요하면 기존 실패 근거를 보존한 새 case를 준비한다.

## 실행 권한

프로젝트 `.codex/rules/scenario-runner.rules`는 다음 명령 prefix 하나만 허용한다.

```text
/usr/bin/python3 -I /home/olbbemi/Project/Aster/tools/scenario_runner.py run
```

규칙은 신뢰된 Aster 프로젝트를 로드하는 Codex를 새로 시작한 뒤 적용된다.
이는 해당 실행기를 샌드박스 밖에서 실행하도록 미리 허용하는 규칙이다.
전역 설정, Python 전체 또는 `/tmp` 전체를 허용하지 않는다.
상위 세션이 샌드박스 밖 실행을 요청할 때 이 prefix가 이미 허용되어 있으면 별도 승인 질문을
생략할 수 있다. 더 제한적인 관리 정책이나 일치하는 prompt/forbidden 규칙은 우선한다.
현재 세션에서 파일을 작성했다는 사실만으로 규칙이 소급 적용됐다고 판단하지 않는다.

실행기 자체는 사용자 권한으로 고정 경로의 Codex CLI를 시작한다. CLI 초기화/인증/세션 저장은
Codex가 관리한다. 실행기는 전역 설정 파일을 편집하지 않는다.
자식에는 `workspace-write`, 추가 쓰기 루트 없음(project가 기본 cwd 쓰기 루트),
`network_access=false`, `approval_policy=never`를 매번 지정한다.
`--ignore-rules`는 지정하지 않으며, 자식 CLI가 전역 규칙과 자신의 작업 경로에서 적용되는
신뢰된 프로젝트 규칙을 읽는다. 상위 Aster의 프로젝트 규칙이 별도 시험 project에도
자동 적용된다고 가정하지 않는다. 적용되는 allow 규칙은 해당 명령의 샌드박스 밖 실행을
허용할 수 있으며 Claude 외의 명령에도 적용된다. 더 제한적인 규칙과 관리 정책은 우선한다.
기본 임시 디렉토리 쓰기는 유지한다. `never`는 추가 권한을 주는 옵션이 아니다.
샌드박스 밖 권한이 필요하지만 적용되는 허용이 없거나 승인 질문이 필요한 동작은
실패 또는 미실행으로 보고할 수 있다.
이는 모든 시나리오/외부 도구에 대한 무개입 성공을 보장하는 설정이 아니다.

실행기는 요청마다 새 자식 CLI 프로세스를 시작한다. 따라서 실행기 인자 변경은 다음 run부터
적용되며 상위 Aster 세션을 다시 시작할 필요가 없다. 기존 case의 resume도 새 프로세스에서
현재 인자를 사용한다. 실제 규칙 적용과 외부 CLI 실행 성공은 해당 호출의 근거로 확인한다.

실행기는 입력을 읽고 정해진 CLI만 호출한다. 임의 Python 파일을 받는 우회 실행 기능은 없다.
Python은 `-I`로 시작해 작업 디렉토리의 모듈이나 `PYTHONPATH`를 자동으로 import하지 않는다.
규칙은 파일 내용의 해시를 고정하지 않으므로 실행기를 수정할 때도 이 권한 계약과 검사를 유지한다.

공식 근거: [Codex Rules](https://learn.chatgpt.com/docs/agent-configuration/rules).
현재 CLI의 옵션은 `codex exec --help`, `codex exec resume --help`로 확인한다.

## 검사와 신규 세션 시험

```bash
python3 -I -B -m unittest discover -s tools/tests -v
codex execpolicy check --pretty --rules .codex/rules/scenario-runner.rules -- /usr/bin/python3 -I /home/olbbemi/Project/Aster/tools/scenario_runner.py run --case CASE_PATH --step 01-entry
```

자동 검사는 임시 디렉토리의 가짜 CLI로 전달/재개, 권한 인자, 경로 제한, 덮어쓰기 차단,
동시 실행 차단, 실패/불완전/세션 불일치/시간 초과를 확인한다. 실제 모델 호출은 포함하지 않는다.
가짜 CLI와 시험 파일은 테스트가 끝나면 삭제한다.

새 Aster 세션에서 실제 적용을 다음 순서로 확인한다.

1. 현재 설정에서 허용한 작업 루트 아래에 기존 시험과 겹치지 않는 `runner-smoke-<고유값>` case를 준비한다.
2. `project/`와 `inputs/`를 만들고 첫 입력은 프로젝트에 `runner-probe.txt`를 만들고 `FIRST_OK`를 쓰도록 요청한다. 다른 파일 변경과 스킬 시나리오는 요청하지 않는다.
3. 공통 실행기로 첫 요청을 전달한 뒤 실제 파일 내용, 로그 및 성공한 세션 ID를 대조한다.
4. 둘째 입력은 같은 파일을 읽고 `SECOND_OK`를 한 줄 추가하도록 요청한다. 같은 공통 명령으로 전달하고 동일한 세션 ID와 두 줄 내용을 확인한다.
5. 두 실행에서 승인 창이 나타났는지 기록한다. 승인 창이 나오면 승인하여 무개입 성공으로 처리하지 말고, 표시 명령과 적용 규칙/관리 정책을 확인한다.
6. 결과는 해당 case에 기록하고 종료한다. 기존 시나리오나 다른 시나리오를 자동으로 시작하지 않는다.

모델이 도구 호출 없이 결과를 주장한 경우 실제 파일이 없으면 실패다. 실제 무승인 시험 전에는
구현/가짜 CLI 검사/규칙 매칭만 확인한 상태로 보고한다.
