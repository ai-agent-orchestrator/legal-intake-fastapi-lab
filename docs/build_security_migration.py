"""Build an offline Dark Tablet explanation and native SVG of the target design."""
from html import escape
from pathlib import Path
import json
import re

from markdown_it import MarkdownIt

DOCS = Path(__file__).resolve().parent
policy = json.loads((DOCS / "async-security-design.json").read_text(encoding="utf-8"))
source = (DOCS / "SECURITY_MIGRATION_PLAN.md").read_text(encoding="utf-8")
assert len(policy["actions"]) == len(set(policy["actions"])) == 9
assert all(name in source for name in policy["actions"])
assert policy["migrationScope"]["authenticationIncluded"] is False
assert policy["migrationScope"]["authorizationIncluded"] is False
assert policy["migrationScope"]["implementedActionCount"] == 0

parts = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 1190" role="img" aria-labelledby="title desc">
<title id="title">FastAPI AI 보안 전체 이전 목표 — 인증·인가 제외</title>
<desc id="desc">구현 전 설계: 요청 문맥, 세션 위험, 입력 검사, 마스킹, 용량과 비용, AI 호출, 출력과 마케팅 검사, 안전 반환 및 실패·취소 정리.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10Z" fill="#6bd6e8"/></marker></defs>
<style>text{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;fill:#e8eff7}.label{font-size:17px;font-weight:600}.small{font-size:14px;fill:#adbed2}.cap{font-size:12px;fill:#6bd6e8;letter-spacing:1px}.link{stroke:#6bd6e8;stroke-width:2;fill:none;marker-end:url(#arrow)}.branch{stroke-dasharray:6 5}</style>
<rect width="1100" height="1190" rx="22" fill="#0e1725"/>
<text x="38" y="40" class="cap">LEGAL INTAKE / AI SECURITY MIGRATION / TARGET DESIGN</text>
<text x="38" y="78" font-size="28" font-weight="700">AI 보안은 FastAPI · Python으로</text>
<text x="38" y="107" class="small">인증·인가 제외 · 9개 action은 목표 설계 · 현재 접수 MVP와 구분</text>
''']


def box(x, y, width, title, detail, *, color="#294c6a", height=70):
    parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="#162438" stroke="{color}"/>')
    parts.append(f'<text x="{x+18}" y="{y+28}" class="label">{escape(title)}</text>')
    parts.append(f'<text x="{x+18}" y="{y+52}" class="small">{escape(detail)}</text>')


nodes = [
    ("01  FastAPI 진입", "Pydantic DTO · 요청별 context · Depends"),
    ("02  validate_request_context", "요청·대상 snapshot 바인딩 확인"),
    ("03  check_session_risk · check_input_policy", "누적 위험·고정 입력 정책 검사"),
    ("04  mask_personal_data", "저장·AI 전송 전에 정의한 개인정보 패턴 치환"),
    ("05  check_generation_admission", "유한 대기열 · 생성 용량 확보"),
    ("06  check_request_budget", "확인+예약 원자 처리 · 초과 시 AI 호출 중단"),
    ("07  await OpenAI", "호출 후 비용 정산 · 생성 슬롯 반환"),
    ("08  check_output_policy", "완성 답변 전체 검사 · 장애 시 공개 중단"),
    ("09  check_marketing_response", "M01/M02 필수 · 보장·과장 문구 → 사람 검토"),
    ("10  최종 마스킹 · 응답 문맥 재확인", "검사 완료 safeText만 JSON / 안전 SSE로 반환"),
]
for index, (title, detail) in enumerate(nodes):
    y = 140 + index * 91
    box(38, y, 640, title, detail)
    if index < len(nodes) - 1:
        parts.append(f'<path class="link" d="M358 {y+70} V{y+89}"/>')

box(718, 140, 344, "범위", "로그인 · JWT · 역할 권한 제외")
box(718, 257, 344, "record_risk_event", "確定 정책 차단만 중복 없이 기록".replace("確定", "확정"))
parts.append('<path class="link branch" d="M678 357 H698 V292 H716"/>')
parts.append('<text x="730" y="349" class="small">기술 오류·과부하·REVIEW는</text><text x="730" y="371" class="small">공격 점수에 적립하지 않음</text>')
box(718, 467, 344, "서비스 finally", "실패·timeout·취소에도 정리", color="#9a7244")
parts.append('<text x="736" y="563" class="small">미종료 예약 정산 · lease 반환</text><text x="736" y="586" class="small">네트워크 대기 중 lock 유지 금지</text>')
parts.append('<path class="link branch" d="M678 721 H698 V502 H716"/>')
box(718, 649, 344, "각 유료 단계의 경계", "용량 → 예약 → 호출 → 정산 → 반환")
box(718, 787, 344, "우선 학습할 3개", "마스킹 · 예산 · 마케팅 검사")
parts.append('<text x="736" y="884" class="small">나머지 6개도 이전 목표에 포함</text><text x="736" y="907" class="small">데코레이터 등록만으로 완료 아님</text>')
parts.append('''<rect x="38" y="1070" width="1024" height="85" rx="12" fill="#142d35" stroke="#3a6c73"/>
<text x="58" y="1099" class="label">현재 완료: 동기 접수 등록·조회 + 비동기 AI 안내 · 테스트 23개</text>
<text x="58" y="1126" class="small">다음: 기반 부품 → 9개 action·NeMo rail → AI pipeline → 실호출 → 법률 게시판·SSE</text>
</svg>''')
svg = "".join(parts)
(DOCS / "assets/security-migration.svg").write_text(svg, encoding="utf-8")

md = MarkdownIt("commonmark").enable("table")
tokens = md.parse(source)
toc = []
for index, token in enumerate(tokens):
    if token.type == "heading_open" and token.tag == "h2":
        anchor = f"migration-{len(toc)+1}"
        token.attrSet("id", anchor)
        toc.append((anchor, tokens[index+1].content))
body = md.renderer.render(tokens, md.options, {})
body = body.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
style = re.search(r"<style>(.*?)</style>", (DOCS / "study-guide.html").read_text(encoding="utf-8"), flags=re.S).group(1)
style += "article img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:14px}"
nav = "".join(f'<a href="#{anchor}">{escape(title)}</a>' for anchor, title in toc)
document = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FastAPI AI 보안 전체 이전 · 인증·인가 제외</title><style>{style}</style></head><body>
<header class="top"><strong>LEGAL INTAKE / SECURITY MIGRATION</strong><a href="readme-preview.html">README</a><a href="backend-dark-tablet.html">전체 흐름도</a><a href="SECURITY_MIGRATION_PLAN.md">원문</a></header>
<div class="layout"><details class="toc" open><summary>전체 이전 범위와 구현 목표</summary><nav aria-label="보안 이전 목차">{nav}</nav></details><article><span class="badge">목표 설계 · 인증·인가 제외 · 9개 action 미구현</span>{body}<footer class="bottom">현재 MVP와 계획을 구분합니다. 주말 이후 단계별 구현·검증을 진행합니다.</footer></article></div></body></html>'''
(DOCS / "security-migration.html").write_text(document, encoding="utf-8")
assert len(toc) == 13
assert all(name in svg for name in policy["actions"])
print(f"Generated migration HTML, SVG: {len(toc)} sections, 9 planned actions, authentication/authorization excluded.")
