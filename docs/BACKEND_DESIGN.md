# FastAPI 실험용 백엔드 설계 — DRAFT

**현재 구현 상태:** 사용자가 선택한 동기 접수 등록·조회 + 비동기 안내 3개 MVP는 루트 app/에 구현했다. 테스트 23개와 실제 uv 개발 서버·fake HTTP·MainThread를 확인했다. [MVP 실행 안내](RUN_MVP.md) 참조. 아래 21개 API·NeMo 9개 내용은 후속 확장 설계이며 현재 구현 목록과 다르다.

기준: 2026-11-04. 이 문서는 **구현 전 설계**다. 원본 Java의 실제 Controller·DTO·비용·보안 서비스와 `docs/API_STATUS_SPEC.md`를 대조했다. 오래된 공개 소개 README보다 현재 소스를 우선한다. 원본 API 37개 중 11개를 선별하고 26개는 이번 실험에서 제외한다. 게시판·리뷰 관련 9개와 health 1개를 신규 제안해 전체 목표는 **21개**다.

- [Dark Tablet 흐름도](backend-dark-tablet.html): 8개 화면, 페이지 이동 및 인쇄 지원
- [비전공자용 공부자료](study-guide.html) · [Markdown 원문](STUDY_GUIDE.md): 전체 구조·Spring 비교·비동기·DI·보안·복습 문제
- [비동기 보안 설계 해설](async-security-explained.html) · [원문](NEMO_ASYNC_ACTIONS.md): action 9개 설계 확정·도입 이유·자원 수명·실험
- [편집 가능한 Mermaid 원본](backend-flows.mmd)
- [API 선정 데이터](api-catalog.json)
- Mermaid 개별 렌더링: [전체](assets/overview.mmd) · [보안](assets/security-actions.mmd) · [SSE](assets/sse-lifecycle.mmd)

## 1. 이번 단계의 경계

**브라우저·Swagger → Uvicorn/ASGI → FastAPI → Python 서비스·NeMo actions → OpenAI** 구조다. 실행 경로에 Spring Boot를 두지 않는다. JWT, 사용자 가입·로그인, ROLE별 권한, Spring 프록시, JPA·운영 DB·Actuator는 이번 단계에서 구현하지 않는다.

**제공된 과제 명세 확정:** ohgi-review-server는 POST /api/reviews(def), GET /api/reviews/{review_id}(def), POST /api/reviews/{review_id}/reply(async def)로 구현했다. 수업 과제 3개와 이 문서의 주력 확장 21개는 별도 앱·계약이다. 주력 확장은 비동기를 유지하며 초기 GET /posts 예제는 참고용이다. 과제 서버에는 NeMo·인증·운영 DB를 추가하지 않는다.

M01/M02는 게시판 데이터를 사용하는 주력 비동기 AI 확장이며 마케팅 action은 이번 필수다. 별도 과제 앱의 답글도 await로 호출하며 등록·조회 def 핸들러에서 asyncio.run으로 AI를 억지 실행하지 않는다.

인증 생략의 전제는 `127.0.0.1`, 단일 사용자, 합성 데이터, 단일 worker 실험이다. `sessionId`는 위험·비용 실험을 위한 구분자이며 신원·권한 증명이 아니다. FastAPI를 외부에 공개하기 전에는 별도의 인증·인가가 필요하다. Python 보안 action은 사용자 인증을 대신하지 않는다.

## 2. 기존 API 선정 — 11개

여기서 '재사용'은 계약·규칙·테스트 입력을 가져온다는 뜻이며 Java 구현을 그대로 실행한다는 뜻이 아니다. 아래 모든 FastAPI 기능은 아직 설계 상태다.

| 기존 ID | 선정한 FastAPI 경로 | 처리 | 유지·변경 내용 |
|---|---|---|---|
| C02 | POST `/api/intakes/classify-preview` | 규칙 | 사건 분류·권장 자료, 무저장·무LLM. `coreStatement` 100자 계약 유지 |
| C04 | POST `/api/legal-intake/minimal` | 규칙 | 간단 안내 생성, 무저장·무LLM. DTO는 원본과 대조해 이전 |
| R01 | GET `/api/legal/procedures` | 참조 | 고정 fixture에서 절차 목록 반환 |
| R02 | GET `/api/legal/procedures/{code}` | 참조 | 고정 fixture에서 상세·단계·양식 정보 반환 |
| R06 | GET `/api/legal/criminal/checklist/supplementary-investigation` | 참조 | 고정 체크리스트. 실제 법률정보 갱신 서비스는 아님 |
| S01 | POST `/api/ai/chat` | AI | 경로·camelCase 응답 유지, Python async 서비스로 이전 |
| S02 | POST `/api/ai/chat/stream` | AI/SSE | SseEmitter를 StreamingResponse로 변경. 전체 검사 후 안전 청크만 전송 |
| S03 | POST `/api/legal/guardrail/input` | 보안 실험 | FastAPI 내부 NeMo 입력 rail 검사. 별도 네트워크 NeMo 서버 의존 제거 |
| S04 | POST `/api/legal/guardrail/output` | 보안 실험 | 생성 없는 출력 rail 검사. 입력 필드는 기존 `response` 유지 |
| C13 | GET `/api/lab/marketing/summary` | 변경 | 기존 marketing-funnel을 게시글·후기 fixture/메모리 집계로 변경. 전환율·이탈률은 제외 |
| C14 | GET `/api/lab/security-events` | 변경 | 기존 관리자 보안 이벤트를 원문 없는 메모리 이벤트 조회로 축소 |

S03·S04는 디버그용 진입점이다. `LLMRails`의 입력/출력 rail만 실행하고 대화 생성은 비활성화하는 어댑터를 사용한다. 단순 Python 함수 직접 호출만으로 'NeMo 연동 완료'라고 판정하지 않는다.

## 3. 신규 API — 10개

게시판·리뷰·마케팅 연동은 이번 fastapi-lab의 필수 범위다. 핵심 Chat 이후 구현하는 순서일 뿐 다음 hybrid 단계로 미루는 선택 기능은 아니다. 특히 추천 5번 check_marketing_response는 M01/M02 반환 전 필수 실행한다. 샘플의 실제 링크/저장 위치와 DTO는 확인 후 확정한다.

강사의 게시판·리뷰 관리 샘플은 아직 받지 않았다. B/M API는 그 샘플에 따른 확정 전 제안이며, 기존 Legal Intake에서 이미 구현된 API가 아니다.

| 제안 ID | HTTP API | 입력·결과 |
|---|---|---|
| H01 | GET `/health` | 상태, fake/real 모드, 정책 버전. 키·원문·환경 전체는 노출하지 않음 |
| B01 | POST `/api/posts` | title/body → 마스킹한 게시글, 201 |
| B02 | GET `/api/posts` | limit 1~50, cursor → 게시글 목록 |
| B03 | GET `/api/posts/{postId}` | 마스킹된 게시글 또는 404 |
| B04 | PATCH `/api/posts/{postId}` | 허용 필드만 수정, 200/404 |
| B05 | DELETE `/api/posts/{postId}` | 메모리 게시글·연결 후기 제거, 204/404; 이 실험에서는 AI action이 호출하지 않음 |
| B06 | POST `/api/posts/{postId}/reviews` | rating/body → 후기, 201/404 |
| B07 | GET `/api/posts/{postId}/reviews` | 해당 게시글 후기 목록, 200/404 |
| M01 | POST `/api/posts/{postId}/ai-summary` | 저장된 마스킹 본문·후기 → AI 요약·주제·만족/불만 요인 |
| M02 | POST `/api/reviews/{reviewId}/reply-draft` | 저장된 후기 → 검토용 답변 초안, 자동 게시하지 않음 |

M01/M02는 S01과 같은 안전 파이프라인을 공유한다. 게시글·후기 본문은 명령이 아닌 분석 데이터로 구분하며, 본문에 포함된 지시를 시스템 정책으로 승격하지 않는다. 타인 개인정보가 들어 있는 원문을 먼저 저장하고 나중에 가리는 대신, 이 실험에서는 저장 전 패턴 마스킹한다.

개수: **1차 핵심 11개** = C02/C04/R01/R02/R06/S01~S04/C14/H01. **샘플 수령 후 10개** = C13/B01~B07/M01/M02. 총 21개이며 필수 선행 구현은 11개로 제한한다.

## 4. 이번에 제외할 기존 API — 26개

| ID | 제외 기능 | 이번 범위에서 제외하는 이유 |
|---|---|---|
| C01, P01 | 로그인·내 정보 | Spring 인증·인가 연동은 다음 hybrid 단계 |
| C03, C05, C09, C10, C11 | 접수 저장·상세·목록·상태·상담 메모 | 사건 DB와 상담 업무 전체를 이전하지 않음 |
| C06, C07, C08, P02, P03 | 검색 요청·결과·이력·외부 검색 실행 | 외부 검색 제공자·이력 저장·검색 LLM 비용 범위 축소 |
| C12 | 운영 대시보드 | Agent·Incident 운영 집계 제외 |
| C15, C17, S05 | Agent 위험 분석·집계·이력 | 현재 챗봇 세션 위험 action과 별개. Agent 실행 엔진은 제외 |
| C16 | Actuator Prometheus | Spring 운영 스택 제거. 실험은 redacted 구조화 로그 사용 |
| C18, C19, C20 | Incident 목록·확인·종결 | Incident 워크플로와 운영 DB 제외 |
| R03, R04, R05 | 절차 단계·양식 전용 API | R02 상세 fixture에 포함하고 전용 경로는 보류 |
| P04, P05, P06 | 파일 업·다운로드·행동 이벤트 | 파일 보안·스토리지·행동 수집 범위 제외 |

추가로 Redis, Celery, Kafka, memvid/RAG, OCR, 자동 외부 게시, 결제·실제 청구 대사는 이번 실행 경로에 넣지 않는다. 기존 Java 서버와 DB는 수정하지 않는다.

## 5. FastAPI 고유 요청 흐름

### 필수 조건: 최소 동기 비교와 끝까지 이어지는 주력 비동기 처리

- 주력 게시판 CRUD·집계·AI 핸들러와 NeMo 호출 경로는 async def 기반이다. 별도 리뷰 과제의 등록·조회는 요구대로 def를 사용한다.
- OpenAI는 비동기 클라이언트, NeMo는 `generate_async` 등 설치 버전에서 지원하는 비동기 API를 사용한다. 외부 HTTP가 필요하면 비동기 클라이언트를 공유한다.
- SSE는 async generator와 StreamingResponse로 구현하고 연결 단절·timeout·취소를 전파한다.
- 비동기 AI의 가짜 지연은 await asyncio.sleep이다. async 경로에서 time.sleep·동기 HTTP/DB를 직접 실행하지 않는다. 최소 def 예제의 핸들러는 FastAPI 스레드 풀에서 실행된다.
- 짧은 로컬 규칙·검증·메모리 접근까지 불필요하게 스레드로 옮기지는 않는다. 오래 걸리는 CPU 작업이 추가되면 측정 후 별도 실행 경계를 둔다.
- 이번에는 DB가 없다. 주력 DB 도입 시 비동기 드라이버·요청별 세션을 사용한다. 샘플의 실제 저장 방식을 확인한 뒤 적용하며 lifespan client를 요청마다 새로 생성하지 않는다.
- 이 조건은 '언젠가 백그라운드에서 실행'한다는 의미가 아니다. 응답이 필요한 검사·생성·정산은 요청의 비동기 흐름에서 완료한다.

1. **lifespan**: 설정 검증 → fake/real 클라이언트·NeMo rails·예산/세션 메모리 저장소를 1회 생성. 종료 시 연결 정리. 키가 없는데 real 모드면 시작 실패로 명확히 구분한다.
2. **ASGI 진입**: Uvicorn이 요청을 전달. middleware가 서버 생성 traceId, 크기 제한, 시간을 관리한다. 원문·키는 로그에서 제외한다.
3. **Pydantic 검증**: camelCase alias, 공백 불가, 길이 상한, `extra='forbid'`. 불일치는 422. Chat의 원본 입력 100자 기준을 유지한다. 새 게시판 본문은 별도 상한을 가진다.
4. **Depends**: 요청에 필요한 서비스와 공유 자원을 명시적으로 주입. JWT·사용자 조회 dependency는 이번에 없다.
5. **APIRouter**: 규칙/참조, 저장, AI 파이프라인 중 필요한 서비스만 호출한다.
6. **async 서비스**: NeMo와 OpenAI I/O를 `await`. 네트워크 대기 중 다른 요청을 처리할 수 있다. 짧은 규칙 검사는 로컬 함수로 처리한다.
7. **응답**: response_model JSON 또는 async generator 기반 StreamingResponse. 기술 오류·정책 차단은 구분한다.
8. **취소·finally**: timeout·클라이언트 단절 시 호출 취소 및 예산 예약 종료. BackgroundTasks로 필수 검사·정산을 미루지 않는다.

`async def` 안에서 동기 HTTP/DB 함수를 직접 호출하면 이벤트 루프가 막힌다. FastAPI가 직접 호출하는 일반 `def` 핸들러·dependency의 스레드 풀 실행과 일반 Python helper 호출은 다르다. CPU 연산이 커지면 별도 offload를 검토한다.

## 6. 보안 Python actions 상세

NeMo `@action` 함수는 정책의 진입점이며, 상태는 요청 context와 공유 서비스에 명시적으로 전달한다. 클라이언트가 action 이름·Python 경로·임계값·사용자 역할을 선택하게 하지 않는다. Colang 흐름에서 반환값을 읽고 중단·변환을 수행해야 하며, 임의 dict 반환만으로 차단이 자동 수행되는 것은 아니다.

### 공통 ActionDecision — 신규 내부 계약

```text
decision: ALLOW | BLOCK | TRANSFORM | REVIEW
reasonCode / detailCode: 사유 코드 또는 null
safeText: 허용된 본문·안전 응답만 포함
policyVersion / traceId / appliedChecks: 재현 가능한 검사 정보
```

REVIEW는 기존 Java 응답에 없던 내부 제안이다. 마케팅 초안에서 발견되면 검토 필요 상태를 반환하고 자동 게시하지 않는다. 외부 기존 Chat 응답에는 없는 필드를 무조건 추가하지 않고 endpoint별 모델에 반영한다.

| action | 입력·실행 위치 | 판단·출력 | 실패·검증 기준 |
|---|---|---|---|
| `validate_request_context` | 요청별 서버 context, 분석 대상·검사 결과·응답 envelope | requestId/traceId/profile/대상 식별·버전의 바인딩 확인, 반환 직전 재확인 | 불일치는 REQUEST_CONTEXT_MISMATCH 기술 오류로 중단. 올바른 격리를 대체하지 않으며 인증·소유권 증명이 아님 |
| `check_session_risk` | 모든 AI 요청의 서버 정규화 sessionId, 입력 rail 시작 | 기존 누적 위험 점수·차단 상태 조회. 차단이면 `DYNAMIC_SESSION_BLOCKED` | 세션 누락 시 서버 발급. 무한 메모리 증가 방지 TTL·용량 제한. sessionId 변경으로 신원 통제 가능하다고 주장하지 않음 |
| `check_input_policy` | Chat/요약/초안의 원문 또는 마스킹된 데이터, 입력 rail | jailbreak·법률 악용·프롬프트 유출·개인정보 탐색·인증 우회·secret 요청을 기존 규칙으로 검사 | 키워드 오탐/우회 가능. 기존 공격/정상 문장을 회귀 테스트. Chat 주제 제한은 marketing용 정책 profile과 구분 |
| `mask_personal_data` | 외부 전송 전·메모리 저장 전·최종 출력 후 | 전화·이메일·주민번호 등 정의한 패턴을 치환, `TRANSFORM` | 자유문 이름 완전 탐지 보장 안 함. 로그에는 원문 대신 종류·발생 여부만 저장 |
| `check_generation_admission` | 유료 검사/생성 단계 직전, 서버의 동시 실행·대기 정책 | 입력 검사를 통과한 요청의 슬롯 진입 허용. 기본 단일 worker 동시 2·대기 4·대기 0.5초 | 서비스 자원 관리자가 lease를 점유·반환. 대기열 초과·timeout은 GENERATION_CAPACITY_EXCEEDED, 공격 점수 제외. 획득 전후 취소·거절에도 누수 0 |
| `check_request_budget` | 유료 단계 실행 직전, 서버 model/stage/출력 상한 | Decimal 기반 예산 확인과 예약을 하나의 lock 구간에서 수행, 초과 시 `COST_LIMIT_BLOCKED` | 단순 잔액 조회만 하면 경쟁 발생. 호출 전 reservation 필수. 없는 가격 설정은 real 호출 거절 |
| `check_output_policy` | 생성 전체 본문, 출력 rail | 빈값·길이·민감정보·정책 검사, 차단 시 안전 응답 | 미검사 출력은 반환하지 않음. 검사 오류는 fail closed. 결정적 로컬 검사 기본, 유료 검사 별도 설정 |
| `check_marketing_response` | M01/M02 생성 결과, 출력 rail | 승소 보장 등 정의한 표현을 검토 대상으로 표시, safe draft 반환 | 법적 적합성 자동 판정으로 표현하지 않음. 원문 자동 게시 기능 없음 |
| `record_risk_event` | 확정된 정책 BLOCK 후, 요청 traceId+단계 키 | 기존 사유별 점수 1회 반영. 임계 도달 시 reason을 동적 차단으로 바꾸고 원 사유는 detailCode 유지 | 중복 콜백·재시도로 점수 중복 반영 금지. 기술 오류를 공격 점수로 적립하지 않음 |

action은 총 9개로 설계를 확정했다. 요청 문맥·입력·마스킹·용량·예산을 먼저 검증하고 real 호출 전에 출력 검사까지 연결한다. 동적 위험과 마케팅도 단계적으로 검증하되 M API 활성화 전 마케팅 출력 검사를 완료한다. 구현·설치 완료는 아니다. 계약·cleanup·설정·사유 코드의 상세 이유는 NEMO_ASYNC_ACTIONS.md를 기준으로 한다.

### 기존 코드와 신규 코드의 구분

- **기존에서 확인**: `BLOCKED_LEGAL_HARM`, `BLOCKED_JAILBREAK`, `BLOCKED_PROMPT_INJECTION`, `BLOCKED_PRIVACY_RISK`, `BLOCKED_AUTH_BYPASS`, `BLOCKED_SECRET_REQUEST`, `OUT_OF_SCOPE_TOPIC`, `DYNAMIC_SESSION_BLOCKED`, `COST_LIMIT_BLOCKED`.
- **기존 비용 상세**: `REQUEST_TOO_LONG` 등. DTO 100자 초과의 422와 비용 정책의 길이 차단은 서로 다르다.
- **신규 제안**: `MARKETING_REVIEW_REQUIRED`, `GUARDRAIL_UNAVAILABLE`, `UPSTREAM_TIMEOUT`. 기존 코드인 것처럼 표시하지 않는다.
- **신규 설계 확정**: `REQUEST_CONTEXT_MISMATCH`, `GENERATION_CAPACITY_EXCEEDED`. 기술/자원 오류이며 record_risk_event의 공격 점수 대상이 아니다.
- Java의 점수 예: 법률 악용 +70, injection/jailbreak +60, privacy/secret/auth 우회 +50. 누적 100 이상·총 차단 3회 등 원본 조건을 회귀 테스트로 보존한다. 이 실험에 없는 사용자 인증과는 무관하다.

## 7. 검사 순서와 비용 경계

```text
서버 context 생성 → 요청 검증/DI → validate_request_context → session precheck → fixed input policy
  → 개인정보 마스킹 → 로컬 또는 선택적 유료 입력 rail
  → 생성 슬롯 확보 → 답변 생성 예산 예약 → await OpenAI → 생성 사용량 정산 → 슬롯 반환
  → 로컬 출력 검사 → 선택적 유료 출력 rail → marketing 검사
  → 최종 마스킹 → 응답 문맥 재확인 → JSON / 검사 완료 SSE → redacted event
  → finally: 미종료 예약 정산·슬롯/대기 카운트 반환 (정상/실패/취소 공통)
```

입력/출력 rail의 기본 action은 로컬 결정적 검사로 구성한다. NeMo 엔진의 암묵적 대화 생성·추가 LLM 호출을 비활성화하고 테스트에서 외부 호출 수를 확인한다. 유료 입력·출력 검사를 켜는 경우 각 단계가 **INPUT_GUARD / GENERATION / OUTPUT_GUARD**로 별도 예약·정산된다. 기존 규칙 전부를 LLM 판단으로 바꾸지 않는다.

각 유료 호출은 동일한 `용량 확보 → 예산 예약 → 호출 → 정산 → 슬롯 반환` 자원 경계를 적용한다. 상위 요청에서 슬롯을 잡은 채 하위 유료 검사가 다시 같은 슬롯을 얻으려 하지 않는다. 슬롯은 네트워크 호출 구간만 점유하고 출력 검사·SSE 전체 시간 동안 잡아두지 않는다. 대기열은 별도 카운터로 제한하며 Semaphore만으로 유한 대기열이 자동 보장된다고 가정하지 않는다.

reservation 상태는 `OPEN → REPORTED | ESTIMATED | RELEASED` 중 한 번만 전이한다.

- 호출 전 실패·취소: RELEASED.
- 제공자 사용량 확인: REPORTED; 실제 청구액이 아니라 보고된 토큰과 설정 단가로 계산한 값.
- 호출 시작 후 사용량 미확인: ESTIMATED. 토큰 필드는 null, `usageAvailable=false`.
- 정산·취소·timeout이 겹쳐도 예약을 두 번 닫지 않는다. 작업 취소 중에도 정산 cleanup이 완료되도록 bounded cleanup을 둔다.
- 생성에 성공한 뒤 출력이 차단되어도 이미 발생한 비용은 정산한다.
- SDK 자동 재시도는 실험 기본값 0으로 설계하고, 이후 재시도를 도입하면 호출 시도별 예약과 중복 생성을 검증한다.
- 메모리 장부는 재시작 시 사라지는 단일 worker 실험용이다. 병렬 요청은 lock으로 다루되 외부 제공자의 청구 상한을 보장하지 않는다.

## 8. SSE와 오류 계약

S01 성공 모델은 원본 `answer/blocked/fallback/traceId/model/reason/reasonCode/detailCode/usageAvailable/costSource`를 유지한다. Python 내부는 snake_case로 작성하고 API JSON은 alias로 camelCase를 사용한다.

| 상황 | JSON API | SSE |
|---|---|---|
| 입력 DTO 오류 | 422 + 정규화된 오류, 원문 input은 제거 | 응답 시작 전 422 |
| 정책 차단 | 기존 S01~S04 호환: 200 + blocked=true + 사유 | 시작 후 `blocked` 1회, done/token 없음 |
| OpenAI timeout | 504 + 기술 오류, blocked=false | 시작 후 `error` 1회, done 없음 |
| 필수 guardrail 실패 | 503 + 안전 응답 | 시작 후 `error` 1회, 출력 누출 없음 |
| 생성 용량 초과·대기 한도 | 503 + GENERATION_CAPACITY_EXCEEDED | 시작 후 `error` 1회, 공격 점수 없음 |
| 서버 요청 문맥 불일치 | 500 + REQUEST_CONTEXT_MISMATCH, 원문 제외 | 시작 후 `error` 1회, 본문 전송 중단 |
| 생성 성공 | 200 + 마스킹 answer | `meta → token* → done` |

SSE `token` 이벤트는 첫 버전에서 **검사 완료 전체 답변을 나눈 청크**다. 진짜 모델 생성 중 토큰 즉시 전송은 하지 않는다. POST SSE는 브라우저의 기본 EventSource 대신 fetch의 ReadableStream으로 읽는다. meta에는 본문·PII를 담지 않는다. 클라이언트 단절은 서버의 disconnect 확인 및 generator cancellation 경로에서 cleanup한다. 응답 시작 후에는 HTTP 상태를 바꾸려 하지 않고 SSE error 이벤트로 전달한다.

## 9. 구현 모듈과 데이터

```text
app/
  main.py                 # FastAPI 생성, lifespan, router 연결
  core/config.py          # 설정·fake/real·가격·상한·policy version
  middleware/trace.py     # trace 및 원문 없는 로그
  schemas/                # Pydantic 요청·응답·action 내부 결정
  routers/                # chat, guardrail, reference, intake, posts, lab
  services/               # AI pipeline, 규칙 분류, 게시판·마케팅
  clients/                # fake 및 async OpenAI 어댑터
  guardrails/actions.py   # @action 함수, 허용된 검사만 등록
  guardrails/config/      # config.yml, rails.co, 정책 profile
  guardrails/adapter.py    # NeMo 입출력 rail만 실행, 계약 정규화
  stores/                 # budget, risk, posts, redacted events
  context/                # 요청별 불변 context·응답 바인딩
  resources/              # bounded admission·lease·취소 cleanup
  fixtures/               # 합성 게시글·후기·절차 데이터
tests/                    # 계약·action·예산 경쟁·SSE 누출/취소
```

메모리 저장소와 lock은 lifespan에서 생성한다. limit/TTL로 세션과 로그 크기를 제한한다. 운영 DB·파일 저장·벡터 검색은 없다. 게시글 저장은 await 없는 짧은 원자 구간 또는 명시적 lock으로 다루며, 동기 장기 I/O를 async 함수에 넣지 않는다.

주력 게시판·AI 상태는 같은 이벤트 루프에서 관리하고 짧은 공유 변경 구간에 asyncio.Lock을 적용한다. AI 분석은 ID·버전을 묶은 불변 snapshot을 사용하며 네트워크 대기 동안 게시판 lock을 잡지 않는다. 샘플에 동기 I/O가 있다면 비동기 어댑터로 변경하거나 명시적 offload 경계를 둔다. 별도 동기 예제는 매 요청 새 고정 목록을 반환하므로 주력 저장소·lock을 공유하지 않는다.

Python 3.14는 학원 실행 기준이다. NeMo의 실제 배포 패키지·의존성 지원은 별도 검증이 필요하다. 설치 호환성이 맞지 않으면 독립된 Python 3.12/3.13 환경을 검증한 뒤 선택하고 lockfile에 고정한다. NeMo 설치·연동 완료로 표시하지 않는다.

## 10. Spring과 비교해서 읽기

| 원본 Spring Boot | 이번 FastAPI |
|---|---|
| Filter/Security/JWT 체인 | ASGI middleware + Pydantic; 이번에는 사용자 인증 체인 없음 |
| @RestController·Bean 생성자 주입 | APIRouter + Depends + 명시적 조립 |
| DTO record·Bean Validation | Pydantic 모델과 422 오류 |
| application 설정·Bean 생명주기 | BaseSettings + lifespan 공유 자원 |
| RestClient·SseEmitter | await 지원 클라이언트·async generator·StreamingResponse |
| synchronized 공유 장부 | 단일 event loop의 asyncio.Lock 및 단발 상태 전이 |
| JPA·Repository·운영 DB | fixture·메모리 저장소 |
| ControllerAdvice | FastAPI exception handler + SSE 이벤트 오류 |
| JUnit·MockMvc | pytest·TestClient/ASGITransport·dependency_overrides |

이벤트 루프에서 대기를 양보하는 것이 핵심이지, FastAPI가 항상 Spring보다 빠르다는 의미는 아니다. Spring도 비동기를 지원한다. 이번에는 Java 기술의 단순 치환보다 Python의 await·자원 수명·취소·가드레일 흐름을 명확하게 배우는 데 집중한다.

## 11. 구현 전후 검증 기준

1. 기존 37개 ID를 선정 11/제외 26으로 빠짐없이 분류한다.
2. fake 모드에서 외부 호출 0회, real 모드 키·가격 누락은 시작/실행 전 실패한다.
3. NeMo 흐름을 실제 통과한 정상/차단/변환 테스트와 일반 action 단위 테스트를 구분한다.
4. 공격·정상·PII·마케팅 사례를 각 profile로 검증한다. 단순 키워드 규칙의 한계를 문서화한다.
5. 동시 예산 요청·중복 정산·호출 전후 취소·출력 차단 비용을 검증한다.
6. SSE 검사 전 본문 0바이트, 최종 안전 청크만 공개, terminal 이벤트 1회, disconnect cleanup을 확인한다.
7. 게시글·리뷰 삭제는 HTTP CRUD에서만 수행하며 LLM/NeMo에 업무 변경 권한을 주지 않는다.
8. 로그·422 오류·health·SSE에 키와 원문 PII가 노출되지 않는지 확인한다.
9. 가짜 LLM의 여러 지연 요청이 순차 시간의 합으로 처리되지 않는지, AI 대기 중 `/health`와 다른 요청이 응답하는지 검증한다. 하드웨어에 종속된 절대 성능 수치를 성공 기준으로 삼지 않는다.
10. 실제 async 경로의 테스트는 AsyncClient+ASGITransport 등으로 수행한다. TestClient의 기본 기능 검증과 비동기 동시성 검증을 구분하고, 테스트 lifespan 시작·종료도 명시적으로 관리한다.
11. 동시 A/B 요청의 원문·결과·판정이 섞이지 않으며 문맥 불일치를 안전 중단하는지 확인한다.
12. 동시 실행·대기열·대기 timeout·예약 전후 취소를 검증하고 활성 슬롯·대기 카운트·열린 예약이 모두 정리되는지 확인한다.

## 근거 및 공식 문서

로컬 기준: `legal-ai-intake-security-server/docs/API_STATUS_SPEC.md`, `api/AiController.java`, `api/LegalGuardrailController.java`, `api/LegalOutputGuardrailController.java`, `dto/AiChatRequest.java`, `dto/AiChatResponse.java`, `riskengine/LegalFixedGuardService.java`, `riskengine/LegalDynamicGuardService.java`, `cost/AiCostControlService.java`. Java 경로는 `backend/guardrail-ready-policy-checker/src/main/java/com/ohgiraffers/handlermethod/` 기준.

- [FastAPI async와 일반 함수의 실행 차이](https://fastapi.tiangolo.com/async/)
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [NeMo Python action 정의·반환값](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/actions/creating-actions)
- [NeMo 입출력 rail 선택 실행](https://docs.nvidia.com/nemo/guardrails/run-guardrailed-inference/using-python-apis/generation-options)

공식 문서의 기능을 바탕으로 작성한 프로젝트별 설계 제안이며, 위 21개 API나 Python action을 이번 문서 작업에서 구현·실행한 것은 아니다.
