# Codex 인수인계: 범위 축소 (2026-11-09 전달)

작성일 2026-11-07. 대상 저장소 `Ai-agent-orchestrator/legal-intake-fastapi-lab`.

## 1. 한 줄 요약

이 저장소의 필수 범위를 **기존 접수·안내 Python action + 보안 action 9개 + 법률 마케팅 강화**로 줄였습니다. LangChain·LangGraph·LangSmith·RAG·임베딩·벡터 검색·memvid·Llama는 **리서치 multi-agent 검색 도구 저장소에서 따로 완성**하므로 이 저장소에서는 더 이상 개발하지 않습니다.

## 2. 이미 바뀐 것

- 브랜치 `docs/readme-scope-security-marketing`에 `README.md`와 `README.en.md` 수정본을 push했습니다. `main`에는 아직 합쳐지지 않았습니다.
- 코드·폴더는 하나도 삭제하거나 옮기지 않았습니다. README만 바꿨습니다.
- README 변경 요지:
  - 필수 범위를 위 한 줄 요약대로 재정의했습니다.
  - 옛 RAG 절(필수 구성, 벡터 개념, 처리 흐름, 공부 자료 링크)을 삭제했습니다.
  - 새 7절 "RAG·검색 기능 분리"에 이전 후보 경로를 적었습니다.
  - 앱 API **최대 11개** 제한은 그대로입니다. 검색용 API는 추가하지 않습니다.

## 3. 월요일에 할 일 (순서대로)

1. **README PR 검토·병합.** 브랜치 `docs/readme-scope-security-marketing` → `main`. 내용이 실제 코드 상태와 맞는지 확인하고, 다르면 README를 먼저 고칩니다.
2. **보안 action 9개 현황 점검.** 아래 4절 표를 코드로 다시 확인해 README 2절 "보안 action 9개" 상태를 정확히 적습니다.
3. **남은 보안 action 구현·연결.** 입력 정책 → 개인정보 마스킹 → 출력 정책 → 용량·예산 action 래핑 순서를 권장합니다. 각 action마다 함수 단위 시험과 실제 NeMo rail 시험을 구분합니다.
4. **서비스 경계.** `용량 확보 → 예산 예약 → 호출 → 정산 → 슬롯 반환`. timeout·취소·실패에서도 정리를 보장하고 시험합니다.
5. **게시판·후기 → M01 요약 / M02 답변 초안.** 전체 출력 검사 후 `check_marketing_response`를 반드시 통과시키고, 최종 마스킹·문맥 확인 뒤에만 반환합니다. 자동 게시는 하지 않습니다.
6. **RAG 코드 이전은 리서치 저장소가 준비된 뒤에** 합니다(5절).

## 4. 보안 action 9개 현황 (2026-11-07, `app/` 검색 기준)

| action | 코드에서 확인한 상태 |
|---|---|
| `validate_request_context` | `app/security/session_actions.py`에 구현, `session_guard.py`에서 호출 |
| `check_session_risk` | 구현, 호출 확인 |
| `record_risk_event` | 구현, 호출 확인 |
| `check_generation_admission` | action 이름으로는 없음. `AdmissionManager`(`admission.py`)는 존재 |
| `check_request_budget` | action 이름으로는 없음. `BudgetStore`(`budget_store.py`)는 존재 |
| `check_input_policy` | `app/`에서 찾지 못함 |
| `mask_personal_data` | `app/`에서 찾지 못함 |
| `check_output_policy` | `app/`에서 찾지 못함 |
| `check_marketing_response` | `app/`에서 찾지 못함 |

주의: 이 표는 이름 검색 결과입니다. 이름이 다른 모듈에 구현돼 있을 수 있고, 시험 통과 여부는 확인하지 않았습니다. 작업 전에 직접 재확인하세요.

## 5. RAG 코드 이전 시 주의

- 이전 후보: `app/rag/`, `rag-runtime/`, RAG 관련 `scripts/`(E5·memvid·검색 평가), `fixtures/rag/`, `tests/rag/`, `tests/test_rag_b03_b05.py`, `docs/RAG_*.md`, `docs/CLAUDE_RAG_DESIGN_REVIEW.md`, `docs/EMBEDDING_RETRIEVAL_STUDY.md`, `docs/evidence/`.
- `app/rag` 바깥의 앱 코드(`app/main.py`, `services`, `security` 등)는 `app.rag`를 import하지 않는 것으로 확인했습니다. 삭제 전에 한 번 더 검색하세요.
- `tests/conftest.py`에 `rag_memvid`, `rag_lc` 마커 등록이 있습니다. RAG 시험을 옮길 때 같이 정리합니다.
- 이전 전에는 지우지 않습니다. 리서치 저장소에서 복사가 끝나고 검증된 뒤 이 저장소에서 제거합니다.
- `uv run pytest -q -m "not nemo"`가 이전 전후 모두 통과해야 합니다.
- 보안 action은 리서치 저장소에서 재사용할 수 있으므로, 이전하면서 경로를 깨지 않게 합니다. 재사용 모듈 분리는 로드맵의 ③ `python-memvid-guardrail` 단계입니다.

## 6. 지켜야 할 제약 (README 기준)

- 앱 API 최대 11개: 접수 3 + `/health` 1 + 게시글 3 + 후기 2 + AI 마케팅 2.
- 게시글 수정·삭제, 독립 Chat/SSE, 단독 guardrail API, 검색 API 추가 금지.
- 인증·인가, 자동 외부 게시, 일반 웹 검색, 운영 DB, Redis/Celery/Kafka 추가 금지. 기존 Java 서버·DB 수정 금지.
- 저장소 발전 순서 ① 현재 저장소 → ③ `python-memvid-guardrail` → ② `spring-fastapi-async-refactor`.
- `.env`는 커밋하지 않습니다. fake/mock 성공과 실제 공급자 호출 성공은 구분해 기록합니다.
- 보존 브랜치 `wip/codex-legal-snapshot`은 `main`에 합치지 않습니다. 그 안의 실패한 마케팅 검사 코드를 완료본으로 쓰지 않습니다.
- 완료 기준은 "구현·연결·시험 통과"입니다. 계획 문서나 샘플 실행 성공은 완료가 아닙니다.

## 7. 확인하지 않은 것

- 코드를 실행하거나 시험을 돌리지 않았습니다. README와 파일 구조, 이름 검색만 봤습니다.
- 리서치 multi-agent 저장소와 나머지 레포 2개(`python-memvid-guardrail`, `spring-fastapi-async-refactor`)는 아직 열어보지 않았습니다.
- 이전 후보 경로의 실제 파일 목록은 이전 시점에 다시 확인해야 합니다.
