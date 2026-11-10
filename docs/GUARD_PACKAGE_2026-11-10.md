# C15b 보안 코어 검증 미러 패키지

2026-11-10 KST. C:\work\legal-intake-guard, feat/intake-guard-package.
C15의 단일 파일 독립성/재내보내기 충돌은 이번 미러 결정으로 해제했다.
정본 app/security/policy_core.py·marketing_core.py는 수정하지 않았다.

구현: 의존성 없는 intake-guard src 패키지, 공개 함수·타입·MASKING_VERSION,
정본과 바이트 동일한 두 미러, sync_intake_guard.py(--check 포함), SHA-256 강제 시험.
MASKING_VERSION legal-pii-2026-11-09-v1 → 패키지 2026.11.9.1.
sync가 정본만 읽고 미러·패키지 버전을 갱신한다. 미러 손 편집 금지.
연결: 기존 보안 환경에 로컬 editable 설치 완료. 앱 코어/어댑터 경로는 그대로다.
패키지 일반 설치 환경의 저장소 밖 import 시험 통과. 기존 -I -S 시험도 통과.

## 지정 보안 범위 시험

```powershell
C:\myLectureWs\legal-intake-fastapi-lab\.venv-security\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_policy_core_structure.py tests/test_policy_actions.py tests/test_marketing_actions.py tests/test_security_pipeline.py tests/test_session_security.py tests/test_l02_input_only_risk.py tests/test_nemo_integration.py tests/test_marketing_api.py tests/test_intake_guard_mirror.py packages/intake_guard/tests/test_intake_guard.py
```

**237 passed, 62 warnings in 19.09s**, 종료 코드 0. 기존 8개 파일 + 신규 2개 파일.
신규 시험 4개 포함. 저장소 전체 시험 통과라는 뜻은 아니다.
경고는 NeMo의 nim_url 필드 폐기 안내이며 시험을 수정하거나 skip하지 않았다.
RAG 시험은 요청대로 수집하지 않았다. 실제 모델 다운로드·LLM 호출 없음.
정본 두 파일 전후 SHA-256 동일. app/** 및 기존 시험의 diff 없음.

## 설치·동기화

```powershell
pip install -e packages/intake_guard
python scripts/sync_intake_guard.py --check
pip install "intake-guard @ git+https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab@feat/intake-guard-package#subdirectory=packages/intake_guard"
```

일반 main Git URL은 패키지가 main에 반영된 후에만 사용한다. 현재 브랜치 또는
검증 커밋으로 고정해야 한다. C16은 요청한 이 로컬 경로로 설치하면 된다.
편집 설치의 egg-info는 패키지 .gitignore로 제외했다.
사용 중인 정책은 제한된 규칙 검사이며 완전한 비식별화/의미 보안 보장은 아니다.
데이터 수정·main 병합·push 없음. 지정 작업 브랜치에만 push한다.
