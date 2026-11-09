# feat/marketing-actions 병합 준비 점검

2026-11-09 KST. 기록만 수행하며 main 병합·코드 수정·실패 시험 수정은 하지 않는다. 병합 여부는 대표가 결정한다.

점검 대상은 `feat/marketing-actions` / `6070a0bec803762b82dbbf7040a237773086a7a5`다. 원격 fetch 후 비교 대상 main은 `4a8c567`, 공통 조상은 `4207df6`이다. 이후 이 보고서만 대상 브랜치에 커밋·push한다.

## 구현·연결·시험 판정

| 확인 항목 | 구현·연결 확인 | 시험·점검 결과 | 판단·한계 |
|---|---|---|---|
| 보안 action 9개 | SessionRiskActions 3개, policy_registry 3개, resource registry 2개, marketing_registry 1개. 접수·안내·마케팅 경계에서 기존 서비스가 소비 | 지정 11개 파일 local **214 passed, 71 deselected in 2.62s**; 실제 NeMo 포함 **285 passed, 71 warnings in 19.99s** | 지정 보안·게시판 범위 통과. 실제 유료 공급자 검증은 아님 |
| 전체 앱 API | app.main:app은 create_full_app으로 기존 접수 3 + health 1 + 게시글 3 + 후기 2 + AI 마케팅 2를 조립 | tests/test_marketing_api.py의 정확한 11개 operation 집합 시험 통과 | README 4절의 경로·메서드와 일치. 문서에 없는 12번째 API 없음 |
| MVP 보존 | create_app은 접수 전용 3개 API. 과거 보강에서 초기화는 바뀌었지만 이번 점검은 수정 없음 | 기존 MVP 23개 포함 지정 시험 통과. 정확히 3개 경로 시험 통과 | 기존 시험 기대값·skip·삭제 변경 없음 |
| 저장·생성 경계 | 등록/조회/공급자 전송/최종 반환의 패턴 마스킹, 출력 검사 후 마케팅 REVIEW, 안전 M02 초안만 저장 | 지정 통합 시험에서 입력 차단·예산 차단·검사 장애·별점별 지침·저장 버전 경쟁 검사 통과 | 패턴의 완전성·광고 법률 적합성·실제 생성 품질을 보장하지 않음 |
| 대상 커밋의 전체 시험 | git ls-tree로 대상에 추적된 시험 파일 17개를 추출해 전부 실행. local 및 NeMo/RAG 사례 포함 | **316 passed, 1 failed, 73 warnings in 45.54s**, exit 1 | 전체 통과 아님. 아래 기존 Windows 실패를 유지 |
| README 상태·개수 | 11개 API, MVP 3개, action 9개 구현·연결, M01/M02 저장·검토 상태는 코드와 일치 | README의 196/267 통과 수는 이전 기록이며 현재 지정 결과 214/285보다 18개씩 적음 | 상태 표기는 부합하지만 최신 수치로 동기화할지 대표 검토 필요. 이번에는 README 수정하지 않음 |
| main과 문서 양쪽 변경 | 공통 조상 이후 양쪽에서 변경된 파일은 README.md와 README.en.md | main에는 연구 저장소 이름·마스킹 제안 등 후속 문서 변경이 있음 | 병합 시 최신 문서 취지와 브랜치의 구현 상태를 함께 보존해야 함. 실제 병합·충돌 해결은 미검증 |

## 저장소 전체 시험의 기존 실패

실패는 `tests/test_rag_b03_b05.py::test_serving_guard_blocks_tracing_even_when_env_enables_it` 1개다. armed_tracing fixture가 socket.socket.connect를 전역 차단한 상태에서 Windows Python 3.12 asyncio의 ProactorEventLoop가 내부 socketpair의 loopback 연결을 만들다가 `OSError: blocked`를 받는다. graph.ainvoke가 실행되기 전 loop 생성 단계에서 실패한다.

이 실패는 연구 저장소 R1에서도 같은 이름과 원인으로 재현됐다. 기대값 수정·skip·코드 수정을 하지 않았다. 73개 경고는 NeMo의 기존 nim_url deprecation 71개와 실패 이후 미await coroutine/loop 정리 경고 2개다. tokenizer의 장문 안내 경고는 tokenizer-only 검증 중 기록됐으며 실제 E5 모델 추론은 실행하지 않았다.

전체 로그는 저장소 밖 `C:\myLectureWs\tmp\legal_merge_readiness_pytest_2026-11-09.txt`에 보존했다. 이 로컬 로그는 커밋 대상이 아니며 docs/evidence를 새로 쓰거나 고치지 않았다.

## 변경 파일·비밀·개인정보 점검

비교 범위는 `git diff --name-only origin/main...feat/marketing-actions`의 62개 파일이다. 파일 이름은 모두 확인하고 `.env*`를 제외한 대상 파일의 현재 커밋 내용을 패턴 검색했다. `.env*` 내용은 Git show로도 열지 않았다. 탐지 값은 보고서에 복사하지 않는다.

| 분류 | 확인 내용 | 처리·한계 |
|---|---|---|
| 환경 파일 | 변경 목록에 `.env.example` 1개 있음. 대상 트리에는 ohgi-review-server/.env.example도 있으나 이 변경 목록에는 없음. 실제 `.env`는 추적 목록에서 발견되지 않음 | 이름만 확인. 내용 미검증이므로 환경 예시 파일에 비밀이 없다고 보증하지 않음 |
| 기존 작업의 금지 경로와 겹침 | 대상 변경에는 app/security/policy_core.py, app/security/marketing_core.py, docs/evidence/**가 포함됨 | 과거 보안·마케팅 구현 커밋의 변경이다. A2 또는 이번 L1에서 수정한 것이 아님. 금지 파일이 전혀 없는 변경 묶음이라고 표시하지 않음 |
| RAG 소스·런타임 | app/rag/**, rag-runtime/**, tests/rag/**는 대상 브랜치의 공통 조상 대비 변경 없음 | 작업 트리에 기존 rag-runtime/pyproject.toml·uv.lock 수정이 별도로 있음. 이번 기록·커밋에서 제외하고 보존 |
| 비밀 패턴 후보 | private key header·공급자/GitHub/AWS 형태 검색에서 후보 1개: tests/test_policy_actions.py:27 | 명시적인 합성 키 입력 차단 시험 문자열. 실키 근거 없음. 비밀 원문은 기록하지 않음 |
| 개인정보 패턴 후보 | 전화 14회, 주민번호 형태 8회, 이메일 17회 | 전화는 합성 예시 2종, 이메일은 example.com/.invalid 도메인. 주민번호 형태 6회는 기존 합성 예시이며 나머지 2회는 docs/evidence/B03/pytest_merge.txt:7,217의 contentHash 숫자 일부가 우연히 일치한 오탐 |
| 이름·주소 예시 | fixtures/masking_scope_v1.json의 version/label_note와 가상 이름·가상 주소 확인 | 합성 평가 자료로 표시됨. 자유문 속 모든 이름·주소·모든 비밀 형식의 부재를 이 패턴 검사만으로 증명하지 않음 |
| 과거 증거·환경 로그 | docs/evidence/B03 등의 환경·시험 로그가 대상 변경에 포함됨 | 로컬 경로·환경 metadata는 남아 있음. 이번 점검에서는 삭제·재작성하지 않음. 공개 범위의 최종 판단은 대표에게 있음 |

이번 점검에서 실제 비밀·실제 개인정보라는 근거는 발견하지 못했다. `.env*` 내용과 전체 Git 이력, 모든 가능한 비밀 형식은 검사하지 않았으므로 완전한 비밀 제거 인증으로 해석하지 않는다.

## 재현 범위와 환경

지정 보안·게시판 파일은 다음 11개다. A2의 미커밋 tests/test_full_app_routes.py는 대상 브랜치에 포함되지 않아 이번 통과 수에 넣지 않았다.

```powershell
$securityTests = @(
  'tests/test_mvp.py', 'tests/test_session_security.py',
  'tests/test_nemo_integration.py', 'tests/test_l02_input_only_risk.py',
  'tests/test_policy_actions.py', 'tests/test_policy_core_structure.py',
  'tests/test_security_pipeline.py', 'tests/test_paid_call_service.py',
  'tests/test_usage_accounting.py', 'tests/test_marketing_actions.py',
  'tests/test_marketing_api.py'
)
$env:PYTHONDONTWRITEBYTECODE='1'
# 214 passed, 71 deselected
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests -m 'not nemo'
# 285 passed, 71 warnings
.\security-runtime\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @securityTests

# 대상 커밋의 추적된 전체 시험 17개 파일: 316 passed, 1 failed
$taskTests = @(git ls-tree -r --name-only 6070a0b -- tests |
  Where-Object { $_ -match '/test_[^/]+\.py$' })
$env:MEMVID_TELEMETRY='0'
$env:HF_HUB_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
$env:TRANSFORMERS_OFFLINE='1'
foreach ($taskKey in @('OPENAI_API_KEY','MEMVID_API_KEY','LANGSMITH_API_KEY','LANGCHAIN_API_KEY','LANGSMITH_TRACING','LANGCHAIN_TRACING_V2')) {
  Remove-Item -LiteralPath "Env:$taskKey" -ErrorAction SilentlyContinue
}
.\rag-runtime\.venv\Scripts\python.exe -m pytest -q -rA --tb=short -p no:cacheprovider @taskTests
```

지정 local 시험은 Python 3.14, NeMo 및 전체 시험은 Python 3.12.10의 기존 환경을 사용했다. 전체 시험 환경은 pytest 9.2.0, memvid-sdk 2.0.160, transformers 5.22.1, NeMo 0.24.1, langchain-core 1.7.6, langgraph 1.2.20, langsmith 0.14.17이다. runtime 의존성 파일에 기존 미커밋 변경이 있으므로 PC의 설치된 환경에서 나온 결과이며, 깨끗한 lock으로 재구축한 결과는 아니다.

실행은 기존 Windows Temp·Python 접근 제한 때문에 승인된 권한에서 수행했다. 키 값은 읽거나 출력하지 않고 실행 프로세스에서 제거했다. 시험은 `_env_file=None`, fake/mock 공급자, 로컬 합성 데이터와 캐시 tokenizer를 사용했다. tracing 시험의 fake endpoint 127.0.0.1:9에 대한 background 접속 거절 로그가 있으므로 네트워크 시도 0회라고 주장하지 않는다. 실제 외부 공급자·외부 게시·모델 다운로드는 수행하지 않았다.

## 대표 판단 전 남은 항목

- 알려진 Windows 전체 시험 실패의 처리 방침.
- README 최신 통과 수와 main의 후속 문서 변경을 병합 시 어떻게 반영할지.
- 내용 미열람인 환경 예시 파일과 과거 환경 로그의 최종 공개 범위.
- A2 별도 팩터리·49개 신규 시험은 아직 로컬 네 파일이며 feat/marketing-actions 커밋에는 없음. 이 점검의 285/316 집계에 섞지 않음.

이번 L1의 구현·연결 변경은 없고 보고서만 추가한다. main 병합·저장소 전체 통과·실제 운영 검증으로 표시하지 않는다.
