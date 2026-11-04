"""Generate the self-contained Dark Tablet design document; no application code."""
from pathlib import Path
from html import escape as E
import json

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)

# ID, phase, origin, verb, proposed path, change
APIS = [
 ('C02','core','reuse','POST','/api/intakes/classify-preview','100자 사건 분류 · 무저장·무LLM'),
 ('C04','core','reuse','POST','/api/legal-intake/minimal','규칙 기반 안내 · 무저장·무LLM'),
 ('R01','core','reuse','GET','/api/legal/procedures','절차 목록 · 고정 fixture'),
 ('R02','core','reuse','GET','/api/legal/procedures/{code}','절차 상세 · 단계·양식 포함'),
 ('R06','core','reuse','GET','/api/legal/criminal/checklist/supplementary-investigation','고정 형사 체크리스트'),
 ('S01','core','change','POST','/api/ai/chat','기존 JSON 계약 → async Python'),
 ('S02','core','change','POST','/api/ai/chat/stream','SseEmitter → 검사 후 StreamingResponse'),
 ('S03','core','change','POST','/api/legal/guardrail/input','NeMo 입력 rail 단독 실험'),
 ('S04','core','change','POST','/api/legal/guardrail/output','NeMo 출력 rail 단독 실험'),
 ('C14','core','change','GET','/api/lab/security-events','관리자 API → 원문 없는 메모리 이벤트'),
 ('H01','core','new','GET','/health','fake/real·정책 버전 · 비밀값 제외'),
 ('B01','sample','new','POST','/api/posts','마스킹 후 메모리 게시글 생성'),
 ('B02','sample','new','GET','/api/posts','limit·cursor 목록'),
 ('B03','sample','new','GET','/api/posts/{postId}','마스킹된 게시글 상세'),
 ('B04','sample','new','PATCH','/api/posts/{postId}','허용 필드 수정 · 저장 전 마스킹'),
 ('B05','sample','new','DELETE','/api/posts/{postId}','게시글·연결 후기 제거 · AI 실행 불가'),
 ('B06','sample','new','POST','/api/posts/{postId}/reviews','후기 생성 · rating/body'),
 ('B07','sample','new','GET','/api/posts/{postId}/reviews','후기 목록 · 합성 데이터'),
 ('M01','sample','new','POST','/api/posts/{postId}/ai-summary','요약·주제·만족/불만 요인'),
 ('M02','sample','new','POST','/api/reviews/{reviewId}/reply-draft','검토용 답변 초안 · 자동 게시 제외'),
 ('C13','sample','change','GET','/api/lab/marketing/summary','기존 퍼널 → 게시글·후기 스냅샷 집계'),
]
EXCLUDED = ['C01','C03','C05','C06','C07','C08','C09','C10','C11','C12','C15','C16','C17','C18','C19','C20','R03','R04','R05','S05','P01','P02','P03','P04','P05','P06']
selected = [a[0] for a in APIS if a[2] != 'new']
original = {f'C{i:02}' for i in range(1,21)} | {f'R{i:02}' for i in range(1,7)} | {f'S{i:02}' for i in range(1,6)} | {f'P{i:02}' for i in range(1,7)}
assert len(APIS) == 21 and len(selected) == 11 and len(EXCLUDED) == 26
assert set(selected).isdisjoint(EXCLUDED) and set(selected) | set(EXCLUDED) == original
assert len({(a[3],a[4]) for a in APIS}) == 21
SYNC_IDS = set()  # Business APIs are async; the tiny sync demo is a separate app.
catalog = [dict(zip(['id','phase','origin','method','path','change'],a), executionModel='sync' if a[0] in SYNC_IDS else 'async') for a in APIS]
assert all(a['executionModel']=='async' for a in catalog)
(ROOT/'api-catalog.json').write_text(json.dumps({'status':'DRAFT_NOT_IMPLEMENTED','sourceDate':'2026-11-04','originalCount':37,'selectedOriginal':11,'excludedOriginal':26,'newProposed':10,'targetCount':21,'syncCount':0,'asyncCount':21,'courseworkApp':{'directory':'ohgi-review-server','status':'IMPLEMENTED_FAKE_AND_MOCK_TESTED','syncCount':2,'asyncCount':1,'includedInApiTargetCount':False},'apis':catalog,'excludedIds':EXCLUDED},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

BG,PANEL,LINE,TEXT,MUTED,CYAN,BLUE,AMBER = '#0e1725','#162438','#2b405b','#e8eff7','#adbed2','#6bd6e8','#68a8ff','#f0c57a'
def svg_start(title,h=430):
 return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 932 {h}" role="img" aria-label="{E(title)}"><title>{E(title)}</title><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="{MUTED}"/></marker></defs><style>text{{font-family:"Malgun Gothic",sans-serif;fill:{TEXT}}}.cap{{fill:{CYAN};font-size:13px}}.sub{{fill:{MUTED};font-size:13px}}</style>'
def node(x,y,w,title,lines=(),accent=False,h=82):
 stroke=CYAN if accent else LINE
 out=f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{PANEL}" stroke="{stroke}"/><text x="{x+16}" y="{y+26}" font-size="16" font-weight="600">{E(title)}</text>'
 for i,s in enumerate(lines): out+=f'<text class="sub" x="{x+16}" y="{y+48+i*19}">{E(s)}</text>'
 return out+'</g>'
def edge(x1,y1,x2,y2,label=''):
 out=f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{MUTED}" stroke-width="1.5" marker-end="url(#arrow)"/>'
 if label: out+=f'<text class="cap" x="{(x1+x2)/2+7}" y="{(y1+y2)/2-7}">{E(label)}</text>'
 return out

overview=svg_start('FastAPI 전체 흐름: ASGI 진입 후 AI, 규칙, 게시판 서비스로 분기',420)
overview+=node(336,5,260,'Swagger · 브라우저',('로컬 단일 사용자 · 합성 데이터',),True,65)
overview+=edge(466,70,466,92)
overview+=node(336,94,260,'ASGI → FastAPI',('trace → Pydantic → Depends',),True,65)
for x,title,lines in [(6,'비동기 챗봇 · AI',('S01·S02 / M01·M02','async def → await AI·NeMo')),(336,'규칙 · 법률 참조',('C02·C04 / R01·R02·R06','고정 fixture · 유료 호출 없음')),(666,'비동기 게시판 · 리뷰',('B01~B07 / C13','async def · 비동기 저장 경계'))]:
 overview+=edge(466,159,x+130,204)
 overview+=node(x,208,260,title,lines, x==6)
 overview+=edge(x+130,290,x+130,322)
for x,title,lines in [(6,'NeMo + OpenAI',('입출력 rail만 · 비동기 호출','전체 검사 → JSON / SSE')),(336,'응답 모델',('camelCase · 오류 계약','규칙 결과와 고정 안내')),(666,'메모리 저장소',('마스킹 · 짧은 async lock','AI에는 불변 snapshot 전달'))]:
 overview+=node(x,326,260,title,lines)
overview+='</svg>'

def chain_svg(title,items,notes,h=385,connect_through=7):
 s=svg_start(title,h)
 xs=[6,244,482,720]; ys=[12,165]
 coords=[(x,ys[0]) for x in xs]+[(x,ys[1]) for x in reversed(xs)]
 for i,(name,a,b) in enumerate(items):
  x,y=coords[i]; s+=node(x,y,206,name,(a,b),i==0)
  if i and i <= connect_through:
   px,py=coords[i-1]
   if py==y:
    s+=edge(px+(206 if x>px else 0),py+41,x+(0 if x>px else 206),y+41)
   else:s+=edge(px+103,py+82,x+103,y)
 for i,n in enumerate(notes): s+=f'<text class="sub" x="8" y="{304+i*25}">{E(n)}</text>'
 return s+'</svg>'

security=chain_svg('9개 action: 문맥·세션, 입력, 마스킹, 용량·예산, 생성, 출력, 반환',[
 ('01 문맥 · 세션 확인','validate_request_context','check_session_risk'),
 ('02 입력 정책','check_input_policy','고정 규칙 · 입력 rail'),
 ('03 입력 마스킹','mask_personal_data','외부 호출 전 PII 치환'),
 ('04 용량 → 예산','check_generation_admission','check_request_budget'),
 ('05 await 생성','OpenAI async client','대기 중 다른 요청 처리'),
 ('06 출력 정책','check_output_policy','marketing 정책은 추가 검사'),
 ('07 최종 마스킹','mask_personal_data','검사한 안전 본문만 전달'),
 ('08 문맥 확인 · 응답','요청 바인딩 재확인','JSON / 검사 완료 SSE'),
 ],['BLOCK → 사유 코드 확정 → record_risk_event 1회 → 안전 응답; 이후 단계 실행 금지',
 'finally: 미종료 예약 정산·슬롯 반환. 과부하·문맥 오류는 기술 error이며 공격 점수 제외.',
 '유료 단계마다 용량 → 예산 → 호출 → 정산 → 반환. 중첩 슬롯 획득 금지. 기본 검사는 로컬.'])

sse=chain_svg('SSE 출력과 예약 상태 전이',[
 ('01 meta','서버 traceId · model','본문과 개인정보 없음'),
 ('02 문맥 · 입력 검사','마스킹 → 용량 → 예산','정책 차단이면 blocked 종료'),
 ('03 await 전체 생성','사용량 확인 · 정산','미확인 사용량은 추정 정산'),
 ('04 전체 출력 검사','마케팅 검사 · 최종 마스킹','검사 실패 시 본문 전송 없음'),
 ('05 token 이벤트','검사 완료 문장을 청크로','실시간 미검사 토큰 아님'),
 ('06 done','usageAvailable / costSource','정상 terminal 1회'),
 ('별도: 단절 · 오류','취소 + bounded cleanup','error / blocked 후 done 없음'),
 ('예산: OPEN → 1회','REPORTED / ESTIMATED','호출 전 취소는 RELEASED'),
 ],['윗줄은 왼쪽 → 오른쪽, 아랫줄은 오른쪽 → 왼쪽. 단절·예산 카드는 별도 종료 규칙이다.',
 'SSE 시작 전: 422/503/504 가능. 시작 후: HTTP 상태 변경 대신 error 이벤트.',
 'POST 스트림은 fetch ReadableStream 사용. BackgroundTasks로 필수 검사·정산을 미루지 않는다.'],connect_through=5)
overview=overview.replace('id="arrow"','id="arrow-overview"').replace('url(#arrow)','url(#arrow-overview)')
security=security.replace('id="arrow"','id="arrow-security"').replace('url(#arrow)','url(#arrow-security)')
sse=sse.replace('id="arrow"','id="arrow-sse"').replace('url(#arrow)','url(#arrow-sse)')
for name,svg in [('overview',overview),('security-actions',security),('sse-lifecycle',sse)]:
 (ASSETS/(name+'.svg')).write_text(svg,encoding='utf-8')

def table(headers,rows,cls=''):
 return '<table class="'+cls+'"><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table>'
def code(t):return '<code>'+E(t)+'</code>'
def api_rows(phase):
 labels={'reuse':'계약 재사용','change':'변경 이전','new':'신규 제안'}
 return [(f'<b>{a[0]}</b>',f'<span class="verb">{a[3]}</span> {code(a[4])}',E(a[5]),labels[a[2]]) for a in APIS if a[1]==phase]
def strip(label,body):return f'<div class="strip"><b>{E(label)}</b><span>{E(body)}</span></div>'
def cards(items):return '<div class="cards">'+''.join(f'<div class="card"><h3>{E(t)}</h3><p>{E(s)}</p></div>' for t,s in items)+'</div>'

pages=[]
pages.append(('리뷰 과제 3개 + 비동기 Legal Intake 확장','01 / REVIEW COURSEWORK + ASYNC LAB',
 '<p class="lead">별도 과제 앱: 동기 등록·조회 2개 + 비동기 답글 1개. 아래 21개 주력 API는 확장 설계.</p>'+overview+
 cards([('11개 우선 구현','분류·참조·Chat·SSE·가드레일·보안 이벤트·health'),('10개 후속 제안','강사 샘플 확인 후 게시판·리뷰·AI 마케팅 기능'),('로컬 실험 한정','단일 worker · localhost · 합성 데이터')]) ))
pages.append(('기존 API에서 가져올 핵심 11개','02 / API SELECTION · CORE',
 '<p class="lead">경로와 응답 계약은 유지하고, Java 서비스 구현을 Python으로 이전한다.</p>'+table(['ID','선정한 API','이번 구현 범위','구분'],api_rows('core'),'api')+
 strip('실행 계약','Chat 입력 100자 · camelCase 응답 · Pydantic 오류 422 · 정책 차단은 기존 호환 응답')+
 strip('구현 순서','규칙/참조 → fake Chat → 입력 actions → 예산 → real Chat → 출력 검사 → SSE')))
pages.append(('게시판·리뷰에서 AI 마케팅으로','03 / API SELECTION · SAMPLE EXTENSION',
 '<p class="lead">주력 B/M/C13은 비동기 확장. 수업 리뷰 API 3개는 별도 앱이며 21개에 합산하지 않음.</p>'+table(['ID','제안 API','동작','구분'],api_rows('sample'),'api')+
 strip('AI 재사용','M01·M02는 Chat과 같은 보안·예산 파이프라인 사용. 게시글·후기 내용은 지시가 아닌 분석 데이터.')+
 strip('집계 범위','C13은 게시글·후기 수와 분석 결과 스냅샷. 상담 전환율·기간별 이탈률은 이번에 제외.')))
pages.append(('보안 Python action의 실행 경계','04 / SECURITY PIPELINE',
 '<p class="lead">NeMo 입력·출력 rail이 검사 결과를 소비하고 실제 중단·변환을 수행하도록 연결한다.</p>'+security+
 strip('공통 내부 결정','ALLOW / BLOCK / TRANSFORM / REVIEW + reasonCode + detailCode + safeText')+
 strip('강제 규칙','클라이언트는 action 이름·임계값·Python 실행 경로를 지정할 수 없다. 업무 변경 action도 없다.')))
action_rows=[
 ('validate_request_context','입력·반환 직전','서버 문맥 바인딩 · A/B 혼합 방지'),
 ('check_session_risk','세션 상태 조회','DYNAMIC_SESSION_BLOCKED · TTL/용량 제한'),
 ('check_input_policy','고정 위험 규칙','법률 악용·injection·secret·privacy · profile별 적용'),
 ('mask_personal_data','전송·저장·반환 전','정의한 PII 패턴 치환 · 자유문 이름 완전 탐지 아님'),
 ('check_generation_admission','각 유료 호출 전','동시 2 · 대기 4 · 대기 한도 0.5초'),
 ('check_request_budget','각 유료 호출 직전','Decimal + lock으로 검사/예약 원자 처리'),
 ('check_output_policy','전체 생성 후','빈값·길이·정책 검사 · 실패 시 안전 종료'),
 ('check_marketing_response','M01/M02 출력','보장·과장 표현 → 사람 검토 · 자동 게시 없음'),
 ('record_risk_event','정책 BLOCK 확정 후','점수 1회 기록 · 원 사유는 detailCode 유지'),
]
pages.append(('9개 action 확정 · 함수와 사유 코드 구분','05 / ACCEPTED SECURITY DESIGN',
 '<p class="lead">기존 7개 + 요청 문맥·생성 진입 제어 2개. 설계 확정이며 실제 구현·설치는 후속 작업.</p>'+table(['Python action','호출 시점','동작과 제한'],[(code(a),E(b),E(c)) for a,b,c in action_rows])+
 strip('실패 구분','문맥 불일치 500 · 용량 초과 503. 정책 차단과 다르며 위험 점수로 적립하지 않음.')+
 strip('이유와 계약','async-security-explained.html: 도입 이유·자원 수명·취소·비교 실험·설정 상세.')))
pages.append(('안전한 SSE와 취소·비용 정산','06 / STREAM & RESOURCE LIFECYCLE',
 '<p class="lead">첫 버전은 전체 답변을 검사한 뒤 전송한다. 비동기 처리와 실시간 토큰 공개는 별개의 선택이다.</p>'+sse+
 strip('이미 발생한 비용','출력 차단·오류·연결 종료여도 호출이 시작됐다면 정산. 미확인 usage를 0으로 만들지 않음.')+
 strip('가격·재시도','단가 설정 없으면 real 호출 거절. 자동 재시도 기본 0. 제공자 실제 청구 상한을 보장하지 않음.')))
compare_rows=[
 ('진입','Filter / Security / JWT','ASGI middleware → Pydantic → Depends'),
 ('조립','Controller / Service Bean','APIRouter + 서비스 + lifespan 공유 자원'),
 ('대기','RestClient / SseEmitter','await 클라이언트 / async generator'),
 ('상태','synchronized / JPA','asyncio.Lock / bounded 메모리 저장소'),
 ('오류','ControllerAdvice','exception handler + SSE error 이벤트'),
 ('검증','JUnit / MockMvc','pytest / ASGI client / dependency_overrides'),
]
pages.append(('Spring 문법 치환보다 자원·대기·취소 이해','07 / FASTAPI NATIVE DESIGN',
 '<p class="lead">수업 리뷰는 def 2개·async def 1개. 주력 비동기 게시판·AI 확장은 별도 설계.</p>'+table(['구간','이전 Spring Boot','이번 FastAPI'],[(E(a),E(b),E(c)) for a,b,c in compare_rows])+
 cards([('시작 · lifespan','설정 → clients → NeMo → stores. 종료 시 close.'),('요청 · Depends','공유 자원 주입. 호출 대기는 await로 양보.'),('종료 · finally','단절·timeout에도 예약을 한 번만 정산.')])+
 '<div class="module">'+code('routers → services → guardrails/actions + clients → stores')+'</div>'+
 strip('실험 환경','NeMo의 Python 3.14 호환성은 미검증. 필요하면 별도 3.12/3.13 환경을 검증 후 고정.')))
excluded_rows=[
 ('C01 · P01','로그인·내 정보','Spring 인증·인가를 이번 실행 경로에서 제외'),
 ('C03 · C05 · C09~C11','접수·상담 업무 저장','운영 DB·사건 상태 워크플로 제외'),
 ('C06~C08 · P02 · P03','외부 검색·이력','검색 제공자·검색 LLM·영속 이력 제외'),
 ('C12 · C15~C20 · S05','운영·Agent·Incident','Actuator·위험 이력·운영 프로세스 제외'),
 ('R03~R05','단계·양식 전용 API','R02 fixture 상세로 축소'),
 ('P04~P06','파일·행동 이벤트','스토리지·OCR·행동 수집 제외'),
]
pages.append(('범위를 줄이고 검증 가능한 단위로','08 / EXCLUSIONS & ACCEPTANCE',
 '<p class="lead">기존 37개 = 선정 11개 + 제외 26개. 신규 10개를 합친 목표 21개 모두 현재 설계 상태다.</p>'+table(['원본 ID','제외 영역','이번 실험의 선택'],[(E(a),E(b),E(c)) for a,b,c in excluded_rows])+
 cards([('보안 검증','정상·공격·PII·마케팅 · 오류 원문 누출 0'),('비용 검증','동시 예약·단발 정산 · 호출 전후 취소'),('SSE 검증','검사 전 본문 0 · terminal 1회 · 단절 cleanup')])+
 '<p class="sources">근거: 원본 API_STATUS_SPEC · AiController/DTO · LegalFixedGuardService · LegalDynamicGuardService · AiCostControlService. 공식 근거와 전체 계약은 상세 설계서 참고.</p>'+
 strip('다음 단계','① fastapi-lab → ③ hybrid-lab → ② ai-service. 이번 문서는 첫 단계 구현을 위한 DRAFT.')))

style='''
:root{color-scheme:dark;--bg:#0e1725;--panel:#162438;--line:#2b405b;--text:#e8eff7;--muted:#adbed2;--cyan:#6bd6e8;--blue:#68a8ff}*{box-sizing:border-box}body{margin:0;background:#09101b;color:var(--text);font-family:"Malgun Gothic",system-ui,sans-serif}header.controls{max-width:1024px;margin:20px auto 12px;display:flex;align-items:center;gap:10px;padding:0 12px;flex-wrap:wrap}button,a{font:inherit}button{border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--text);padding:9px 15px;cursor:pointer}button:hover,button:focus-visible{border-color:var(--cyan)}button:disabled{opacity:.4;cursor:default}.counter{margin-right:auto;color:var(--muted);font-size:14px}a{color:var(--cyan)}.page{width:min(1024px,100%);min-height:768px;margin:0 auto 32px;padding:26px 46px 20px;background:var(--bg);border:1px solid var(--line);border-radius:18px;display:flex;flex-direction:column;box-shadow:0 16px 60px #0004}.page[hidden]{display:none}.eyebrow{font-size:12px;color:var(--cyan);letter-spacing:1px;display:flex;justify-content:space-between;padding-bottom:14px;border-bottom:1px solid var(--line)}h1{font-size:29px;line-height:1.4;letter-spacing:-.7px;margin:20px 0 8px}h3{font-size:15px;color:var(--cyan);margin:0 0 7px}.lead{font-size:15px;line-height:1.65;color:var(--muted);margin:0 0 18px}svg{width:100%;height:auto;display:block}table{width:100%;border-collapse:collapse;table-layout:fixed;margin:2px 0 16px;font-size:13px;line-height:1.55}th{text-align:left;color:var(--cyan);background:#1b3a50;padding:10px 11px;font-weight:600}td{padding:10px 11px;border-bottom:1px solid var(--line);overflow-wrap:anywhere;vertical-align:top}tr:nth-child(even) td{background:#122033}th:first-child{width:21%}.api th:nth-child(1){width:6%}.api th:nth-child(2){width:49%}.api th:nth-child(3){width:33%}.api th:nth-child(4){width:12%}.api td{padding:7px 9px}.api code{font-size:12px;word-break:break-word}.verb{font-size:11px;color:var(--cyan);font-weight:600;display:inline-block;min-width:44px}code{font-family:Consolas,"Malgun Gothic",monospace;font-size:13px}.strip{display:flex;gap:16px;background:var(--panel);padding:12px 15px;border-radius:10px;margin-top:10px;font-size:13px;line-height:1.65}.strip b{color:var(--cyan);min-width:90px;flex-shrink:0}.strip span{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}.card{padding:16px;background:var(--panel);border-radius:12px}.card p{font-size:13px;line-height:1.65;color:var(--muted);margin:0;overflow-wrap:anywhere}.footer{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-top:auto;padding-top:18px;border-top:1px solid var(--line)}.content{padding-bottom:20px}.module{background:var(--panel);padding:18px;margin-top:14px;border-radius:10px;color:var(--cyan)}.sources{font-size:12px;line-height:1.7;color:var(--muted);margin:15px 0 0}.links{font-size:13px;margin:0 auto 25px;max-width:1024px;padding:0 15px;line-height:2}button:focus-visible,a:focus-visible{outline:2px solid var(--cyan);outline-offset:3px}@media(max-width:720px){.page{padding:22px 20px;border-radius:0;min-height:0}h1{font-size:24px}.cards{grid-template-columns:1fr}.api{font-size:12px}.api td{padding:7px 4px}.api code{font-size:11px}.strip{display:block}.strip b{display:block;margin-bottom:4px}.eyebrow{font-size:10px;letter-spacing:0}}@media print{@page{size:1024px 768px;margin:0}body{background:var(--bg);print-color-adjust:exact;-webkit-print-color-adjust:exact}.controls,.links{display:none!important}.page,.page[hidden]{display:flex!important;width:1024px;height:768px;min-height:0;break-after:page;margin:0;border:0;border-radius:0;box-shadow:none}.page:last-child{break-after:auto}a{color:var(--cyan)}}
'''
style=style.replace('padding:26px 46px 20px','padding:24px 46px 18px').replace('margin:0 0 18px','margin:0 0 14px').replace('padding:10px 11px;border-bottom','padding:9px 11px;border-bottom').replace('padding:7px 9px','padding:6px 9px').replace('.card{padding:16px','.card{padding:14px').replace('padding-top:18px','padding-top:14px').replace('.content{padding-bottom:20px}', '.content{padding-bottom:12px}')
articles=''.join(f'<article class="page" id="page-{i}" aria-label="{i}. {E(title)}" {"hidden" if i>1 else ""}><div class="eyebrow"><span>LEGAL INTAKE / FASTAPI LAB</span><span>{E(label)}</span></div><h1>{E(title)}</h1><div class="content">{body}</div><div class="footer"><span>DRAFT · 구현 전 설계 · 2026-11-04 · DARK TABLET 4:3</span><span>{i:02} / {len(pages):02}</span></div></article>' for i,(title,label,body) in enumerate(pages,1))
script='''const pages=[...document.querySelectorAll('.page')];let n=0;function show(i){n=Math.max(0,Math.min(pages.length-1,i));pages.forEach((p,j)=>p.hidden=j!==n);document.getElementById('counter').textContent=`${n+1} / ${pages.length} · ${pages[n].querySelector('h1').textContent}`;document.getElementById('prev').disabled=n===0;document.getElementById('next').disabled=n===pages.length-1;history.replaceState(null,'',`#page-${n+1}`);window.scrollTo(0,0)}document.getElementById('prev').onclick=()=>show(n-1);document.getElementById('next').onclick=()=>show(n+1);document.getElementById('print').onclick=()=>window.print();document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')show(n+1);if(e.key==='ArrowLeft')show(n-1)});const initial=Number(location.hash.replace('#page-',''));show(Number.isInteger(initial)&&initial>0?initial-1:0);'''
html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Legal Intake · FastAPI Backend · Dark Tablet</title><style>'+style+'</style></head><body><header class="controls"><span class="counter" id="counter" aria-live="polite"></span><button id="prev" aria-label="이전 페이지">← 이전</button><button id="next" aria-label="다음 페이지">다음 →</button><button id="print">인쇄 / PDF</button></header><main>'+articles+'</main><nav class="links" aria-label="설계 자료"><a href="BACKEND_DESIGN.md">상세 백엔드 설계</a> · <a href="api-catalog.json">API 선정 데이터</a> · <a href="backend-flows.mmd">Mermaid 원본</a> · <a href="assets/overview.svg">전체 흐름 SVG</a> · <a href="assets/security-actions.svg">보안 흐름 SVG</a></nav><script>'+script+'</script></body></html>'
(ROOT/'backend-dark-tablet.html').write_text(html,encoding='utf-8')
security_policy=json.loads((ROOT/'async-security-design.json').read_text(encoding='utf-8'))
assert {r[0] for r in action_rows} == set(security_policy['actions'])
mermaid=(ROOT/'backend-flows.mmd').read_text(encoding='utf-8')
part1,tail=mermaid.split('%% 02 security actions.',1)
part2,part3=tail.split('%% 03 SSE lifecycle.',1)
for name,source in [('overview',part1),('security-actions',part2[part2.index('flowchart TD'):]),('sse-lifecycle',part3[part3.index('sequenceDiagram'):])]:
 (ASSETS/(name+'.mmd')).write_text(source.strip()+'\n',encoding='utf-8')
print(f'Generated {len(pages)} pages, {len(APIS)} APIs, 3 SVGs. Original API coverage: 37/37.')
