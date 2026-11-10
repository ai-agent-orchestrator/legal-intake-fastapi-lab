# C15 보안 코어 패키지 분리 차단 보고서

2026-11-10 KST. 요청한 새 클론 C:\work\legal-intake-guard,
기준 main 98af86e, 브랜치 feat/intake-guard-package.
기존 legal-intake 작업 폴더와 미커밋 RAG 변경은 건드리지 않았다.

## 구현·연결

패키지 추출 및 호환 파일 변경은 미착수. 이 보고서만 커밋한다.
기존 구조 시험과 명세가 충돌한다:

- tests/test_policy_core_structure.py의 test_core_only_imports_standard_library는
  app/security의 두 코어에 표준 라이브러리 외 import 및 상대 import를 금지한다.
- test_core_file_imports_with_site_packages_and_app_unavailable는 코어 한 파일만
  tmp_path에 복사하고 Python -I -S에서 실행한다. 주변 app, 설치 패키지,
  packages/intake_guard/src는 그 고립된 실행에 존재하지 않는다.
- C15는 두 코어를 intake_guard 재내보내기 파일로 바꾸면서 기존 시험 기대값은
  수정하지 말라고 한다. 얇은 재내보내기는 위 두 계약을 함께 만족할 수 없다.

동적 import로 AST 검사를 우회하거나 코어 구현을 양쪽에 복사하지 않았다.
제안: 별도 승인 범위에서 한 파일 독립성 시험을 패키지 독립성 시험으로 변경한 뒤,
코어 바이트를 그대로 이동하고 공개 API/호환 경로의 동일 객체를 검증한다.
이는 현재 명세의 기존 시험 불변 범위를 넘으므로 적용하지 않았다.

## 전체 시험

기존 보안 전용 환경으로 새 클론에서 실행:

```powershell
C:\myLectureWs\legal-intake-fastapi-lab\.venv-security\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

결과: **0 passed, 1 collection error in 3.95s**, 종료 코드 2.
tests/test_rag_b03_b05.py:8에서 langchain_core 부재로 수집 중단.
보안 시험 및 패키지 시험 통과로 주장하지 않는다. 패키지 시험은 미구현.
환경 의존성 설치·시험 수정·재시험 없이 원인을 기록하고 다음 명세로 진행한다.

## 다음 단계

C16의 전제인 설치 가능한 intake-guard 패키지는 이번 브랜치에서 만들지 못했다.
단독 import 및 git URL 설치도 검증하지 않았다. 따라서 C16은 전제 없음으로 보고해야 한다.
추후 추출 승인 시 설치 안내는 pip install -e packages/intake_guard와
git+https://github.com/ai-agent-orchestrator/legal-intake-fastapi-lab#subdirectory=packages/intake_guard이며,
MASKING_VERSION 변경 시 패키지 버전도 올리는 규칙을 채택할 수 있다.
현재는 해당 패키지 경로가 없으므로 위 설치 명령을 실행하지 않았다.

app 코어·기존 시험·데이터·RAG 경로 변경 없음. 모델 다운로드·Kiwi 설치·LLM 호출 없음.
main 병합·push 없음. 보고서만 요청한 브랜치에 push한다.
