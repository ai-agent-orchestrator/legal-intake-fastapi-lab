"""Minimal synchronous comparison app; no DB, AI, or API key.

Adapted from the GET-list pattern in the academy chap01 menu sample.
The separate board-management sample has not been located yet.
"""
from fastapi import FastAPI

app = FastAPI(title="최소 동기 게시판 예제")


@app.get("/posts", summary="샘플 게시글 목록")
def list_posts() -> list[dict[str, int | str]]:
    return [
        {"id": 1, "title": "상담 전 준비자료 안내"},
        {"id": 2, "title": "게시판 이용 안내"},
    ]
