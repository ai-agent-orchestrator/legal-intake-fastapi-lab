# B03 연결 착수 — 1단계 전체 시험 실패로 정지

2026-11-06 KST 18:24 착수 확인, 18:52 실패 원인·보호 대상 확인. **사용자의 ‘전체 pytest 실패 시 원인만 기록하고 2번으로 넘어가지 말 것’ 지시에 따라 검색→그래프 어댑터는 구현하지 않았다.** 이 문서는 완료 보고가 아닌 착수 차단 증거다.

## Git 준비와 병합 상태

- 시작 시 작업 폴더 깨끗함. 실제 HEAD는 `f6c0c9c`이며 지시서의 `f7f58ba` 이후 README 충돌 해결 커밋이었다.
- `git fetch origin` 후 main은 `144da7d`(PR #1 병합). 기존 B03~B05 뼈대 `06f2d28`과 README `efa3ff2`는 현재 코드에 이미 포함돼 있다.
- `git merge --no-ff --no-commit origin/main`은 충돌 없이 병합 대기 상태가 됐다. 전체 시험 통과 전에 merge 커밋을 만들지 않았다.
- 시험 실패 후 `git merge --quit`으로 병합 대기 메타데이터만 해제했다. reset·checkout·stash·force는 사용하지 않았다. 숫자·증거·기존 코드의 충돌 해결 변경도 없었다.
- 실패 원인과 시험 로그만 문서 커밋한다. 준비한 `rag-runtime/pyproject.toml`, `rag-runtime/uv.lock` 변경은 **미커밋으로 남긴다**. 2단계 어댑터·신규 통합 시험은 미작성이다.

## 환경 준비

기존 Python 3.12 `rag-runtime`에는 LangChain 계열이 없어 B03 뼈대 시험에 필요한 패키지만 lock에 추가하고 frozen sync했다.

```powershell
uv add --project rag-runtime --no-sync --cache-dir .uv-cache langchain-core langgraph langsmith
uv sync --project rag-runtime --frozen --cache-dir .uv-cache
```

추가된 직접 패키지는 langchain-core 1.7.6, langgraph 1.2.20, langsmith 0.14.17이다. 전이 의존성 포함 17개가 추가됐고 **기존 122개 패키지 버전 변경은 0개**였다. 설치는 했으나 전체 시험 실패로 환경 변경을 완료본으로 커밋하지 않는다. 세부 목록은 `new_packages.json`, 설치 출력은 `dependency_install.txt`에 있다. 기존 security-runtime 환경은 변경하지 않았다.

## 전체 시험 결과

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_ADDOPTS='-p no:cacheprovider'
$env:HF_HUB_OFFLINE='1'
$env:MEMVID_TELEMETRY='0'
$env:LANGSMITH_TRACING='false'
.\rag-runtime\.venv\Scripts\python.exe -m pytest -q
```

```text
2 failed, 134 passed, 36 warnings in 14.12s
```

| 실패 시험 | 저장된 traceback으로 확인한 원인 | 판정·미확인 |
|---|---|---|
| `tests/rag/test_index.py::test_native_thirty_chunks_reopen_and_every_self_top1_before_activation` | 실제 memvid `put_many`에서 `MV999: Tantivy error`, Windows `os error 5` 접근 거부. `app/rag/index.py`가 `RetrievalUnavailable`로 올림 | 저장 도중 실패이며 활성화 완료가 아님. OS 권한·임시 경로·파일 잠금·보안 프로그램 중 근본 원인은 확인 불가. 이번 실행에서 임의 재시도·수정하지 않음 |
| `tests/test_rag_b03_b05.py::test_serving_guard_blocks_tracing_even_when_env_enables_it` | `asyncio.run`이 Windows ProactorEventLoop를 초기화하면서 `socket.socketpair → _fallback_socketpair → csock.connect(127.0.0.1, 임시포트)` 호출. `armed_tracing`의 전역 socket.connect 차단이 이를 가로막아 `OSError: blocked` | graph 실행 전 이벤트 루프 초기화 실패. 이 실패를 LangSmith 원격 전송 발생이나 serving guard 자체의 실패로 단정하지 않음. 해당 guard 검증은 통과로 표시하지 않음 |

로그 끝에는 대조군이 사용한 `http://127.0.0.1:9`의 LangSmith `/info` 접속 실패 경고도 있다. 실제 원격 LangSmith endpoint를 사용한 성공 기록이 아니며, 가짜 client가 fixture 종료 후 실행하는 background 작업까지 어떻게 차단·회수할지 검토가 필요하다. 대조군이 있는 기존 시험 기대값을 고치거나 skip하지 않았다.

전체 traceback은 `pytest_merge.txt`에 보존했다. 합성 벡터 배열은 증거 공개 규칙에 따라 표시를 지웠다. 가공 전 원문은 Git 제외 경로 `data/B03/pytest_merge.raw.txt`에 남겼으며 원문 SHA256은 `verification.json`에 기록했다. 실패 이름·예외·요약 숫자는 바꾸지 않았다.

## 보호 대상과 하지 않은 것

- B01/B02a/B02b 증거, 합성 fixture, E5 고정 모델 설정 **52개 Git blob 변경 0개**. `baseline_environment.json`, `verification.json` 참조.
- E5 재인코딩 0, 확인10 재검색 0, 임계값 변경 0. 전체 시험의 memvid 입력은 신규 합성 벡터이며 실제 E5 확인셋 검색이 아니다.
- 실제 Llama/Qwen 생성·유료 API·실제 접수·의뢰인 자료·새 API endpoint 연결 없음.
- main·보존 브랜치 수정 없음. main 직접 push/merge 없음.
- 전체 시험은 통과하지 않았으며, merge 완료·검색→그래프 연결 완료·합성 PII 통합 검증 완료라고 표시하지 않는다.

## 다음 단계 — 별도 진행 결정 후

1. memvid Windows 임시 경로·파일 잠금·접근 거부를 분리 재현한다.
2. asyncio 내부 loopback 초기화와 원격 tracing 차단을 구분하고 background client까지 회수하는 시험 경계를 검토한다.
3. 전체 회귀 통과 후에만 main merge 커밋 → 얇은 어댑터 → 통합 시험 순서로 재개한다.

정지 이유: **1단계 전체 시험 실패 — 사용자 지시에 따라 2단계 미착수.**
