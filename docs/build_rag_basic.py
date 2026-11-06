"""Render the review-only RAG design in the existing offline Dark Tablet style."""
from html import escape
from pathlib import Path
import re

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
PAGES = {
    "RAG_BASIC_DESIGN.md": ("rag-basic-dark-tablet.html", "기본 개발안 · 공부 문서", "한 예제로 배우는 검색과 생성"),
    "RAG_ARCHITECTURE_REVIEW.md": ("rag-architecture-dark-tablet.html", "개발 전 구조 설계", "개발 전, 연결 구조부터 확인하기"),
    "CLAUDE_RAG_DESIGN_REVIEW.md": ("claude-rag-review-dark-tablet.html", "Claude 전달 요청서", "검수한 뒤 최종안으로 개발하기"),
}
md = MarkdownIt("commonmark", {"html": True}).enable("table")
base = (ROOT / "study-guide.html").read_text(encoding="utf-8")
style = re.search(r"<style>(.*?)</style>", base, flags=re.S).group(1)
style += '''
:root{--gold:#eccb8b;--green:#a0e3c0}
.top a{display:inline-flex;align-items:center;min-height:40px}.hero{padding-bottom:25px;margin-bottom:25px;border-bottom:1px solid var(--line)}
.eyebrow{display:block;color:var(--gold);font-size:12px;letter-spacing:.4px;line-height:1.8}.hero h1{font-size:35px;margin:12px 0 15px;line-height:1.45}.hero p{color:var(--muted);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:20px 0}.chip{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:3px 9px;font-size:13px;color:var(--cyan)}
.hero-actions{display:flex;flex-wrap:wrap;gap:12px;font-size:14px}.doc-title{font-size:23px;font-weight:600;line-height:1.6}.status{display:inline-block;border:1px solid #6d6043;border-radius:20px;padding:3px 12px;margin-bottom:15px;font-size:12px;color:var(--gold)}
.note,.example{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--cyan);border-radius:10px;padding:20px;margin:24px 0}.note p,.example p{margin:10px 0 0}.note strong{color:var(--cyan)}
.triad{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:25px 0}.triad>div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 14px}.triad b{font-size:19px;color:var(--cyan)}.triad span,.triad small{display:block}.triad span{margin:7px 0}.triad small{color:var(--muted);font-size:12px;line-height:1.8}
.pipeline{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin:20px 0}.pipeline h3{margin:0 0 13px;font-size:17px}.pipeline ol{display:flex;flex-wrap:wrap;gap:9px;list-style:none;padding:0;margin:0;counter-reset:step}.pipeline li{counter-increment:step;background:#102033;border:1px solid var(--line);border-radius:7px;padding:8px 11px;font-size:14px;margin:0}.pipeline li:before{content:counter(step) ' / ';color:var(--cyan);font-size:12px}
.search-demo{background:var(--panel);border:1px solid #466a84;border-radius:14px;padding:22px;margin:26px 0}.search-demo label{display:block;margin:13px 0 8px;font-weight:600}.search-demo select{width:100%;font:inherit;color:var(--text);background:#0e1725;border:1px solid #597088;border-radius:8px;padding:11px;min-height:48px}.mode-buttons{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
button{font:inherit;cursor:pointer;border:1px solid #587188;border-radius:8px;background:#0e1725;color:var(--text);min-height:46px;padding:9px 14px;font-size:14px}button[aria-pressed=true]{background:#224b61;border-color:var(--cyan);color:#c4f6ff}button:focus-visible,select:focus-visible,.table-wrap:focus-visible{outline:2px solid var(--cyan);outline-offset:4px}
.demo-result{background:#0e1725;border:1px solid var(--line);border-radius:9px;padding:19px;min-height:185px}.demo-result strong{color:var(--green)}.demo-result p{margin:10px 0 0}.demo-result p:last-child{color:var(--muted);font-size:14px}.table-wrap{margin-bottom:20px}table{min-width:520px}td:first-child{font-weight:600}.toc nav a{padding:8px;min-height:40px}.bottom a{margin-right:12px}
@media(max-width:950px){.hero h1{font-size:30px}.toc{max-height:250px}.toc nav{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.triad{grid-template-columns:1fr}.hero h1{font-size:26px}.search-demo{padding:16px}.toc nav{grid-template-columns:1fr}table{min-width:480px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{.hero-actions,.mode-buttons,select{display:none}.table-wrap{overflow:visible}table{min-width:0}.pipeline,.note,.example,.search-demo{break-inside:avoid}}
'''
script = '''
(() => {
  const query=document.getElementById('demo-query');
  if(!query) return;
  const buttons=[...document.querySelectorAll('[data-mode]')];
  const names={lex:'키워드',sem:'벡터',hybrid:'혼합 비교'};
  let mode='lex';
  function render(){
    const noHit=query.value==='unknown'||(query.value==='paraphrase'&&mode==='lex');
    let title,body;
    if(query.value==='unknown'){
      title=names[mode]+' · 저장된 자료에 없는 질문';
      body='학습 예시에서는 관련 근거가 없습니다. 의미 검색이라고 언제나 답을 찾는 것은 아닙니다.';
    }else if(noHit){
      title='키워드 · 표현이 다르면 놓칠 수 있어요';
      body='고정 예시에서는 일치 문서가 없습니다. 실제 결과는 토큰화·문서 내용·검색 설정에 따라 달라집니다.';
    }else{
      title=names[mode]+' · GUIDE-001 / 임대차 보증금 반환 상담 준비';
      body=mode==='hybrid'?'키워드와 의미 검색 결과를 결합하는 고정 예시입니다. 실제 품질 향상이나 검색 점수를 측정한 결과는 아닙니다.':'근거 문서의 계약서·입금 자료 준비 항목을 전달합니다. 실제 검색 성능은 별도 평가로 확인합니다.';
    }
    document.getElementById('demo-title').textContent=title;
    document.getElementById('demo-body').textContent=body;
    document.getElementById('demo-route').textContent=noHit?'LangGraph → 근거 없음 → 추가 자료 요청 · 생성 0회':'LangGraph → 근거 있음 → LangChain + Llama → 출처 검증 · 생성 최대 1회';
    buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===mode)));
  }
  buttons.forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.mode;render();}));
  query.addEventListener('change',render);render();
})();
'''

for filename, (output, title, subtitle) in PAGES.items():
    source = (ROOT / filename).read_text(encoding="utf-8")
    tokens = md.parse(source)
    toc = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            anchor = f"chapter-{len(toc) + 1}"
            token.attrSet("id", anchor)
            toc.append((anchor, tokens[index + 1].content))
        for child in token.children or []:
            if child.type == "link_open":
                target = child.attrGet("href") or ""
                if target and not target.startswith(("http:", "https:", "#")):
                    path, separator, fragment = target.partition("#")
                    assert (ROOT / path).is_file(), target
                    if path in PAGES:
                        # Cross-page Markdown section labels are prose, not assumed HTML IDs.
                        child.attrSet("href", PAGES[path][0] + (separator + fragment if separator else ""))
    body = md.renderer.render(tokens, md.options, {})
    body = body.replace('<table>', '<div class="table-wrap" tabindex="0" aria-label="좌우로 스크롤할 수 있는 표"><table>').replace('</table>', '</table></div>')
    body = re.sub(r'<h1>(.*?)</h1>', r'<p class="doc-title">\1</p>', body, count=1, flags=re.S)
    nav = ''.join(f'<a href="#{a}">{escape(t)}</a>' for a,t in toc)
    page_links = ''.join(f'<a href="{p[0]}">{escape(p[1])}</a>' for key,p in PAGES.items() if key != filename)
    chips = ''.join(f'<span class="chip">{name}</span>' for name in ('LangChain','LangGraph','LangSmith','RAG','임베딩','벡터 RAG','memvid'))
    document = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Legal Intake · {escape(title)}</title><style>{style}</style></head>
<body><header class="top"><strong>LEGAL INTAKE / BASIC AI DESIGN</strong><a href="study-guide.html">기존 공부자료</a>{page_links}</header>
<div class="layout"><details class="toc" open><summary>목차 · {len(toc)}개 주제</summary><nav aria-label="문서 목차">{nav}</nav></details><article>
<section class="hero"><span class="eyebrow">DARK TABLET · 2026.11.06 · DESIGN REVIEW</span><h1>{escape(subtitle)}</h1><p>합성 안내문 10개에서 시작하는 기본 개발안</p><div class="chips">{chips}</div><span class="status">Claude 검수 전 초안 · 검색 기능 미구현</span><div class="hero-actions">{page_links}<a href="{filename}">Markdown 원문</a></div></section>
{body}<footer class="bottom">설계 검수 → 지적 반영 → 최종안 확정 → 단계별 구현<br>화면의 검색 비교는 고정 학습 예시이며 실제 검색 점수가 아닙니다.</footer></article></div><script>{script}</script></body></html>'''
    assert document.count('<table>') == document.count('</table>')
    assert document.count('<pre>') == document.count('</pre>')
    assert 'Claude 검수 전 초안' in document
    (ROOT / output).write_text(document, encoding="utf-8")
    print(f"Generated {output}: {len(toc)} sections, offline Dark Tablet.")
