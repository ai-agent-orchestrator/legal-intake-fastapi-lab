# 조건 정지 후 결정할 사항

## Q1 — 구조화 metadata 반환 계약

B02a 실제 `find(mode='sem', query_embedding=...)` hit에는 metadata dict가 없고, 저장한 documentId·chunkId가 본문/스니펫 문자열에만 포함됐다. 필수 검증이 실패했으므로 현재 실행은 정지했다.

다음 착수 전에 결정: 공식 SDK의 별도 frame/문서 조회로 구조화 metadata를 회수하는 어댑터가 이 계약을 만족하는지 검수할 것. 그 API의 실제 지원·원본 contentHash 보존·재오픈 일치 여부는 **확인 불가**다. SDK 교체, metadata 문자열 파싱, sidecar를 통한 조용한 대체는 하지 않았다. 재착수 승인 전 이 결정을 적용하지 않는다.

## Q2 — sem 결과의 점수와 engine 라벨

동일/직교/반대 합성 단위 벡터의 점수는 1.0 / 0.2928932309150696 / 0.0이며 코사인 원값이 아니다. `mode='sem'` 결과의 engine 라벨은 `hybrid`였다. 순수 벡터 동작과 점수 의미를 공식 소스/SDK로 확인한 다음 B02b 사전 등록 규칙에 어떤 점수를 사용할지 정해야 한다. 현재는 해석을 확정하지 않았다.

## Q3 — 미실행 사항

- 버전 인덱스 및 active.json 원자 포인터 전환, SDK 재적재 멱등성은 B02a 조건 정지로 미실행이다.
- 실제 E5 가중치·encode 시간·실제 벡터 품질·Hit@3·무근거 혼동표는 미실행이다. 확인 세트는 retrieval 평가에 사용하지 않았다.
- Llama 모델은 미선정·미설치. S0 사양: i5-14400F, RAM 약 16GB, RTX 5060 VRAM 8151MiB. 대표가 이후 결정한다.
- LangChain·LangGraph·LangSmith, 보안 S1~S3의 실제 접수 연결, B03 이후는 이번 범위 밖이다.
