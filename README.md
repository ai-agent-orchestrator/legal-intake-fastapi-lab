# 확정한 진행 범위: 오늘 1안, 주말 추가 구현

- **오늘(2026-11-04):** 1안인 동기 접수 등록·조회와 비동기 AI 안내, 3개 API까지 완성합니다. 현재 구현과 fake/mock 기반 테스트 23개는 완료했습니다. 실제 OpenAI 어댑터도 포함하지만 유료 API 호출 검증은 별도입니다.
- **주말:** 현재 MVP를 먼저 복습한 뒤 개인정보 마스킹·입력/출력 검사 Python action부터 작은 단위로 추가합니다. NeMo 연동·SSE·비동기 게시판은 후속 후보이며, 주말에 전부 완성하는 범위로 잡지 않습니다.
- **구현 범위:** 오늘은 MVP 범위를 넓히지 않고, 추가 구현은 주말에 진행합니다. 인증·인가는 이번 구현에서 제외합니다.

오늘 범위를 작게 잡는 이유는 등록 → 조회 → 저장 사실 기반 AI 안내라는 한 흐름에서 동기/비동기·DI·예외 처리를 확인하기 위해서입니다. 보안 action과 스트리밍을 이후에 하나씩 붙여야 변경 효과와 오류 원인을 비교하기 쉽습니다.

[한국어](README.md) | [English](README.en.md)

## 1. 세 저장소의 발전 순서 — ① → ③ → ②

| 순서 | 저장소 | 역할 |
|---|---|---|
| 첫 번째 · 현재 ① | **`legal-intake-fastapi-lab`** | HOWTO 복습·FastAPI 단독 비동기 실험·Legal Intake 일부 이전 |
| 두 번째 ③ | **`legal-intake-hybrid-lab`** | Spring Boot 인증·인가와 FastAPI AI 서비스를 연결하고 경계 검증 |
| 세 번째 ② | **`legal-intake-ai-service`** | 검증한 기능을 재사용 가능한 AI 서비스로 발전·운영 조건 보완 |

앞 단계의 코드·계약·테스트를 다음 단계로 가져옵니다. 세 저장소의 개발·배포가 완료되었다는 뜻은 아닙니다.

## 2. 현재 완성 범위: Legal Intake 동기 2개 + 비동기 1개

선택한 MVP는 학원 리뷰의 처리 구조를 Legal Intake로 바꾼 작은 개인 학습용 버전입니다. 기존 Spring 접수 API 전체와 호환되는 이전본이 아니며, 수업 도메인 변경 허용 여부는 별도 확인 대상입니다.

| 현재 MVP API | 방식 | 결과 |
|---|---|---|
| POST /api/intakes | def | clientName·caseType·coreStatement·선택 desiredNextStep → 201/422 |
| GET /api/intakes/{intake_id} | def | camelCase 접수 → 200, 사용자 정의 404 |
| POST /api/intakes/{intake_id}/guidance | async def | 저장 사실 → prompt → await AI → 200, LLM 실패 502 |

동기 Repository는 짧은 lock으로 보호하고 async 서비스는 snapshot 조회를 to_thread로 분리합니다. 의뢰인 이름은 AI prompt에서 제외합니다. 나머지 사건 본문 자동 마스킹·NeMo·예산·SSE·인증·영속 DB는 아직 없습니다. 재시작하면 메모리 접수는 초기화됩니다.

### 참고: 학원 리뷰 과제 계약

사용자가 제공한 실제 과제 명세를 기준으로 **ohgi-review-server**를 구현했습니다. 이전의 단순 GET /posts 예제 대신 이 서버가 동기·비동기 과제의 기준입니다. 요청한 main/dependencies/core/domain/repositories/schemas/clients/services/routers 구조와 빈 __init__.py를 갖췄습니다. 학원 chap01·02의 구조를 참고해 제공된 요구사항으로 작성했으며 원본 전체 소스를 복제했다고 표시하지 않습니다.

| 과제 API | 실행 방식 | 검증한 결과 |
|---|---|---|
| POST /api/reviews | def | customerName·rating(정수 1~5)·content → 201, 잘못된 입력 422 |
| GET /api/reviews/{review_id} | def | camelCase 리뷰 반환, 사용자 정의 ReviewNotFoundError/처리기로 404 |
| POST /api/reviews/{review_id}/reply | async def | 저장된 리뷰 → 프롬프트 → await LLM → 답글, 호출 실패 AiRequestError/처리기로 502 |

### 강사가 안내한 직접 작성 순서

1. 프로젝트: 빈 폴더에서 uv init → uv add fastapi[standard] → 패키지·빈 __init__.py → pyproject entrypoint.
2. 리뷰: 엔티티 → 딕셔너리 저장소 → DTO → 예외·처리기 → 서비스 → 의존성 함수 → 라우터 → main 조립.
3. 답글: pydantic-settings·openai 추가 → 설정 → LLM client → 답글 서비스 → 의존성 함수 → async 핸들러 → lifespan.

설정·LLM client는 chap02 파일을 참고할 수 있습니다. 직접 작성한 코드와 이 참고본을 위 순서로 비교합니다.

### 완성 기준과 선택 심화

실제 Uvicorn·fake LLM으로 /docs, 201·422·404와 답글을 확인했고, 로그에서 등록·조회는 AnyIO worker thread, 답글은 MainThread임을 확인했습니다. 독립 uv 환경의 uv run fastapi dev와 실제 OpenAI·수동 Postman은 별도 확인 대상으로 남깁니다.

별점별 말투, 답글 저장·조회, 동기 LLM 답글 비교 API는 **시간이 남을 때만 할 선택 심화**이며 아직 추가하지 않았습니다. Postman 요청과 live 확인 명령은 [참고본 README](ohgi-review-server/README.md)에 있습니다.

| 파트 | 구현 방식 | 범위 |
|---|---|---|
| **현재 루트 MVP** | def 2개 + async def 1개 | 접수 등록·조회·저장된 접수 기반 AI 안내, 구현·23개 테스트 확인 |
| 수업 과제 앱 | def 2개 + async def 1개 | ohgi-review-server, 딕셔너리 리뷰·LLM 답글, 인증·DB·NeMo 제외 |
| 주력 비동기 게시판 | async def 핸들러·요청별 비동기 처리 | B01~B07 게시글·후기 관리, C13 로컬 집계 |
| 비동기 챗봇 | `async def`·비동기 client·`await` | S01/S02 Legal Intake Chat·SSE, NeMo·예산·용량·취소 |
| 게시판 AI 확장 | 비동기 챗봇 파트의 공통 AI 서비스 재사용 | M01 요약·M02 답변 초안·필수 마케팅 action |

현재 루트 MVP 3개, 리뷰 참고본 3개, 후속 확장 21개는 계약·구현 상태를 구분합니다. 현재 MVP의 등록·조회와 리뷰 과제의 등록·조회는 def로 유지합니다. 후속 확장 초안의 전체 비동기화·마케팅 action을 현재 MVP에 이미 구현한 것으로 표시하지 않습니다.

### 후속 21개 확장 흐름 — 아래 보안 기능은 아직 설계

```text
Swagger / 브라우저
 → Uvicorn / ASGI
 → FastAPI: trace·Pydantic·Depends·APIRouter
 → 요청 문맥·세션 위험·입력 정책 검사·개인정보 마스킹
 → 생성 용량 확보 → 비용 예약
 → await OpenAI 비동기 호출
 → 사용량 정산·출력 검사·마케팅 검사·최종 마스킹
 → 응답 문맥 재확인 → JSON 또는 검사 완료 SSE
 → finally: 미종료 예약 정산·실행 슬롯 반환
```

- 주력 확장은 async def 기반입니다. 별도 리뷰 과제의 등록·조회는 요구대로 def를 사용합니다.
- OpenAI·NeMo·외부 I/O는 지원되는 비동기 API와 await로 연결합니다.
- 비동기 AI의 가짜 대기는 await asyncio.sleep입니다. async 함수에서 동기 I/O로 이벤트 루프를 막지 않습니다. 별도 def 예제는 스레드 풀에서 실행됩니다.
- SSE는 async generator로 전송하고 timeout·연결 단절 시 취소와 정산을 마칩니다.
- 짧은 규칙·검증·메모리 접근은 직접 처리하고 주력 공유 상태는 이벤트 루프 안에서 관리합니다. DB 도입 시 비동기 드라이버·요청별 세션을 사용합니다. CPU 작업은 async 선언만으로 빨라지지 않습니다.
- AI 대기 중에도 health·다른 요청이 처리되는지 검증합니다.

현재는 localhost·단일 사용자·합성 데이터·단일 worker 실험입니다. **Spring Boot·JWT·로그인·역할 권한은 이번 실행 경로에서 제외**합니다. 인증·인가는 hybrid 단계에서 다룹니다. sessionId와 내용 검사 action은 사용자 인증을 대신하지 않습니다.

## 3. 학원 HOWTO 세 챕터와 연결

학원은 **하나의 프로젝트를 chap01 → chap02 → chap03으로 확장**합니다. 메뉴 예제로 구조와 검증 방법을 배우고 우리 프로젝트에서는 Legal Intake·게시판에 응용합니다.

| 원본 | 학원 핵심 | 우리 적용 |
|---|---|---|
| HOWTO-chap01 | 프로젝트·계층·DTO·검증·예외·DI·라우터 조립 | 분류·참조·게시판 구조·응답 계약 |
| HOWTO-chap02 | 설정·동기/비동기 LLM·fake client·lifespan·비교 | 비동기 AI pipeline·fake/real·자원 관리 |
| HOWTO-chap03 | fixture·단위/통합 테스트·의존성 교체·커버리지·벤치마크 | 외부 API 격리·action·예산·SSE·동시성 검증 |

원본 위치는 `C:\myLectureWs\08_fastapi-main\howto`입니다. 반영본은 **2026-11-04 / f1928c8**입니다. 수업 자료는 이 저장소에 복제하지 않고 학습 항목과 적용점을 요약합니다.

### 3-1. chap01 — FastAPI 프로젝트의 뼈대

| 항목 | 핵심 | 우리 프로젝트에 반영 |
|---|---|---|
| uv·가상환경 | pyproject.toml·.venv·uv.lock·인터프리터 | 환경·버전 분리와 재현 |
| 패키지·진입점 | app 하위 모듈·수업용 `__init__.py`·app.main:app | 파일 분리·서버 시작 위치 |
| 도메인 엔티티 | 데이터를 Python 객체로 표현 | 게시글·후기 내부 데이터 |
| Repository | 딕셔너리 조회·저장·추가, DB와 구분 | fixture·메모리 저장소 |
| Pydantic DTO | 요청/응답 분리·타입·길이·값 검증 | 잘못된 요청과 업무 규칙 분리 |
| camelCase alias | Python snake_case ↔ JSON camelCase | Java·화면 필드와 연결 |
| 예외·처리기 | 사용자 정의 예외 → HTTP 상태·JSON | 404·422·기술 오류 계약 |
| Service | 저장소 주입·업무 규칙 수행 | Router와 업무 순서 분리 |
| Depends·Annotated | 필요한 부품과 하위 의존성 선언 | 진짜/가짜 부품 교체 |
| APIRouter·main.py | prefix·경로·상태 코드·라우터·처리기 등록 | 자동 탐색 대신 명시적 조립 |
| Swagger·Postman | 본문·응답 코드·필드 확인 | 화면 없이 API부터 시험 |

학원 chap01은 세 API입니다. **메뉴 수정·삭제까지 있는 전체 CRUD 샘플은 아닙니다.**

| 학원 API | 확인할 내용 |
|---|---|
| GET `/api/menus` | 초기 5개 메뉴·camelCase 응답 |
| GET `/api/menus/{menu_code}` | 정상 200·없는 메뉴 404·정수 아닌 경로 422 |
| POST `/api/menus` | 올바른 본문 201·잘못된 입력 422·목록 반영 |

이동 순서는 `Router → Service → Repository → 응답 DTO`입니다. FastAPI가 선언된 의존성을 해석하지만 Spring Bean 자동 탐색·등록과 같지는 않습니다. **요청 단위 dependency 캐시와 서버 전체 공유 객체는 구분**합니다. 라우터·예외 처리기·객체 조립 위치를 찾아봅니다.

예외 응답의 code/description/detail과 Pydantic 오류의 loc를 읽습니다. reload·재시작 후 메모리 데이터는 초기화됩니다. Pyrefly search-path는 편집기의 모듈 인식 설정이며 실제 패키지 설치를 대신하지 않습니다.

### 3-2. chap02 — LLM 호출과 동기·비동기 비교

| 항목 | 핵심 | 우리 프로젝트에 반영 |
|---|---|---|
| 설정 | pydantic-settings·BaseSettings·SecretStr·환경 변수·.env·기본값 | 키·모드·모델·한도·timeout |
| 설정 재사용 | lru_cache로 읽기 반복 축소 | 요청별 재생성 방지·변경 후 재시작 |
| 동기 client | 동기 OpenAI 호출은 해당 흐름에서 대기 | 비교 실험용 |
| 비동기 client | AsyncOpenAI·await·응답 텍스트 | 실제 AI 경로 필수 |
| 가짜 client | 같은 호출 규약·고정 지연·가짜 응답 | 비용·네트워크 없는 재현 |
| 코루틴 | 호출만으로 결과가 즉시 나오지 않음 | Service→client까지 await 연결 |
| lifespan·app.state | 시작 시 생성·공유·종료 시 정리 | clients·NeMo·stores 수명 관리 |
| 의존성 주입 | client→Service→Router | 테스트에서 교체 |
| 예외 변환 | 키·한도·연결·timeout → 프로젝트 오류 | 정책 차단과 기술 실패 분리 |
| 관찰 | 시간·스레드 이름·토큰 usage | HTTP 200과 실제 연결 성공 구분 |

학원은 동일한 `{"question":"..."}` 요청을 세 방식으로 비교합니다.

| 학원 경로 | 구현 | 대기 중 동작 |
|---|---|---|
| POST `/api/ai/ask/sync` | def + 동기 client | 스레드 풀에서 대기 |
| POST `/api/ai/ask/async` | async def + 비동기 client + await | 이벤트 루프가 다른 준비된 요청 처리 |
| POST `/api/ai/ask/blocking` | async def + 동기 client | 이벤트 루프를 막는 잘못된 예 |

**우리 Chat은 `/api/ai/chat`, 입력은 message입니다.** 학원 question과 혼동하지 않습니다. 비교용 sync/blocking 경로는 우리 실제 서비스 경로에 추가하지 않습니다.

실험 1: 5초 가짜 AI 대기 중 메뉴 조회가 되는지 확인. 실험 2: THREAD_POOL_SIZE=1에서 sync 대기와 async 겹친 대기 비교. 수업의 기본 40은 AnyIO limiter의 동시 실행 토큰 수이며 모든 서버의 고정 처리량 상한은 아닙니다.

학원은 키가 없으면 fake로 전환합니다. **우리 설계는 fake/real 명시, real에서 키·가격 누락 시 호출 전 실패**입니다. 모델 접근·실제 응답은 따로 확인합니다. .env는 Git에 올리지 않고 변경 후 서버를 재시작합니다. 환경 변수가 .env보다 우선할 수 있습니다.

LLM이 우리 메뉴·사건·게시글을 자동으로 아는 것은 아닙니다. 필요한 데이터를 검사·마스킹 후 전달합니다. memvid/RAG는 이번 범위에서 제외합니다.

### 3-3. chap03 — 테스트·커버리지·성능 측정

| 항목 | 핵심 | 우리 검증에 반영 |
|---|---|---|
| pytest 설정 | dev 의존성·testpaths·pythonpath | 테스트 위치·모듈 경로 |
| conftest·fixture | 준비물·yield 뒤 정리 | 메모리·예산·이벤트 격리 |
| dependency_overrides | 실제 부품을 가짜로 교체·정리 | 유료 호출 없이 흐름 검증 |
| 서비스 단위 테스트 | 직접 부품 주입·assert·pytest.raises | action·규칙·사유 코드·예산 상태 |
| API 통합 테스트 | TestClient의 상태·JSON·검증 오류 | 정상·404·422·안전 응답 |
| parametrize | 여러 입력에 같은 검증 적용 | 정상·공격·PII·마케팅 사례 |
| 비동기 테스트 | 학원 동기 테스트에서 asyncio.run | 서버 내부는 await·별도 async 동시성 검증 |
| 장애 주입 | 실패 client로 오류 변환 확인 | timeout·guardrail 실패·단절 |
| 커버리지 | 테스트가 실행한 코드 범위 | 외부 연동 성공과 구분 |
| 벤치마크 | 실행 중인 서버에 AsyncClient·gather | 대기 겹침·응답성·실패·cleanup |

학원에는 **20개 테스트 통과 예시**가 있습니다. 원본 기록이며 우리 서버가 통과했다는 뜻은 아닙니다. 테스트별 새 저장소·가짜 client를 제공하고 override를 정리합니다. 실제 OpenAI 코드를 격리하면 그 코드의 커버리지가 낮을 수 있습니다. 수치만으로 완성을 판단하지 않습니다.

asyncio.run은 독립된 동기 테스트·스크립트의 진입 방법입니다. Uvicorn이 이미 루프를 실행하는 핸들러 안에서는 다시 호출하지 않고 await합니다. lifespan이 필요한 테스트는 시작·종료도 관리합니다. TestClient 기본 응답 확인과 async 동시성 검증은 별개입니다.

TestClient는 메모리에서 ASGI 앱을 호출할 수 있지만 **학원 벤치마크는 실행 중인 서버**에 연결하므로 터미널 두 개가 필요합니다.

| 지표 | 읽는 방법 |
|---|---|
| 전체 시간 | 요청 묶음 완료 시간 |
| p50 | 정렬한 응답 시간의 중간 지점 |
| p95 | 약 95% 요청이 이 시간 안에 완료되는 지점 |
| 최대 지연 | 가장 오래 걸린 요청 |
| RPS | 초당 완료 요청 수 |
| 실패 수 | 비정상 상태·연결 실패·timeout 등 |

FAKE_LLM=true·고정 지연으로 측정합니다. 원본은 fake 여부 사전 확인, sync/async 각 100개·blocking 10개, client 5개 분산 구조입니다. 127.0.0.1로 주소 해석 지연을 줄이고 측정 도구의 병목도 살핍니다. **요청 수가 다른 결과의 전체 시간만 직접 비교하지 않으며**, 수업 PC 수치를 보장 성능으로 삼지 않습니다.

## 4. HOWTO에서 확장하는 Legal Intake

| 기능 | 처리 |
|---|---|
| 분류·간단 안내·법률 참조 | 규칙·고정 fixture, AI 없음 |
| 챗봇·요약·분류·답변 초안 | 공통 비동기 AI pipeline |
| 입력 보안 | 세션 위험·고정 규칙·마스킹 |
| 비용 통제 | 단계별 예약·보고/추정 정산·중복 종료 방지 |
| 출력 보안 | 전체 검사·마케팅 검토·최종 마스킹 |
| SSE | 검사 완료 청크·단절 cleanup |

Java의 계약·규칙·사유 코드·테스트 사례를 이전합니다. Java 코드를 Python에서 그대로 실행하지 않습니다. 실제 소스는 legal-ai-intake-security-server이며 로컬 legal-ai-intake-system은 소개 문서 중심입니다.

## 5. API 선정과 제외

**원본 37개 = 선정 11개 + 제외 26개. 신규 10개를 합친 목표는 21개입니다.**

| 구분 | API |
|---|---|
| 분류·안내 | C02 POST /api/intakes/classify-preview · C04 POST /api/legal-intake/minimal |
| 법률 참조 | R01 GET /api/legal/procedures · R02 GET /api/legal/procedures/{code} · R06 고정 형사 체크리스트 |
| AI 비동기 | S01 POST /api/ai/chat · S02 POST /api/ai/chat/stream |
| NeMo 검사 | S03 POST /api/legal/guardrail/input · S04 POST /api/legal/guardrail/output |
| 축소·변경 | C14 GET /api/lab/security-events · C13 GET /api/lab/marketing/summary |
| 신규 상태 | H01 GET /health |
| 신규 게시판 | B01~B05: /api/posts 생성·목록, /api/posts/{postId} 상세·수정·삭제 |
| 신규 후기 | B06~B07: /api/posts/{postId}/reviews 생성·목록 |
| 신규 AI 마케팅 | M01 POST /api/posts/{postId}/ai-summary · M02 POST /api/reviews/{reviewId}/reply-draft |

**핵심 11개 우선**: C02/C04/R01/R02/R06/S01~S04/C14/H01. **이번 실험의 게시판 연동 10개**: C13/B01~B07/M01/M02. 이는 다음 hybrid 단계로 미루는 선택 기능이 아니라 **이번 fastapi-lab의 필수 범위**입니다. 샘플 구조를 확인해 세부 필드·경로를 확정합니다. 원본 선정 11개와 우선 구현 11개는 health·C13 위치 때문에 구성이 다릅니다.

제외: Spring 로그인·JWT·역할 권한·운영 사건 DB·외부 검색·파일 저장·Agent/Incident 운영·Actuator/Prometheus. Redis·Celery·Kafka·memvid/RAG·OCR·자동 게시도 제외합니다. 기존 Java 서버·DB는 수정하지 않습니다. 전체 ID와 정확한 경로는 [상세 설계](docs/BACKEND_DESIGN.md)를 봅니다.

## 6. NeMo 보안 Python action — 9개 설계 확정

**이전 범위 확정:** 우선 복습할 3개뿐 아니라 아래 **9개 전체**를 FastAPI 내부로 이전하는 목표입니다. 로그인·JWT·역할·소유권 인가는 제외합니다. [전체 이전 흐름도](docs/assets/security-migration.svg)와 [책임·순서·확장 단계 해설](docs/SECURITY_MIGRATION_PLAN.md)에 남은 설계를 정리했습니다. action 외에 서비스의 정산·슬롯 반환·취소 정리도 구현 목표에 포함합니다.

action은 **검사 함수**, reasonCode는 **판단 사유 값**입니다. 코드를 함수 이름으로 바꾸지 않고 기존 판정 로직을 Python으로 옮깁니다.

| action | 역할 |
|---|---|
| validate_request_context | 서버가 만든 요청 문맥·분석 대상·응답 연결 확인, A/B 데이터 혼합 방지 |
| check_session_risk | 세션 누적 위험·기존 차단 확인 |
| check_input_policy | 법률 악용·jailbreak·injection·secret·privacy 검사 |
| mask_personal_data | 저장·외부 전송·반환 전 정의한 PII 치환 |
| check_generation_admission | 동시 실행·유한 대기열·대기 한도 정책, 실제 슬롯은 서비스 관리 |
| check_request_budget | lock 안에서 예산 확인+예약 |
| check_output_policy | 전체 답변 빈값·길이·정책 검사 |
| check_marketing_response | 보장·과장 표현을 사람 검토 대상으로 표시 |
| record_risk_event | 확정된 정책 차단을 한 번만 점수로 기록 |

기존 7개에 추천한 문맥 검사·생성 진입 제어 2개를 **정식 설계 범위에 추가**했습니다. 아직 구현 완료는 아닙니다. API 21개 계획은 유지합니다. 문맥 격리·입력 정책·마스킹·용량·예산을 먼저 연결하고, real 호출 전 출력 정책까지 검증합니다. M API 활성화 전 마케팅 검사를 완료합니다. action 단위 테스트와 **실제 NeMo rail의 호출·결과 소비·차단/변환 통합 검증**을 구분합니다.

### 왜 두 개를 추가했나요?

- **문맥 검사:** 비동기로 A/B 요청이 겹쳐도 질문·후기·검사 결과가 섞이지 않도록 요청마다 독립 context를 사용하고, 반환 직전에도 연결을 확인합니다. requestId만 같다고 사용자 권한이 증명되지는 않습니다.
- **생성 진입 제어:** 비동기는 동시 요청을 많이 받기 쉬우므로 예산뿐 아니라 실행 개수도 제한합니다. 서버 설정의 예시는 동시 2개·대기 4개·대기 한도 0.5초입니다. 분산 환경의 전역 한도가 아니라 단일 worker 실험값입니다.
- **용량 먼저, 비용 나중:** 기다리는 요청이 예산을 오래 예약하지 않도록 슬롯 확보 후 비용을 예약합니다. 거절·취소 때는 이미 확보한 자원도 반환합니다.
- **종료 책임 분리:** timeout·disconnect·정산·슬롯 반환은 서비스의 finally에서 보장합니다. 다음 action이 실행되어야만 정리되는 구조로 만들지 않습니다.

자세한 이유·계약·사례·실험은 [비동기 보안 설계 해설](docs/async-security-explained.html)에 정리했습니다. NeMo의 execute_async 옵션과 Python await는 구분하며, 필수 검사 결과를 기다리지 않고 생성을 시작하지 않습니다.

### 추천 5번도 이번 필수: check_marketing_response

게시판·리뷰 샘플을 우리 변호사 마케팅 도구에 연결하는 만큼 **5번도 이번에 구현·검증**합니다. M01 요약과 M02 답변 초안은 전체 출력 검사 후 이 action을 반드시 통과하고, 최종 마스킹·문맥 확인을 마쳐야 반환합니다. 보장·과장 표현은 검토 필요로 표시하고 안전하게 정리한 초안만 제공하며 자동 게시하지 않습니다. 정상 문구·보장 표현·부정/인용 문맥·개인정보·검사 실패 사례를 테스트합니다. 샘플을 실행하는 것과 이 AI 보안 확장을 구현하는 것은 별도로 확인합니다.

내부 결정은 ALLOW/BLOCK/TRANSFORM/REVIEW, 사유는 reasonCode/detailCode입니다. 기존 COST_LIMIT_BLOCKED·DYNAMIC_SESSION_BLOCKED 등과 신규 제안을 구분합니다. 패턴 마스킹의 완전성·표현 검사의 법률적 적합성을 보장한다고 가정하지 않습니다.

## 7. 비용·SSE·오류 처리

- 입력 검사·생성·출력 검사를 구분하며 유료 검사는 각 호출을 예약·정산합니다.
- 확인+예약은 원자 처리하고 OPEN → REPORTED/ESTIMATED/RELEASED 중 한 번만 종료합니다.
- 생성 진입은 유한 대기열과 별도 timeout을 사용하고, 기다리는 동안 예산을 예약하지 않습니다. 과부하·문맥 오류는 공격 점수로 적립하지 않습니다.
- 호출 전 취소는 해제, 시작 후 usage 미확인은 추정 정산입니다. usage를 모른다고 0원으로 쓰지 않습니다.
- 출력 차단·timeout·단절에도 이미 발생한 호출을 정산합니다. 필수 검사·정산을 BackgroundTasks로 미루지 않습니다.
- camelCase 응답을 유지하고 원문 PII가 검증 오류·로그에 노출되지 않도록 정규화합니다.
- SSE 정상은 meta → 검사 완료 token 청크들 → done, 차단은 blocked, 기술 실패는 error로 종료합니다.
- **전체 생성·출력 검사·마스킹 후** 전송합니다. 비동기와 미검사 토큰 실시간 공개는 다릅니다.
- POST SSE는 fetch로 읽고 시작 후 오류는 이벤트로 전달합니다.
- 메모리 장부는 실험용이며 실제 제공자 청구 상한을 보장하지 않습니다.

## 8. 제공된 리뷰 명세 반영과 확장 경계

### 우리 도메인: 법률 마케팅 게시판 + 필수 action 3개

식당 리뷰 샘플의 구조를 **법률사무소 게시글·상담 서비스 후기·검토용 답변 초안**으로 응용합니다. `ohgi-review-server`는 수업 원형 비교용으로 보존하고, 주말 확장은 우리 Legal Intake의 법률 마케팅 게시판으로 구현합니다. 오늘의 접수 MVP 3개 API와는 별도 단계입니다.

| 우선 복습할 Python action | 법률 마케팅 게시판에서의 역할 | 실행 위치 |
|---|---|---|
| `mask_personal_data` | 전화번호·이메일 등 정의한 개인정보 패턴 치환 | 게시글·후기 저장 전, AI 전송 전, 최종 반환 전 |
| `check_request_budget` | 기존 비용 제어 기준을 Python의 원자적 확인·예약·정산 구조로 이전 | M01 요약·M02 답변 초안의 각 유료 호출 직전 |
| `check_marketing_response` | 승소 보장·과장 표현을 검토 대상으로 표시 | 생성 결과 반환 전, 최종 마스킹 전 |

흐름은 **게시글/후기 → 마스킹·저장 → 예산 예약 → await OpenAI → 출력 검사·마케팅 검사 → 최종 마스킹 → 검토용 응답·정산**입니다. 예산 초과·필수 검사 실패 시 생성을 중단하거나 결과를 반환하지 않습니다. `reviewRequired` 등 응답 필드는 후속 계약 제안이며 현재 MVP 응답에 추가한 필드는 아닙니다.

세 action은 기존 9개 설계 중 우선 학습할 묶음이며 전체 9개나 보안 요구를 대체하지 않습니다. **현재 NeMo action 구현·설치는 아직 없으며 주말 구현 대상**입니다. [도메인 전환·실행 순서·설계 이유·완성 기준](docs/LEGAL_MARKETING_BOARD.md)을 따릅니다.

제공된 리뷰 API·폴더 명세는 ohgi-review-server에 반영했습니다. 과제 서버의 동기 리뷰 등록·조회와 비동기 답글은 구현·검증했습니다. 별도의 주력 게시판·마케팅 확장은 아래 절차로 연결하며, 추가 원본 코드가 제공되면 실제 필드와 대조합니다. 과제 서버에 운영 보안·비용 시스템을 모두 넣어 범위를 키우지 않습니다.

| 순서 | 반영 작업 |
|---|---|
| 1 | 출처·README·실행 조건·재사용 조건 확인 |
| 2 | 게시글/후기 모델·CRUD·저장 방식·의존성·테스트 확인 |
| 3 | chap01과 비교해 B01~B07 필드·경로·응답 확정 |
| 4 | 주력 샘플의 비동기 구조와 DB 호출 방식을 확인, 동기 비교는 최소 예제로 분리 |
| 5 | 저장 전 마스킹·조회 계약·없는 ID 404 등 검증 |
| 6 | M01 요약·M02 초안을 공통 AI pipeline 및 필수 check_marketing_response에 연결 |
| 7 | C13 집계를 실제 구현 데이터 기준으로 확정 |
| 8 | API 목록·흐름도·공부자료·README 갱신 |

샘플 일반 게시판과 우리 AI 확장을 구분합니다. 게시글·후기는 분석 데이터이며 본문 지시를 시스템 명령으로 취급하지 않습니다. 답변은 검토용 초안이며 자동 외부 게시를 하지 않습니다.

## 9. 현재 상태

| 항목 | 상태 |
|---|---|
| **현재 Legal Intake MVP** | 루트 app/ 구현, 동기 등록·조회 + 비동기 AI 안내, 테스트 23개 통과 |
| MVP 실제 개발 서버 | uv run --no-sync fastapi dev로 실행, fake 모드 HTTP·MainThread 확인 |
| MVP Postman collection | 요청 파일 작성 완료, Postman 앱 수동 실행은 미확인 |
| 학원 자료 | 최신본 반영 완료 · f1928c8 |
| README·설계·API 목록 | 작성 완료 · 구현 전 DRAFT |
| Dark Tablet 흐름도 | 8개 화면 작성·레이아웃 확인 |
| 비전공자 공부자료 | 16개 장·복습 8문항·목차·읽기 화면 작성 |
| asyncio 예제 | 실행 확인: 순차 약 3.01초 / 동시 약 1.01초. 서버 성능 비교 아님 |
| 최소 동기 예제 | 별도 def GET /posts 구현. AI·DB 없음, 주력 앱과 분리 |
| 제공된 리뷰 과제 서버 | 동기 2·비동기 1 구현, 가짜·mock 테스트 11개 통과, 실제 유료 호출 미검증 |
| 실제 로컬 서버 확인 | Uvicorn·fake로 /docs·201·422·404·답글 확인, async MainThread·sync worker 로그 확인 |
| 별도 chap02 실습 폴더 | Python 3.14·의존성·가짜 API 3개·422·Swagger 확인 |
| 후속 21개 확장 API | 설계 단계, 현재 MVP 3개와 구분 |
| 실제 OpenAI | 아직 검증하지 않음 |
| NeMo 설치·9개 action 연결 | 설계 확정 · 아직 구현·검증하지 않음 |
| 리뷰 과제 자료 | API·폴더 명세 수령 및 반영. 원본 프로젝트 전체 코드와는 구분 |
| Spring 연결·배포 | 후속 단계 |

루트에는 Legal Intake MVP의 app·pyproject.toml·전용 .venv·uv.lock이 있고, ohgi-review-server에는 리뷰 참고본이 있습니다. Python 3.14로 MVP를 검증했으며 후속 NeMo의 호환성은 별도 검증 대상입니다.

## 10. 지금 실행할 수 있는 것

### 현재 Legal Intake MVP — 루트에서 실행

```powershell
cd C:\myLectureWs\legal-intake-fastapi-lab
uv run fastapi dev --host 127.0.0.1 --port 8012
```

Swagger는 http://127.0.0.1:8012/docs입니다. uv 캐시 권한 문제 시 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012`로 실행할 수 있습니다. 검증은 `.\.venv\Scripts\python.exe -m pytest -q`입니다. 실행 중인 서버가 있으면 중복 실행하지 않습니다.

```json
{"clientName":"연습의뢰인","caseType":"CIVIL","coreStatement":"보증금 반환 상담에 필요한 자료를 준비하려고 합니다.","desiredNextStep":"상담 준비자료 정리"}
```

POST /api/intakes의 intakeId로 GET 조회와 POST /api/intakes/{id}/guidance를 순서대로 실행합니다. 가짜 응답은 model=fake-llm이며 실제 연결 성공을 뜻하지 않습니다. 자세한 필드·키 설정은 [MVP 안내](docs/RUN_MVP.md)를 봅니다.

### 실제 리뷰 과제 서버: 동기 2개·비동기 1개

```powershell
cd C:\myLectureWs\legal-intake-fastapi-lab\ohgi-review-server
C:\myLectureWs\fastapi-openai-practice\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

http://127.0.0.1:8011/docs 에서 리뷰를 등록한 뒤 조회·답글을 실행합니다. 초기 FAKE_LLM=true이므로 비용이 발생하지 않습니다. 설치·JSON 예시·실제 키 연결은 [과제 서버 README](ohgi-review-server/README.md)를 봅니다. 초기 GET /posts 파일은 참고용으로만 남깁니다.

```powershell
# 위 과제 폴더에서 실행: 네트워크 없이 11개 테스트 확인
C:\myLectureWs\fastapi-openai-practice\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### 비용 없는 asyncio 예제

현재 PC의 PowerShell:

```powershell
cd C:\myLectureWs\legal-intake-fastapi-lab
C:\myLectureWs\fastapi-openai-practice\.venv\Scripts\python.exe examples\async_wait_demo.py
```

일반 환경은 python examples/async_wait_demo.py로 실행합니다. 키·네트워크를 사용하지 않습니다.

### 기존 별도 학원 실습 서버

다음은 **이 저장소가 아닌 fastapi-openai-practice의 chap02 서버**입니다. .env의 FAKE_LLM=true를 확인합니다.

```powershell
cd C:\myLectureWs\fastapi-openai-practice
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Swagger는 http://127.0.0.1:8001/docs입니다. 이 서버 입력은 question, model=fake-llm은 가짜 응답입니다. 실제 호출은 그 폴더의 실습안내.md를 봅니다.

## 11. 학원 원본 실습 명령

**학원 실습 프로젝트 안에서 사용하는 명령 모음입니다.** 현재 루트 MVP에는 이미 프로젝트와 환경이 있으므로 uv init을 다시 실행하지 않습니다. uv init은 별도 빈 실습 폴더에서 사용합니다.

| 단계 | 명령 |
|---|---|
| chap01 빈 프로젝트 | uv init --no-package --python 3.14 |
| FastAPI 설치 | uv add "fastapi[standard]" |
| chap02 추가 | uv add pydantic-settings openai |
| chap03 추가 | uv add --dev pytest pytest-cov |
| starter/complete 설치 | 해당 챕터 폴더에서 uv sync --python 3.14 |
| 서버 | uv run fastapi dev |
| 테스트·상세 출력 | uv run pytest · uv run pytest -v |
| 커버리지 | uv run pytest --cov=app |

진입점은 [tool.fastapi]의 entrypoint = "app.main:app"입니다. 테스트는 [tool.pytest.ini_options]의 testpaths = ["tests"], pythonpath = ["."]를 설정합니다. 실제 파일 구조를 만든 뒤 사용합니다.

학원 chap03 벤치마크는 두 터미널에서 실행합니다. 기본 8000은 기존 실습의 8001과 다릅니다.

```powershell
# 터미널 1: 학원 complete/chap03_test_benchmark 폴더
$env:FAKE_LLM="true"
$env:FAKE_LLM_DELAY_SECONDS="1"
uv run fastapi dev
```

```powershell
# 터미널 2: 같은 학원 챕터 폴더
uv run python benchmark/benchmark.py
```

종료는 Ctrl+C입니다. 환경 변수가 터미널에 남으므로 실제 호출은 새 터미널에서 시작하거나 설정을 정리합니다. 현재 PC의 uv Python 바로가기 오류는 로컬 `C:\myLectureWs\fastapi-openai-practice\실습안내.md`의 실행 파일 직접 지정 방법을 참고합니다. 이 형제 폴더는 저장소 복제만으로 생기지 않으며 GitHub 링크로 제공하지 않습니다.

## 12. 구현·복습 순서와 완료 기준

### 다음 구현 목표 — 오늘 MVP 다음 단계

현재 완료는 접수 MVP 3개·테스트 23개입니다. 주말 이후의 보안 확장은 **기반 부품 → action 9개·NeMo rail → 공통 AI pipeline → 실제 OpenAI 검증 → 법률 게시판·SSE** 순서로 진행합니다. Redis/DB·여러 worker는 이후 확장입니다. 인증·인가는 이 순서에 넣지 않습니다. 단계별 종료 기준은 [전체 이전 계획](docs/SECURITY_MIGRATION_PLAN.md)을 따릅니다.

1. chap01 계층과 규칙·참조 API의 요청 이동 설명.
2. chap02 비교 후 우리 fake 비동기 Chat 구현.
3. 요청 문맥·입력 action·마스킹·용량·예산을 fake AI에 연결.
4. 출력 action·최종 마스킹·오류·정산 검증 후 실제 OpenAI 단건 확인.
5. chap03 테스트에 async 동시성·취소 검증 추가.
6. 검사 완료 SSE·미검사 본문 누출·단절 cleanup 확인.
7. 주력 비동기 게시판 샘플 구현·검증 후 비동기 AI 마케팅 API 연결.
8. fake 부하 실험·복습 문서 갱신 후 hybrid 준비.

- [ ] fake는 외부 호출 0, real은 설정을 검증한다.
- [x] 선택한 MVP: 동기 접수 등록·조회와 비동기 AI 안내 구현, pytest 23개와 실제 HTTP 확인.
- [ ] AI 대기 중 다른 요청이 처리된다.
- [x] 과제 요구의 동기 리뷰 등록·조회, 비동기 답글, 201·422·404·502를 가짜·mock으로 검증했다.
- [ ] 주력 확장의 비동기 챗봇 AI 대기 중 게시판도 응답한다.
- [ ] 기존 Java 사유 코드와 신규 코드가 구분된다.
- [ ] NeMo 함수 단위/실제 rail 통합 테스트가 있다.
- [ ] 동시 A/B 요청의 문맥이 섞이지 않고, 생성 한도·대기 한도·취소 후 슬롯 반환을 검증한다.
- [ ] 정상·422·404·정책 차단·기술 오류를 구분한다.
- [ ] 동시 예약·중복 정산·호출 전후 취소·출력 차단 비용을 확인한다.
- [ ] SSE 본문 누출·terminal 중복이 없다.
- [ ] 오류·로그·health에 키·원문 PII가 노출되지 않는다.
- [ ] 게시판 출처·변경점·B/M API를 확정한다.
- [ ] 추천 5번 check_marketing_response를 M01/M02에서 우회할 수 없고 정상·검토·차단·실패 사례를 검증한다.
- [ ] 문서만 보고 실험을 재현한다.

주말 복습은 **전체 구조 → 비동기·DI → 보안·비용·SSE** 순서입니다. 원본을 읽고 우리 설계의 대응 위치를 찾은 뒤 예제·테스트로 확인합니다.

## 13. 참고 자료와 원본 위치

| 경로 | 용도 |
|---|---|
| C:\myLectureWs\08_fastapi-main\howto\HOWTO-chap01.md | 프로젝트·DI·기본 API |
| C:\myLectureWs\08_fastapi-main\howto\HOWTO-chap02.md | LLM·설정·동기/비동기 |
| C:\myLectureWs\08_fastapi-main\howto\HOWTO-chap03.md | 테스트·커버리지·벤치마크 |
| C:\myLectureWs\08_fastapi-main\complete · starter | 완성본·작성 뼈대 |
| C:\myLectureWs\fastapi-openai-practice | 기존 가짜 LLM 환경·실습 안내 |
| C:\myLectureWs\legal-ai-intake-security-server | 실제 Java·API 명세 |
| C:\myLectureWs\legal-ai-intake-system | 서비스 소개·개요 |

이 README는 원문 전체나 코드 복제본을 대신하지 않습니다. 세 챕터 핵심을 우리 설계에 연결한 요약이며 실제 파일 작성은 원본과 대조합니다.

- [학원 저장소](https://github.com/20260728-saltlux-llm-agent-service-1st/08_fastapi)
- [FastAPI async](https://fastapi.tiangolo.com/async/) · [Depends](https://fastapi.tiangolo.com/tutorial/dependencies/) · [lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [OpenAI 공식 Python 문서](https://developers.openai.com/api/reference/python)
- [NeMo custom actions](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/actions/creating-actions)
