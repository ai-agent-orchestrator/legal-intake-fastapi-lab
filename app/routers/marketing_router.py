from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.dependencies import LlmDep
from app.schemas.marketing import (PostCreate, PostResponse, ReviewCreate, ReviewResponse,
                                   SummaryResponse, ReplyResponse)
from app.services.marketing_service import MarketingService

router = APIRouter(prefix="/api", tags=["Marketing review drafts"])
SessionId = Annotated[str | None, Header(alias="X-Session-ID", min_length=1, max_length=128,
                                        pattern=r"^[A-Za-z0-9_.:-]+$")]


def get_marketing_service(request: Request, client: LlmDep):
    return MarketingService(request.app.state.board_store, request.app.state.session_guard,
                            request.app.state.paid_calls, client)


Service = Annotated[MarketingService, Depends(get_marketing_service)]


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(body: PostCreate, service: Service, session_id: SessionId = None):
    return await service.create_post(body, session_id)


@router.get("/posts", response_model=list[PostResponse])
async def posts(service: Service):
    return await service.posts()


@router.get("/posts/{postId}", response_model=PostResponse)
async def post(postId: int, service: Service):
    return await service.post(postId)


@router.post("/posts/{postId}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(postId: int, body: ReviewCreate, service: Service, session_id: SessionId = None):
    return await service.create_review(postId, body, session_id)


@router.get("/posts/{postId}/reviews", response_model=list[ReviewResponse])
async def reviews(postId: int, service: Service):
    return await service.reviews(postId)


@router.post("/posts/{postId}/ai-summary", response_model=SummaryResponse)
async def summary(postId: int, service: Service, session_id: SessionId = None):
    return await service.summary(postId, session_id)


@router.post("/reviews/{reviewId}/reply-draft", response_model=ReplyResponse)
async def reply(reviewId: int, service: Service, session_id: SessionId = None):
    return await service.reply(reviewId, session_id)
