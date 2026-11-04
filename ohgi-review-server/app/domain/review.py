from dataclasses import dataclass


@dataclass(frozen=True)
class Review:
    review_id: int
    customer_name: str
    rating: int
    content: str
