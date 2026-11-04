"""Render the Markdown study guide as an offline readable document."""
from html import escape
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
md = MarkdownIt('commonmark', {'html': True}).enable('table')
source = (ROOT / 'STUDY_GUIDE.md').read_text(encoding='utf-8')
tokens = md.parse(source)
for token in tokens:
    for child in token.children or []:
        if child.type in {'link_open', 'image'}:
            target = child.attrGet('href' if child.type == 'link_open' else 'src') or ''
            if target and not target.startswith(('http:', 'https:', '#')):
                assert (ROOT / target.split('#', 1)[0]).exists(), target
toc = []
for i, token in enumerate(tokens):
    if token.type == 'heading_open' and token.tag == 'h2':
        anchor = f'chapter-{len(toc)+1}'
        token.attrSet('id', anchor)
        toc.append((anchor, tokens[i+1].content))
body = md.renderer.render(tokens, md.options, {})
nav = ''.join(f'<a href="#{anchor}">{escape(title)}</a>' for anchor, title in toc)
style = '''
:root{color-scheme:dark;--bg:#0e1725;--panel:#162438;--line:#2b405b;--text:#e8eff7;--muted:#adbed2;--cyan:#6bd6e8;--blue:#68a8ff}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}body{margin:0;background:#09101b;color:var(--text);font-family:"Malgun Gothic",system-ui,sans-serif;font-size:16px;line-height:1.95}a{color:var(--cyan);text-underline-offset:4px}a:hover{color:var(--text)}a:focus-visible,summary:focus-visible{outline:2px solid var(--cyan);outline-offset:4px}.top{max-width:1220px;margin:auto;padding:22px 26px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--muted)}.top strong{color:var(--cyan);letter-spacing:1px;margin-right:auto}.layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:24px;max-width:1220px;margin:0 auto 40px;padding:0 22px}.toc{position:sticky;top:20px;max-height:calc(100vh - 40px);overflow:auto;align-self:start;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}.toc summary{font-weight:600;color:var(--cyan);cursor:pointer;padding-bottom:10px}.toc nav{display:grid;gap:3px}.toc a{font-size:13px;text-decoration:none;color:var(--muted);padding:6px 8px;border-radius:6px;line-height:1.7}.toc a:hover{background:#1b3a50;color:var(--text)}article{background:var(--bg);border:1px solid var(--line);border-radius:18px;padding:35px 42px;min-width:0}h1{font-size:32px;line-height:1.5;margin:0 0 20px;letter-spacing:-1px}h2{font-size:25px;line-height:1.55;margin:52px 0 18px;padding-top:24px;border-top:1px solid var(--line);color:var(--cyan)}h3{font-size:19px;line-height:1.7;margin:28px 0 12px;color:var(--blue)}p{margin:0 0 18px}li{margin-bottom:7px}strong{font-weight:600}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.8;margin:20px 0 26px;table-layout:auto}th{background:#1b3a50;color:var(--cyan);text-align:left}td,th{padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}tr:nth-child(even){background:#122033}pre{padding:20px 22px;background:var(--panel);border:1px solid var(--line);border-radius:11px;overflow-x:auto;font-size:14px;line-height:1.85;margin:20px 0 25px;tab-size:4}code{font-family:Consolas,"Malgun Gothic",monospace}p code,li code,td code{font-size:.9em;color:#b8eaf2;background:#14283a;border-radius:4px;padding:1px 4px}img{width:100%;height:auto;display:block;border-radius:10px}article details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px 18px;margin:13px 0}article details summary{cursor:pointer;color:var(--cyan);font-size:15px;line-height:1.85}article details p{font-size:15px;margin:14px 0 4px;color:var(--text)}.table-wrap{overflow-x:auto}.bottom{border-top:1px solid var(--line);margin-top:45px;padding-top:20px;color:var(--muted);font-size:13px}.badge{display:inline-block;background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:3px 12px;font-size:12px;color:var(--cyan);margin-bottom:20px}.jump{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:24px;font-size:13px}@media(max-width:950px){.layout{grid-template-columns:1fr;max-width:850px}.toc{position:static;max-height:280px}.toc nav{grid-template-columns:repeat(2,minmax(0,1fr))}article{padding:26px}.top{padding:20px 24px}h1{font-size:28px}}@media(max-width:560px){.layout{padding:0 10px;gap:12px}article{padding:23px 17px;border-radius:12px}h1{font-size:25px}h2{font-size:22px}body{font-size:16px}td,th{padding:9px}pre{padding:14px;font-size:13px}.toc nav{grid-template-columns:1fr}.top{padding:18px 15px}table{font-size:13px;min-width:460px}}@media print{@page{size:A4;margin:16mm}body{background:var(--bg);print-color-adjust:exact;-webkit-print-color-adjust:exact}.top,.toc,.jump{display:none}.layout{display:block;max-width:none;padding:0;margin:0}article{border:0;border-radius:0;padding:0}h1{font-size:24px}h2{font-size:20px;break-after:avoid}h3{break-after:avoid}body{font-size:12px;line-height:1.8}pre,table{font-size:10px}details{break-inside:avoid}details p{display:block}pre{white-space:pre-wrap}a{overflow-wrap:anywhere}}
'''
# Tables retain readable type on narrow screens without clipping the whole document.
body = body.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
document = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Legal Intake · 비전공자용 FastAPI 공부자료</title><style>{style}</style></head>
<body><header class="top"><strong>LEGAL INTAKE / STUDY NOTES</strong><span>DARK TABLET · 2026-11-04</span><a href="backend-dark-tablet.html">흐름도</a><a href="BACKEND_DESIGN.md">상세 설계</a></header>
<div class="layout"><details class="toc" open><summary>공부할 내용</summary><nav aria-label="학습 목차">{nav}</nav></details><article><span class="badge">학습용 설명 · 프로젝트는 구현 전 DRAFT</span><div class="jump"><a href="#chapter-5">비동기부터 읽기</a><a href="#chapter-7">의존성 주입부터 읽기</a><a href="#chapter-15">복습 문제</a></div>{body}<footer class="bottom">실제 프로젝트의 구현 상태는 README를 기준으로 확인합니다. 이 자료의 예제는 가짜 응답만 사용하며 OpenAI API 비용이 발생하지 않습니다.</footer></article></div></body></html>
'''
(ROOT / 'study-guide.html').write_text(document, encoding='utf-8')
assert len(toc) == 17
assert document.count('<details>') == 8
assert document.count('<pre>') == document.count('</pre>')
print(f'Generated study-guide.html: {len(toc)} chapters including references, 8 review answers.')
