"""Internal contracts. RetrievalUnavailable HTTP mapping is reserved, not installed."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.security.decisions import ActionDecision


class RetrievalStatus(StrEnum):
    OK = "OK"
    EMPTY = "EMPTY"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"


class RetrievalUnavailable(RuntimeError):
    code = "RETRIEVAL_UNAVAILABLE"
    status_code = 503

    def __init__(self):
        super().__init__(self.code)


@dataclass(frozen=True)
class Chunk:
    text: str
    metadata: dict


@dataclass(frozen=True)
class Evidence:
    document_id: str
    chunk_id: str
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    status: RetrievalStatus
    evidence: tuple[Evidence, ...]
    mode: str
    index_version: str


class RetrievedMaterialPolicy(Protocol):
    """B03+ only: input patterns with profile=retrieved, not user-risk scoring.

    check_retrieved_material(chunk) returns a decision. The future caller excludes
    and audits only BLOCK chunks, never calls record_risk_event, and returns EMPTY
    if all chunks are excluded. This protocol has no executable policy yet.
    """

    def check_retrieved_material(self, chunk: Chunk) -> ActionDecision: ...
