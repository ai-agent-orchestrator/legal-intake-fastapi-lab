"""Public API of the byte-verified mirror; app/security remains canonical."""
import re
from .policy_core import (
    Decision, TextDecision, PolicyError, MASKING_VERSION, MAX_POLICY_CHARS, PROFILES,
    check_input_policy, mask_personal_data, check_output_policy,
)
from .marketing_core import (
    MarketingDecision, MarketingError, RULE_VERSION, check_marketing_response,
)

_version = re.fullmatch(r"legal-pii-(\d{4})-(\d{2})-(\d{2})-v(\d+)", MASKING_VERSION)
if _version is None:
    raise RuntimeError("MASKING_VERSION format changed; update package version mapping")
__version__ = ".".join(str(int(part)) for part in _version.groups())

__all__ = ["Decision", "TextDecision", "PolicyError", "MASKING_VERSION", "MAX_POLICY_CHARS", "PROFILES",
           "check_input_policy", "mask_personal_data", "check_output_policy", "MarketingDecision",
           "MarketingError", "RULE_VERSION", "check_marketing_response", "__version__"]
