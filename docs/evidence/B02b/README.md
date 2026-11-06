# B02b — 실제 E5 × memvid 검색 평가

2026-11-06 · 합성 자료만 · CPU float32 · 실제 E5·실제 memvid. API/생성 모델 연결 없음.

이 문서는 `retrieval_eval.json`의 질문별 결과에서 다시 계산했습니다. 모델이나 확인 세트 검색을 재실행하지 않습니다.

## 문서 단위 검색 순위

| 세트 | 방식 | Hit@1 | Hit@3 | 근거 질문 분모 |
|---|---|---|---|---|
| 비교20 | lex | 12/14 | 14/14 | 14 |
| 비교20 | vector | 14/14 | 14/14 | 14 |
| 확인10 (단회) | lex | 5/6 | 5/6 | 6 |
| 확인10 (단회) | vector | 6/6 | 6/6 | 6 |

Hit는 관련성 gate 적용 전 순위입니다. 근거 문서 중 청크 최고점으로 상위 3문서를 고릅니다. 정답 문서 집합과 하나 이상 겹치면 hit입니다. 무작위 3/10은 10문서·정답1개·균등 비복원 추출의 이론 기준선입니다.

## 근거 판정 혼동표 (개수)

| 세트 | 방식 | 근거 있음→수용 | 근거 있음→거절 | 무근거→수용 | 무근거→거절 |
|---|---|---|---|---|---|
| compare | lex | 14 | 0 | 0 | 6 |
| compare | vector | 14 | 0 | 0 | 6 |
| holdout | lex | 4 | 2 | 0 | 4 |
| holdout | vector | 5 | 1 | 0 | 4 |

## 유형별 결과 (태그 중복 가능)

| 유형 | 세트 | 방식 | Hit@1 | Hit@3 | 근거 거절 | 무근거 오수용 |
|---|---|---|---|---|---|---|
| 의역 | compare | lex | 8/8 | 8/8 | 0 | 0 |
| 의역 | compare | vector | 8/8 | 8/8 | 0 | 0 |
| 의역 | holdout | lex | 3/4 | 3/4 | 2 | 0 |
| 의역 | holdout | vector | 4/4 | 4/4 | 1 | 0 |
| 법률 용어 | compare | lex | 4/6 | 6/6 | 0 | 0 |
| 법률 용어 | compare | vector | 6/6 | 6/6 | 0 | 0 |
| 법률 용어 | holdout | lex | 2/2 | 2/2 | 0 | 0 |
| 법률 용어 | holdout | vector | 2/2 | 2/2 | 0 | 0 |
| 합성 PII | compare | lex | 2/2 | 2/2 | 0 | 0 |
| 합성 PII | compare | vector | 2/2 | 2/2 | 0 | 0 |
| 합성 PII | holdout | lex | 1/1 | 1/1 | 0 | 0 |
| 합성 PII | holdout | vector | 1/1 | 1/1 | 0 | 0 |
| 무근거 | compare | lex | N/A (no evidence questions) | N/A (no evidence questions) | 0 | 0 |
| 무근거 | compare | vector | N/A (no evidence questions) | N/A (no evidence questions) | 0 | 0 |
| 무근거 | holdout | lex | N/A (no evidence questions) | N/A (no evidence questions) | 0 | 0 |
| 무근거 | holdout | vector | N/A (no evidence questions) | N/A (no evidence questions) | 0 | 0 |

## 지연

| 세트 | 방식 | 검색 평균 ms | 검색 p95 ms | 질문 임베딩 평균 ms | 질문 임베딩 p95 ms |
|---|---|---|---|---|---|
| compare | lex | 1.764 | 3.242 | N/A | N/A |
| compare | vector | 0.710 | 0.830 | 177.614 | 210.919 |
| holdout | lex | 1.450 | 2.229 | N/A | N/A |
| holdout | vector | 0.761 | 0.936 | 202.354 | 280.048 |

검색 시간에는 모델 초기 로딩을 포함하지 않습니다. E5는 CPU 4 threads, 문서 batch2·질문 batch1, float32입니다. 문서30개 encode는 embedding_documents.json, 모델 로딩 시간은 각 embedding JSON에 별도 기록했습니다. p95는 nearest-rank입니다.

## 실패·주의할 질문

| ID | 세트 | 방식 | 관찰 |
|---|---|---|---|
| Q02 | compare | lex | top1 정답 아님 |
| Q08 | compare | lex | top1 정답 아님 |
| Q21 | holdout | lex | top1 정답 아님 / top3 정답 없음 / 관련성 gate에서 근거 없음 판정 |
| Q22 | holdout | vector | 관련성 gate에서 근거 없음 판정 |
| Q23 | holdout | lex | 관련성 gate에서 근거 없음 판정 |

## 고정 조건과 한계

- 모델: intfloat/multilingual-e5-large-instruct / revision 274baa43b0e13e37fafa6428dbc7938e62e5c439. 질문 instruction 있음, 문서에는 없음. 최종 길이를 검사하며 조용히 truncate하지 않습니다.
- 비교20만으로 임계값을 고정하고 frozen_thresholds.json SHA를 confirm_once.json에 기록한 뒤 확인10을 1회 검색했습니다. 확인 결과를 본 재조정은 없습니다.
- lex는 라벨·마스크·연산자 토큰을 제외하고 OR 결합합니다. 형태소 분석 없음. vector는 query 문자열을 비우고 명시적 sem+외부 벡터로 호출합니다. native score는 코사인 원값이 아닙니다.
- 8개 이하의 put_many에 opts enable_embedding=False를 명시합니다. 30개 전수·자기 top1 검증 후에만 포인터를 변경했습니다. index_activation.json 참조.
- 최초 암묵적 float16 CPU 실행은 정규화 검사에 실패했습니다. 실패 로그를 보존하고 float32 명시로 재실행했습니다. 확인 세트 사용 전의 수정입니다.
- worker 프로세스 상한 180초, timeout일 때만 batch1로 1회 재시도합니다. Windows는 worker 트리를 종료한 뒤 재시도합니다. 이번 성공한 float32 실행에 timeout은 없었습니다.
- Python socket/DNS 차단, HF_HUB_OFFLINE=1, MEMVID_TELEMETRY=0. Rust의 모든 syscall을 OS firewall로 차단했다는 증거는 아닙니다.
- 작은 합성 코퍼스와 동일 작성자의 평가이므로 일반 한국어·실제 법률 상담 성능을 보장하지 않습니다. 모델 간 비교나 Llama 생성 평가도 아닙니다.

재계산: `.\rag-runtime\.venv\Scripts\python.exe scripts/report_retrieval.py`. 검색·확인 세트를 재실행하지 않고 저장된 결과에서 표를 만듭니다.
