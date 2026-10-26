"""Capture-plan version checks, including the immutable original plan."""
import hashlib
import json

ORIGINAL_PLAN_SHA256 = "f9a8eae46f7c1fa94829ae5fab48777f4a10d2a242eb5ae77d0f3ff9d57a4dcc"
CAPTURE_SPEC = "incoming_and_generated_prefixes_v1"
BUDGET_APPROVAL = "shared_cap_15usd_v1"


def approved_stream_plan(raw: bytes) -> bool:
    if hashlib.sha256(raw).hexdigest() == ORIGINAL_PLAN_SHA256:
        return True
    plan = json.loads(raw)
    return (plan.get("capture_spec") == CAPTURE_SPEC
            and plan.get("budget_approval") == BUDGET_APPROVAL)
