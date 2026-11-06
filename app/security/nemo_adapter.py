"""L01: explicit local and NeMo rails, with request-local action receipts."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import StrEnum
from inspect import isawaitable
import re
from types import MappingProxyType
from typing import Callable, Mapping
from uuid import uuid4

from app.security.context import Envelope, RequestContext, fingerprint
from app.security.decisions import ActionDecision, Decision, SecurityError


class RailDirection(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True)
class RailReceipt:
    source: Envelope
    decision: ActionDecision
    output: Envelope


@dataclass
class _Invocation:
    name: str
    source: Envelope
    arguments: dict
    decisions: list[ActionDecision] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)


_current: ContextVar[_Invocation] = ContextVar("legal_rail_invocation")

_COLANG = '''
define bot legal refusal
  "요청을 처리할 수 없습니다."

define flow legal input rail
  $result = execute legal_dispatch
  if $result["decision"] == "BLOCK"
    bot legal refusal
    stop
  if $result["decision"] == "TRANSFORM"
    $user_message = $result["text"]

define flow legal output rail
  $result = execute legal_dispatch
  if $result["decision"] == "BLOCK"
    bot legal refusal
    stop
  if $result["decision"] == "TRANSFORM"
    $bot_message = $result["text"]
'''
_YAML = '''
models: []
rails:
  input:
    flows: [legal input rail]
  output:
    flows: [legal output rail]
'''


class _NoConversationHistory(dict):
    def __setitem__(self, key, value):
        # One-shot validation has no conversation state to reuse or retain.
        pass


class NemoAdapter:
    """A registered action must run exactly once and its rail must consume its result."""
    def __init__(self, actions: Mapping[str, Callable], backend: str = "local"):
        if backend not in {"local", "nemo"} or not actions or any(
            not re.fullmatch(r"[a-z][a-z0-9_]*", name) or not callable(fn)
            for name, fn in actions.items()
        ):
            raise ValueError("Invalid server guardrail configuration")
        self.backend = backend
        self.actions = MappingProxyType(dict(actions))
        self._rails = None
        if backend == "nemo":
            try:
                from nemoguardrails import LLMRails, RailsConfig
                from nemoguardrails.actions import action
                self._rails = LLMRails(RailsConfig.from_content(
                    colang_content=_COLANG, yaml_content=_YAML,
                ))
                self._rails.events_history_cache = _NoConversationHistory()
                self._rails.register_action(action(name="legal_dispatch")(self._dispatch), name="legal_dispatch")
            except Exception:
                # An explicitly requested runtime is never silently replaced by local checks.
                raise SecurityError("GUARDRAIL_UNAVAILABLE") from None

    async def _dispatch(self):
        invocation = _current.get()
        try:
            result = self.actions[invocation.name](invocation.source, **invocation.arguments)
            if isawaitable(result):
                result = await result
            if not isinstance(result, ActionDecision) or not isinstance(result.decision, Decision):
                raise SecurityError("GUARDRAIL_INVALID_DECISION")
            if result.decision in {Decision.TRANSFORM, Decision.REVIEW} and not isinstance(result.safe_text, str):
                raise SecurityError("GUARDRAIL_INVALID_DECISION")
            invocation.decisions.append(result)
            # REVIEW also consumes a sanitized draft in the runtime, while keeping its own decision.
            return {"decision": "TRANSFORM" if result.decision == Decision.REVIEW else result.decision.value,
                    "text": result.safe_text}
        except Exception as exc:
            invocation.errors.append(exc)
            return {"decision": "BLOCK", "text": None}

    async def check(self, name: str, source: Envelope, *, direction=RailDirection.INPUT, **arguments) -> RailReceipt:
        if name not in self.actions or not isinstance(direction, RailDirection):
            raise SecurityError("GUARDRAIL_NOT_CONFIGURED")
        if (not isinstance(source, Envelope) or not isinstance(source.context, RequestContext)
                or not isinstance(source.text, str) or fingerprint(source.text) != source.digest):
            raise SecurityError("REQUEST_CONTEXT_MISMATCH", 500)
        invocation = _Invocation(name, source, arguments)
        token = _current.set(invocation)
        try:
            if self._rails is None:
                await self._dispatch()
                runtime_result = None
            else:
                # NeMo receives an opaque, unique marker, never the original personal data.
                marker = "legal-check-" + uuid4().hex
                role = "user" if direction == RailDirection.INPUT else "assistant"
                runtime_result = await self._rails.check_async([{"role": role, "content": marker}])
            if invocation.errors:
                error = invocation.errors[0]
                if isinstance(error, SecurityError):
                    raise error
                raise SecurityError("GUARDRAIL_UNAVAILABLE")
            if len(invocation.decisions) != 1:
                raise SecurityError("GUARDRAIL_INVALID_DECISION")
            decision = invocation.decisions[0]
            if runtime_result is not None:
                blocked = str(runtime_result.status.value).upper() == "BLOCKED"
                if blocked != (decision.decision == Decision.BLOCK):
                    raise SecurityError("GUARDRAIL_INVALID_DECISION")
                expected_text = decision.safe_text if decision.decision in {Decision.TRANSFORM, Decision.REVIEW} else marker
                if not blocked and runtime_result.content != expected_text:
                    raise SecurityError("GUARDRAIL_INVALID_DECISION")
            text = ("요청을 처리할 수 없습니다." if decision.decision == Decision.BLOCK
                    else decision.safe_text if decision.decision in {Decision.TRANSFORM, Decision.REVIEW}
                    else source.text)
            return RailReceipt(source, decision, Envelope.bind(source.context, text))
        except SecurityError:
            raise
        except Exception:
            raise SecurityError("GUARDRAIL_UNAVAILABLE") from None
        finally:
            _current.reset(token)
