# B02a — 조건 정지: metadata 검증 실패

2026-11-06 · 실제 Windows memvid-sdk 2.0.160 · **필수 11항목 중 10 pass / 1 fail**

`probe.txt`는 실제 실행 출력이다. `memvid_capabilities.json`의 `checks`에서 개수를 다시 계산할 수 있다. 반환값은 합성 문구와 점수만 포함하며 실제 벡터 배열은 증거에 저장하지 않았다.

| 항목 | 실제 관찰 |
|---|---|
| 외부 1024차원 벡터 저장 | 합성 단위 벡터 3개 저장 성공 |
| query 벡터 검색 / lex 검색 | 명시적 sem / lex 호출 모두 결과 반환 |
| metadata 반환 | **실패:** 검색 hit에 `metadata` 필드 없음. documentId·chunkId가 text/snippet 문자열에만 포함됨 |
| query / 저장 벡터 차원 오류 거절 | 1023차원에 VecDimensionMismatchError, expected 1024 |
| 점수 방향 | 일치 / 직교 / 반대 벡터 순서. 점수 1.0 / 0.2928932309150696 / 0.0. 이 점수는 코사인 원값 1 / 0 / -1과 다르므로 코사인이라고 표시하지 않음 |
| 재오픈 | frame_id·제목·점수 동일 |
| Windows 열린 파일 교체 | PermissionError, winerror 5 |
| Windows 열린 파일 삭제 | 이번 read_only 핸들에서는 허용됨. 항상 거절된다고 가정하면 안 됨 |
| 없는 인덱스 | FileNotFoundError, 대체 저장소나 가짜 검색으로 전환하지 않음 |

**이 실패는 현재 probe의 `find()` 구조화 metadata 계약을 확인하지 못했다는 뜻이다. SDK 전체에 metadata 조회 기능이 없다고 단정하지 않는다.** 별도 frame 조회나 다른 공식 API 조합이 가능한지는 확인 불가로 남긴다. 문자열을 임의 파싱하거나 sidecar로 대신해 통과 처리하지 않았다.

sem을 명시했는데 응답의 engine 라벨은 `hybrid`였다. 라벨만으로 실제 혼합 검색을 했다고 단정할 수 없으며, B02b의 순수 벡터 대 lex 비교에 쓰기 전 확인이 필요하다.

조건 정지로 버전 인덱스+`active.json` 포인터 전환, 실제 memvid 재적재 멱등성, 실제 E5 검색은 구현·완료로 표시하지 않는다. E5 가중치 다운로드·B02b 평가·확인 세트 실행은 하지 않았다. B03 이후로 넘어가지 않았다.

실행 명령:

```powershell
.\rag-runtime\.venv\Scripts\python.exe scripts/probe_memvid.py
# 실제 종료 코드: 2 (allMandatoryPassed=false)
```

probe는 Python 소켓/DNS를 차단하고 MEMVID_TELEMETRY=0, HF_HUB_OFFLINE=1을 설정했다. Python socket 차단이 Rust 내부의 모든 네트워크 syscall을 운영체제 수준에서 차단한 증거라는 뜻은 아니다. 이번 호출에는 원격 모델·키·원격 동기화를 사용하지 않았다.
