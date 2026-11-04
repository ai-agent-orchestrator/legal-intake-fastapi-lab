from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ReviewNotFoundError(Exception):
    def __init__(self, review_id: int):
        self.review_id = review_id
        super().__init__(f"리뷰가 존재하지 않습니다. reviewId={review_id}")


class AiRequestError(Exception):
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReviewNotFoundError)
    async def handle_missing(_: Request, exc: ReviewNotFoundError):
        return JSONResponse(status_code=404, content={
            "code": "REVIEW_NOT_FOUND", "description": "리뷰 조회 실패",
            "detail": str(exc),
        })

    @app.exception_handler(AiRequestError)
    async def handle_ai_error(_: Request, exc: AiRequestError):
        return JSONResponse(status_code=502, content={
            "code": "AI_REQUEST_FAILED", "description": "답글 생성 실패",
            "detail": str(exc),
        })
