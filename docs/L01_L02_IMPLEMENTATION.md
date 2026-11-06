# L01 NeMo 래퍼 → L02 문맥·세션 위험

2026-11-06. 이 문서는 `feat/security-input-actions`의 후속 개발 범위다.
이 기록의 L01/L02 코드는 현재 로컬 미커밋 작업이다. 문서 공개가 해당 코드의 공개 커밋 반영을 뜻하지 않는다.
새로 복제한 저장소에서 전용 runtime·파일 존재 여부를 확인한 뒤 실행 방법을 적용한다.
L01/L02 번호는 이 작업에서 아래 계약으로 정의한다. 다른 번호별 구현 명세가 저장소에 존재한다는 뜻은 아니다.

| 단계 | 구현 | 완료 판단 |
|---|---|---|
| L01 | `NemoAdapter`, `RailReceipt`, input/output Colang rail | 실제 NeMo에서 ALLOW/BLOCK/TRANSFORM/REVIEW 소비, 장애 시 안전 중단, 동시성·취소 검증 |
| L02 | `SessionRiskActions`, `ContextSessionGuard`, 기존 guidance API 연결 | 입력/반환 문맥 확인, 기존 세션 차단 시 공급자 호출 0회, TTL·용량·중복·A/B 격리 검증 |

## 범위와 설계 대응

`SECURITY_MIGRATION_PLAN.md` §4의 `validate_request_context`, `check_session_risk`,
`record_risk_event`, §5의 lifespan 조립, §6의 정책/기술 오류 구분, §11의 실제 rail 검증을 구현한다.
`NEMO_ASYNC_ACTIONS.md` §4의 문맥 검증 계약을 따른다.

기존 3개 API와 응답의 정상 계약은 유지한다. 안내 API에는 선택적 `X-Session-ID` 헤더만 추가하며
HTTP API 수는 여전히 3개다. 세션 ID는 ASCII 영숫자·`_.:-`, 1~128자로 제한한다.
이는 로그인이나 사용자 소유권 증명이 아니다. 세션이 없으면 요청마다 독립적인 서버 키를 만든다.
내부에서 공백 세션이 들어와도 공통 빈 세션으로 합치지 않는다.

L02는 이미 확정된 정책 차단을 기록하는 기반이며 새 입력 공격 탐지기는 아니다.
위험 이벤트를 기록하는 HTTP endpoint는 제공하지 않는다. 이후 입력/출력 정책 서비스가
`ContextSessionGuard.record`를 호출해야 실제 정책 차단이 점수에 반영된다.
비용·과부하·기술 오류·REVIEW·기존 세션 차단 자체는 위험 점수에 더하지 않는다.

마케팅 검사·게시판·memvid·SSE·유료 비용 pipeline은 이번 범위가 아니다.
보존 브랜치의 실패한 `actions.py`와 기존 `nemo_adapter.py`는 가져오지 않았다.
마케팅 검사를 고쳤거나 전체 보안 action 9개를 완성했다고 표시하지 않는다.

## L01의 실제 rail 연결

`NemoAdapter`는 서버가 구성한 함수 registry만 호출한다. NeMo에는 `legal_dispatch`를 등록하고,
Colang input/output flow가 반환된 결정을 명시적으로 소비한다. 데코레이터만 붙인 시험과 다르다.
TRANSFORM/REVIEW의 안전 본문이 실제 runtime 결과와 같은지도 검증한다.
미호출·중복 호출·잘못된 판정/본문·검사기 예외는 안전하게 중단한다.

각 invocation은 `ContextVar`로 분리한다. `RailReceipt`에는 원본 envelope와 검사된 출력 envelope가
함께 묶인다. shared client의 현재 질문 속성은 사용하지 않는다. NeMo에는 원문 대신 요청별
불투명 marker를 전달하고, 실제 함수에는 해당 invocation의 envelope만 전달한다.
독립된 일회성 검사이므로 NeMo 0.24.1의 대화 이력 cache는 저장하지 않도록 설정한다.
모델·임베딩 생성이나 유료 공급자 호출은 이 검사에 필요하지 않다.

`GUARDRAIL_BACKEND=nemo`를 지정했는데 import/초기화/실행이 실패하면 local로 우회하지 않는다.
`local`은 별도로 명시한 Python 함수 실행 모드이며 NeMo 검증 성공과 구분한다.

## L02의 실행 흐름

```text
저장된 접수 snapshot 조회 → 요청별 불변 context/envelope 생성
 → validate_request_context(input) → check_session_risk
 → 기존 비동기 LLM 호출 → 생성 단계가 보존한 envelope
 → validate_request_context(output) → 원래 guidance 응답
```

trace·정규화 세션·대상 snapshot·profile·정책 버전이 다른 응답, 본문 fingerprint가 달라진 envelope는
`REQUEST_CONTEXT_MISMATCH` 500으로 중단한다. 생성 단계가 넘긴 envelope를 검증하며,
검증 직전에 다른 요청의 응답을 현재 context로 다시 묶어 통과시키지 않는다.
공급자가 잘못된 본문을 반환해도 내용만으로 출처를 판별하는 기능은 아니다.

세션 차단은 HTTP 200 + `blocked=true` + `DYNAMIC_SESSION_BLOCKED`, 검사 장애는 안전한 503,
문맥 불일치는 500이다. 원문·키·내부 예외 내용은 이 오류 응답에 포함하지 않는다.
현재 상태는 단일 worker 메모리 저장소이며 재시작하면 사라진다. TTL 내 용량이 가득 차면
기존 차단 세션을 퇴출하지 않고 새 위험 기록을 503으로 거절한다.

## 재현 환경

기존 루트 `.venv`·`pyproject.toml`·`uv.lock`의 Python 3.14 MVP 의존성은 유지한다.
NeMo 0.24.1은 별도 `security-runtime/pyproject.toml`과 `security-runtime/uv.lock`으로 고정한다.
이 환경은 Python 3.12/3.13을 허용하며 이번 실검증은 Windows Python 3.12.10에서 수행한다.
두 lockfile은 각자의 프로젝트와 일치한다. 가상환경·캐시·실제 키는 커밋 대상이 아니다.

저장소 루트에서 Windows PowerShell로 실행한다.

```powershell
uv sync --project security-runtime --frozen --python 3.12
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_ADDOPTS = '-p no:cacheprovider'
$env:HF_HUB_OFFLINE = '1'
.\security-runtime\.venv\Scripts\python.exe -m pytest -q
```

기존 Python 3.14 환경에서 NeMo 없이 확인할 때는 명시적으로 local 범위를 고른다.
`nemo` 표시는 실제 라이브러리 통합 시험이며, 누락 시 조용히 skip하지 않는다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m 'not nemo'
```

전용 환경으로 서버를 실행하면 `.env`에서 `GUARDRAIL_BACKEND=nemo`를 사용할 수 있다.
기존 모델 설정과 실제 OpenAI 키는 별도이며 이번 fake/mock 검증에서는 돈이 드는 호출을 하지 않는다.

```powershell
.\security-runtime\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 확인한 테스트 결과

2026-11-06, Windows에서 전체 시험은 잠금 환경의 Python 3.12.10으로 수행했다.
유료 API·외부 모델 다운로드 없이 실제 NeMo 0.24.1 Colang input/output rail을 실행했다.

```text
95 passed, 32 warnings in 7.36s
```

32개 경고는 NeMo의 `jailbreak_detection/rail_config.py`에서 발생한 `nim_base_url` 관련
upstream deprecation 경고다. 우리 action의 성공 판정으로 숨기거나 경고를 필터링하지 않았다.
기존 `tests/test_mvp.py`는 수정하지 않았으며 원본 23개 사례가 전체 시험에 포함된다.

기존 루트 Python 3.14 환경에서 실제 NeMo 표식을 제외한 local 범위 결과는 다음과 같다.
제외된 32개는 위 전체 시험에서는 모두 실행됐다.

```text
63 passed, 32 deselected in 1.60s
```

## 공식 근거

- [NeMo 0.24.1 사용자 정의 action 등록](https://docs.nvidia.com/nemo/guardrails/v0.24.1/configure-guardrails/actions/registering-actions)
- [NeMo 0.24.1 check_async 검증 전용 API](https://docs.nvidia.com/nemo/guardrails/v0.24.1/run-guardrailed-inference/using-python-apis/check-messages)
