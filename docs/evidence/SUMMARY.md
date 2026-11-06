# RAG v1 무인 실행 종료 보고

## 최신 실행 — B02a 우회 조건부 통과와 B02b 완료

2026-11-06 KST 16:12 재착수, 16:35 구현·증거·검증 정리 완료. 사용자 추가 승인에 따라 18:00 전에 로컬 커밋과 개발 브랜치 push까지 진행한다. 아래 최초 조건 정지 보고는 이력이며 최신 상태는 이 절과 B02b 증거를 따른다.

| 단계 | 한 일 | 실행한 명령 | 결과(수치·통과 수) | 실제/fake 구분 | 미확인·다음 결정 |
|---|---|---|---|---|---|
| B02a 적재 계약 | 8개 이하 put_many·명시적 opts false, seal/read_only 재오픈 후 전체 수·ID 집합·모든 자기 top1 검증. 실패 시 기존 포인터 보존 | `rag-runtime/.venv/Scripts/python.exe -m pytest -q tests/rag/test_index.py` | 5 passed in 2.84s. 누락·자기검색 불일치 주입 시 active.json 불변 | 실제 SDK 30청크 시험 + 명시적으로 구분한 fake 장애 주입 | SDK 유실 버그 자체를 수정한 것은 아님 |
| B02a 대량 probe | 60개 일괄의 유실, 8개 묶음 60/120개 전수 검사 | `rag-runtime/.venv/Scripts/python.exe scripts/probe_memvid_workaround.py` | 대량60: 6/60, batch8: 60/60·120/120. 우회 gate 통과. 기준 커밋 fc15bdd | 실제 memvid, 결정적 합성 벡터이며 E5 아님 | 최초120 검사에 Windows os error5. 실패 원본·개별 재검사·전체 재실행 모두 보존 |
| B02b 임베딩 | 고정 E5 가중치1회 수신, offline CPU float32 encode | `... scripts/download_e5.py weights`; `... scripts/evaluate_retrieval.py` | 30문서 청크 encode 15.974초, 최종 최대293토큰. 1024차원·정규화·유한값 확인. 30/30 자기검색 후 활성화 | 실제 E5, 실제 memvid, 합성 자료만 | 첫 기본float16 CPU 정규화 실패 로그 보존. float32 명시 후 성공. Llama 미설치 |
| B02b 평가 | compare20만으로 보정, 임계값 SHA 고정 후 confirm10 단회 적용. OR lex 대 vector | `... scripts/evaluate_retrieval.py` | compare: lex Hit@1 12/14·Hit@3 14/14, vector 14/14·14/14. confirm: lex 5/6·5/6, vector 6/6·6/6 | 실제 검색. 확인10으로 재튜닝 없음 | confirm 근거 거절 lex2·vector1, 무근거 오수용 두 방식 모두0/4. 순위 성공과 gate 수용은 구분 |
| 결과 재계산 | 저장된 질문별 순위·점수·판정에서 표 재계산 | `... scripts/report_retrieval.py` | 저장 metrics와 일치. 유형별 의역·법률용어·합성PII·무근거, Hit@1/3·혼동표·질문임베딩/검색 지연 기록 | 모델/검색 재실행 아님 | 작은 합성셋·같은 작성자. 일반화 성능 보장 아님 |
| 최종 회귀 | 기존95 기대값을 바꾸지 않은 전체 시험, 신규 포인터/보정/timeout/증거 해시 검사 | `rag-runtime/.venv/Scripts/python.exe -m pytest -q` | **122 passed, 36 warnings in 14.44s** | 실제 NeMo rail·실제 SDK 포함, LLM 응답 fake. timeout/장애는 명시적 주입 | 기존 경고는 NeMo nim_url deprecation. Claude B03~B05 시험을 실행한 결과는 아님 |
| 학습 자료 | 임베딩/의미검색·단어검색 비교·직접 코사인 구현·Golden Set 모델 비교 절차 | `... docs/build_retrieval_study.py` | Markdown 8절·기존 테마 다크 HTML, HTML parse·목차·외부 script 없음 확인 | 코드의 장난감2차원 벡터와 실제 E5 결과를 구분 | 새 PDF는 생성하지 않음. 기존 PDF보다 최신 실행 증거 우선 |

confirm 질문 임베딩 평균202.354ms, vector 검색 평균0.761ms(임베딩/초기로드 제외), lex 검색 평균1.450ms. 비교 세트의 대응 평균은177.614ms / 0.710ms / 1.764ms이다. 원본 개별 시간·p95·유형별 표는 [B02b 결과](B02b/README.md)에 있다. vector의 확인 Q22는 top1 정답이나 gap/절대점 gate에 의해 거절되었다. lex는 Q21을 top3에서 놓치고 Q21·Q23을 거절했다. threshold를 확인 결과에 맞춰 바꾸지 않았다.

증거: [우회 probe](B02a/memvid_workaround_windows.json), [E5 인덱스 활성화](B02b/index_activation.json), [30개 질문 결과](B02b/retrieval_eval.json), [동결 임계값](B02b/frozen_thresholds.json), [단회 확인 marker](B02b/confirm_once.json), [환경·가중치/lock 해시](B02b/environment.json), [최종 pytest 원문](B02b/pytest_all.txt).

Golden Set 원본과 동결 임계값은 최초 측정한 Windows CRLF 바이트에 SHA256이 연결되어 있다. 두 경로에만 `.gitattributes -text -eol`을 적용해 Git의 LF 정규화가 원본 증거 해시를 바꾸지 않도록 했다. 질문·정답·임계값은 수정하지 않았고, Git blob에서도 기존 SHA가 일치하는지 확인한다. 숫자나 확인 결과를 다시 튜닝한 변경이 아니다.

모델/벡터/cache/`.mv2`는 커밋하지 않는다. API 추가0, guidance 연결0, RAG_ENABLED 기본false. LangChain·LangGraph·LangSmith 설치·원격 전송0, Llama·유료 API·실제 접수 사용0. 이번 push 대상은 feat/security-input-actions뿐이며 main·보존 브랜치를 변경하지 않는다.

## 최초 실행 이력 — 아래는 추가 승인 전 조건 정지 보고

2026-11-06 · `feat/security-input-actions` · 시작 06:24 UTC / 15:24 KST, 조건 정지 06:41 UTC / 15:41 KST. 보고 정리 포함 약 20분. 4시간을 채우기 전에 사용자가 지정한 실패 정지 조건에 도달했다.

| 단계 | 한 일 | 실행한 명령 | 결과(수치·통과 수) | 실제/fake 구분 | 미확인·다음 결정 |
|---|---|---|---|---|---|
| 계획 | 최종 지시의 범위·계약·지표·정지 조건을 먼저 문서 커밋 | `git add -- docs/RAG_V1_PLAN.md`; `git commit -m "docs: freeze approved RAG v1 synthetic learning plan"` | `f0cbc8d`, 착수 10분 이내 저장 | 계획 문서이며 구현 증거와 구분 | 종전 초안보다 v1 우선 |
| S0 기준점 | L01/L02·공백 세션 분리 수정 보존. 입력 정책 차단만 위험 적립하도록 변경하고 새 시험 추가. 낡은 문서 현재 상태 정리 | `security-runtime/.venv/Scripts/python.exe -m pytest -q tests/test_mvp.py tests/test_nemo_integration.py tests/test_session_security.py`; `... -m pytest -q tests/test_l02_input_only_risk.py` | 기존 **95 passed, 32 warnings in 11.19s**, 추가 **9 passed, 4 warnings in 1.89s**. `2808606` | 실제 NeMo rail 포함. AI 답변은 fake/mock, 유료 모델 호출 없음 | 마스킹·입출력 정책·용량/예산 운영 연결은 미완료 |
| S0 환경 | Python 3.12 별도 RAG lock·환경, 기존 환경 보존. import·하드웨어·설치 후 회귀 확인 | `uv lock --project rag-runtime --cache-dir .uv-cache`; `uv sync --project rag-runtime --frozen --cache-dir .uv-cache --python C:/Users/Codelab/AppData/Local/Programs/Python/Python312/python.exe`; `rag-runtime/.venv/Scripts/python.exe -m pytest -q tests/test_mvp.py tests/test_nemo_integration.py tests/test_session_security.py` | 기존 **95 passed, 32 warnings in 6.92s**. 기존 패키지 버전 차이 **0**. 실제 import 성공. `ce3acc0` | 실제 설치: memvid 2.0.160, ST 6.2.0, torch 2.15.0+cpu, numpy 2.5.4. LC/LG/LS 없음 | CPU i5-14400F, RAM 약16GB, GPU RTX5060 VRAM8151MiB. Llama 선택은 대표 결정 |
| B01 | 합성 안내문·DTO 평가셋·tokenizer 분할·멱등 청크·최종 입력 길이·사전 지표 등록 | `rag-runtime/.venv/Scripts/python.exe scripts/download_e5.py tokenizer`; `... scripts/build_synthetic_guides.py`; `... scripts/build_synthetic_eval.py`; `... scripts/inspect_rag_corpus.py`; `... -m pytest -q tests/rag/test_corpus.py` | **6 passed in 6.98s**. 안내문 **10개/603~666토큰**, 청크 **30개/최대293토큰**, 최종 질문 최대 **63토큰**. 비교 **20(근거14/무근거6)**, 확인 **10(근거6/무근거4)**. `1760db1` | 자료는 합성, tokenizer는 실제 고정 revision. HF_HUB_OFFLINE=1·Python socket 차단 시험 | 멱등성은 청크 집합 수준; 실제 SDK 재적재는 미검증 |
| B02a | 실제 memvid로 합성 1024차원 벡터 저장·검색·재오픈·차원 오류·Windows 동작 검증 | `rag-runtime/.venv/Scripts/python.exe scripts/probe_memvid.py` | **필수 11개 중10 pass / 1 fail**, exit **2**. 실패는 `metadata_return`. `60fdf3c` | SDK 실제, 벡터는 결정적 합성 단위 벡터. 실제 E5 임베딩 아님 | find hit에 구조화 metadata가 없음. SDK 다른 조회 API 가능성은 확인 불가. 인덱스 포인터 전환 미구현. 실패를 우회하지 않음 |
| B02b | **착수하지 않음** | 실행 없음 | 실제 E5 가중치 다운로드 **0**, 임베딩·평가 **0회**, 확인 세트 retrieval 적용 **0회** | 결과·Hit@3·혼동표를 만들어내지 않음 | B02a 필수 실패 해소 방침과 재착수 승인이 먼저 |

## 증거와 재계산

- [S0 환경](S0/env.txt), [하드웨어](S0/hardware.txt), [설치 후 기존95 전체 pytest 요약](S0/pytest.txt), [L02 추가 시험](S0/pytest_l02_contract.txt).
- [B01 원본에서 계산한 수치](B01/corpus_manifest.json), [사전 등록 규칙](B01/preregistered_rules.json), [시험 출력](B01/pytest.txt).
- [B02a 항목별 실제 출력](B02a/memvid_capabilities.json), [raw 실행 기록](B02a/probe.txt), [실패 해석과 한계](B02a/README.md).
- [미확인·다음 결정](OPEN_QUESTIONS.md).

개수는 `memvid_capabilities.json`의 `checks`에서 `pass` true/false 개수를 세어 재계산한다. 문서 길이·청크 수·평가 분포는 `scripts/inspect_rag_corpus.py`로 원본과 실제 tokenizer에서 재계산한다. 별도 시점에 실행한 95개·9개·6개를 한 번의 `110 passed` 출력으로 바꾸지 않는다. 원문 512초과 tokenizer 경고는 분할 전 원문 측정의 관찰이며 실제 모델 입력을 512초과로 실행한 기록이 아니다.

S0 env 기록의 초기 sandbox import는 응답이 늦었으나 세션 회수 시 exit0 및 정상 버전 출력을 반환했다. 별도의 외부 sandbox import 스모크도 정상 종료했다. env.txt의 ‘interrupted’ 메모는 초기 대기 시점 표현이며 최종 결과는 실패가 아니다.

## 보존·범위

모든 변경은 개발 브랜치의 로컬 커밋이다. push·main 병합·보존 브랜치 변경은 하지 않았다. 종료 직전 main은 `c92d5e6028b15954919c3a968866a0431fcfd3fc`, 보존 브랜치는 `e6df05018f6237e024feed1c4da2088dccd78304`로 유지된다. API 새 연결은 없고 RAG_ENABLED 기본값은 false다. 모델 캐시는 저장소 밖이며 모델·벡터 파일은 커밋하지 않았다. B03 이후·Llama·LangSmith 전송·실제 접수 데이터·유료 API는 실행하지 않았다.

당시 정지 이유: **조건 정지 — B02a 필수 metadata 반환 검증 실패.**

최신 정지 이유: **완료 — 승인된 B02a 우회 계약과 B02b 실제 E5 검색 평가까지 완료. B03 이후·실제 접수 연결은 미실행.**
