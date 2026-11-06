"""Render the beginner retrieval notes with the existing offline tablet dark theme."""
import re
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
source = (ROOT/"EMBEDDING_RETRIEVAL_STUDY.md").read_text(encoding="utf-8")
base = (ROOT/"study-guide.html").read_text(encoding="utf-8")
style = re.search(r"<style>(.*?)</style>",base,re.S).group(1)
style += "\n.wrap{max-width:1040px;margin:auto;padding:24px}article{min-width:0}pre{overflow:auto}table{min-width:560px}.table-wrap{overflow:auto}h2{scroll-margin-top:20px}nav a{display:block;padding:8px;min-height:44px}code{overflow-wrap:anywhere}"
md = MarkdownIt("commonmark").enable("table")
tokens = md.parse(source)
toc = []
for i,token in enumerate(tokens):
    if token.type == "heading_open" and token.tag == "h2":
        anchor = "chapter-"+str(len(toc)+1)
        token.attrSet("id",anchor)
        toc.append((anchor,tokens[i+1].content))
body = md.renderer.render(tokens,md.options,{})
body = body.replace("<table>",'<div class="table-wrap" tabindex="0"><table>').replace("</table>","</table></div>")
nav = "".join(f'<a href="#{anchor}">{escape(title)}</a>' for anchor,title in toc)
page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>임베딩과 의미 검색 · 초보 공부</title><style>{style}</style></head><body><main class="wrap"><p><a href="EMBEDDING_RETRIEVAL_STUDY.md">Markdown 원문</a> · <a href="rag-basic-dark-tablet.html">RAG 기본안</a></p><nav aria-label="목차">{nav}</nav><article>{body}</article></main></body></html>'''
assert len(toc)==8
assert "<script" not in page and 'src="http' not in page
(ROOT/"embedding-retrieval-dark-tablet.html").write_text(page,encoding="utf-8")
print("Rendered 8 chapters, offline dark tablet HTML")
