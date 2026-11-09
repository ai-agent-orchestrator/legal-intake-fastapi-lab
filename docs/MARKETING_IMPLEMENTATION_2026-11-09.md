# 마케팅 action·11개 API 연결과 마스킹 범위 평가

2026-11-09 KST · 개발 브랜치 `feat/marketing-actions` · main 병합은 대표가 수행한다.

## 항목별 결과

| 요청 | 구현 | 연결 | 시험·측정 | 한계·미검증 |
|---|---|---|---|---|
| A1 마케팅 검사 | 독립 `marketing_core.py`와 얇은 `marketing_actions.py` | 9번째 action으로 registry/NeMo 연결 | 단독 local 26 passed, 실제 NeMo 포함 29 passed | 문서의 보장 표현 3개만. 광고 법령 적합성 자동 판정 아님 |
| A2 게시판·후기/M01/M02 | 표준 라이브러리 BoardStore, DTO·라우터·서비스 | 실행 앱 `app.main:app`은 정확히 11개 HTTP operation | 기존 local 153 → **196 passed, 71 deselected**; 실제 NeMo 포함 기존 211 → **267 passed, 71 warnings** | fake 생성·SDK mock 검증. 실제 유료 호출·실제 생성 품질 미검증 |
| A3 마스킹 범위 확대 검토 | 앱 밖의 버전 표시 실험 후보와 합성 정답 24개 | 운영 정책에는 연결하지 않음 | 유형별 기존 규칙 FP 0/FN 4, 실험 후보 FP 2/FN 2 | 이름·자유 주소·사건번호 자동 익명화로 표시하지 않음 |
| A4 정책 코어 분리 준비 | AST stdlib import 검사·파일만 복사한 `python -I -S` 단독 실행 | 새 구조 시험 파일로 고정 | 위 단독 29개 중 구조 시험 4개 통과 | 설치 패키지 추출 O4는 미실행 |

통과 수는 보안·게시판 범위다. RAG 코드·시험·의존성은 수정하지 않았고, `tests/rag/`와 `tests/test_rag_b03_b05.py`는 실행하지 않았다. 기존 RAG 오류를 해결했다거나 저장소 전체가 통과했다고 표시하지 않는다.

## 규칙의 출처와 열린 질문

규칙 묶음 `marketing-guarantees-2026-11-09-v1`은 `LEGAL_MARKETING_BOARD.md`의 세 표현만 대상으로 한다.

| ID | 문서의 표현 |
|---|---|
| `WIN_100_PERCENT` | `100% 승소 보장` |
| `UNCONDITIONAL_WIN` | `무조건 승소` |
| `COMPENSATION_PROMISE` | `반드시 보상받습니다` |

Unicode/공백 정규화는 탐지 뷰에만 적용한다. 직접 부정하는 문구와 인용 표현을 명시적으로 사용하지 않겠다는 문구는 정상 문맥으로 다룬다. 인용 부호만으로 허용하지 않으며, 다른 문장의 부정문이 뒤의 보장 표현을 면제하지 않는다. 위험 표현이 있으면 해당 문장 전체를 제외한 `safeDraft`와 REVIEW를 반환한다. 안전 문장이 남지 않으면 검토 안내문을 반환한다. 검사기 예외는 503으로 중단하고 미검사 본문을 반환·저장하지 않는다. 검토 판정은 사용자 공격 점수를 올리지 않는다.

열린 질문: 변호사법 위반 소지의 구체적 문구·조건, 다른 과장 표현·변형 표현, 비교/우월 표현, 개별 비용/보상 약속의 허용 기준은 문서에 없다. 담당자의 규칙과 사례 확정 전에는 추가 탐지 규칙을 만들지 않는다. 현재 패턴의 부정·인용 처리도 일반 자연어 이해를 보장하지 않는다.

## 앱 조립과 API

사용자가 승인한 구성으로 기존 `create_app(settings)`는 접수 3개 API 팩터리를 보존한다. `create_full_app(settings)`가 게시판 7개와 health 1개를 더하며, `app.main:app`은 이 전체 앱이다. 기존 “경로 3개” 회귀 시험은 수정하지 않았다. 새 앱의 정확한 11개 operation은 새 통합 시험에서 고정한다.

```powershell
# 전체 앱: 접수 3 + health 1 + 게시글 3 + 후기 2 + AI 마케팅 2
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8012
# 기존 MVP만 필요할 때
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8012
```

등록·조회는 마스킹된 데이터만 저장·반환한다. 작성자는 공개 별칭이며 생성 프롬프트에는 별칭도 넣지 않는다. M01은 저장 게시글/후기의 요약과 개선 주제, M02는 저장 후기의 답변 초안이다. 모든 별점에서 같은 보안 경계를 수행한다. 1~2는 사과·공감, 3은 공감·개선, 4~5는 감사 지침을 서버가 공급자에 전달한다. fake 생성이 실제 모델의 말투 품질을 검증한 것은 아니다.

생성 경계는 문맥·세션·입력 정책·마스킹 → 용량 확보 → 예산 예약 → 호출 → 정산·슬롯 반환 → 전체 출력 검사 → **마케팅 검사 → 최종 마스킹 → 문맥 확인**이다. 기존 PaidCallService의 실패·취소·timeout 정리를 재사용한다. 입력이 canonical 상한을 넘으면 자르지 않고 생성 전에 중단한다.

M02는 안전 초안만 저장하고 후기 목록의 `replyDraft`에 노출한다. 생성 전에는 null이고 생성 후 `text`, `reviewRequired`, `reasonCode`, `matchedRules`, `generatedAt`, `policyVersion`, `ruleVersion`, `sourceVersion`, `model`, `version`, `status=DRAFT`를 반환한다. M01 생성 중 새 후기가 추가돼 원본 snapshot이 바뀌거나 M02 동시 재생성 결과가 이미 저장된 새 초안을 덮으려 하면 409로 거절한다. 게시글 수정·삭제·승인 API는 추가하지 않는다. 저장된 초안은 공개 게시가 아니며 ALLOW도 자동 외부 게시하지 않는다. 인증·인가가 없는 합성 학습용 API이고 실제 자료를 받는 운영 기능이 아니다.

BoardStore는 표준 라이브러리만 쓰는 독립 파일이다. 메모리 데이터는 재시작하면 사라진다. 게시글 1000개·후기 5000개까지 유지하며 꽉 차면 503으로 중단한다. 예산 영속화·날짜 리셋은 추가하지 않았다.

## 합성 마스킹 실측

`fixtures/masking_scope_v1.json`: 이름·주소·사건번호 각각 양성 4, 음성 4로 총 24개. 공개 형식 예시와 안내 문구를 비민감 대조군으로 정한 **임시 합성 정답**이며 실제 적용 정책 승인이 아니다. span의 유형·시작·끝이 일치할 때 TP다.

| 유형 | 현재 canonical TP / FP / FN | 후보 v1 TP / FP / FN |
|---|---|---|
| 이름 | 0 / 0 / 4 | 2 / 2 / 2 |
| 자유 형식 주소 | 0 / 0 / 4 | 2 / 2 / 2 |
| 사건번호 | 0 / 0 / 4 | 2 / 2 / 2 |

후보는 이름/주소 라벨이 붙은 입력과 일부 사건번호 형식만 찾는다. 일반 문구도 가리거나 라벨 없는 자유문을 놓친다. `experiments/masking_scope_v1.py`의 세 규칙 묶음은 버전이 있으나 앱이 import하지 않는다. 현재 canonical 마스킹 동작은 바꾸지 않았다.

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_masking_scope.py
```

[기계 판독 결과](evidence/MARKETING_2026-11-09/masking_scope.json)

## 시험 재현과 미검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --ignore=tests/rag --ignore=tests/test_rag_b03_b05.py -m 'not nemo'
.\security-runtime\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --ignore=tests/rag --ignore=tests/test_rag_b03_b05.py
```

[실제 NeMo 포함 최종 로그](evidence/MARKETING_2026-11-09/pytest_nemo.txt): **267 passed, 71 warnings in 23.38s**. 경고는 NeMo `nim_url` deprecation이다. 단독 local 첫 실행에서 구조 시험 2개가 Windows Temp 권한 때문에 setup 오류였으나 시험 변경 없이 승인된 권한으로 같은 시험을 실행해 26개 모두 통과했다.

합성 정상/위반·부정/인용·혼합 문장, 검사 장애, 저장/입력/출력 PII, 별점 1~5 및 범위/타입 오류, 예산/없는 ID의 공급자 호출 0회, 원본 snapshot 변경, 동시 답글 저장 충돌, 기존 취소/timeout/예산 경쟁·문맥 격리 회귀를 검증했다. 실제 OpenAI 유료 호출·실모델 품질·외부 게시·실제 자료·멀티 worker·운영 DB는 미검증/범위 밖이다.

## 연구 저장소 중단

연구 `origin`을 대표가 지정한 새 URL `https://github.com/ai-agent-orchestrator/langchain-rag-research-agent.git`로 변경했다. `feat/m0-skeleton`에서 변경 전 전체 시험이 51 passed / 1 failed였다. Windows asyncio 내부 loopback 생성이 시험의 전역 소켓 차단에 막혀, 지시대로 시험을 고치지 않고 M0 구현을 시작하기 전에 중단했다. 연구 패키지 이름 변경·P0 골격·M1/M5는 미실행이다. 자세한 원인은 연구 저장소 `docs/M0_BASELINE_BLOCKER_2026-11-09.md`에 기록한다.
