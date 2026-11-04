from dataclasses import asdict

from app.repositories.review_repository import ReviewRepository
from app.schemas.review import ReviewCreateRequest, ReviewResponse


class ReviewService:
    def __init__(self, repository: ReviewRepository):
        self.repository = repository

    def register(self, request: ReviewCreateRequest) -> ReviewResponse:
        review = self.repository.save(request.customer_name, request.rating, request.content)
        return ReviewResponse(**asdict(review))

    def find(self, review_id: int) -> ReviewResponse:
        return ReviewResponse(**asdict(self.repository.find_by_id(review_id)))
