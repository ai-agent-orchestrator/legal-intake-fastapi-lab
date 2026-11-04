import logging
from threading import current_thread

from fastapi import APIRouter

from app.dependencies import ReplyServiceDep, ReviewServiceDep
from app.schemas.review import ReplyResponse, ReviewCreateRequest, ReviewResponse

router = APIRouter(prefix="/api/reviews", tags=["리뷰"])
logger = logging.getLogger("uvicorn.error")


@router.post("", response_model=ReviewResponse, status_code=201)
def register_review(body: ReviewCreateRequest, service: ReviewServiceDep) -> ReviewResponse:
    logger.info("[register] thread=%s", current_thread().name)
    return service.register(body)


@router.get("/{review_id}", response_model=ReviewResponse)
def find_review(review_id: int, service: ReviewServiceDep) -> ReviewResponse:
    logger.info("[find] thread=%s reviewId=%s", current_thread().name, review_id)
    return service.find(review_id)


@router.post("/{review_id}/reply", response_model=ReplyResponse)
async def create_reply(review_id: int, service: ReplyServiceDep) -> ReplyResponse:
    logger.info("[reply] thread=%s reviewId=%s", current_thread().name, review_id)
    return await service.create_reply(review_id)
