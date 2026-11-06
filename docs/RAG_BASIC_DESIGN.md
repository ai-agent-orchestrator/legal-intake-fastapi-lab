# 근거를 찾고, 흐름을 연결하고, 결과를 확인하기

2026-11-06 · **Claude 검수 전 기본 설계 초안 / 아래 검색 기능은 아직 미구현**

LangChain·LangGraph·LangSmith·RAG·임베딩·벡터 RAG·memvid를 모두 개발 범위에 포함한다.
첫 목표는 **합성 상담 준비 안내문 10개에서 근거를 찾아, 출처가 있는 안내 답변 하나를 만드는 것**이다.
큰 시스템부터 만들지 않고 같은 작은 예제를 일곱 개념으로 끝까지 이해한다.

<div class="note"><strong>현재와 앞으로를 구분합니다.</strong><p>현재 개발 브랜치에는 기존 API 3개와 L01/L02 문맥·세션 위험 코드가 있으며 실제 NeMo를 포함한 95개 테스트를 통과했다. 이 문서의 LangChain·LangGraph·LangSmith·임베딩·memvid 검색은 앞으로 만들 설계다. 이 화면의 비교 체험은 고정된 학습 예시이며 실제 모델이나 검색기를 실행하지 않는다.</p></div>

먼저 [개발 전 구조 설계안](RAG_ARCHITECTURE_REVIEW.md)을 Claude에게 검수한다.
[Claude 전달 요청서](CLAUDE_RAG_DESIGN_REVIEW.md)의 형식으로 피드백을 받고,
지적 사항을 반영한 최종 개발안이 확정된 뒤 구현한다. 이 문서만으로 구현 착수를 승인한 상태는 아니다.

## 1. 일곱 가지를 한 문장씩

| 이름 | 쉬운 설명 | 우리 프로젝트에서 할 일 |
|---|---|---|
| LangChain | 한 단계의 일을 만드는 부품 | 메시지·프롬프트·검색 인터페이스·구조화 출력 |
| LangGraph | 여러 단계의 순서와 분기를 정하는 진행표 | 검색 → 근거 있음/없음 → 답변/추가 질문 |
| LangSmith | 과정과 결과를 확인하는 기록·평가 도구 | 검색 결과·응답 시간·프롬프트 버전 비교 |
| RAG | 자료를 찾고 그 자료를 근거로 답하는 방식 | 상담 준비 안내문을 근거로 답변 |
| 임베딩 | 문장의 의미를 숫자 배열로 바꾸는 일 | 질문과 문서를 같은 의미 공간에 배치 |
| 벡터 RAG | 벡터 유사도 검색을 이용하는 RAG | 표현이 달라도 관련 안내문 찾기 |
| memvid | 문서와 검색 인덱스를 담는 파일 기반 엔진 | `.mv2`에 마스킹한 청크와 벡터 저장 |

**RAG 대신 memvid를 쓰는 것이 아니라 memvid로 RAG를 만든다.**
별도 Chroma·Pinecone·Milvus를 함께 운영하지 않아도 이번 학습 흐름을 구성할 수 있다.
이는 이 프로젝트의 기본 설계이며 대규모 운영에서 모든 벡터 DB를 대체한다는 뜻은 아니다.

## 2. LangChain · LangGraph · LangSmith는 무엇이 다른가

| 구분 | LangChain | LangGraph | LangSmith |
|---|---|---|---|
| 해결할 질문 | 각 작업을 어떻게 만들까? | 다음에 무엇을 실행할까? | 어디서 느려지고 틀렸을까? |
| 핵심 개념 | 모델·메시지·템플릿·retriever·LCEL | state·node·edge·조건 분기 | trace·dataset·experiment·evaluator |
| 이번 최소 사용 | `prompt → model → schema` | 검색 뒤 두 갈래 분기 | 단계별 trace와 합성 질문 20개 비교 |
| 예시 | 준비자료 목록을 JSON으로 생성 | 근거가 없으면 생성하지 않음 | 키워드와 벡터 검색의 정답 문서 발견률 비교 |
| 처음에 사용하지 않을 기능 | 자율 에이전트의 반복 검색 | 다중 에이전트·영속 checkpoint | 실제 의뢰인 원문 전체 수집 |

LangGraph가 반드시 LangChain을 요구하는 것은 아니다. 여기서는 LangChain 부품을 LangGraph의 node 안에서 사용한다.
LangSmith도 두 프레임워크에 종속된 검색기가 아니며 실행을 관찰하고 평가하는 역할이다.
[LangGraph 공식 역할 설명](https://docs.langchain.com/oss/python/langgraph/overview)과
[워크플로와 에이전트 구분](https://docs.langchain.com/oss/python/langgraph/workflows-agents)을 근거로 이처럼 나눈다.

<div class="triad"><div><b>LangChain</b><span>작업을 만든다</span><small>프롬프트 · 모델 · retriever</small></div><div><b>LangGraph</b><span>순서를 연결한다</span><small>state · node · 조건 분기</small></div><div><b>LangSmith</b><span>결과를 비교한다</span><small>trace · 평가 · 실험</small></div></div>

## 3. 첫 번째 사용 사례

질문은 “집주인이 돈을 안 돌려줘요. 상담 전에 뭘 준비하죠?”로 시작한다.
저장된 “임대차 보증금 반환 상담 준비” 안내문에서 계약서·입금 자료·사건 경위 정리 항목을 찾는다.
답변에는 준비자료와 확인할 질문, 사용한 문서 ID를 포함한다. 법률 판단·승소 확률을 생성하는 서비스로 확장하지 않는다.

처음 저장할 문서는 합성 안내문 10개다. 접수 원문과 개인 사건 기록을 검색용 지식으로 자동 적재하지 않는다.
후기·게시글의 분석은 이후 별도 자료 구분을 두고 추가한다. 후기를 공식 안내 근거처럼 섞지 않는다.

<div class="example"><span class="eyebrow">하나의 예제로 끝까지</span><p><strong>질문</strong> 집주인이 돈을 안 돌려줘요.</p><p><strong>검색 근거</strong> GUIDE-001 / 보증금 반환 상담 준비 / v1</p><p><strong>안내</strong> 계약서와 입금 자료를 정리해 상담에 준비하세요.</p><p><strong>검증</strong> 이 출처가 실제 검색 결과에 있는가? 자료에 없는 판단을 만들지 않았는가?</p></div>

## 4. 적재와 질문 응답은 두 흐름이다

**적재는 미리 한 번**, 질문 응답은 요청마다 실행한다. 같은 문서를 질문마다 다시 임베딩하지 않는다.

<div class="pipeline"><h3>미리 준비하기 · 적재</h3><ol><li>합성 안내문 읽기</li><li>입력 검사·개인정보 마스킹</li><li>제목·문단 단위 분할</li><li>E5 문서 임베딩</li><li>memvid 저장</li></ol></div>

<div class="pipeline"><h3>사용자가 질문할 때</h3><ol><li>요청 문맥·세션·입력 검사</li><li>마스킹한 질문 임베딩</li><li>memvid 검색</li><li>LangGraph 근거 분기</li><li>LangChain + Llama 생성</li><li>출력 검사 후 반환</li></ol></div>

검색 결과도 외부에서 온 데이터처럼 다룬다. 자료에 “검사를 생략하라”는 문장이 있어도 시스템 지시로 승격하지 않는다.
마스킹과 보안 검사는 그래프 안의 LLM이 임의로 생략할 수 없도록 서비스 경계에서 강제한다.
LangSmith는 이 흐름의 단계별 실행을 기록하되 원문을 보내기 전에 기록 데이터도 처리한다.

## 5. 키워드 검색과 벡터 검색 비교하기

### 최소 개념: 벡터와 코사인 유사도

벡터는 임베딩 모델이 문장을 표현한 숫자 배열이다. 코사인 유사도는 두 벡터의 방향이
얼마나 비슷한지 비교하는 기준이며, 같은 모델 공간에서 관련 자료 후보를 정렬할 때 사용한다.
유사도는 정답 확률이나 법률적 정확도가 아니다. top-k는 가져올 후보 수이며 근거의 충분함과 다르다.
이번에는 Legal Intake 이해를 위한 개념 공부로 제한한다. 별도 리서치 시스템, 개인 검색식,
Llama 질의 요약기나 맞춤 랭킹 설계는 추가하지 않는다.
[LangChain의 벡터 유사도 검색 설명](https://docs.langchain.com/oss/python/integrations/vectorstores/index).

키워드 검색은 표현이 겹치는 자료를 찾고, 벡터 검색은 임베딩의 유사도를 사용한다.
법률 용어·문서 번호가 정확한 질문에는 키워드가 유용하고, 일상어로 바꿔 말한 질문에는 의미 검색이 도움이 될 수 있다.
처음에는 두 방식을 따로 비교한다. 어느 방식이 좋은지는 우리 평가 질문으로 확인한다.

<div class="search-demo" id="search-demo"><span class="eyebrow">학습용 고정 예시 · 실제 임베딩/검색 실행 아님</span><label for="demo-query">어떤 질문을 찾을까요?</label><select id="demo-query"><option value="paraphrase">집주인이 돈을 안 돌려줘요</option><option value="exact">보증금 반환 상담 준비</option><option value="unknown">저장된 안내문에 없는 질문</option></select><div class="mode-buttons" aria-label="검색 방식 선택"><button type="button" data-mode="lex" aria-pressed="true">키워드</button><button type="button" data-mode="sem" aria-pressed="false">벡터</button><button type="button" data-mode="hybrid" aria-pressed="false">혼합 비교</button></div><div class="demo-result" aria-live="polite"><strong id="demo-title">키워드 · 표현이 다르면 놓칠 수 있어요</strong><p id="demo-body">고정 예시에서는 일치 문서가 없습니다. 실제 결과는 토큰화·문서 내용·검색 설정에 따라 달라집니다.</p><p id="demo-route">LangGraph → 근거 없음 → 추가 자료 요청</p></div></div>

혼합 검색은 후속 비교 단계다. 두 결과를 합칠 때 점수 체계가 다른 값을 그대로 더하지 않는다.
기본 실습에서는 먼저 키워드/벡터를 선택하도록 만들고, 혼합은 순위 기반 결합의 효과를 확인한 뒤 활성화한다.

## 6. 임베딩 선택 · Llama 생성과 E5 검색

**대표님이 정한 Qwen 제외 방침을 반영해 Qwen 모델은 기본 실행 후보에서 제외한다.**
생성 모델은 Llama 계열, 검색 임베딩의 우선 검토 모델은 `intfloat/multilingual-e5-large-instruct`로 정한다.
이 조합은 모델 계열이 달라도 가능하다. 임베딩은 숫자 벡터를 만들고 Llama는 검색한 텍스트를 읽어 답한다.
현재 저장소의 실제 생성 client는 OpenAI SDK이므로 Llama 실행 어댑터는 앞으로 추가할 작업이다.

E5의 개발 주체는 Microsoft 연구진이며 `intfloat`는 배포 계정명이다.
[Microsoft 소속이 명시된 기술 보고서](https://arxiv.org/html/2402.05672v1)와
[Microsoft 공식 E5 저장소](https://github.com/microsoft/unilm/tree/master/e5)에서 확인한다.
Microsoft가 이 프로그램의 실행을 대신 맡거나 데이터를 자동 보호한다는 의미는 아니다.

### OpenAI small/large 표는 별도 비교 항목이다

`text-embedding-3-small`과 `text-embedding-3-large`는 E5·Qwen과 다른 OpenAI API 모델이다.
기본 차원은 각각 1536·3072이며 요청 시 차원을 줄이는 기능이 있다.
[OpenAI 공식 임베딩 안내](https://developers.openai.com/api/docs/guides/embeddings).
전달받은 `14/20·19/20`, `18/20·20/20` 수치는 평가 질문·문서·top-k·지표 이름이 없어
일반 성능이나 우리 프로젝트 실측 결과로 인용하지 않는다. 현재는 확인 불가다.
외부 API 임베딩은 Llama 생성과 함께 쓸 수 있지만 텍스트가 해당 API로 전송된다.
기본안은 로컬 E5 우선 검토를 유지하고, 원격 API는 검토 가능한 대안으로만 둔다.

| 비교 | multilingual-e5-large-instruct | Qwen3-Embedding-8B |
|---|---|---|
| 개발 계열 | Microsoft 연구진 / E5 | Qwen 팀 / Alibaba 계열 |
| 용도 | 다국어 검색 임베딩 | 다국어 검색 임베딩 |
| 규모 | 모델 카드 표기 약 0.6B | 8B |
| 벡터 차원 | 1024 | 기본 최대 4096, 32~4096 조절 지원 |
| 입력 길이 | 최대 512 토큰 | 32K 토큰 |
| 라이선스 표기 | MIT | Apache-2.0 |
| 질문 전처리 | 질문에 검색 task instruction 필요 | instruction-aware, 공식 권장 형식 적용 |
| 문서 전처리 | 문서에는 질문용 instruction을 붙이지 않음 | 선택한 모델의 passage 규약 사용 |
| 로컬 실행 | Transformers / Sentence Transformers | Transformers / Sentence Transformers, 버전 요구 확인 |
| 이번 채택 | 우선 구현·한국어 검색 평가 대상 | 비교 설명만 포함, 실행하지 않음 |

위 사양의 근거는 [E5 모델 카드](https://huggingface.co/intfloat/multilingual-e5-large-instruct)와
[Qwen 모델 카드](https://huggingface.co/Qwen/Qwen3-Embedding-8B)다.
벡터 차원이 크거나 모델이 크다고 우리 한국어 상담 질문에서 항상 더 잘 찾는다는 뜻은 아니다.
두 모델의 같은 데이터·같은 조건의 한국어 법률 검색 우열은 아직 측정하지 않았다.

E5의 핵심 주의점은 512 토큰 제한이다. 처음에는 **E5 tokenizer 기준 300토큰 청크·40토큰 겹침**을
실험 시작값으로 사용하고 제목과 문단을 보존한다. 질문 instruction을 포함한 최종 입력도 길이를 확인한다.
이는 확정 최적값이 아니며, 긴 문서를 통째로 넣어 뒤가 잘리는 방식을 피하기 위한 기본값이다.
문서와 질문에는 같은 E5 모델 revision·차원·정규화 규약을 쓴다.
모델을 바꾸면 새 `.mv2` 인덱스를 만들고 재임베딩하며 기존 벡터를 혼합하지 않는다.

메모리는 정밀도·배치·장치·길이에 따라 달라진다. 단순 가중치 계산으로 0.6B × 2바이트는 약 1.2GB,
8B × 2바이트는 약 16GB이며 **실제 실행에는 여기에 추가 메모리**가 든다.
이 수치는 필요한 GPU 메모리 보장값이 아니다. 이 PC에서 E5/Llama의 동시 실행 속도와 메모리는 아직 확인하지 않았다.

### 보안은 개발사와 실행 경로를 따로 확인한다

공식 모델을 내려받아 로컬 추론하는 방식과 외부 임베딩 API를 호출하는 방식은 다르다.
E5도 외부 호스팅 API를 쓰면 텍스트가 그 제공자에게 전송될 수 있다. 로컬 Qwen 실행을 두고
근거 없이 중국으로 데이터를 보낸다고 단정하지 않는다. 이번 설계는 대표님의 Qwen 제외 방침을 따른다.

실행 설계는 고정 revision의 공식 가중치·검토한 패키지·로컬 추론을 우선한다.
임의 원격 코드 실행 옵션을 켜지 않고, 모델을 준비한 뒤 오프라인 로딩·외부 전송 여부를 검증한다.
임베딩도 원문에서 유래한 데이터이므로 공개 산출물로 자동 업로드하지 않는다.
LangSmith 원문 추적을 켜면 로컬 Llama/E5 구성에서도 데이터가 외부로 나갈 수 있으므로 별도로 제어한다.

## 7. memvid와 retriever의 연결

memvid는 마스킹한 안내문 청크·출처·버전·임베딩을 저장한다.
Windows에서 memvid SDK의 내장 로컬 임베딩 제한을 피하기 위해, **별도 E5 provider에서 벡터를 만든 뒤
memvid에 외부 벡터로 전달**하는 어댑터를 설계한다. 실제 설치 버전의 저장·질의 기능을 먼저 통합 시험한다.
[memvid SDK 공식 안내](https://pypi.org/project/memvid-sdk/2.0.160/)는 외부 임베딩과 질의 벡터 전달을 설명한다.

| 데이터 | 저장할 내용 |
|---|---|
| 본문 | 마스킹된 청크 텍스트 |
| 출처 | documentId, chunkId, title, sourceVersion |
| 모델 | embeddingModel, pinnedRevision, dimension, normalization |
| 범위 | collectionId=`synthetic-guides-v1`, documentType=`guide` |
| 운영 기준 | 적재 실행 ID와 활성 인덱스 버전 |

`MemvidRetriever`는 질문을 받아 `Document` 목록으로 반환하는 내부 어댑터다.
생성 모델은 벡터가 아니라 검색된 텍스트를 읽는다. memvid의 직접 답변 생성 함수를 사용해
우리 출력 검사를 우회하지 않고, 검색 결과를 기존 서비스로 되돌린다.
관련 자료가 없으면 임의 문서를 억지로 근거로 붙이지 않는다.
관련성 기준은 고정 cosine 0.8처럼 임의로 정하지 않고 합성 평가 질문으로 보정한다.
항상 top-k 결과가 나온다는 사실만으로 근거가 있다고 판단하지 않는다.

## 8. LangGraph는 작은 분기 하나부터

첫 그래프는 반복 없이 끝나는 고정 workflow다. 요청마다 별도 state를 만들며 초기 버전에서는
대화 checkpoint와 영속 대화 기억을 사용하지 않는다. 세션 위험 저장소와 그래프 state는 서로 다른 책임이다.

```text
START → retrieve → 근거 유무 확인
                  ├─ 있음 → generate → END
                  └─ 없음 → ask_for_materials → END
```

| node | 입력 → 출력 | 호출 규칙 |
|---|---|---|
| retrieve | safeQuestion → 근거 청크·출처 | memvid 검색 1회, vector 모드일 때 질문 임베딩 1회 |
| generate | 질문·근거 → 구조화 초안 | LangChain chain + Llama, 최대 생성 1회 |
| ask_for_materials | 질문 → 추가 자료 요청 템플릿 | LLM 생성 0회 |

graph 안에 보안 우회 분기는 두지 않는다. 입력/출력 검사와 유료 단계의 용량·예산·취소 정리는
서버 서비스가 감싸서 보장한다. 오류를 “근거 없음”으로 숨기지 않고 기술 오류로 구분한다.
자동 재시도·재검색 루프는 첫 범위에서 제외한다. LangGraph 재실행으로 같은 유료 호출이
중복 실행되지 않는지 후속 영속화 도입 전에 별도로 설계한다.

## 9. LangChain · 메시지·LCEL·구조화 출력

LangChain에서는 시스템 지시·사용자 질문·검색 근거의 역할을 구분하는 템플릿을 만든다.
자료를 구분자로 넣는 것만으로 injection이 해결되지는 않으므로 별도 입력 검사를 통과해야 한다.
LCEL은 이 짧은 node의 연결에 사용하고 전체 업무의 분기는 LangGraph가 담당한다.

```text
검색 근거 정리 → ChatPromptTemplate → Llama 모델 어댑터 → Pydantic 검증
```

구조화 출력은 내부 DTO에 먼저 적용한다. 생성 모델의 native schema 지원 여부를 확인하고,
지원하지 않으면 JSON 출력과 서버 Pydantic 검증으로 동작시킨다. 실패한 출력을 그대로 공개하지 않는다.
JSON 형식이 맞아도 사실·안전성이 맞는 것은 아니다.

```json
{
  "answer": "상담 전에 계약서와 입금 자료를 정리하세요.",
  "preparationItems": ["계약서", "입금 자료"],
  "questions": ["현재 보유한 자료가 무엇인가요?"],
  "citationIds": ["GUIDE-001:chunk-01:v1"],
  "evidenceStatus": "FOUND"
}
```

서버는 citationIds가 실제 검색 결과의 ID 부분집합인지 확인한다. 자료가 없으면
`evidenceStatus=NOT_FOUND`와 빈 출처를 **서버가** 확정하고 추가 자료 안내를 보낸다.
현재 API의 answer/model/intakeId 계약은 유지하고, 새 필드는 내부 평가에 먼저 사용한다.
외부 응답 확장은 별도 계약 변경으로 검토한다.
[구조화 출력 공식 문서](https://docs.langchain.com/oss/python/langchain/structured-output).

## 10. LangSmith는 추적과 평가로 반드시 사용한다

개발 완료 기준에 **실제 LangSmith trace 확인과 합성 데이터 평가 실험**을 포함한다.
SDK를 설치한 것만으로 연동 완료라고 하지 않는다. 키가 없는 환경에서는 local 시험이 가능하지만
LangSmith 원격 연동 완료 상태와 구분한다.

기본 trace 구성은 `request → graph → retrieve / generate / validation`이다.
기록할 값은 요청 trace ID, node 이름, 문서 ID, 검색 모드, 시간, 결과 코드, 모델·프롬프트·인덱스 버전이다.
기존 session 원문·전화·이메일·실제 사건 내용·키·원문 예외를 metadata나 오류에 넣지 않는다.
입력·출력은 기본 숨김으로 시작하고, 합성 평가 데이터에 한해 명시적으로 내용을 기록한다.
[LangSmith 입력·출력·metadata 처리](https://docs.langchain.com/langsmith/mask-inputs-outputs)를 적용한다.

| 평가 | 첫 기준 |
|---|---|
| 검색 | 질문 20개 중 기대 문서가 top-3 안에 있는 비율: Hit@3 |
| 무근거 분기 | 근거 없는 질문은 생성 0회·출처 비어 있음 |
| 출처 | 응답의 모든 ID가 실제 검색 결과에 포함됨 |
| 안전성 | 합성 PII가 저장·전송·응답·trace에 남지 않음 |
| 지연 | 질문 임베딩·검색·생성 시간을 구분해서 측정 |
| 비용·사용량 | 원격 임베딩/생성 사용량과 로컬 자원 사용을 구분 |

초기 목표 예시는 Hit@3 80% 이상이지만 아직 달성한 결과가 아니다.
평가 질문 20개와 별도 확인 질문 10개를 두고, 청크/모델 변경은 같은 질문으로 비교한다.
처음에는 코드 평가와 사람의 확인을 사용하며 LLM judge 비용은 필수로 만들지 않는다.
LangSmith 장애는 보안 검사 실패와 구분한다. 기록 실패가 생겨도 보안 검사를 생략하거나 원문을
실패 로그에 다시 출력하지 않는다. [LangSmith 평가 공식 문서](https://docs.langchain.com/langsmith/evaluation).

## 11. 보안 action 9개와 연결하기

| 경계 | 연결할 action |
|---|---|
| 진입·반환 | validate_request_context |
| 입력 전 | check_session_risk |
| 질문·검색 근거 | check_input_policy |
| 저장·임베딩 전송·최종 응답 | mask_personal_data |
| 유료 단계 진입 | check_generation_admission |
| 유료 임베딩·생성 호출 | check_request_budget |
| 생성 전체 | check_output_policy |
| 향후 M01/M02 | check_marketing_response |
| 확정 정책 차단 | record_risk_event |

L01/L02 외 action과 유료 pipeline의 실행 연결은 아직 후속 개발이다.
현재 마케팅 검사 실패 코드는 보존 브랜치에 있으며 정상 기능으로 재사용하지 않는다.
이 전체 경계를 갖추기 전에는 실제 의뢰인 데이터나 공개 운영 검증이 완료됐다고 하지 않는다.

로컬 E5/Llama에는 공급자 토큰 요금이 없더라도 계산 자원·동시성·timeout 제어는 필요하다.
원격 임베딩을 선택하면 생성과 별도의 비용 예약 단계를 거친다. trace 비용 표시는
예산 원자 예약을 대신하지 않는다. 네트워크·native 동기 호출은 async node 안에서 직접 블로킹하지 않도록
비동기 client 또는 제한된 worker로 분리한다.

## 12. 개발 순서와 예정 파일

다음 B 번호는 이 문서의 기본 학습 단계다. 기존 L01/L02와 다른 번호 체계임을 명시한다.

| 단계 | 작은 개발 묶음 | 끝났다고 판단할 증거 |
|---|---|---|
| 선행 | 나머지 필수 입력·마스킹·출력 경계와 비용/자원 service 연결 | 차단/오류 시 우회·누출·누수 없음 |
| B01 | 합성 문서 10개·token 분할·출처 metadata | 재적재 시 동일 문서 중복 없음, token 상한 시험 |
| B02 | E5 provider·memvid 외부 벡터 적재/검색 | 실제 E5 문서/질문 encode와 `.mv2` 검색, 차원 불일치 거절 |
| B03 | LangChain prompt·Llama client·내부 structured DTO | fake와 실제 어댑터 구분, 필드·출처 검증 |
| B04 | LangGraph 3 node·근거 없음 분기 | 정상 1회 생성, 무근거 0회, A/B state 격리 |
| B05 | LangSmith trace·한국어 평가 | 원격 trace 확인, 같은 dataset의 keyword/vector 실험 비교 |
| B06 | 주력 안내 연결·향후 게시판 재사용 | 기존 API 회귀, M 기능 활성화 전 마케팅 검사 재검증 |

아래 파일명은 **생성할 예정**이며 현재 코드 존재를 뜻하지 않는다.

```text
app/retrieval/
  ingest.py                 # 합성 자료·분할·적재
  embeddings.py             # E5 문서/질문 규약
  memvid_store.py           # 외부 벡터·.mv2 경계
  retriever.py              # LangChain Document 반환
app/chains/
  guidance_chain.py         # prompt·Llama·구조화 출력
app/graphs/
  guidance_graph.py         # retrieve/generate/ask_for_materials
app/observability/
  tracing.py                # 전송 전 trace 정보 처리
scripts/
  ingest_guides.py
  evaluate_retrieval.py
tests/                      # 적재·검색·graph·trace 경계별 시험
```

LangChain·LangGraph·LangSmith·memvid·E5 실행 의존성은 실제 조합을 설치·시험한 후 전용 runtime lock에 고정한다.
이번 설계 문서 작업에서 모델을 내려받거나 패키지를 새로 설치하지 않았다.
Llama의 정확한 모델 ID·정밀도·실행 서버는 하드웨어와 운영 조건을 확인한 뒤 정한다.

## 13. 앱 API는 최대 11개

기존 API 3개와 다음 확장 8개를 합친 기본 구성으로 정한다. 이 목록은 목표 계약이고
현재 브랜치에서 실행되는 API는 기존 3개다. 내부 적재·검색·평가는 별도 공개 API를 늘리지 않는다.

| 구분 | 메서드·경로 | 개수 |
|---|---|---|
| 기존 접수 | POST `/api/intakes`, GET `/api/intakes/{intake_id}`, POST `/api/intakes/{intake_id}/guidance` | 3 |
| 상태 | GET `/health` | 1 |
| 게시글 | POST·GET `/api/posts`, GET `/api/posts/{postId}` | 3 |
| 후기 | POST·GET `/api/posts/{postId}/reviews` | 2 |
| AI 마케팅 | POST `/api/posts/{postId}/ai-summary`, POST `/api/reviews/{reviewId}/reply-draft` | 2 |
| 합계 | 메서드와 경로의 조합으로 집계 | **11** |

기존 상세 설계·api-catalog.json의 21개는 이전 후보 목록이다. 이번 기본 구성에는
독립 Chat/SSE·게시글 수정/삭제·단독 guardrail 시험 API를 추가하지 않는다.
동기/비동기 비교는 별도 학습 앱에서 진행한다. 이 설계로 인증·인가 범위를 확대하지 않는다.

## 14. 공부할 때 스스로 설명해 보기

<details><summary>LangChain과 LangGraph를 모두 쓰면 역할이 겹치지 않나요?</summary><p>LangChain은 node 안의 프롬프트·모델·retriever 부품, LangGraph는 그 node의 순서와 분기를 담당합니다. 전체 서비스의 필수 보안 경계는 별도로 유지합니다.</p></details>
<details><summary>memvid가 있으면 임베딩이 필요 없나요?</summary><p>키워드 검색만 할 때는 임베딩 없이도 시작할 수 있습니다. 이번 목표인 벡터 RAG는 E5로 문서와 질문의 벡터를 만들어 사용합니다.</p></details>
<details><summary>Llama로 생성하면 임베딩도 Llama여야 하나요?</summary><p>아닙니다. E5로 찾은 문서 텍스트를 Llama에 전달할 수 있습니다. 문서와 검색 질문의 임베딩 모델은 서로 일치해야 합니다.</p></details>
<details><summary>임베딩 모델을 바꾸면 같은 1024차원끼리 섞어도 되나요?</summary><p>안 됩니다. 차원이 같아도 의미 공간과 전처리 규약이 다를 수 있습니다. 새 revision·모델은 별도 인덱스로 적재·평가합니다.</p></details>
<details><summary>JSON 스키마가 맞으면 답변도 정확한가요?</summary><p>형식과 내용의 정확성은 다릅니다. 실제 근거 ID 검사, 정책 검사, 사람이 확인하는 평가를 함께 수행합니다.</p></details>
<details><summary>로컬 모델이면 LangSmith도 자동으로 로컬인가요?</summary><p>아닙니다. 로컬 추론과 trace 전송 목적지는 별개입니다. 기본 원문 숨김을 유지하고 원격 연결과 합성 평가를 따로 검증합니다.</p></details>

## 15. 공식 근거와 현재 구현 기록

- [LangGraph: 구성 요소의 역할](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph: 고정 workflow와 agent](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangChain: 메시지](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain: 구조화 출력](https://docs.langchain.com/oss/python/langchain/structured-output)
- [LangChain: 텍스트 분할](https://docs.langchain.com/oss/python/integrations/splitters/index)
- [LangSmith: 실행 추적](https://docs.langchain.com/langsmith/observability)
- [LangSmith: 평가](https://docs.langchain.com/langsmith/evaluation)
- [LangSmith: 민감정보 기록 제어](https://docs.langchain.com/langsmith/mask-inputs-outputs)
- [memvid SDK 2.0.160](https://pypi.org/project/memvid-sdk/2.0.160/)
- [E5 공식 모델 카드](https://huggingface.co/intfloat/multilingual-e5-large-instruct)
- [E5 Microsoft 기술 보고서](https://arxiv.org/html/2402.05672v1)
- [Qwen 임베딩 비교용 모델 카드](https://huggingface.co/Qwen/Qwen3-Embedding-8B)
- [현재 L01/L02 구현·검증](L01_L02_IMPLEMENTATION.md)
- [전체 보안 이전 목표](SECURITY_MIGRATION_PLAN.md)
- [법률 마케팅 게시판 목표](LEGAL_MARKETING_BOARD.md)
- [개발 전 구조 설계안](RAG_ARCHITECTURE_REVIEW.md)
- [Claude 검수 요청서](CLAUDE_RAG_DESIGN_REVIEW.md)
