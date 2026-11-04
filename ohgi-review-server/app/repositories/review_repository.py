from threading import Lock

from app.core.exceptions import ReviewNotFoundError
from app.domain.review import Review


class ReviewRepository:
    """서버 재시작 시 초기화. 동기 핸들러의 동시 접근을 짧은 lock으로 보호."""
    def __init__(self):
        self._reviews: dict[int, Review] = {}
        self._next_id = 1
        self._lock = Lock()

    def save(self, customer_name: str, rating: int, content: str) -> Review:
        with self._lock:
            review = Review(self._next_id, customer_name, rating, content)
            self._reviews[review.review_id] = review
            self._next_id += 1
            return review

    def find_by_id(self, review_id: int) -> Review:
        with self._lock:
            review = self._reviews.get(review_id)
        if review is None:
            raise ReviewNotFoundError(review_id)
        return review
