# 비동기 보안 설계 해설 — action 9개와 자원 관리

2026-11-04 · **추천안을 채택해 설계 범위를 확정했다. 구현·설치는 아직 하지 않았다.** 기존 7개에 validate_request_context와 check_generation_admission을 추가해 총 9개다. API 21개 계획은 유지한다. action 이름은 NVIDIA 내장 함수가 아니라 이 프로젝트의 사용자 정의 이름이다.

핵심은 '검사를 더 많이 넣는다'가 아니라 **어느 요청의 데이터를 검사했고, 언제 실행을 허용하며, 중단해도 자원이 정리되는지**를 명확하게 만드는 것이다. 이 해설은 도입 이유를 먼저 설명하고, 구현 계약과 실험 기준을 함께 정한다.

제공된 수업 과제는 별도 ohgi-review-server의 동기 리뷰 등록·조회와 비동기 답글 3개 API다. 여기에 NeMo 9개를 모두 넣지 않는다. 9개 action과 필수 마케팅 검사는 주력 Legal Intake 챗봇·M01/M02 확장에 적용한다. 두 앱의 요구·검증 상태를 구분한다.

## 1. 정책과 실행 방식을 구분하기

개인정보를 가리고 위험 요청을 막는 정책은 동기/비동기 또는 Spring/FastAPI에 따라 무조건 달라지지 않는다. 달라지는 것은 호출 방식, 공유 상태 관리, 취소·timeout 처리, 답변 공개 시점이다. Spring도 비동기 요청을 처리할 수 있고 Java 서버에서도 예산 경쟁·상태 혼합 문제가 생길 수 있다.

| 구간 | Spring에서 가능한 구조 | 이번 FastAPI 구조 |
|---|---|---|
| NeMo 호출 | Java가 Python NeMo 서비스에 HTTP 요청 | Python 프로세스 안에서 비동기 rail API 호출 |
| 실행 자원 | 스레드·비동기 클라이언트 등 구성에 따라 다름 | 이벤트 루프에서 비동기 I/O 대기 |
| 위험·예산 상태 | 동기화된 공유 서비스·DB 등 | 단일 worker 메모리 store + 짧은 lock |
| 연결 종료 | 서버·client별 종료 콜백 | disconnect·generator cancellation·finally |
| 출력 | JSON·SSE 모두 가능 | JSON 또는 전체 검사 후 안전한 SSE 청크 |

이는 프로젝트의 선택이다. FastAPI에서도 별도 NeMo 서버를 호출할 수 있으며, 프레임워크가 배치를 강제하지 않는다.

## 2. 채택한 설계와 검증 우선순위

| 우선순위 | action | 현재 구분 | 실험의 핵심 |
|---|---|---|---|
| 1 | check_request_budget | 기존 강화 | 동시 요청도 확인+예약을 한 번의 원자 처리로 수행 |
| 2 | validate_request_context | 신규 설계 확정 | 동시 요청 A/B의 데이터·결과가 뒤섞이지 않게 서버 문맥 확인 |
| 3 | check_output_policy + mask_personal_data | 기존 강화 | 검사 완료한 정확한 본문만 SSE로 공개 |
| 4 | check_generation_admission | 신규 설계 확정 | 유료 생성의 동시 실행 수를 제한하고 무한 대기를 막음 |
| 5 | check_marketing_response | 이번 샘플 연동 필수 | 후기·요약·답변 초안의 보장/과장 표현 검사 및 사람 검토 표시 |

입력 정책과 마스킹은 기본이다. 위 순위는 그 기반 위에서 비동기를 배우기 위해 집중할 순서이며 모든 서비스에 동일한 action이 필수라는 뜻은 아니다.

확정한 전체 9개 action은 다음과 같다. 데이터 형태의 합의 내용은 [설계 설정](async-security-design.json)에도 기록한다.

| action | 필수 책임 |
|---|---|
| validate_request_context | 요청·대상 snapshot·응답의 바인딩 |
| check_session_risk | 누적 위험·기존 세션 차단 확인 |
| check_input_policy | 원본 위험 규칙과 endpoint별 입력 정책 |
| mask_personal_data | 전송·저장·반환 전 정의한 패턴 마스킹 |
| check_generation_admission | 각 유료 호출의 실행 용량 진입 정책 |
| check_request_budget | 예산 원자 예약과 호출 허용 |
| check_output_policy | 완성 답변의 정책 검사 |
| check_marketing_response | 마케팅 답변 초안의 검토 필요 판단 |
| record_risk_event | 확정된 정책 위험을 중복 없이 기록 |

## 3. 기존 강화: check_request_budget

가상 예산 100, 호출당 예약 70으로 요청 2개를 동시에 보낸다. 잠금 없이 각자 100을 조회하면 둘 다 허용될 수 있다. lock 안에서 확인+예약하면 하나만 허용된다. 이 숫자는 실제 요금이 아니다.

- 입력: 서버가 정한 모델·단계·출력 상한·세션 구분자.
- 출력: ALLOW와 reservation 또는 COST_LIMIT_BLOCKED.
- 네트워크 대기 동안 lock을 잡지 않는다.
- 호출 전 실패는 RELEASED, 시작 후 usage 미확인은 ESTIMATED, 보고되면 REPORTED.
- 오류와 취소가 겹쳐도 한 번만 종료한다. 재시도는 별도 설계한다.

비교 실험: 의도적으로 잘못된 '조회 후 나중에 차감' 구현과 원자 예약을 가짜 client로 비교한다. 실제 유료 호출로 경쟁을 재현하지 않는다.

## 4. 신규 확정: validate_request_context

각 요청마다 서버가 만든 requestId/traceId와 독립 context를 사용한다. 질문·후기 ID·검사 결과가 어느 요청의 것인지 확인한다. 공유 client 객체에 current_message/current_user 같은 요청별 값을 넣지 않는다.

- 입력: 서버 context와 서비스가 선택한 분석 대상의 context. 클라이언트의 주장만으로 통과시키지 않는다.
- 검사: 필수 문맥 누락·다른 요청의 결과 재사용·컨텍스트 바인딩 불일치.
- 실패: REQUEST_CONTEXT_MISMATCH라는 **신규 설계 코드**로 안전 중단. typed ContextBindingError를 서비스에서 500/SSE error로 매핑하고, 정책 차단의 200/blocked로 바꾸거나 공격 점수로 적립하지 않는다. 본문을 오류에 넣지 않는다.
- 한계: requestId가 맞다고 사용자 소유권이 증명되는 것은 아니다. 로그인·권한 검사는 hybrid 단계에서 별도 수행한다.

비교 실험: 합성 데이터 A/B 요청을 동시에 반복하고 의도적으로 하나의 전역 current_message를 공유한 잘못된 예와 요청별 context 예를 비교한다. A 응답·로그에 B의 본문·판정이 섞이지 않아야 한다. 이 검사는 올바른 상태 격리를 대체하는 마법 같은 방어가 아니라 오류를 일찍 발견하는 보조 장치다.

## 5. 기존 강화: 출력 검사·마스킹과 SSE

입력 검사만 해서는 출력의 개인정보 누출을 막을 수 없다. 전체 생성 결과를 검사하고 최종 마스킹한 safeText만 전송한다. 검사를 통과한 뒤 다른 본문으로 바꿔 전송하지 않는다.

실험은 가짜 client가 의도적으로 합성 전화번호·금지 표현을 포함한 답변을 반환하게 만든다. SSE 이벤트를 수집해 최종 마스킹 전 원문이 한 번이라도 노출되었는지 확인한다. 단일 청크 단위 검사뿐 아니라 전체 재조립 결과도 확인한다.

현재 첫 버전은 전체 검사 후 전송이다. 이후 NeMo 자체의 output-rail streaming을 실험한다면 설치 버전의 stream_async·streaming 설정·청크 문맥·stream_first 정책을 함께 확인한다. 문서의 stream_first=True는 검사 전에 청크가 전달될 수 있으므로 현재 요구와 동일한 보장으로 취급하지 않는다.

## 6. 신규 확정: check_generation_admission

동시 생성 2개라는 실험 제한을 두고 요청 10개를 보낸다. 동시에 실행되는 AI 호출은 최대 2개로 제한하고, 나머지는 짧게 대기하거나 설정된 정책에 따라 거절한다. 동시 실행 수 제한과 초당 요청 수 제한은 다르다.

- action 역할: 서버 정책에 따라 생성 진입 허용 여부를 판단하고 서비스 자원 관리자와 연결한다.
- 실제 점유·해제: async semaphore/자원 관리자가 처리. 반환값에 슬롯을 표현해도 서버만 발급·관리한다.
- 실패: 대기 한도 초과 시 GENERATION_CAPACITY_EXCEEDED라는 **신규 설계 코드**로 503/SSE error를 반환한다. typed AdmissionRejected를 서비스에서 처리하며 정책 차단 blocked 이벤트나 공격 점수로 바꾸지 않는다.
- 유한 대기열과 timeout을 둔다. 취소되면 슬롯이 남지 않게 finally에서 해제한다.
- 용량 확보를 기다리는 동안 비용을 오래 예약해 두지 않는다. 권장 순서는 용량 확보 → 예산 예약 → 호출 → 정산 → 슬롯 해제다. 예산 거절 시에도 확보한 슬롯을 해제한다.
- 이 실험은 단일 worker 한정이다. worker 여러 개에 걸친 전역 한도는 메모리 semaphore 하나로 보장되지 않는다.

실험에서 최대 동시 실행 수, 대기 시간, 거절 수, 요청 취소 후 활성 슬롯 0을 확인한다. 함수 이름만 action으로 만들고 실제 동시 호출을 제한하지 않으면 완료가 아니다.

## 7. action으로 넘기면 안 되는 필수 종료 처리

| 기능 | 책임 위치 |
|---|---|
| API timeout | 서비스·client의 timeout 경계 |
| 사용자 연결 종료 감지 | request/stream generator |
| 비용 정산·예약 종료 | 서비스의 bounded cleanup·상태 저장소 |
| 동시 실행 슬롯 해제 | 자원 관리자의 finally/async context manager |
| 요청별 context 생성 | 진입 middleware·dependency |

이 기능은 정상 rail이 끝까지 실행되어야만 수행되는 action 하나에 의존시키지 않는다. 취소를 삼켜 성공으로 바꾸지 않고 정리를 마친 뒤 취소를 전달한다. 단순 asyncio.Lock·Semaphore는 NeMo의 기능이 아니라 Python 동시성 도구다.

## 8. 꼭 알아둘 async 옵션의 차이

`async def`·await로 비동기 I/O를 기다리는 것과 NeMo의 `@action(execute_async=True)`는 다르다. 공식 문서상 후자는 Colang 2.x에서 action 완료를 기다리지 않고 이벤트 처리를 계속하는 옵션이다. 입력·예산 검사는 결과가 나와야 다음 단계로 갈 수 있으므로 '비동기니까 모든 검사에 True를 붙인다'는 방식으로 구성하지 않는다.

NeMo 버전·Colang 런타임·Python 호환성을 먼저 고정한다. action 함수가 결과 dict를 반환해도 흐름이 이를 읽고 중단·변환해야 한다. 함수 실행만으로 NeMo 통합 완료를 판정하지 않는다.

## 9. 추천 학습 순서

1. 기존 예산 action의 원자 예약을 가짜 요청 2개로 확인.
2. 요청별 context와 전역 변수 오용을 A/B 비교.
3. 합성 PII 답변의 SSE 누출 여부 확인.
4. 동시 실행 2개 제한과 대기 중 취소 확인.
5. 강사 게시판 샘플 수령 후 마케팅 표현 검사 연결.

두 신규 action은 정식 설계 범위다. 구현·동작 검증 완료와는 구분한다.

## 10. 왜 이 구조를 선택했는가 — 문제에서 구현으로

### 10-1. 예산과 동시 실행 제한은 서로 다른 문제다

하루 예산이 충분해도 요청 1,000개를 한꺼번에 실행하면 연결·메모리·제공자 동시 한도를 소모한다. 반대로 동시 실행 2개만 허용해도 하루 내내 호출하면 예산을 초과할 수 있다. 그래서 **admission은 지금 실행할 자리, budget은 쓸 수 있는 돈**을 각각 관리한다.

동시 실행 제한만으로 RPS 제한이 되는 것도 아니다. 짧은 요청 두 개가 빠르게 끝나면 초당 여러 개가 실행될 수 있다. 이번에는 동시 실행·유한 대기만 구현하고 제공자별 시간당 토큰/RPS 제어는 별도 후속 범위로 둔다.

### 10-2. 대기 후 예약하는 이유

대기열에 있는 요청이 먼저 돈을 예약하면 아직 실행도 하지 않았는데 다른 요청의 가용 예산을 묶는다. 따라서 입력을 검사한 뒤 **자리 확보 → 돈 예약 → 외부 호출** 순서를 따른다. 돈 예약에 실패하면 자리를 즉시 반환한다.

유료 입력/출력 검사를 켜면 그 호출도 같은 실행 자원 경계를 사용한다. 상위 Chat이 자리를 잡은 채 하위 검사도 같은 자리를 요구하는 중첩 획득은 금지한다. 동시 한도를 1로 낮춰도 교착되지 않아야 한다.

### 10-3. 출력 검사를 다시 강조하는 이유

사용자가 보낸 질문을 검사해도 AI가 만든 답변의 내용은 그 뒤에 생긴다. 따라서 입력과 출력은 서로 다른 검사 대상이다. SSE로 미리 보낸 문장은 나중에 회수할 수 없으므로 전체 답변 검사·마스킹을 마친 후 전송한다.

이 선택은 첫 글자까지 기다리는 시간이 길어질 수 있다. 학습 첫 단계에서는 안전한 공개 시점을 이해하는 데 집중하고, 이후 청크 단위 검사를 별도 실험한다. NeMo의 stream_first 설정도 설치 버전 기준으로 확인한다.

### 10-4. 문맥 확인만으로 충분하지 않은 이유

전역 current_message를 공유한 상태에서 requestId만 비교하면 이미 섞인 데이터를 알아채지 못할 수 있다. 기본 방어는 **요청별 독립 상태와 불변 데이터 전달**이다. action은 그 구조를 검사하는 두 번째 확인 단계다.

서버는 requestId/traceId를 생성하고, 분석할 게시글·후기는 ID와 버전을 묶은 snapshot으로 고정한다. Client·NeMo 객체는 공유할 수 있어도 사용자 본문·검사 결과를 그 객체의 현재 요청 속성에 저장하지 않는다. 같은 sessionId에서 요청이 동시에 와도 요청별 context는 분리한다.

## 11. 구현 계약: 부품이 어디까지 책임지는가

| 부품 | 생성·수명 | 책임 |
|---|---|---|
| RequestContext | 요청 진입마다 생성, 불변 | requestId·traceId·정책 profile/version·분석 대상 snapshot 식별 |
| PipelineEnvelope | 단계별 새 값으로 전달 | 요청 context와 해당 단계 본문·검사 결과를 묶음 |
| AdmissionManager | lifespan 공유, 단일 worker | 활성 호출·대기 카운트·유한 큐·lease 발급/반환 |
| BudgetStore | lifespan 공유 | Decimal 잔액·단계별 reservation·단발 정산 |
| NeMo adapter/actions | client/rails는 공유 가능, 요청 데이터는 분리 | 9개 검사·결정을 호출하고 정책 차단과 기술 오류를 구분 |
| PaidCallService | 각 유료 단계에서 실행 | 용량→예산→호출→정산, 항상 cleanup |
| Publisher | 요청별 | 최종 안전 본문·문맥 확인 후 JSON/SSE 반환 |

이름은 구현 시 사용할 내부 계약이며 아직 클래스 파일이 존재하는 것은 아니다. Python dataclass(frozen=True) 또는 동등한 불변 모델을 사용한다. ContextVar를 도입하더라도 별도 task 전파·reset을 검증하며, 모든 상태를 숨은 전역 변수로 옮기는 대안으로 사용하지 않는다.

응답 직전 validate_request_context는 requestId, 정책 버전, 분석 snapshot의 연결을 재확인한다. safeText와 검사 결과의 내부 바인딩도 확인하고 Publisher는 그 safeText를 그대로 사용한다. 필요하면 내부 content fingerprint를 사용하되 원문·fingerprint를 일반 로그나 API에 노출하지 않으며, fingerprint를 사용자 인증 수단으로 취급하지 않는다.

### 공통 반환값과 기술 오류

정책 action의 내부 결과는 ALLOW/BLOCK/TRANSFORM/REVIEW와 reasonCode/detailCode를 갖는다. 두 신규 action의 문맥 불일치·과부하는 정책 BLOCK과 다르므로 typed 기술 예외를 서비스 어댑터가 처리한다. NeMo의 일반적인 차단 응답으로 일괄 변환하지 않는다.

- REQUEST_CONTEXT_MISMATCH: HTTP 500 또는 시작 후 SSE error. 내부 상태 혼합 가능성이므로 본문 반환 중단.
- GENERATION_CAPACITY_EXCEEDED: HTTP 503 또는 시작 후 SSE error. 슬롯/대기 제한에 따른 과부하.
- COST_LIMIT_BLOCKED: 기존 API 계약의 정책 차단, HTTP 200 + blocked 또는 SSE blocked.
- timeout·guardrail 실패: 기존 상세 설계의 504/503 또는 SSE error.

위 HTTP 매핑과 새 코드는 우리 설계 계약이며 NeMo 기본 사양이 아니다. 기술 오류에 내부 stack·키·원문을 싣지 않는다.

## 12. 실행 순서와 자원 수명

```text
서버가 RequestContext 생성
 → 요청 검증/DI → validate_request_context
 → session risk → input policy → input mask
 → 로컬 입력 rail
 → PaidCallService
     [입장 허용·슬롯 확보] → [예산 예약] → [await 외부 호출]
     → [보고/추정 정산] → [슬롯 반환]
 → 로컬 출력 rail → marketing 검사 → 최종 mask
 → validate_request_context 재확인 → 안전 JSON/SSE

어느 단계에서 중단되어도 finally에서 남은 자원 정리
```

기본 입력·출력 검사는 유료 생성 없이 로컬 action으로 처리한다. 유료 검사를 켜는 경우 INPUT_GUARD·GENERATION·OUTPUT_GUARD 각각 PaidCallService 경계를 통과한다. 슬롯은 외부 호출과 그 정산 구간에만 유지하며 느린 SSE 수신자에게 전송하는 전체 시간 동안 잡지 않는다.

다음은 흐름을 설명하는 의사 코드다. 취소 경쟁과 종료 상태는 실제 자원 관리자에서 검증해야 한다.

```text
lease = 없음, reservation = 없음
try:
    lease = await admission.acquire(대기 한도)
    reservation = await budget.reserve(서버가 정한 상한)
    mark_call_started()
    result = await provider.call()
    await budget.settle_once(result.usage)
    return 요청에 바인딩된 result
finally:
    미종료 reservation은 호출 시작 여부에 따라 해제/추정 정산
    lease와 대기 카운트는 소유한 경우에만 한 번 반환
    정리를 마치고 원래 오류·취소를 그대로 전달
```

다음 action에서 release를 실행하도록 기대하지 않는다. 취소는 어느 await 사이에서도 일어날 수 있다. acquire 완료 직후의 취소도 관리자 내부에서 반환을 보장하고, 소유하지 않은 permit을 release하여 한도를 늘리지 않도록 한다. 단순 Semaphore만으로 대기열 길이 제한은 생기지 않으므로 별도 동기화 카운터가 필요하다. FIFO 공정성은 이번 보장에 포함하지 않는다.

## 13. 실험용 설정과 명확한 한계

| 새 설정 이름 | 설계 기본값 | 이유 |
|---|---|---|
| AI_MAX_CONCURRENT | 2 | 가짜 요청의 겹친 대기를 관찰하기 쉬운 작은 값 |
| AI_MAX_WAITERS | 4 | 무한 대기열을 피하고 거절 경로도 실험 |
| AI_QUEUE_WAIT_SECONDS | 0.5 | 대기 한도를 짧게 재현 |
| AI_REQUEST_TIMEOUT_SECONDS | 30 | 요청 전체에 걸친 유한 deadline |
| AI_CLEANUP_TIMEOUT_SECONDS | 2 | 취소 후 정리가 무기한 대기하지 않도록 상한 |
| workers | 1 | 메모리 슬롯·예산이 프로세스별로 분리되는 문제를 피하는 학습 범위 |

이는 Settings 구현 전 합의한 기본값이며 현재 .env에 이미 적용되어 있다는 뜻은 아니다. queue·provider timeout은 요청 잔여 deadline보다 길지 않게 계산한다. 필수 정리에는 제한된 추가 시간을 허용한다. 그 정리마저 실패하면 cleanup failure를 원문 없이 기록하고 상태를 정상 정리 완료로 표시하지 않는다. 추적되지 않는 fire-and-forget task로 정리를 떠넘기지 않는다.

외부 요청 자체가 과도하게 들어오는 문제까지 해결한 것은 아니다. 공개 서비스의 인증·요청 크기·ingress rate limit·분산 한도는 hybrid/운영 단계의 별도 범위다.

## 14. 이유를 확인하는 비교 실험과 완료 기준

| 실험 | 입력·고장 주입 | 통과 기준 |
|---|---|---|
| 예산 경쟁 | 예산 100, 예약 70짜리 요청 2개, barrier로 동시 진입 | 하나만 예약·한도 초과 없음·중복 정산 없음 |
| A/B 문맥 | 합성 A/B 본문·다른 snapshot을 교차 스케줄 | 결과·판정·로그 바인딩 혼합 없음, 잘못 묶은 결과는 500 |
| 실행 한도 | 최대 동시 2, fake 호출을 event로 붙잡고 요청 추가 | 실제 in-flight ≤2, waiter ≤4, 초과는 503 |
| 대기 취소 | 대기열에 있는 요청을 취소 | waiter와 permit 누수 없음, 예산 예약 없음 |
| 획득 직후 취소 | 슬롯 획득/예산 예약 전후에 취소 주입 | 소유 자원만 한 번 반환, 실제 호출 전 예약은 RELEASED |
| 호출 이후 단절 | provider 호출 시작 후 단절·usage 미확인 | ESTIMATED 한 번, 연결·슬롯 정리 |
| 출력 누출 | 합성 PII 답변·검사 지연·출력 차단 | JSON/SSE 원문 누출 없음, 차단 전에 발생한 비용은 정산 |
| 중첩 유료 검사 | 동시 한도 1에서 유료 입력/생성/출력 순차 실행 | 자기 슬롯 재획득 교착 없음, 단계별 정산 |
| 재요청 | 정산·취소 callback 반복 | 상태 전이 중복 없음; 다른 새 유료 요청은 별도 예약 |
| 이벤트 루프 | AI 대기 중 health와 다른 요청 호출 | 이벤트 루프 blocking 없음, 대기와 실행 수 관찰 가능 |

실험은 fake provider·event/barrier로 순서를 제어한다. 실제 돈을 쓰거나 특정 CPU의 절대 시간 수치를 통과 조건으로 삼지 않는다. 개인정보·키·본문을 일반 로그에 기록하지 않고 서버 식별자·단계·결정·카운트·시간만 관찰한다.

단위 테스트는 자원 관리자와 action 로직을 확인하고, 통합 테스트는 실제 NeMo 흐름을 통과해 오류 분류·응답 공개를 확인한다. fake API 테스트 통과를 NeMo 설치나 실제 OpenAI 연결 성공으로 표시하지 않는다.

## 15. 구현 순서

1. 버전·Colang 런타임·Python 호환성을 확인하고 lockfile 고정.
2. 불변 context/envelope와 fake provider를 만들고 A/B 격리 검증.
3. AdmissionManager와 BudgetStore의 단발 상태 전이를 독립 검증.
4. 9개 action을 등록하고 입력·출력 rail 및 기술 예외 매핑 연결.
5. JSON Chat에서 정상/차단/과부하/취소를 확인한 뒤 SSE 추가.
6. 강사 샘플 수령 후 M01/M02와 marketing 정책 profile 검증.

별도 HTTP action 실행 API나 임의 Python 실행 endpoint는 추가하지 않는다. 현재 서버 기능은 미구현이며 이번 변경은 설계 채택·해설·시각 자료의 갱신이다.

## 16. 추천 5번: 이번 게시판 샘플에 반드시 연결

check_marketing_response는 이번 fastapi-lab의 필수 기능이다. 다음 hybrid 단계나 선택 과제로 미루지 않는다. 기존 9개 action에 포함되어 있으므로 action 개수는 증가하지 않는다. 강사 샘플의 기본 CRUD와 우리가 추가하는 AI 정책 검사를 구분해 검증한다.

**도입 이유:** 단순 개인정보 마스킹만으로는 '100% 승소 보장' 같은 표현이 안전한 마케팅 초안으로 바뀌지 않는다. 일반 Chat의 위험 검사와 마케팅 문구의 검토 정책은 목적이 다르므로 별도 action이 필요하다. 이는 프로젝트의 표현 정책 검사이며 광고 관련 법령의 자동 적합성 판정이 아니다.

적용 흐름은 M01 요약/M02 답변 생성 → check_output_policy → check_marketing_response → 최종 마스킹 → 응답 문맥 확인 → 반환이다. 두 endpoint에서 이 단계를 생략할 수 없도록 공통 서비스에 연결한다. 정상 문구가 통과해도 자동 외부 게시는 하지 않는다.

| 실험 사례 | 정책 결과 |
|---|---|
| 상담 경험에 대한 통상적인 감사 문구 | ALLOW, 초안으로 반환 |
| 단정적인 승소 보장·과장 표현 | REVIEW, 안전하게 정리한 초안과 검토 필요 표시 |
| '승소를 보장하지 않습니다' 또는 보장 문구를 비판적으로 인용 | 단어 포함만으로 자동 차단하지 않음. 문맥 규칙을 회귀 테스트하고 불확실하면 REVIEW |
| 합성 전화번호·이메일이 섞인 초안 | 최종 마스킹 후 반환, 원문은 이벤트·로그에 미노출 |
| 위험 행위를 돕는 본문 | 공통 출력 정책의 BLOCK 경로, 초안 원문 미반환 |
| 검사 오류·timeout | 안전한 기술 오류, 검사 생략 후 원문 반환 금지 |

M endpoint 전용 제안 응답에 reviewRequired·reviewReasons·draftStatus를 명시한다. 이 필드는 샘플 실제 DTO와 대조해 확정하며 기존 Chat 응답 계약에 무조건 추가하지 않는다. REVIEW의 safeText에는 제거·치환을 마친 초안만 넣고, 원 표현이 안전하게 수정되지 않으면 본문 대신 고정 안내와 검토 사유만 반환한다.

필수 통과 기준: M01/M02 모두에서 검사 호출 확인, 위 사례 검증, 검토 플래그와 안전 본문 일치, 검사 실패 시 누출 없음, 문서·흐름도·샘플 API 계약 일치. 자료의 실제 링크/저장 위치를 확인하기 전에는 구체적인 샘플 필드나 구현 완료를 추정하지 않는다.

## 공식 근거

- [NeMo actions: async 함수와 execute_async 옵션](https://docs.nvidia.com/nemo/guardrails/v0.24.1/configure-guardrails/actions/creating-actions)
- [NeMo output-rail streaming](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/yaml-schema/streaming/output-rail-streaming)
- [NeMo 런타임 구조](https://docs.nvidia.com/nemo/guardrails/reference/colang-architecture-guide)

정책·실험·새 함수 이름은 공식 문서에 기반한 프로젝트별 제안이다.
