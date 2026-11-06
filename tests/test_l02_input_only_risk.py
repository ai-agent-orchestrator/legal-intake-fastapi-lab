"""New v1 contract tests; original 95 cases and expectations remain unchanged."""
import asyncio

import pytest

from app.security.context import Envelope, RequestContext
from app.security.nemo_adapter import NemoAdapter
from app.security.risk_store import RiskStore
from app.security.session_actions import RISK_REASONS, SessionRiskActions


@pytest.mark.parametrize("backend", ["local", pytest.param("nemo", marks=pytest.mark.nemo)])
@pytest.mark.parametrize("stage,reason", [
    ("output", "OUTPUT_POLICY_BLOCKED"),
    ("output", "PROMPT_INJECTION"),
    ("retrieved", "PROMPT_INJECTION"),
    ("input", "OUTPUT_POLICY_BLOCKED"),
])
def test_output_and_material_violations_never_score_user_risk(backend, stage, reason):
    store = RiskStore(60, 10, 1)
    actions = SessionRiskActions(store)
    adapter = NemoAdapter(actions.registry(), backend)
    source = Envelope.bind(RequestContext.create("synthetic", "v1-test", "guidance"),
                           "synthetic confidential text")

    async def scenario():
        result = await adapter.check("record_risk_event", source, stage=stage, reason=reason)
        assert result.decision.detail_code == "NON_POLICY_EVENT"

    asyncio.run(scenario())
    assert "OUTPUT_POLICY_BLOCKED" not in RISK_REASONS
    assert not store.events and not store.blocked(source.context.session_id)
    if stage != "input":
        assert list(actions.audit_events) == [{"traceId": source.context.trace_id,
                                              "stage": stage, "reasonCode": reason}]
        assert source.text not in str(actions.audit_events)


def test_only_confirmed_input_policy_reason_scores():
    store = RiskStore(60, 10, 1)
    actions = SessionRiskActions(store)
    source = Envelope.bind(RequestContext.create("synthetic", "v1-test", "guidance"), "text")
    actions.record_risk_event(source, stage="input", reason="PROMPT_INJECTION")
    assert store.blocked(source.context.session_id) and len(store.events) == 1
    assert not actions.audit_events
