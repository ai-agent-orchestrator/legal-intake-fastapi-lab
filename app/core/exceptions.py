from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.security.decisions import PolicyBlocked, SecurityError
from app.marketing.board_core import BoardError


class IntakeNotFoundError(Exception):
    def __init__(self, intake_id: int):
        self.intake_id = intake_id
        super().__init__(f"접수가 존재하지 않습니다. intakeId={intake_id}")


class AiRequestError(Exception):
    def __init__(self, message: str, *, cost_usd=None):
        super().__init__(message)
        self.cost_usd = cost_usd


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BoardError)
    async def handle_board(_: Request, exc: BoardError):
        return JSONResponse(status_code=exc.status, content={"code": exc.code,
                            "description": "게시판 요청을 완료하지 못했습니다."})

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        # FastAPI's default detail includes the rejected input and may echo PII.
        known_locations = {"body", "path", "query", "header", "intake_id", "X-Session-ID",
                           "clientName", "caseType", "coreStatement", "desiredNextStep"}
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": [part if isinstance(part, int) or part in known_locations else "[field]"
                     for part in error["loc"]],
             "type": error["type"], "msg": "입력 형식이나 길이를 확인하세요."}
            for error in exc.errors()
        ]})

    @app.exception_handler(SecurityError)
    async def handle_security(_: Request, exc: SecurityError):
        return JSONResponse(status_code=exc.status, content={
            "code": exc.code, "description": "보안 검사를 완료하지 못했습니다.",
        })

    @app.exception_handler(PolicyBlocked)
    async def handle_policy(_: Request, exc: PolicyBlocked):
        return JSONResponse(status_code=200, content={
            "blocked": True, "reasonCode": exc.decision.reason_code,
            "answer": "보안 정책상 처리할 수 없는 요청입니다.",
        })

    @app.exception_handler(IntakeNotFoundError)
    async def handle_missing(_: Request, exc: IntakeNotFoundError):
        return JSONResponse(status_code=404, content={
            "code": "INTAKE_NOT_FOUND", "description": "접수 조회 실패", "detail": str(exc),
        })

    @app.exception_handler(AiRequestError)
    async def handle_ai_error(_: Request, exc: AiRequestError):
        return JSONResponse(status_code=502, content={
            "code": "AI_REQUEST_FAILED", "description": "AI 안내 생성 실패",
            "detail": "AI 안내를 생성하지 못했습니다. 설정과 연결 상태를 확인하세요.",
        })
