# B01 — 합성 자료와 실제 tokenizer

실제 E5 tokenizer를 고정 revision으로 다운로드한 뒤 `HF_HUB_OFFLINE=1`과 새 시험의 Python socket 차단 하에 검증했다. **가중치·임베딩·검색은 아직 실행하지 않은 단계**다. `tokenizer_download.txt`는 모델 파일 수신 기록이고 자료 내용 업로드는 없다. Windows 캐시 symlink 경고는 보존했으며 캐시는 저장소 밖 `C:/myLectureWs/model-cache/huggingface`다.

- 원본: `fixtures/rag/guides.json`, `fixtures/rag/guides/G01.md`~`G10.md`, `fixtures/rag/evaluation.json`.
- 혼동 주제 쌍: 대여금/보증금, 환불/사기 의심, 이혼/상속. 모든 내용은 합성 학습 자료이며 법률적 판단 근거가 아니다.
- 원문 600~1,200토큰은 **원문 길이**다. tokenizer가 512 초과 경고를 내는 것은 예상된 관찰이다. 원문을 모델에 넣지 않고 제목 포함 최대 300토큰 청크로 분할한다. 제목·문단을 우선 보존하고 겹침 목표는 40토큰이다.
- metadata 13필드, 문서+버전+분할버전+위치+내용 해시의 청크 ID, 중복 문서 재입력 시 같은 청크 집합을 시험했다. 실제 memvid 재적재는 다음 단계에서 별도로 확인할 대상이다.
- 합성 PII 마스킹은 예제 전화/이메일 패턴에 한정된다. 운영 개인정보 처리의 완전성을 주장하지 않는다.
- 비교 20개와 확인 10개를 고정했다. 조회 전에 `preregistered_rules.json`으로 지표·임계값 선택 규칙·CPU/배치/시간 상한을 등록했다. 확인 세트 점수를 튜닝에 쓰지 않는다.

재현 명령(저장소 루트):

```powershell
$env:HF_HUB_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
$env:MEMVID_TELEMETRY='0'
.\rag-runtime\.venv\Scripts\python.exe scripts/inspect_rag_corpus.py
.\rag-runtime\.venv\Scripts\python.exe -m pytest -q tests/rag/test_corpus.py
```

`corpus_manifest.json` 수치는 원본과 tokenizer에서 다시 계산한다. 시험 결과는 `pytest.txt` 참조. 기존 안내 API는 연결하지 않았고 `RAG_ENABLED=false`다.

학습 포인트: 문서를 나눈 청크와 질문은 다음 단계에서 각각 1024개 숫자로 바뀐다. 벡터가 정규화됐다면 내적은 코사인 유사도다. 그 값은 문장 방향의 가까움을 나타내며 법적 정답 확률이 아니다. 이번에는 memvid 키워드 검색과 벡터 검색만 비교한다.
