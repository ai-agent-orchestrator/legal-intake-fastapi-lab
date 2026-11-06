# Legal Intake RAG v1 — 확정 실행 계획

2026-11-06 · 사용자 최종 지시 반영 · Claude 재검수 의견과 구체화 포함

이 문서가 종전 RAG v0.1 문서와 충돌하면 이 문서를 따른다. 검수 의견을 반영한 계획이며, 구현이나 시험 통과를 증명하는 문서는 아니다. 완료 여부는 `docs/evidence/`의 실제 실행 증거로 구분한다.

## 목적·범위·시간

임베딩·memvid·벡터 RAG를 합성 자료로 직접 구현하고 공부한다. 실제 접수 흐름 연결은 이번 범위가 아니다. 이번 실행은 **S0 → B01 → B02a → B02b**까지만 한다. B02b 완료, 필수 조건 실패 또는 착수 후 4시간 중 먼저 도달하는 시점에 정리하고 정지한다. B03 이후는 별도 승인이다.

- 착수 시각: 2026-11-06 06:24 UTC / 15:24 KST. 종료 상한: 10:24 UTC / 19:24 KST.
- 브랜치: `feat/security-input-actions`. 단계별 로컬 커밋. push·main 병합 금지.
- 보존 브랜치 `wip/codex-legal-snapshot` (`e6df050`)는 변경하지 않는다.
- 착수 후 10분 이내 이 문서를 먼저 커밋한다.

## 확정 결정

1. S0에서 새 의존성 설치 전에 L01/L02를 별도 커밋한다. `context.py`의 공백 세션 병합 버그 수정도 포함한다.
2. 세션 위험 적립은 **사용자 입력 정책 차단만** 한다. 출력 위반·검색 자료 차단은 기록만 한다. `RISK_REASONS`에서 `OUTPUT_POLICY_BLOCKED`를 제외하는 L02 계약 변경에는 새 시험을 추가하며 기존 시험 기대값은 유지한다.
3. `check_retrieved_material(chunk)`는 입력 정책 패턴의 `retrieved` profile을 사용하는 별도 계약이다. BLOCK 청크만 제외·기록하고 `record_risk_event`를 호출하지 않는다. 전부 제외되면 EMPTY. 이번에는 계약만 정의하며 실제 연결은 B03 이후다.
4. Llama는 설치하지 않는다. S0 사양 보고 후 사용자가 모델을 결정한다.
5. 검색 비교는 **키워드(memvid lex) 대 벡터**만 한다. RRF·가중식·혼합 검색은 하지 않는다.
6. LangChain·LangGraph·LangSmith는 최종 개발 범위에 포함하지만 **이번에 설치하지 않는다**. B03 이후 역할은 각각 prompt/chain·분기 workflow·합성 평가/추적이다. LangSmith 원격 전송은 이번에 0이다.

## 다운로드·외부 전송

lock된 패키지 설치, `intfloat/multilingual-e5-large-instruct` 고정 revision의 tokenizer(B01)와 가중치(B02b) 1회 다운로드만 허용한다. 모델 캐시는 저장소 밖에 둔다. 이후 `HF_HUB_OFFLINE=1`로 오프라인 로딩을 검증한다. 합성 자료 내용도 외부로 전송하지 않으며 새 시험은 소켓을 차단한다. `.gitignore`에 `*.npy`, `*.npz`, `*.safetensors`, `*.bin`, 평가 원본 출력 폴더를 추가한다. `.mv2`와 `data/` 제외 규칙은 유지한다.

## S0 — 환경과 기준점

- L01/L02를 먼저 커밋하고 보안 계획의 과거 ‘23개·NeMo 미구현’, README §9의 ‘검수를 받았다는 뜻은 아님’을 현재 증거에 맞춰 정리한다.
- Python 3.12 우선. `security-runtime` 확장 또는 별도 RAG lock 중 하나를 선택하고 이유를 기록한다. 신규 설치 대상은 `memvid-sdk`, `sentence-transformers`(+torch), `numpy`와 그 필수 전이 의존성뿐이다. 기존 환경을 덮어쓰지 않는다.
- `docs/evidence/S0/env.txt`: Python, lock SHA256, 주요 패키지 버전, 설치 명령과 import 스모크 결과.
- `hardware.txt`: CPU, RAM, GPU/VRAM, 여유 디스크.
- `pytest.txt`: 설치 후 기존 **95개** 시험 재실행 출력과 전체 요약. 추가 시험은 별도 집계한다. 기대값 변경 금지.
- 3.12 의존성 충돌이면 원인과 시도 명령을 기록하고 S0에서 정지한다. 기존 95개 실패 시 원인을 기록하고 새 의존성 때문이면 새 의존성을 되돌린 뒤 정지한다.

## B01 — 합성 자료와 분할

- 안내문 10개. caseType마다 최소 2개, 혼동하기 쉬운 주제 쌍 2쌍 이상. 문서별 E5 tokenizer 기준 600~1,200토큰. 첫 줄은 `합성 학습 자료, 법률 자문 아님`. 실명·실제 사건 금지.
- 평가 30개는 접수 DTO 형태다. 비교 20개에 무근거 ≥6개, 확인 10개에 무근거 ≥4개. 의역·법률 용어·무근거·합성 PII 태그, 정답 documentId 집합을 갖는다.
- 쿼리는 `clientName`을 제외하고 마스킹한 `caseType`, `coreStatement`, `desiredNextStep`을 순서대로 결합한다. 이는 합성 평가용 계약이며 운영 입력 경로는 연결하지 않는다.
- E5 tokenizer 300토큰 / 겹침 40토큰. 제목·문단 경계를 우선 보존한다. metadata 기본 10필드는 `documentId`, `chunkId`, `title`, `caseType`, `sourceVersion`, `chunkerVersion`, `embeddingModel`, `pinnedRevision`, `indexVersion`, `tokenCount`. 여기에 `contentHash`, `maskingVersion`, `policyVersion`을 포함한다. 멱등 키는 documentId+sourceVersion+chunkerVersion이며 청크 ID에 내용/분할 버전을 반영한다.
- 재적재 멱등 시험과 최종 입력 길이 시험을 둔다. query instruction·특수 토큰을 포함해 512토큰을 넘지 않는다.

## B02a — memvid 필수 기능 검증

결정적 합성 1024차원 벡터로만 다음을 실제 SDK와 시험한다: 외부 문서 벡터 저장, query 벡터 검색, metadata 반환, 차원 불일치 거절, 재오픈 후 동일 결과, 점수 방향, Windows에서 열린 `.mv2` 교체·삭제 동작, 실패 시 조용한 대체 없음.

인덱스는 `data/index/<indexVersion>.mv2`, 포인터는 `active.json`이다. 포인터는 `indexVersion`, `file`, `sha256`, `embeddingModel`, `pinnedRevision`, `createdAt`을 갖는다. 버전 파일을 완성하고 핸들을 닫은 후 **포인터 파일만** `os.replace`로 전환한다. 열린 인덱스 파일을 덮어쓰지 않는다.

`docs/evidence/B02a/memvid_capabilities.json`에 항목별 pass/fail 및 실제 근거 출력을 기록한다. **필수 항목 하나라도 fail이면 정지한다.** 다른 저장소로 바꾸지 않는다. B02a는 합성 벡터 시험이며 실제 E5 연동 완료로 표시하지 않는다.

## B02b — 실제 E5 검색 평가

- 고정 revision E5 query instruction을 질문에만 적용한다. 문서에는 적용하지 않는다. 장치(cpu/cuda), 배치 상한, encode 시간 상한을 실행 전에 명시한다. CPU에서 상한 초과 시 배치를 줄여 1회 재시도하고 다시 초과하면 측정값과 함께 정지한다.
- Hit@3는 **근거 질문만** 분모로 하며 documentId별 청크 최고점으로 정렬한 상위 3개 문서와 정답 ID 집합의 교집합을 본다. `n/근거 질문 수`를 보고한다. 10문서 중 정답이 정확히 1개이고 균등 무작위 비복원 top3이면 무작위 기준선은 3/10이다. 정답 복수이면 이 가정과 구분한다.
- 무근거 혼동표는 개수로 보고하고 유형별 결과, 질문 임베딩 지연, 검색 지연도 기록한다.
- **관련성 규칙 사전 등록:** 벡터 문서 점수는 청크 최고점. `top1 ≥ τ_abs`이고 `(top1 − top2) ≥ τ_gap`이면 근거 있음. 키워드는 결과 없음 또는 `τ_lex` 미만이면 근거 없음.
- 비교 20개로만 임계값을 정한다. 무근거의 근거 있음 오판은 **0개**를 제약으로 하고, 그 안에서 근거 질문의 무근거 오판 수를 최소화한다. 동률이면 보수적 임계값을 택한다. 확인 10개에는 **한 번만** 적용하며 다시 튜닝하지 않는다.
- `RetrievalResult(status: OK|EMPTY|BELOW_THRESHOLD, evidence, mode, index_version)`. 검색 장애는 `RetrievalUnavailable`이며 향후 503 `RETRIEVAL_UNAVAILABLE`로 매핑한다. 이번에는 계약만 정의하고 API 연결은 하지 않는다.
- `RAG_ENABLED=false` 기본값. 기존 guidance API와 기존 3개 API 기대값은 유지한다. 새 공개 API는 0개다. 향후 최대 11개는 사용자 정의 업무 API만 집계한다(`/docs`, `/openapi.json` 제외).
- `docs/evidence/B02b/retrieval_eval.json`: 질문 ID, 근거 유무, 정답 ID, 방식별 top3 ID·점수·판정·시간. 이 파일에서 보고 수치를 다시 계산할 수 있어야 한다.

## 미해결 상황·정지 조건

- 모델 다운로드 불가: 가능한 B01 작업까지 정리하고 B02b 전에 정지. tokenizer도 없으면 B01 완료로 표시하지 않는다.
- 의존성 충돌, 기존 시험 회귀, memvid 필수 기능 실패, CPU 재시도 상한 초과는 위 규칙대로 정지한다.
- 다른 설계 결정 필요 시 임의 결정하지 않고 `docs/evidence/OPEN_QUESTIONS.md`에 적은 뒤 영향 없는 작업을 계속하거나 정지한다.
- 실제 접수 데이터·유료 API·LangSmith 원격 전송·Llama 설치·기존 시험 기대값 변경·push·main 병합·보존 브랜치 변경·fake를 실제 연동으로 표시하는 행위는 금지한다.

## 종료 산출물

마지막 로컬 커밋에 `docs/evidence/SUMMARY.md`를 포함한다. 단계별 `한 일 | 실행한 명령 | 결과(수치·통과 수) | 실제/fake 구분 | 미확인·다음 결정` 표를 작성한다. 증거는 합성 자료만 포함하고 벡터·키는 포함하지 않는다. 마지막 줄에 `정지 이유: 완료 / 조건 정지 / 시간 초과` 중 실제 이유를 적는다.
