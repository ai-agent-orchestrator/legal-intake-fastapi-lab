"""Render the accepted async security design as an offline explanation."""
from html import escape
from pathlib import Path
import json
import re
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
policy = json.loads((ROOT / 'async-security-design.json').read_text(encoding='utf-8'))
source = (ROOT / 'NEMO_ASYNC_ACTIONS.md').read_text(encoding='utf-8')
assert len(policy['actions']) == len(set(policy['actions'])) == 9
assert all(action in source for action in policy['actions'])
assert policy['apiTargetCount'] == 21
md = MarkdownIt('commonmark', {'html': True}).enable('table')
tokens = md.parse(source)
toc = []
for i,token in enumerate(tokens):
    if token.type == 'heading_open' and token.tag == 'h2':
        anchor = f'reason-{len(toc)+1}'
        token.attrSet('id', anchor)
        toc.append((anchor,tokens[i+1].content))
body = md.renderer.render(tokens, md.options, {}).replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
style = re.search(r'<style>(.*?)</style>', (ROOT / 'study-guide.html').read_text(encoding='utf-8'), flags=re.S).group(1)
nav = ''.join(f'<a href="#{a}">{escape(t)}</a>' for a,t in toc)
html = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>비동기 보안 설계 · 이유와 구현 계약</title><style>{style}</style></head><body>
<header class="top"><strong>LEGAL INTAKE / ASYNC SECURITY DESIGN</strong><a href="readme-preview.html">README</a><a href="backend-dark-tablet.html">흐름도</a><a href="NEMO_ASYNC_ACTIONS.md">원문</a></header>
<div class="layout"><details class="toc" open><summary>설계 이유와 계약</summary><nav aria-label="설계 해설 목차">{nav}</nav></details><article><span class="badge">추천안 채택 · 9개 action 설계 확정 · 미구현</span>{body}<footer class="bottom">API 21개 계획 유지 · 단일 worker 실험 · 구현과 실제 연동 검증은 후속 작업</footer></article></div></body></html>'''
(ROOT / 'async-security-explained.html').write_text(html, encoding='utf-8')
print(f'Generated async-security-explained.html: {len(toc)} sections; 9 accepted actions; API target unchanged.')
