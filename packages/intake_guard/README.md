# intake-guard

표준 라이브러리만 사용하는 입력·마스킹·출력·문구 정책의 설치 가능한 미러입니다.
정본은 저장소의 `app/security/policy_core.py`, `marketing_core.py`입니다.
패키지 미러를 손으로 수정하지 마세요.

```powershell
pip install -e packages/intake_guard
python scripts/sync_intake_guard.py
python scripts/sync_intake_guard.py --check
```

배포된 브랜치/태그에 패키지가 있을 때 Git 설치:

```powershell
pip install "intake-guard @ git+https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab@feat/intake-guard-package#subdirectory=packages/intake_guard"
```

main에 패키지가 반영된 뒤에는 `@feat/intake-guard-package`를 생략할 수 있습니다.
프로젝트에서 사용 중인 버전/커밋을 고정하세요.

```python
from intake_guard import check_input_policy, mask_personal_data
decision = check_input_policy("계약서 상담 자료", profile="research")
masked = mask_personal_data("연락처 synthetic@example.invalid")
```

마스킹 결과가 ALLOW이면 safe_text가 None이므로 입력을 유지하고, TRANSFORM이면
safe_text를 사용합니다. 규칙 기반 검사이며 완전한 익명화·의미 판정을 보장하지 않습니다.
패키지 버전은 `legal-pii-YYYY-MM-DD-vN`을 `YYYY.M.D.N`으로 변환합니다.
MASKING_VERSION을 바꾸면 sync가 패키지 버전도 맞춥니다. SHA-256 시험이 정본/미러
바이트 동일성을 강제하며 기존 단일 파일 시험은 그대로 유지합니다.
