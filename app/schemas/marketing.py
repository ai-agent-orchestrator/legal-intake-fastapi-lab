from pydantic import Field

from app.schemas.base import CamelModel


class PostCreate(CamelModel):
    author_alias: str = Field(default="익명", min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2000)


class ReviewCreate(CamelModel):
    author_alias: str = Field(default="익명", min_length=1, max_length=50)
    rating: int = Field(ge=1, le=5, strict=True)
    content: str = Field(min_length=1, max_length=2000)


class DraftResponse(CamelModel):
    text: str
    review_required: bool
    reason_code: str
    matched_rules: tuple[str, ...]
    generated_at: str
    policy_version: str
    rule_version: str
    source_version: int
    model: str
    version: int
    status: str


class PostResponse(PostCreate):
    post_id: int
    version: int


class ReviewResponse(ReviewCreate):
    review_id: int
    post_id: int
    version: int
    reply_draft: DraftResponse | None = None


class SummaryResponse(DraftResponse):
    post_id: int


class ReplyResponse(DraftResponse):
    review_id: int
