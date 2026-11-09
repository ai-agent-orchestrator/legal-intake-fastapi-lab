# Legal Intake MVP — 실행과 복습

사용자가 선택한 첫 범위는 **동기 접수 등록·조회 + 비동기 AI 안내**입니다. 학원 리뷰 3 API의 구조를 Legal Intake 도메인으로 바꾼 개인 학습용 버전입니다. 강사의 제출 조건에서 도메인 변경을 허용하는지는 별도 확인 대상이며, AI 생성 코드를 직접 작성한 제출물로 표시하지 않습니다.

## 1. 세 API

| API | 구현 | 응답 |
|---|---|---|
| POST /api/intakes | def | 생성 201, 잘못된 데이터 422 |
| GET /api/intakes/{intake_id} | def | 조회 200, 사용자 정의 INTAKE_NOT_FOUND 404 |
| POST /api/intakes/{intake_id}/guidance | async def | 저장된 접수로 await AI 안내 200, 호출 실패 AI_REQUEST_FAILED 502 |

이 MVP는 기존 Spring의 동일 경로와 모든 요청·응답 필드가 호환되는 전체 이전본이 아닙니다. 별도의 작은 학습 계약입니다. 앞서 설계한 21개 API·NeMo action 9개는 후속 설계로 유지하며 이번에 전부 구현했다고 표시하지 않습니다.

## 2. 실행

이 프로젝트 전용 가상환경과 uv.lock을 준비했습니다. PowerShell에서:

```powershell
cd C:\myLectureWs\legal-intake-fastapi-lab
uv run fastapi dev --host 127.0.0.1 --port 8012
```

uv 캐시·Python 바로가기 문제로 실행이 막히면 이미 설치된 프로젝트 Python을 직접 사용할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8012
```

Swagger: http://127.0.0.1:8012/docs

최초 환경을 다시 만들 때는 `uv sync --python 3.14`를 사용합니다. 기존 학습 PC에서는 Python의 실제 설치 경로를 직접 지정해 설치했습니다. 서버 종료는 Ctrl+C입니다.

## 3. Swagger / Postman 실험

Postman에서는 [MVP collection](legal-intake-mvp.postman_collection.json)을 Import해 1~5번 순서대로 실행할 수 있습니다. 첫 요청의 응답 ID가 collection 변수에 저장됩니다. 파일은 준비했으며 Postman 앱에서의 수동 실행은 아직 하지 않았습니다.

POST /api/intakes에 다음 JSON을 보냅니다.

```json
{
  "clientName": "연습의뢰인",
  "caseType": "CIVIL",
  "coreStatement": "보증금 반환 상담에 필요한 자료를 준비하려고 합니다.",
  "desiredNextStep": "상담 준비자료 정리"
}
```

- clientName: 공백 제외 1~50자.
- caseType: CIVIL / CRIMINAL / FAMILY / OTHER.
- coreStatement: 공백 제외 1~100자. 기존 학습 설계의 100자 기준을 사용합니다.
- desiredNextStep: 선택, 최대 100자. 빈 문자열은 null로 정리합니다.
- JSON은 camelCase, Python 내부는 snake_case입니다.

201 응답의 intakeId를 이용해 GET /api/intakes/1과 POST /api/intakes/1/guidance를 실행합니다. 안내 생성에는 본문을 추가하지 않습니다. caseType을 INVALID로 바꾸면 422, 없는 ID는 404입니다.

현재 .env는 FAKE_LLM=true입니다. model=fake-llm과 '(가짜 AI 안내)'가 나오면 서버 흐름 확인에 성공한 것이며 실제 OpenAI 연결 성공은 아닙니다. 가짜 안내는 고정 문장입니다. 저장된 사실이 프롬프트로 전달되는지는 별도 mock 테스트에서 확인합니다.

## 4. 실제 OpenAI 호출

.env.example을 참고해 로컬 .env에 본인 키와 접근 가능한 모델을 설정합니다.

```dotenv
FAKE_LLM=false
OPENAI_API_KEY=본인_키
OPENAI_MODEL=사용할_모델
```

서버를 재시작합니다. real 모드인데 키가 없으면 시작에 실패합니다. 사용자 키를 채팅·로그·Git에 넣지 않습니다. actual 키·모델 권한·실제 유료 응답은 아직 검증하지 않았습니다.

이름은 AI 프롬프트에 넣지 않습니다. 사건 본문 전체에 대한 개인정보 자동 탐지·마스킹은 아직 구현하지 않았으므로 합성 데이터로 실험합니다. 운영 인증·영속 DB·NeMo·예산 제어·SSE도 이번 최소 범위에는 없습니다.

## 5. 코드 읽는 순서

1. domain/intake.py: 사건 유형 enum과 불변 접수 엔티티.
2. repositories/intake_repository.py: 딕셔너리·ID·짧은 thread lock.
3. schemas/intake.py: 등록 DTO·응답 DTO·camelCase·길이 검증.
4. core/exceptions.py: 없는 접수 404·AI 실패 502.
5. services/intake_service.py: 동기 등록·조회.
6. dependencies.py: 저장소·client·서비스 연결.
7. routers/intake_router.py: def 2개·async def 1개와 스레드 로그.
8. services/guidance_service.py: 불변 snapshot 조회·저장된 사실 JSON·await LLM.
9. clients/llm_client.py: fake의 asyncio.sleep과 AsyncOpenAI 호출.
10. main.py: lifespan에서 공유 자원 생성·종료, 예외·라우터 등록.

각 경로는 app/ 기준이며 모든 app 패키지에 빈 __init__.py가 있습니다. 접수 데이터는 서버 재시작 시 사라집니다. 동기 Repository를 쓰는 async 안내 서비스는 조회를 to_thread로 분리해 이벤트 루프에서 lock 대기를 피합니다.

## 6. 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=app
```

테스트에서는 실제 OpenAI를 호출하지 않습니다. 기본 계약, 입력 경계, 404, await와 저장 사실 전달, 502, SDK 오류·빈 답변, 키 누락, 동시 ID 발급, 재시작 초기화를 확인합니다.

비동기 검증은 가짜 client의 대기를 event로 붙잡습니다. 안내 요청 두 개가 모두 시작한 뒤에도 조회가 완료되는지, 안내 A/B가 섞이지 않는지 확인한 다음 대기를 해제합니다. CPU에 종속된 절대 속도 수치로 통과 여부를 정하지 않습니다.

Postman에서 직접 실행한 결과와 실제 OpenAI 결과는 자동 mock 테스트 결과와 구분합니다.
