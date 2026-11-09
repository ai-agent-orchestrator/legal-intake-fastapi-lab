from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

POLICY_VERSION = "legal-2026-11-09-v2"


def fingerprint(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RequestContext:
    trace_id: str
    session_id: str
    snapshot: str
    profile: str
    policy_version: str = POLICY_VERSION

    @classmethod
    def create(cls, session_id: str | None, snapshot: str, profile: str):
        # Identifiers are untrusted grouping keys, never authentication credentials.
        trace = uuid4().hex
        normalized_session = (session_id or "").strip() or trace
        return cls(trace, fingerprint(normalized_session), snapshot, profile)


@dataclass(frozen=True)
class Envelope:
    context: RequestContext
    text: str
    digest: str

    @classmethod
    def bind(cls, context: RequestContext, text: str):
        return cls(context, text, fingerprint(text))
