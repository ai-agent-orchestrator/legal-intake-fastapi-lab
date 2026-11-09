# check_marketing_response — 한정 범위 구현·검증

2026-11-09 KST. 이번 작업은 마케팅 코어·어댑터·해당 시험·이 문서와 추가로 허용받은 루트 `REPORT.md`에만 한정한다. 작업 시작점은 `85380ef`이며 마케팅 코어와 게시판 앱 조립은 이 커밋에 이미 존재했다. 이번에는 기존 마케팅 코어 계약을 확인하고 예외/잘못된 반환값 차단과 명시적인 멱등·단독 import 검증을 보강했다. 이전 작업의 API 구현을 이번 작업에서 새로 연결한 것으로 보고하지 않는다.

## 구현·연결·시험 상태

| 구분 | 결과 |
|---|---|
| 독립 코어 | `marketing_core.py`는 표준 라이브러리만 import. 다른 app·FastAPI·NeMo 모듈을 import하지 않음 |
| 얇은 앱 어댑터 | `marketing_actions.check_marketing_response(Envelope)`가 코어 결과를 `ActionDecision`으로 변환 |
| 등록 | `marketing_registry()`가 action 이름과 함수의 dict를 반환. 기존 `policy_registry()`와 같은 등록 방식 |
| NeMo 연결 | 명시적으로 만든 registry와 실제 output rail의 ALLOW/REVIEW 소비·장애 중단 시험 통과 |
| 앱·M01/M02 연결 | 이번 작업에서는 변경하지 않음. 앱 팩터리·라우터·API는 작업 범위 밖 |
| local 지정 회귀 | **193 passed, 61 deselected in 2.09s** |
| 실제 NeMo 포함 지정 회귀 | **254 passed, 61 warnings in 11.69s** |

local 수치는 기존 8개 파일 **153 passed** + 마케팅 파일 **40 passed** = **193 passed**다. 마케팅 파일의 local 40개 중 22개는 작업 시작점에 이미 있었고 이번에는 18개를 추가했다. 기존 시험 기대값·skip·삭제 변경은 없다. 실제 NeMo 환경에서는 기존 211개 + 마케팅 43개 = 254개다. 각 집계는 포함 관계이므로 합산하지 않는다. 61개 경고는 NeMo의 `nim_url` deprecation이다.

**지정한 9개 파일의 회귀 결과이며 저장소 전체 시험 통과가 아니다.** 다른 마케팅 API 시험이나 RAG 시험을 이 수치에 포함하지 않는다.

## 규칙의 근거

근거는 `docs/LEGAL_MARKETING_BOARD.md`의 `check_marketing_response` 절과 README의 마케팅 강화 절이다. 그 밖의 문서·법령·다른 코드에서 마케팅 금지 규칙을 가져오지 않았다. 규칙 묶음은 기존 `marketing-guarantees-2026-11-09-v1`을 유지한다. 탐지 규칙은 추가·변경하지 않았다.

| 규칙 ID | 문서의 표현 / 합성 위반 | 합성 정상 문맥 |
|---|---|---|
| `WIN_100_PERCENT` | `100% 승소 보장!` | `100% 승소 보장하지 않습니다.` |
| `UNCONDITIONAL_WIN` | `무조건 승소합니다.` | `무조건 승소를 보장하지 않습니다.` |
| `COMPENSATION_PROMISE` | `반드시 보상받습니다.` | `‘반드시 보상받습니다’라는 표현은 사용하지 않습니다.` |

세 규칙 모두 정상·위반 시험이 있다. Unicode/공백 정규화는 탐지 뷰에서 수행한다. 직접 부정과 해당 인용 표현을 명시적으로 배제하는 문맥은 허용하지만, 인용 부호 자체로는 면제하지 않는다. 전체 출력의 뒤쪽 위반과 정상 부정문/보장 표현이 한 문장에 섞인 사례도 검사한다.

문서가 정한 위반 처리는 `REVIEW`, `reviewRequired=true`, `MARKETING_REVIEW_REQUIRED`, 규칙 ID와 안전 초안이다. **위반 원문을 그대로 반환하는 것을 막고 위험 문장 전체를 제외**한다. 이 작업에서 임의의 `BLOCK` 정책으로 바꾸지 않았다. 안전 문장이 남지 않으면 검토 안내문을 반환한다. 검토 판정은 공격 점수 적립이나 자동 외부 게시를 뜻하지 않는다.

## 오류 시 반환 중단

* 코어의 잘못된 입력은 `MarketingError`이고 어댑터는 `MARKETING_CHECK_UNAVAILABLE` 기술 오류로 바꾼다.
* 예상하지 못한 검사기 예외는 직접 어댑터 호출에서도 `GUARDRAIL_UNAVAILABLE`로 정규화하며 예외 메시지의 원문을 전달하지 않는다. 기존 NeMo 장애 사유 계약과 같다.
* 코어가 None/dict를 반환하거나, ALLOW가 본문을 바꾸거나, REVIEW가 원문을 그대로 두거나, 검토 플래그·사유·버전·규칙 ID·안전 본문 형식이 일치하지 않으면 `GUARDRAIL_INVALID_DECISION`으로 중단한다.
* 오류 경로에는 안전 초안으로 가장한 원문 fallback이 없다. 기존 어댑터/rail 장애 시험과 새 직접 호출·잘못된 반환값 시험으로 확인했다.

원본 코어가 만든 검토 메타데이터는 후속 서비스가 보존해야 한다. 개인정보 마스킹·출력 정책·문맥 확인은 각각 별도의 경계이며 이 마케팅 action이 대신하지 않는다.

## 멱등·독립성

같은 원문을 반복 검사하면 같은 결정 dataclass가 나온다. 안전 초안을 다시 검사해도 **안전 본문은 변하지 않는다**. 다만 위반 문장을 제거한 안전 본문의 재검사 결과는 ALLOW가 될 수 있으며, 이것은 최초 REVIEW가 취소되었다는 뜻이 아니다. 원문의 검토 상태를 잃지 않도록 최초 판정과 안전 본문을 함께 보관해야 한다. 무상태 문자열 검사만으로 이미 제거된 원문의 검토 이력을 재구성하지 않는다.

파일 단독 import 시험은 AST에서 모든 import가 표준 라이브러리인지 검사하고 별도 Python을 `-I -S -B`로 실행해 해당 파일만 로딩한다. app이나 site-packages 없이 정상·위반 판정이 동작하고 `app`을 import하지 않은 것을 확인한다. 이 시험도 허용된 `tests/test_marketing_actions.py` 안에 있다.

## 재현 명령

모든 기존 앱 시험은 `Settings(_env_file=None, ...)`를 사용한다. `.env` 파일을 열거나 키를 읽지 않으며 실제 공급자 호출은 mock/fake로 대체한다. 테스트 과정의 bytecode·pytest cache 저장도 끈다. 출력 로그를 `docs/evidence/`에 저장하지 않았다.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$checkTests = @(
  'tests/test_mvp.py', 'tests/test_session_security.py',
  'tests/test_nemo_integration.py', 'tests/test_l02_input_only_risk.py',
  'tests/test_policy_actions.py', 'tests/test_security_pipeline.py',
  'tests/test_paid_call_service.py', 'tests/test_usage_accounting.py',
  'tests/test_marketing_actions.py'
)
# Python 3.14 local: 193 passed
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @checkTests -m 'not nemo'
# Python 3.12.10 / NeMo 0.24.1: 254 passed
.\security-runtime\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider @checkTests
```

Windows Python 3.12 실행 파일은 sandbox 밖에 있어 실제 NeMo 시험만 승인된 권한으로 실행했다. 실패를 우회하기 위해 시험을 바꾼 것이 아니다. 기존 회귀 실패나 금지 파일 변경 필요로 인한 중단은 없었다.

## 한계

3개 표현의 패턴 검사이며 일반적인 과장·법률 광고 적합성 분류기나 모든 한국어 부정/인용 의미를 이해하는 기능이 아니다. 문장 단위 제외로 정상 문맥도 함께 빠질 수 있다. 완전한 익명화·법률 검토 완료로 표시하지 않는다. 규칙별 정상/위반과 합성 우회 사례의 통과를 실제 자료의 탐지율로 해석하지 않는다.

## 열린 질문

1. 문서에 없는 변호사법 위반 소지·비교 광고·우월 표현의 구체적인 금지 문구와 허용/금지 사례는 무엇인가?
2. 세 표현의 의미상 변형(예: 확률 표기 변형, 문서에 없는 보상 약속 표현)은 어떤 범위까지 포함할 것인가?
3. 이중 부정·긴 인용·반어 등 현재 합성 사례 밖의 문맥은 어떤 정답 기준으로 구분할 것인가?
4. 안전 초안에서 문장 전체가 빠지는 손실을 허용하는 범위와 사람 검토 절차는 무엇인가?

위 항목은 추가 규칙으로 구현하지 않았다.

## 미검증·수행하지 않은 항목

실제 공급자·실모델 품질, 실제 사건·개인정보, 자동 게시, 설치 패키지 추출, 이번 변경에 대한 M01/M02 API 통합·HTTP 검증은 수행하지 않았다. RAG 코드·시험·증거, 앱 팩터리·라우터·정책 코어·의존성 파일은 변경하지 않았다. 기존 `rag-runtime` 미커밋 두 파일은 작업 전후 Git blob 해시가 같으며 그대로 보존했다. 커밋·push는 하지 않았다.
