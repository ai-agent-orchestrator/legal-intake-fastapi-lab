"""Render the repository README with the existing Dark Tablet reading style."""
from html import escape
import os
from pathlib import Path
import re
from urllib.parse import unquote
from markdown_it import MarkdownIt

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
source = (ROOT / 'README.md').read_text(encoding='utf-8')
md = MarkdownIt('commonmark', {'html': True}).enable('table')
tokens = md.parse(source)
toc = []
local_targets = []
for i, token in enumerate(tokens):
    if token.type == 'heading_open' and token.tag == 'h2':
        anchor = f'section-{len(toc)+1}'
        token.attrSet('id', anchor)
        toc.append((anchor, tokens[i+1].content))
    for child in token.children or []:
        if child.type not in {'link_open', 'image'}:
            continue
        key = 'href' if child.type == 'link_open' else 'src'
        target = child.attrGet(key) or ''
        if not target or target.startswith(('https:', 'http:', '#')):
            continue
        filename, _, fragment = target.partition('#')
        resolved = (ROOT / unquote(filename)).resolve()
        local_targets.append(resolved)
        child.attrSet(key, Path(os.path.relpath(resolved, DOCS)).as_posix() + (f'#{fragment}' if fragment else ''))
body = md.renderer.render(tokens, md.options, {})
body = body.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
study = (DOCS / 'study-guide.html').read_text(encoding='utf-8')
style = re.search(r'<style>(.*?)</style>', study, flags=re.S).group(1)
nav = ''.join(f'<a href="#{a}">{escape(t)}</a>' for a,t in toc)
html = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>legal-intake-fastapi-lab · README</title><style>{style}</style></head><body>
<header class="top"><strong>LEGAL INTAKE / PROJECT README</strong><span>HOWTO 01 + 02 + 03 · 2026-11-04</span><a href="../README.md">Markdown 원문</a><a href="study-guide.html">공부자료</a><a href="backend-dark-tablet.html">흐름도</a></header>
<div class="layout"><details class="toc" open><summary>README 목차</summary><nav aria-label="README 목차">{nav}</nav></details><article>{body}<footer class="bottom">현재 MVP·리뷰 참고본·후속 확장 설계의 구현 상태를 구분합니다.</footer></article></div></body></html>'''
(DOCS / 'readme-preview.html').write_text(html, encoding='utf-8')
assert len(toc) == 14
missing = [str(p) for p in local_targets if not p.exists()]
assert not missing, missing
assert len(re.findall(r'^```', source, flags=re.M)) % 2 == 0
for topic in ['HOWTO-chap01', 'HOWTO-chap02', 'HOWTO-chap03', '① → ③ → ②', 'dependency_overrides', 'lifespan', 'parametrize', 'p95', 'check_request_budget', '법률 마케팅 게시판', 'check_marketing_response', '21개', '아직 구현']:
    assert topic in source, topic
print(f'README verified: {len(source.splitlines())} lines, {len(toc)} sections; local links and code fences valid.')
