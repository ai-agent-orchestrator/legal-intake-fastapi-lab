from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class IntakeNotFoundError(Exception):
    def __init__(self, intake_id: int):
        self.intake_id = intake_id
        super().__init__(f"접수가 존재하지 않습니다. intakeId={intake_id}")


class AiRequestError(Exception):
    pass


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntakeNotFoundError)
    async def handle_missing(_: Request, exc: IntakeNotFoundError):
        return JSONResponse(status_code=404, content={
            "code": "INTAKE_NOT_FOUND", "description": "접수 조회 실패", "detail": str(exc),
        })

    @app.exception_handler(AiRequestError)
    async def handle_ai_error(_: Request, exc: AiRequestError):
        return JSONResponse(status_code=502, content={
            "code": "AI_REQUEST_FAILED", "description": "AI 안내 생성 실패", "detail": str(exc),
        })
