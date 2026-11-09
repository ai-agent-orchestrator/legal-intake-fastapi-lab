"""Single-process synthetic board. Standard library only, no app/framework imports."""
from dataclasses import dataclass, replace
from threading import Lock


class BoardError(Exception):
    def __init__(self, code: str, status: int = 404):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class Draft:
    text: str
    review_required: bool
    reason_code: str
    matched_rules: tuple[str, ...]
    generated_at: str
    policy_version: str
    rule_version: str
    source_version: int
    model: str
    version: int = 0
    status: str = "DRAFT"


@dataclass(frozen=True)
class Post:
    post_id: int
    author_alias: str
    title: str
    content: str
    version: int = 1


@dataclass(frozen=True)
class Review:
    review_id: int
    post_id: int
    author_alias: str
    rating: int
    content: str
    version: int = 1
    reply_draft: Draft | None = None


class BoardStore:
    def __init__(self, max_posts: int = 1000, max_reviews: int = 5000):
        self._posts: dict[int, Post] = {}
        self._reviews: dict[int, Review] = {}
        self._lock = Lock()
        self.max_posts, self.max_reviews = max_posts, max_reviews

    def create_post(self, author_alias: str, title: str, content: str) -> Post:
        with self._lock:
            if len(self._posts) >= self.max_posts:
                raise BoardError("BOARD_CAPACITY_EXCEEDED", 503)
            post = Post(len(self._posts) + 1, author_alias, title, content)
            self._posts[post.post_id] = post
            return post

    def posts(self) -> tuple[Post, ...]:
        with self._lock:
            return tuple(self._posts.values())

    def snapshot_post(self, post_id: int) -> tuple[Post, tuple[Review, ...]]:
        with self._lock:
            if post_id not in self._posts:
                raise BoardError("POST_NOT_FOUND")
            return self._posts[post_id], tuple(r for r in self._reviews.values() if r.post_id == post_id)

    def create_review(self, post_id: int, author_alias: str, rating: int, content: str) -> Review:
        with self._lock:
            if post_id not in self._posts:
                raise BoardError("POST_NOT_FOUND")
            if len(self._reviews) >= self.max_reviews:
                raise BoardError("BOARD_CAPACITY_EXCEEDED", 503)
            if not 1 <= rating <= 5:
                raise ValueError("rating must be 1..5")
            review = Review(len(self._reviews) + 1, post_id, author_alias, rating, content)
            self._reviews[review.review_id] = review
            post = self._posts[post_id]
            self._posts[post_id] = replace(post, version=post.version + 1)
            return review

    def snapshot_review(self, review_id: int) -> Review:
        with self._lock:
            if review_id not in self._reviews:
                raise BoardError("REVIEW_NOT_FOUND")
            return self._reviews[review_id]

    def check_post_version(self, post_id: int, version: int) -> None:
        with self._lock:
            if post_id not in self._posts:
                raise BoardError("POST_NOT_FOUND")
            if self._posts[post_id].version != version:
                raise BoardError("MARKETING_SNAPSHOT_CHANGED", 409)

    def save_reply(self, review_id: int, source_version: int, expected_draft_version: int, draft: Draft) -> Draft:
        with self._lock:
            if review_id not in self._reviews:
                raise BoardError("REVIEW_NOT_FOUND")
            review = self._reviews[review_id]
            current = review.reply_draft.version if review.reply_draft else 0
            if review.version != source_version or current != expected_draft_version:
                raise BoardError("MARKETING_SNAPSHOT_CHANGED", 409)
            if draft.source_version != source_version:
                raise BoardError("MARKETING_SNAPSHOT_CHANGED", 409)
            saved = replace(draft, version=current + 1)
            self._reviews[review_id] = replace(review, reply_draft=saved)
            return saved
