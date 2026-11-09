# 보안 action 재확인과 접수·안내 경계 구현

2026-11-09 KST · 인수인계 6절 ②~④ · `feat/security-input-actions` 개발 브랜치.

최신 `origin/main`의 확정 D3/P0 문서(4207df6)를 기준으로 검수하고 개발 브랜치에 반영한다. main에 개발 변경을 합치거나 push하지 않는다. 기존 `rag-runtime/pyproject.toml`, `rag-runtime/uv.lock`의 미커밋 변경은 보존한다.

## 현황 재확인

| action | 착수 시 코드 확인 | 현재 연결 |
|---|---|---|
| `validate_request_context` | `SessionRiskActions` 구현·안내 연결 | 접수 검사·조회 마스킹·안내 입출력 |
| `check_session_risk` | 구현·안내 연결 | 접수 등록·안내 진입 |
| `record_risk_event` | 구현, 확정 입력 차단 연결 없음 | 확정 입력 차단만 점수, 출력 차단은 본문 없는 감사 기록 |
| `check_input_policy` | 없음 | 접수 저장 전·안내 전 필드별 검사 |
| `mask_personal_data` | 없음 | 저장 전·조회 반환 전·공급자 전송 전·생성 반환 전 |
| `check_output_policy` | 없음 | 완성한 생성 전체 검사 |
| `check_generation_admission` | 함수 없음, `AdmissionManager`만 있음 | 유한 lease 획득 후 action, 공유 활성/대기 한도 |
| `check_request_budget` | 함수 없음, `BudgetStore`만 있음 | 용량 확보 후 원자 예약, 서비스가 종료 정산 |
| `check_marketing_response` | 없음 | 미구현. 게시판·M01/M02와 함께 후속 |

8개 구현·연결과 9개 전체 완료는 구분한다. 같은 폴더의 기존 변경은 사용자에게 확인한 뒤 **이 세션에서 이어서 검수·완성**했다. 아래 최신 시험은 입력 정책·마스킹·출력·자원 action 및 이를 소비하는 실제 접수/안내 경계를 포함한다. 마케팅 action과 연구 저장소 연결은 완료로 표시하지 않는다.

## 호출과 결정 계약

최신 main의 확정 D3/P0에 따라 `app/security/policy_core.py`의 판정 코어는 **표준 라이브러리만 import**한다. FastAPI·NeMo·다른 app 모듈 없이 파일 단독 로딩과 합성 입력/마스킹 시험을 통과했다. 폴더는 `app/security/`에 유지하며 실제 설치 패키지 추출 시점 O4는 이번에 진행하지 않는다. 독립 코어의 계약은 다음과 같다.

```python
check_input_policy(text: str, *, profile: str = "guidance") -> TextDecision
mask_personal_data(text: str) -> TextDecision
check_output_policy(text: str, *, max_chars: int = 8000, profile: str = "guidance") -> TextDecision
```

`TextDecision`은 불변 결정·reason/detail·safe_text·matched_rules다. 입력 실패는 본문 없는 `PolicyError`로 표현한다. 앱의 `policy_actions.py`는 아래 Envelope 인터페이스를 유지하며 코어 결과를 기존 `ActionDecision`으로 변환하고, `PolicyError`를 `SecurityError`로 매핑하는 얇은 어댑터다.

```python
check_input_policy(source: Envelope) -> ActionDecision
mask_personal_data(source: Envelope) -> ActionDecision
check_output_policy(source: Envelope, *, max_chars: int = 8000) -> ActionDecision
```

`Envelope`는 요청별 불변 context·본문·fingerprint를 묶는다. action은 원문을 로그나 판정 metadata에 넣지 않는다. 서버가 registry/profile을 선택한다. `intake`·`guidance`는 법률 주제 제한을 적용하고 `research`는 그 제한을 적용하지 않되 같은 공격 규칙을 적용한다. 연구 저장소 프로토콜 변경·가짜 구현 교체·설치 패키지 호환성 검증은 하지 않았다. 재사용 시 독립 코어 시그니처와 버전을 연구 측 어댑터에 명시적으로 연결해야 한다.

현재 입력 사유는 `BLOCKED_JAILBREAK`, `BLOCKED_PROMPT_INJECTION`, `BLOCKED_SECRET_REQUEST`, `BLOCKED_PRIVACY_RISK`, `BLOCKED_AUTH_BYPASS`, `BLOCKED_LEGAL_HARM`이다. 기존 Java 사유 이름을 사용하며 L02의 기존 접두사 없는 위험 이벤트와 함께 수용한다. 도메인 밖 주제 차단 `OUT_OF_SCOPE_TOPIC`은 공격 점수를 올리지 않는다. 광범위한 Java 부분문자열 검사와 탐지 결과가 완전히 같다는 뜻은 아니다.

마스킹 토큰은 `[PHONE]`, `[EMAIL]`, `[ID_NUMBER]`. 국내 전화·+82 표기·이메일·주민번호 형태를 치환하며, 현재 마스킹은 탐지용 Unicode 정규화 뷰의 위치를 원문에 매핑해 비대상 텍스트를 보존한다. 반복 적용 시 같은 안전 본문을 유지한다. 이름·자유 형식 주소·모든 언어의 개인정보나 모든 우회 공격을 탐지하는 완전한 익명화/분류기는 아니다. 공개 시험은 합성 자료만 사용한다.

## 실제 서비스 경계

접수 등록은 기존 `def` 라우터를 유지한다. AnyIO worker에서 같은 이벤트 루프의 async rail 실행을 기다린 뒤에만 저장한다. 자유 입력 값의 **결합 본문과 각 필드**를 검사하므로 JSON 키 사이 또는 필드 경계를 이용한 분할 우회를 검증한다. 어느 필드든 차단되면 저장하지 않는다. 조회도 저장 snapshot의 정의된 개인정보 패턴을 가린 뒤 반환한다.

안내 흐름:

```text
저장 snapshot 조회 → 문맥·세션 확인 → 결합/필드별 입력 정책·마스킹
 → 용량 확보 → admission action → budget action/원자 예약
 → 공급자 호출(timeout 적용) → 정산 → 슬롯 반환
 → 생성 envelope 문맥 확인 → 전체 출력 정책 → 최종 마스킹
 → 반환 직전 문맥 확인 → JSON
```

서버 입력은 공급자에게 이름을 보내지 않는다. 출력 차단이나 검사 장애에도 미검사 본문을 반환하지 않는다. 등록·안내 정책 차단은 HTTP 200 + `blocked=true` + `reasonCode`; 용량/rail 장애는 503, 문맥 오류는 500, 공급자 실패/생성 timeout은 기존 안내 오류 계약인 502다. 422 오류는 원문·임의 필드 이름·예외 context를 그대로 반사하지 않는다. AI 오류 응답도 예외 원문을 포함하지 않는다.

## 용량·예산·종료 처리

기본 동시 생성 2, 대기 4, 대기 한도 0.5초, 생성 timeout 30초다. 대기 중에는 비용을 예약하지 않는다. 예산 차단은 공급자 호출 0회이며 슬롯을 반환한다.

예산은 프로세스 수명 동안의 단일 worker 메모리 USD 장부다. 기본 한도 1.00, 요청별 예약 추정액 0.01이며 운영자가 설정한다. **이 수치는 실측 공급자 가격이 아니다.** 실제 OpenAI 서비스 호출은 입력·출력 단가가 둘 다 설정되지 않으면 `MODEL_PRICE_NOT_CONFIGURED`로 자원 확보/호출 전에 거절한다. 단가가 있으면 UTF-8 입력 byte 상계와 출력 토큰 상한으로 계산한 예약액과 운영자 예약액 중 큰 값을 사용한다. 날짜별 리셋·영속화·worker 간 전역 한도는 구현하지 않았다.

예약 소유권은 서비스의 요청별 `BudgetTicket`이 갖는다. 실제 예약 이후 NeMo가 취소되거나 receipt 검증이 실패해도 서비스의 `finally`에서 닫힌다. 상태는 한 번만 전이한다.

| 상태 | 적용 |
|---|---|
| `RELEASED` | 예약했지만 공급자 호출을 시작하지 않음 |
| `REPORTED` | 공급자 토큰 사용량과 서버에 설정한 입력·출력 단가로 계산 가능. fake client는 유료 호출 없이 가상 장부 0으로 처리 |
| `ESTIMATED` | 호출 시작 후 성공·실패·timeout·취소에서 보고 사용량을 알 수 없음. 예약액으로 정산. 단가 없는 실제 서비스 호출은 진입 전 거절 |

사용량이 있어도 생성 본문이 비면 비용 metadata는 오류에 보존해 정산한다. 공급자 client에 `last_usage` 같은 공유 요청 상태를 넣지 않는다. 사용량을 모르는 호출을 무료로 기록하지 않는다. 정산은 lock 안의 동기 연산이고 슬롯 반환에도 await가 없어 취소 중 추가 cleanup task 없이 끝난다.

`GENERATION_RESERVATION_USD`는 운영자 추정치이므로 실제 비용이 예약액을 넘을 수 있다. 보고된 비용은 실제 계산값으로 기록하고 후속 예약을 막지만, 이 장부가 제공자 청구액의 엄격한 상한을 보장하지는 않는다. 가격을 추측해 기본 활성화하지 않는다.

## 시험과 재현

시험 대상은 다음 8개 파일이다. 실제 NeMo 0.24.1 rail은 `nemo` 마커로 분리하며, 네트워크 모델 생성은 사용하지 않는다.

```powershell
$securityTests = @(
  'tests/test_mvp.py', 'tests/test_session_security.py',
  'tests/test_nemo_integration.py', 'tests/test_l02_input_only_risk.py',
  'tests/test_policy_actions.py', 'tests/test_security_pipeline.py',
  'tests/test_paid_call_service.py', 'tests/test_usage_accounting.py'
)
# Python 3.14, local 함수/서비스 회귀
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests -m 'not nemo'
# Python 3.12 + security-runtime의 고정 lock 환경, 실제 NeMo 포함
.\security-runtime\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests
```

기준선은 local 68 passed, 실제 NeMo 포함 104 passed였다. **최종 실행은 Python 3.14 루트 `.venv`와 Python 3.12.10 `security-runtime/.venv`**를 사용했다. Windows의 가상환경 launcher가 sandbox 안에서 실패한 경우에는 승인된 sandbox 밖에서 실행했다. `rag-runtime`은 이번 구현과 시험에서 사용하거나 커밋하지 않았다.

시험은 합성 정상/공격 입력, PII 저장·조회·전송·출력 경계, 출력 위험의 사용자 점수 제외, 실패 시 차단, A/B 격리, 동시 예약 경쟁, 중복 정산, 유한 큐 거절, 대기 취소/timeout, 호출 취소/timeout/실패, 예약 rail 중단, 보고 사용량과 빈 공급자 응답 정산을 포함한다. 기존 보안 장애 회귀 1개는 등록에도 세션 검사가 추가된 뒤에도 원래 시험 대상인 guidance 장애를 주입하도록 profile 조건만 추가했다.

시험 대상 8개 파일만 명시했다. RAG 코드를 고치거나 삭제해 성공으로 만들지 않았으며 RAG 시험도 재실행하지 않았다. **보안 회귀 통과와 저장소 전체 회귀 통과를 구분한다.** 기존 memvid Windows 접근 거부와 tracing guard의 loopback 초기화 차단은 미해결이다. 향후 연구 저장소로 RAG 코드를 옮길 때 `docs/evidence/B03/README.md`와 해당 시험을 함께 이전한다. 이번 보안 증거는 legal-intake의 기준 구현 기록으로 남긴다.

실제 OpenAI 유료 호출은 미검증이다. SDK 응답/사용량은 가짜 응답으로 검증했으며 실제 NeMo 성공을 실제 생성 성공으로 기록하지 않는다. Equalizer·RAG 이전·저장소 개명·게시판·마케팅은 이번 작업에서 시작하지 않았다.

## 최종 검증 기록

| 실행 | 결과 | 증거 |
|---|---|---|
| Python 3.14, `-m 'not nemo'`, 보안 8개 파일 | **153 passed, 58 deselected in 1.98s** | [최종 local 로그](evidence/SECURITY_2026-11-09/pytest_local.txt) |
| Python 3.12.10, NeMo 0.24.1 포함, 보안 8개 파일 | **211 passed, 58 warnings in 12.05s** | [최종 NeMo 포함 로그](evidence/SECURITY_2026-11-09/pytest_security_nemo.txt) |
| `git diff --check` | 통과 | 공백 오류 없음 |
| 정책 코어 EOF 공백만 정리한 뒤 함수/NeMo 재검증 | **53 passed, 1 warning in 1.71s** | [정책 최종 로그](evidence/SECURITY_2026-11-09/pytest_policy_final.txt) |
| 중간 141/195 실행 당시 두 파일 SHA256 비교(참고 이력) | 당시 동일, 이후 이 세션에서 추가 검수함 | [중간 실행 전](evidence/security-2026-11-09-snapshot-before.json) · [중간 실행 후](evidence/security-2026-11-09-snapshot-after.json) |
| 최종 보호 대상 및 검수 소스 SHA256 | RAG runtime·B03 실패 보고서·B02b 결과/임계값 보존 | [최종 검증](evidence/SECURITY_2026-11-09/verification.json) |

`tests/rag/`, `tests/test_rag_b03_b05.py`는 별도 연구 범위로 실행하지 않았다. pytest 전체 기본 목록을 바꾸거나 시험을 skip 처리하지 않았다. 중간 141/195 결과는 기존 `security-2026-11-09-*.txt`에 보존하지만 위 최종 결과를 우선한다. 재현 명령은 앞서 나열한 보안 파일 8개를 사용한다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests -m 'not nemo'
.\security-runtime\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests
```

개발 코드·시험·문서만 선별 커밋하며 `rag-runtime/pyproject.toml`, `rag-runtime/uv.lock`의 기존 미커밋 변경은 그대로 남긴다. 최신 소스/보호 대상 해시·명령은 `docs/evidence/SECURITY_2026-11-09/verification.json`에 기록한다.
