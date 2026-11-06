# RAG v1 무인 실행 종료 보고

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

정지 이유: **조건 정지 — B02a 필수 metadata 반환 검증 실패.**
