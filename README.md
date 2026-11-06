# Legal Intake FastAPI Lab

FastAPI 기반 상담 준비 안내와 법률 마케팅 도구를 만드는 공개 프로젝트입니다. **보안 action 9개와 LangChain·LangGraph·LangSmith·RAG·임베딩·벡터 RAG·memvid를 필수 개발 범위**에 포함합니다. 앱 API는 기존 MVP를 포함해 **최대 11개**로 제한합니다.

[한국어](README.md) | [English](README.en.md)

> **2026-11-06 진행 상황:** Codex는 S0·B01을 완료하고 B02a 검증에서 조건 정지했습니다. Claude의 B03~B05 뼈대는 main에 반영됐으며, 실제 모델·검색·보안 흐름의 통합 완료와 구분합니다. [확정 v1](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/RAG_V1_PLAN.md) · [Codex 실행 증거](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/evidence/SUMMARY.md) · [Claude 검색 개발 브랜치](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/tree/claude/rag-corpus-b01)

## 1. 개발 방향과 필수 구성

현재 v1 범위는 **합성 안내문 10개로 E5 임베딩·memvid 벡터 검색을 구현하고 공부하는 것**입니다. 실제 접수 데이터나 guidance API에는 연결하지 않습니다. 검색 모델은 `intfloat/multilingual-e5-large-instruct`이며 revision `274baa43b0e13e37fafa6428dbc7938e62e5c439`로 고정했습니다. 생성은 Llama 계열을 검토하지만 아직 모델을 선정하거나 설치하지 않았습니다. Qwen은 기본 실행 범위에서 제외합니다.

| 구성 | 역할 | 최소 적용 |
|---|---|---|
| LangChain | 각 작업의 부품 | 메시지·프롬프트 템플릿·LCEL·retriever·구조화 출력 |
| LangGraph | 실행 순서와 분기 | 검색 → 근거 있음: 생성 / 근거 없음: 자료 요청 |
| LangSmith | 추적과 평가 | 단계별 시간·결과·버전, 합성 질문 dataset 실험 |
| RAG | 검색 자료를 근거로 답하는 방식 | 상담 준비 안내문을 근거로 사용 |
| 임베딩 | 문장을 숫자 벡터로 표현 | E5로 문서와 질문 encode |
| 벡터 RAG | 벡터 유사도 검색을 이용하는 RAG | 표현이 다른 질문에서도 관련 근거 찾기 |
| memvid | 문서·벡터·검색 인덱스 저장 | 마스킹된 청크·출처를 `.mv2`에서 검색 |

**memvid는 RAG의 저장·검색 부품입니다.** 처음에는 별도 벡터 DB나 다중 에이전트를 추가하지 않습니다. 새 검색 기능은 **Claude 검수 → 지적 반영 → 최종 개발안 확정 → 단계별 구현** 순서로 진행합니다.

## 2. 현재 구현과 검증 범위

2026-11-06 기준입니다. 아래 결과의 **브랜치와 실제/fake 범위**를 구분합니다. main에 모든 개발 브랜치가 합쳐진 것은 아닙니다.

| 구분 | 상태 |
|---|---|
| 루트 MVP | 동기 접수 등록·조회 + 비동기 안내 3개 API 구현. 기존 테스트 23개 |
| 선별 기반 `4fcc698` | 결정 DTO·불변 문맥·용량 관리자·예산 장부·위험 저장소 |
| L01 NeMo 래퍼 / L02 문맥·세션 위험 | `feat/security-input-actions`의 `2808606`에 커밋·push 완료. 공백 세션 분리와 입력 정책 차단만 위험 적립하는 계약 포함 |
| S0 환경·회귀 | Codex 브랜치: 별도 Python 3.12 RAG lock·환경. 설치 후 기존 95개 통과. L02 추가 9개는 별도 실행에서 통과 |
| B01 합성 자료·분할 | Codex 브랜치: 안내문 10개(603~666토큰), 청크 30개(최대 293토큰), 평가 30개. 오프라인 시험 6개 통과 |
| B02a memvid | Codex 기존 probe는 구조화 metadata 반환 검증 실패로 정지. 이후 Windows에서 대량 적재 유실과 8개 묶음 보존을 재현. 아래 재검수 결과 참조 |
| B02b 실제 E5 평가 | Codex에서는 미착수. 실제 E5 가중치·Hit@3·확인 세트 평가 결과 없음 |
| B03~B05 LangChain·LangGraph·LangSmith | Claude 뼈대가 PR #2로 main에 병합됨. 실모델·실검색·LangSmith 원격 평가·접수 통합 완료를 뜻하지 않음 |
| 법률 마케팅 게시판·M01/M02 | 후속 구현. 보존본의 실패한 마케팅 검사 코드를 완료본으로 사용하지 않음 |
| 생성 모델 | 현재 OpenAI 비동기 어댑터와 fake client. Llama 어댑터는 개발 예정 |

95개는 기존 API와 보안 경계의 회귀 시험이며 새 RAG의 완료 증거가 아닙니다. AI 응답은 fake/mock이고 실제 NeMo rail은 포함됩니다. 95개·추가 9개·B01 6개는 서로 다른 실행의 결과입니다. 보존 브랜치 `wip/codex-legal-snapshot`(`e6df050`)는 복구용이며 main에 합치지 않습니다. [기존 L01/L02 설명](docs/L01_L02_IMPLEMENTATION.md)보다 [최신 실행 증거](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/evidence/SUMMARY.md)를 우선합니다.

### memvid 2.0.160 재검수 — Windows 실측

seal·close·재오픈 후 `k=전체 수` 검색과 모든 벡터의 자기 검색 1위를 확인했습니다. 자료와 벡터는 합성입니다.

| 전체 청크 | 한 번에 적재 | 검색 가능한 청크 / 전체 | 자기 벡터 top1 / 전체 |
|---|---|---|---|
| 60 | 60개 | 6/60 | 6/60 |
| 60 | 30개 | 49/60 | 49/60 |
| 60 | 8개 | 60/60 | 60/60 |
| 120 | 8개 | 120/120 | 120/120 |

적재는 **8개 이하 묶음**으로 제한하고, 재오픈 후 전체 수와 모든 자기 검색을 통과해야 활성화합니다. 이는 제한된 합성 벡터 시험 결과이며 실제 E5 연동 통과가 아닙니다. 출처는 `title=chunkId`를 manifest와 대조하는 방안으로 검수 중입니다. lex는 caseType·마스크·연산자 토큰을 제외한 키워드를 OR로 결합하는 기준선을 검증합니다. `MEMVID_TELEMETRY=0`을 강제하고 `put_many`에는 `opts={"enable_embedding": False}`를 명시해야 합니다. 현재 참고 probe의 5개 벡터 검사는 30개 이상으로 보강해야 합니다.

현재 루트 앱의 API:

| 메서드·경로 | 방식 | 정상·오류 |
|---|---|---|
| POST `/api/intakes` | `def` | 등록 201, 입력 오류 422 |
| GET `/api/intakes/{intake_id}` | `def` | 조회 200, 없으면 404 |
| POST `/api/intakes/{intake_id}/guidance` | `async def` | 저장된 사실 기반 안내, LLM 실패 502 |

메모리 데이터는 재시작하면 초기화됩니다. fake/mock 성공과 실제 공급자 호출 성공은 별도로 확인합니다.

## 3. 최소 개념: 벡터와 코사인 유사도

- **벡터:** 임베딩 모델이 문장의 특징을 표현한 숫자 배열입니다.
- **코사인 유사도:** 두 벡터의 방향이 얼마나 비슷한지 비교하는 기준입니다. 같은 모델 공간에서 관련 자료 후보를 정렬하는 데 사용합니다.
- **top-k:** 가까운 후보를 몇 개 가져올지 정하는 값입니다. 후보가 있다고 충분한 근거가 있다는 뜻은 아닙니다.
- 유사도는 정답 확률이나 법률적 정확도가 아닙니다. 문서와 질문의 모델·revision·차원·전처리를 일치시키고 검색 결과를 검증합니다.

이번에는 Legal Intake를 이해하는 **최소 개념 공부**로 제한합니다. 별도 리서치 시스템·개인 검색식·Llama 질의 요약기·맞춤 랭킹 설계는 추가하지 않습니다.

## 4. 기본 처리 흐름

아래는 최종 연결 목표입니다. 현재 합성 학습 범위와 main의 B03~B05 뼈대를 운영 안내 흐름에 연결한 상태는 아닙니다.

```text
미리 적재:
합성 안내문 → 검사·마스킹 → 토큰 분할 → E5 문서 임베딩 → memvid

질문 응답:
요청 문맥·세션·입력 검사·마스킹
 → E5 질문 임베딩 → memvid 검색 → 자료 검사·근거 판정
 → LangGraph 분기
    ├─ 근거 있음: LangChain 템플릿 → Llama → 구조화 초안
    └─ 근거 없음: 추가 자료 요청, 생성 호출 0회
 → 출처 ID·전체 출력 검사 → 최종 마스킹·문맥 확인 → 응답

LangSmith: 각 단계의 추적·합성 dataset 평가, 전송 전 기록 정보 처리
```

E5의 길이 제한을 고려해 문서를 나누고 출처·문서 버전·모델 revision을 보존합니다. 구조화 출력은 내부 DTO에 먼저 적용할 계획입니다. 서빙 tracing은 기본 OFF이고, LangSmith 원격 전송은 현재 실행하지 않습니다. 이후 승인한 합성 평가에서만 원격 trace를 검증합니다. 접수 유래 입력·출력·예외·metadata를 원격 전송하는 흐름은 이번 범위에 포함하지 않습니다.

## 5. 보안 action 9개는 전체 필수

| action | 책임 |
|---|---|
| `validate_request_context` | 요청·snapshot·응답의 연결 확인 |
| `check_session_risk` | 누적 위험과 기존 세션 차단 확인 |
| `check_input_policy` | 법률 악용·jailbreak·injection·secret·privacy 검사 |
| `mask_personal_data` | 저장·외부 전송·반환 전 정의한 개인정보 치환 |
| `check_generation_admission` | 동시 실행·유한 대기열·대기 한도 |
| `check_request_budget` | 원자 예산 확인·예약 |
| `check_output_policy` | 생성 전체의 빈값·길이·정책 검사 |
| `check_marketing_response` | 보장·과장 표현의 사람 검토 표시 |
| `record_risk_event` | 사용자 입력 정책 차단만 중복 없이 위험 적립. 출력·검색 자료 차단은 점수 없이 기록 |

서비스가 **용량 확보 → 예산 예약 → 호출 → 정산 → 슬롯 반환**을 관리합니다. timeout·취소·실패에서도 정리를 보장하고, 검사 함수 단위 시험과 실제 NeMo rail의 호출·결과 소비 시험을 구분합니다. 모든 action이 이미 구현·연결됐다는 뜻은 아닙니다.

### 이번 필수: `check_marketing_response`

법률 마케팅 게시판의 **M01 요약과 M02 답변 초안은 전체 출력 검사 후 이 action을 반드시 통과**하고, 최종 마스킹·문맥 확인 뒤에만 반환합니다. 보장·과장 표현은 검토 필요로 표시하고 안전하게 정리한 초안만 제공하며 자동 게시하지 않습니다.

정상 문구·보장 표현·부정/인용 문맥·개인정보·검사기 실패 사례를 테스트합니다. 정상 부정문과 보장 표현이 한 문장에 섞인 우회 사례도 포함합니다. 샘플 실행 성공과 AI 보안 확장 완료는 따로 확인합니다.

내부 결정은 `ALLOW/BLOCK/TRANSFORM/REVIEW`, 사유는 `reasonCode/detailCode`입니다. 기존 `COST_LIMIT_BLOCKED`·`DYNAMIC_SESSION_BLOCKED`와 신규 제안을 구분합니다. 패턴 마스킹의 완전성이나 표현 검사의 법률적 적합성을 보장한다고 가정하지 않습니다.

## 6. 최종 앱 API는 최대 11개

아래는 검수할 목표 구성입니다. **현재 루트 구현은 기존 3개**이며 적재·검색·평가를 위한 공개 API는 추가하지 않습니다.

| 기능 | 메서드·경로 | 개수 |
|---|---|---|
| 기존 접수 | POST `/api/intakes`, GET `/api/intakes/{intake_id}`, POST `/api/intakes/{intake_id}/guidance` | 3 |
| 상태 | GET `/health` | 1 |
| 게시글 | POST·GET `/api/posts`, GET `/api/posts/{postId}` | 3 |
| 후기 | POST·GET `/api/posts/{postId}/reviews` | 2 |
| AI 마케팅 | POST `/api/posts/{postId}/ai-summary`, POST `/api/reviews/{reviewId}/reply-draft` | 2 |
| 합계 | 메서드와 경로의 조합 | **11** |

API 수는 사용자 정의 업무 API의 메서드·경로 조합으로 셉니다. `/docs`·`/openapi.json` 같은 자동 경로는 제외합니다. 이전 상세 설계의 21개는 과거 후보 목록입니다. 게시글 수정·삭제·독립 Chat/SSE·단독 guardrail API를 여기에 더하지 않습니다. 동기 비교는 별도 학습 앱에서 진행합니다.

## 7. 진행 순서와 최소 학습 요구사항

Codex 확정 범위는 **S0 → B01 → B02a → B02b**이며 B02a 필수 실패로 정지했습니다. [확정 v1](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/RAG_V1_PLAN.md)이 종전 초안보다 우선합니다. Claude는 별도 브랜치에서 B03~B05 뼈대를 병렬 개발했습니다. 통합 시 DTO·manifest·증거 계약을 먼저 맞춥니다. 실제 접수를 넣기 전에는 입력 정책·마스킹 → 추론 동시성 제한 → 출력 정책을 반드시 연결·검증해야 합니다.

기초 리뷰·답글 예제는 다음 순서만 유지합니다.

1. **프로젝트:** 빈 폴더의 `uv init` → `uv add "fastapi[standard]"` → 패키지 폴더 → `pyproject.toml`의 `entrypoint = "app.main:app"` 설정.
2. **리뷰 API:** 엔티티 → 딕셔너리 저장소 → DTO → 예외·처리기 → 서비스 → 의존성 함수 → 라우터 → `main.py` 조립.
3. **답글 API:** `uv add pydantic-settings openai` → 설정 → LLM client → 답글 서비스 → 의존성 함수 → 비동기 핸들러 → lifespan. `core/config.py`와 `clients/llm_client.py`는 기존 예제 구조를 참고할 수 있습니다.

완성 기준은 `uv run fastapi dev`, `/docs`·Postman의 세 API 호출, 등록 201·잘못된 입력 422·없는 리뷰 404, 저장 리뷰 기반 답글과 실제 서버 로그의 `MainThread` 확인입니다. [독립 리뷰 예제](ohgi-review-server/README.md)는 루트 접수 API와 구분합니다.

심화는 **별점 1~2 사과·공감 / 3 공감·개선 / 4~5 감사**, 검사 완료 답글의 저장·조회, 별도 `def`+동기 client와 비동기 client의 비교입니다. 주력 M02는 비동기로 유지하며 어느 별점도 마케팅 검사를 생략하지 않습니다.

`.env`는 Git에 올리지 않습니다. 기초 학습에서는 구조를 직접 설명·작성하고 AI는 자료구조·문법·오류 이해에 보조적으로 사용합니다. 막히면 기존 `HOWTO-chap01.md`·`HOWTO-chap02.md`·`HOWTO-chap03.md`를 참고합니다.

## 8. 현재 MVP 실행

저장소 루트에서 실행합니다. 기존 프로젝트에서 `uv init`을 다시 하지 않습니다.

```powershell
uv sync --python 3.14
$env:FAKE_LLM = "true"
$env:GUARDRAIL_BACKEND = "local"
uv run fastapi dev
```

Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

```powershell
# 기존 MVP 23개 회귀 시험. B03~B05 시험은 해당 의존성 환경에서 별도로 실행합니다.
uv run pytest -q tests/test_mvp.py
```

실제 OpenAI·Llama·E5 가중치 추론·LangSmith 원격 연결은 Codex에서 검증하지 않았습니다. memvid는 위의 실제 SDK·합성 벡터 검사까지만 확인했습니다. Python 3.12 NeMo/RAG 환경과 전체 회귀 명령은 개발 브랜치의 [S0 증거](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/evidence/S0/env.txt)에 있습니다. main 기본 환경에 아직 없는 선택 의존성이 필요한 시험을 기존 MVP 시험과 구분합니다.

## 9. 공부 자료와 검수 문서

- [확정 개발안 v1](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/RAG_V1_PLAN.md) · [단계별 실행 보고](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/evidence/SUMMARY.md) · [미확인·다음 결정](https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab/blob/5609bf98e053869699beefff58515af71415f4a8/docs/evidence/OPEN_QUESTIONS.md)

- [30쪽 태블릿 다크 모드 공부 PDF](docs/LEGAL_INTAKE_RAG_DESIGN_DARK_TABLET.pdf)
- [다크 태블릿 기본안](docs/rag-basic-dark-tablet.html) · [Markdown](docs/RAG_BASIC_DESIGN.md)
- [개발 전 구조 설계](docs/rag-architecture-dark-tablet.html) · [Markdown](docs/RAG_ARCHITECTURE_REVIEW.md)
- [Claude 검수 요청서](docs/claude-rag-review-dark-tablet.html) · [Markdown](docs/CLAUDE_RAG_DESIGN_REVIEW.md)
- [전체 보안 이전 목표](docs/SECURITY_MIGRATION_PLAN.md) · [마케팅 게시판 계약](docs/LEGAL_MARKETING_BOARD.md)

HTML은 내려받아 브라우저에서 엽니다. GitHub에서 바로 읽으려면 Markdown이나 PDF를 이용합니다. PDF·HTML은 기본 개념 학습 자료입니다. 이후 검수·실측으로 달라진 실행 범위와 수치는 확정 v1 및 단계별 증거를 우선합니다. Claude 검수 의견은 반영했으며, 설계 검수와 실제 연동·시험 완료는 구분합니다.

## 10. 저장소 발전 순서

| 순서 | 역할 |
|---|---|
| ① 현재 `legal-intake-fastapi-lab` | FastAPI 단독에서 보안·검색·생성·마케팅 기능 검증 |
| ③ `python-memvid-guardrail` | 검증한 검색·보안 부품을 재사용 모듈로 분리 |
| ② `spring-fastapi-async-refactor` | Spring 인증·인가와 FastAPI AI 서비스 연결 |
| 이후 | 검증한 기능을 기반으로 별도 비공개 상업화 개발 |

① → ③ → ② 순서를 유지합니다. 이번에는 인증·인가·자동 외부 게시·일반 웹 검색·운영 DB·Redis/Celery/Kafka를 추가하지 않습니다. 기존 Java 서버와 DB도 수정하지 않습니다.
