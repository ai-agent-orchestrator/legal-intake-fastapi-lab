# 개발 전 구조 설계안 · 작은 근거 기반 안내 서비스

2026-11-06 · **검토용 v0.1 / Claude 검수 대기 / 검색 기능 구현 착수 전**

목표는 합성 안내문 10개로 “검색 → 근거 분기 → 구조화 안내 → 검증”을 완성하는 것이다.
LangChain·LangGraph·LangSmith·RAG·임베딩·벡터 RAG·memvid를 모두 포함하되, 첫 기능은 기존 안내 API 하나에 집중한다.
이 문서의 파일·함수·DTO는 예정 계약이며 이미 존재한다는 뜻이 아니다.

## 1. 현재 코드와 새 설계의 경계

| 영역 | 현재 확인한 상태 | 이번 새 설계 |
|---|---|---|
| 브랜치 | `feat/security-input-actions` | 같은 저장소에서 검수 후 단계별 구현 |
| 보존본 | `wip/codex-legal-snapshot` / `e6df050` | 변경하지 않음 |
| 선별 커밋 | `4fcc698` 보안 기반 모듈 | 재사용하되 수정 필요성은 별도 검수 |
| 기존 API | 등록·조회·안내 3개 | 3개 정상 계약 유지 |
| L01/L02 | 현재 작업 폴더에 구현, 95개 시험 통과 기록, 아직 미커밋 | 최종 개발 전 검수·기반 확정 |
| 새 검색 기능 | 미구현 | 이 문서의 검수 대상 |
| 마케팅 검사 | 보존본에 실패 사례가 있음 | 실패 코드를 정상 입력 action처럼 가져오지 않음 |
| 생성 client | 현재 OpenAI SDK 어댑터 | Llama 어댑터를 검수 후 추가, 기존 client는 회귀 기준으로 유지 |

Claude는 실제 Git 상태와 문서의 상태가 일치하는지 먼저 확인한다. 95개는 L01/L02 등의 기존 시험 기록이며
새 RAG·임베딩·memvid·LangSmith 기능의 통과 개수가 아니다.

## 2. 전체 구조 · 부품과 연결

```text
                 [FastAPI: 기존 guidance API]
                            │
           [요청 context · 세션 · 입력 검사 · 마스킹]
                            │
             [Guidance service: 실행과 자원 책임]
                            │
                  [LangGraph: 고정 workflow]
                  retrieve → 근거 유무 분기
                     │              │
                   있음            없음
                     │              └→ 추가 자료 요청 템플릿
              [LangChain chain]
          Prompt → Llama → 구조화 DTO
                     │
          [출처 ID 검증 · 전체 출력 검사 · 최종 마스킹]
                     │
              [문맥 재확인 → 기존 응답]

retrieve 내부:
  마스킹된 질문 → E5 query embedding → memvid → 근거 Document[]

미리 적재:
  합성 문서 → 검사·마스킹 → token 분할 → E5 document embedding → memvid

LangSmith:
  위 서비스/graph/node의 실행 추적과 평가
  전송 전 입력·출력·metadata·오류 정보 처리
```

| 책임 | 단일 소유자 | 첫 범위 |
|---|---|---|
| 모델·프롬프트 조합 | LangChain chain | 짧은 LCEL node 하나 |
| 순서·분기 | LangGraph | 3 node, 재검색/재시도 루프 없음 |
| 벡터 생성 | E5 provider | 문서/질문 API 분리 |
| 저장·검색 | memvid adapter | 활성 `.mv2` 인덱스 하나 |
| 정책·문맥 | 기존 security service | graph가 우회할 수 없음 |
| 예산·용량·정리 | 실행 service | 모델 node 바깥의 호출 경계 |
| 관찰·실험 | LangSmith adapter + 평가 script | 합성 dataset 중심 |

검색 node에도 자료 검사와 관련성 gate가 필요하다. 검색 결과 3개가 있다는 이유만으로
항상 generate로 이동하지 않는다. 서비스의 policy gate는 graph의 선택적 도구로 만들지 않는다.

## 3. 파일과 인터페이스 계약

아래 배치는 검토용이다. 같은 역할을 다른 라이브러리가 이미 담당하면 중복 추상화를 만들지 않는다.

```text
app/
  security/                  # 현재 기반 + 검수 후 나머지 필수 경계
  services/guidance_service.py# 기존 endpoint의 진입점·정리·계약 유지
  clients/llama_client.py     # 생성 모델 어댑터
  retrieval/
    schemas.py               # Chunk / RetrievedEvidence / IndexManifest
    ingest.py                # read → mask → split → embed → stage index
    embeddings.py            # E5 encode_documents / encode_query
    memvid_store.py          # index publish / search / close
    retriever.py             # LangChain Document 인터페이스
  chains/guidance_chain.py    # template → Llama → Pydantic
  graphs/guidance_graph.py    # retrieve / generate / ask_for_materials
  observability/tracing.py    # 기록 전 처리·trace context
scripts/
  ingest_guides.py
  evaluate_retrieval.py
tests/
  test_retrieval_ingest.py
  test_memvid_integration.py
  test_guidance_graph.py
  test_trace_redaction.py
```

| 인터페이스 | 입력 → 출력 | 검수할 제약 |
|---|---|---|
| `encode_documents` | 안전 청크 목록 → 벡터 목록 | 개수·차원·유한값·정규화·모델 revision 검사 |
| `encode_query` | 안전 질문 → 벡터 | E5 query instruction 적용, 문서와 같은 모델 공간 |
| `publish_index` | 검증 완료 staged 인덱스 → 활성 manifest | 완료 전 노출 금지, 실패 시 기존 인덱스 유지 |
| `retrieve` | 안전 질문·collection → 근거 목록 | top-k, 자료 범위·버전 고정, 관련성 판정 |
| `generate` | 질문·검증 근거 → 내부 DTO | 생성 1회, 임의 출처 생성 거절 |
| `run_graph` | 요청별 state → 초안/추가 자료 요청 | 공유 mutable state 금지, 실행 상한 |
| `trace` | 허용한 실행 정보 → trace | 원문·키·예외·metadata의 전송 전 처리 |

### 자료와 state의 최소 필드

- `Chunk`: documentId, chunkId, sourceVersion, collectionId, safeText, tokenCount.
- `IndexManifest`: indexVersion, embeddingModel, pinnedRevision, dimension, normalization, chunkerVersion.
- `RetrievedEvidence`: 검색한 Chunk + retrievalMode + score + indexVersion. 점수 의미는 검색 방식별로 구분한다.
- `GraphState`: 서버 requestContext, safeQuestion, evidence, evidenceStatus, draft. 요청마다 새 값으로 전달한다.
- `GuidanceDraft`: answer, preparationItems, questions, citationIds, evidenceStatus. 외부 DTO는 우선 변경하지 않는다.

긴 작업을 최초 적재로 분리한다. 모델 로딩은 요청마다 반복하지 않는다.
E5/Llama inference가 동기 GPU/CPU 작업이면 제한된 실행 자원으로 옮기며 async def 안에서 직접 blocking하지 않는다.
취소가 Python task에 전달돼도 native 추론이 즉시 멈추는지는 별도 검증하고 실행 슬롯을 성급히 반환하지 않는다.

## 4. 모델·저장소·관찰의 결정과 미확정 사항

| 항목 | 기본안 | 최종 확정 전 확인 |
|---|---|---|
| 생성 | Llama 계열 | 정확한 모델 ID·양자화·서버·한국어 JSON 품질 |
| 임베딩 | 로컬 E5-large-instruct 우선 검토 | revision 고정, Windows 실행·자원·한국어 Hit@3 |
| Qwen | 대표님 방침에 따라 실행 제외 | 비교 설명만 유지 |
| OpenAI embeddings | 원격 API 대안 | 원문 외부 전송 조건을 따로 결정, 기존 점수 표는 출처 미확인 |
| 검색 엔진 | memvid, 외부 E5 벡터 주입 | SDK 버전의 문서·query 벡터 지원과 반환 metadata 확인 |
| 기본 검색 | vector + keyword 기준선 비교 | 실제 자료로 관련성 기준 보정 |
| 혼합 검색 | 후속 비교 | 점수 직접 합산 대신 순위 결합 검토 |
| tracing | LangSmith, 기본 본문 숨김 | 키·project·전송 필터·SDK 오류 경로 실제 검증 |
| 평가 | 한국어 합성 질문 20개 + 확인용 10개 | 정답 문서 ID·무근거 사례·민감정보 사례 확정 |

임베딩과 생성 모델의 회사가 같을 필요는 없다. 문서와 질의 임베딩의 모델·revision·차원·전처리는 일치해야 한다.
E5의 512토큰 상한에 맞춰 300토큰/40토큰 overlap을 실험 시작값으로 두며 실제 tokenizer로 확인한다.
원격 LangSmith를 쓰는 경우 로컬 추론이라는 이유만으로 데이터가 외부로 안 나간다고 설명하지 않는다.

memvid의 lexical/vector 검색과 저장 형식은 실제 SDK 통합 검수 항목이다.
인덱스 재생성은 새 파일에서 완료한 뒤 manifest를 바꿔 활성화한다. 읽는 중 파일을 덮어쓰지 않는다.
첫 지식 범위는 합성 안내문뿐이며 접수·후기와 섞지 않는다. 공개 저장소에는 실제 데이터·벡터·키를 올리지 않는다.

벡터·코사인 유사도는 이번 Legal Intake를 이해하는 최소 개념 공부로 설명한다.
별도 리서치 시스템·개인 검색식·질의 요약기·맞춤 랭킹 설계로 범위를 확장하지 않는다.

## 5. 완료 조건과 개발 착수 gate

| 묶음 | 필수 검증 | 완료로 세지 않는 것 |
|---|---|---|
| 보안 선행 | 입력·마스킹·출력·문맥·비용·용량·취소 | 검사 함수 이름만 존재 |
| 적재·검색 | 실제 E5 encode + 실제 memvid round-trip | fake 벡터만으로 통과 |
| LangChain | 실제 template와 schema 검증, fake/실모델 구분 | 문자열 붙이기만 하고 LangChain이라고 표시 |
| LangGraph | 실제 StateGraph 실행, 근거 없음 시 생성 0회 | Python if만 있는 흐름 |
| LangSmith | 원격 trace 확인 + dataset experiment | SDK 설치·mock 성공만으로 완료 표시 |
| 회귀 | 기존 3개 API 계약·기존 시험 유지 | 테스트 기대값을 바꿔서 숨기기 |
| 품질 | 같은 질문·정답 문서로 Hit@3·지연 비교 | 공개 순위나 출처 없는 20문항 점수 인용 |

최대 앱 API 11개 구성은 [기본 설계 §13](RAG_BASIC_DESIGN.md)에 적었다. 최초 연결은 기존 guidance 하나다.
게시판·M01/M02는 같은 내부 부품을 재사용하며 마케팅 검사 재검증 뒤 별도로 활성화한다.

**다음 순서로 진행한다.**

1. 이 구조 설계안과 공부 문서를 Claude에게 전달한다. 읽기 검수만 수행한다.
2. Claude가 P0/P1/P2 지적·누락·중복·대안을 근거와 함께 반환한다.
3. Codex가 지적별 수용/보류/반박과 수정안을 정리한다. 검수자의 의견을 자동 적용하지 않는다.
4. 최종 개발안 v1에 채택 범위·실행 환경·단계별 테스트·미확정 사항을 고정한다.
5. 대표님이 최종안을 확정한 뒤 B01부터 작은 단위로 구현한다. 검수 전에는 새 검색 구현을 시작하지 않는다.

현재 gate는 **1번 전달 준비 완료 / Claude 검수 대기**다.
[복사할 Claude 검수 요청서](CLAUDE_RAG_DESIGN_REVIEW.md) · [공부 문서](RAG_BASIC_DESIGN.md).
