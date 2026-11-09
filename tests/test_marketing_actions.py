import asyncio

import pytest

from app.security import marketing_actions, marketing_core
from app.security.context import Envelope, RequestContext
from app.security.decisions import Decision, SecurityError
from app.security.marketing_actions import marketing_registry
from app.security.nemo_adapter import NemoAdapter, RailDirection


@pytest.mark.parametrize("text", [
    "상담 준비를 도와드립니다.", "이용해 주셔서 감사합니다.",
    "100% 승소 보장하지 않습니다.", "무조건 승소를 보장하지 않습니다.",
    "‘무조건 승소’ 같은 표현을 사용하지 않습니다.",
    "‘반드시 보상받습니다’라는 표현은 사용하지 않습니다.",
])
def test_normal_and_directly_rejected_guarantees(text):
    result = marketing_core.check_marketing_response(text)
    assert result.decision.value == "ALLOW" and result.safe_draft == text
    assert not result.review_required


@pytest.mark.parametrize("text,rule", [
    ("100% 승소 보장!", "WIN_100_PERCENT"),
    ("무조건 승소합니다.", "UNCONDITIONAL_WIN"),
    ("반드시 보상받습니다.", "COMPENSATION_PROMISE"),
    ("１００％ 승소 보장", "WIN_100_PERCENT"),
    ("무조\u200b건 승소합니다.", "UNCONDITIONAL_WIN"),
    ("‘무조건 승소’라고 안내드립니다.", "UNCONDITIONAL_WIN"),
    ("승소를 보장하지 않습니다. 그러나 무조건 승소합니다.", "UNCONDITIONAL_WIN"),
    ("100% 승소 보장하지 않지만 반드시 보상받습니다.", "COMPENSATION_PROMISE"),
])
def test_guarantees_require_review_and_are_removed_from_safe_draft(text, rule):
    result = marketing_core.check_marketing_response(text)
    assert result.decision.value == "REVIEW" and result.review_required
    assert result.reason_code == "MARKETING_REVIEW_REQUIRED" and rule in result.matched_rules
    assert marketing_core.check_marketing_response(result.safe_draft).decision.value == "ALLOW"


def test_retains_safe_sentences_and_does_not_echo_risky_claim():
    result = marketing_core.check_marketing_response("이용해 주셔서 감사합니다. 무조건 승소합니다. 문의 사항을 남겨 주세요.")
    assert "감사합니다" in result.safe_draft and "문의 사항" in result.safe_draft
    assert "무조건 승소" not in result.safe_draft


@pytest.mark.parametrize("text", [None, "", " ", "가" * 8001])
def test_checker_errors_do_not_produce_an_unchecked_fallback(text):
    with pytest.raises(marketing_core.MarketingError):
        marketing_core.check_marketing_response(text)


@pytest.mark.parametrize("backend", ["local", pytest.param("nemo", marks=pytest.mark.nemo)])
@pytest.mark.parametrize("risky", [False, True])
def test_real_rails_consume_marketing_allow_or_review(backend, risky):
    async def scenario():
        text = "무조건 승소합니다." if risky else "상담 준비를 도와드립니다."
        context = RequestContext.create("synthetic", "post:1:v1", "marketing")
        adapter = NemoAdapter(marketing_registry(), backend)
        receipt = await adapter.check("check_marketing_response", Envelope.bind(context, text),
                                      direction=RailDirection.OUTPUT)
        assert receipt.decision.decision == (Decision.REVIEW if risky else Decision.ALLOW)
        assert receipt.output.context == context
        assert receipt.output.text == receipt.decision.safe_text
    asyncio.run(scenario())


@pytest.mark.parametrize("backend", ["local", pytest.param("nemo", marks=pytest.mark.nemo)])
def test_checker_failure_is_closed_by_rail(backend, monkeypatch):
    def failure(text):
        raise RuntimeError("synthetic private draft")
    monkeypatch.setattr(marketing_core, "check_marketing_response", failure)
    async def scenario():
        adapter = NemoAdapter(marketing_actions.marketing_registry(), backend)
        source = Envelope.bind(RequestContext.create(None, "post:1:v1", "marketing"), "synthetic private draft")
        with pytest.raises(SecurityError, match="GUARDRAIL_UNAVAILABLE"):
            await adapter.check("check_marketing_response", source, direction=RailDirection.OUTPUT)
    asyncio.run(scenario())


def test_registry_exposes_only_the_named_marketing_action():
    assert marketing_registry() == {"check_marketing_response": marketing_actions.check_marketing_response}


@pytest.mark.parametrize("text", [
    "상담 준비를 도와드립니다.",
    "100% 승소 보장하지 않습니다.",
    "무조건 승소합니다.",
    "반드시 보상받습니다.",
    "100% 승소 보장! 무조건 승소합니다. 반드시 보상받습니다.",
    "감사합니다. 무조건 승소합니다. 문의 사항을 남겨 주세요.",
])
def test_repeat_input_and_safe_draft_transformation_are_idempotent(text):
    first = marketing_core.check_marketing_response(text)
    assert marketing_core.check_marketing_response(text) == first
    again = marketing_core.check_marketing_response(first.safe_draft)
    assert again.safe_draft == first.safe_draft
    assert marketing_core.check_marketing_response(again.safe_draft) == again
    if first.review_required:
        # Rechecking sanitized text is not permission to discard the first REVIEW.
        assert again.decision.value == "ALLOW" and first.review_required


def test_checks_the_complete_output_including_a_late_guarantee():
    text = "상담 절차를 확인합니다.\n" * 100 + "반드시 보상받습니다."
    result = marketing_core.check_marketing_response(text)
    assert result.review_required and result.matched_rules == ("COMPENSATION_PROMISE",)
    assert "반드시 보상받습니다" not in result.safe_draft
    assert result.safe_draft.count("상담 절차를 확인합니다.") == 100


@pytest.mark.parametrize("failure,code", [
    (marketing_core.MarketingError("synthetic private unchecked draft"), "MARKETING_CHECK_UNAVAILABLE"),
    (RuntimeError("synthetic private unchecked draft"), "GUARDRAIL_UNAVAILABLE"),
])
def test_direct_adapter_sanitizes_checker_exceptions_without_a_draft(failure, code, monkeypatch):
    def broken(text):
        raise failure
    monkeypatch.setattr(marketing_core, "check_marketing_response", broken)
    source = Envelope.bind(RequestContext.create(None, "synthetic:1", "marketing"),
                           "synthetic private unchecked draft")
    with pytest.raises(SecurityError) as error:
        marketing_actions.check_marketing_response(source)
    assert error.value.code == code and str(error.value) == code
    assert "unchecked" not in str(error.value) and error.value.__suppress_context__


@pytest.mark.parametrize("result", [
    None,
    {"decision": "ALLOW", "safe_draft": "synthetic private unchecked draft"},
    marketing_core.MarketingDecision(marketing_core.Decision.ALLOW, "changed unchecked draft"),
    marketing_core.MarketingDecision(marketing_core.Decision.REVIEW, "synthetic private unchecked draft", True,
                                     "MARKETING_REVIEW_REQUIRED", ("UNCONDITIONAL_WIN",)),
    marketing_core.MarketingDecision(marketing_core.Decision.REVIEW, "safe draft", False,
                                     "MARKETING_REVIEW_REQUIRED", ("UNCONDITIONAL_WIN",)),
    marketing_core.MarketingDecision(marketing_core.Decision.REVIEW, "safe draft", True,
                                     "MARKETING_REVIEW_REQUIRED", ("UNKNOWN_RULE",)),
    marketing_core.MarketingDecision(marketing_core.Decision.ALLOW, ""),
])
def test_malformed_core_returns_never_become_publishable_decisions(result, monkeypatch):
    monkeypatch.setattr(marketing_core, "check_marketing_response", lambda text: result)
    source = Envelope.bind(RequestContext.create(None, "synthetic:1", "marketing"),
                           "synthetic private unchecked draft")
    with pytest.raises(SecurityError, match="GUARDRAIL_INVALID_DECISION"):
        marketing_actions.check_marketing_response(source)


def test_marketing_core_imports_as_a_single_file_with_only_standard_library():
    import ast
    from pathlib import Path
    import subprocess
    import sys

    path = Path(__file__).resolve().parents[1] / "app/security/marketing_core.py"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)
    script = (
        "import runpy,sys\n"
        "scope=runpy.run_path(sys.argv[1])\n"
        "check=scope['check_marketing_response']\n"
        "assert check('100% 승소 보장!').decision.value == 'REVIEW'\n"
        "assert check('상담 준비 안내').decision.value == 'ALLOW'\n"
        "assert 'app' not in sys.modules\n"
        "print('standalone-core-ok')\n"
    )
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script, str(path)],
                            capture_output=True, text=True, encoding="utf-8", timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "standalone-core-ok"
