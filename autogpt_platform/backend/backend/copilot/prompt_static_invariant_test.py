"""Regression guards: the baseline + SDK system prompts must stay identical
across users regardless of the ``GRAPHITI_MEMORY`` LaunchDarkly flag.

Background: the Langfuse prompt is compiled with ``users_information=""`` and
both paths append ``SHARED_TOOL_NOTES`` / ``get_sdk_supplement()`` plus the
Graphiti memory instructions.  A previous bug flag-gated the supplement on
``is_enabled_for_user(user_id)`` — which meant flag-on users and flag-off
users got different system-prompt byte sequences, forking the Anthropic
prompt cache by cohort and burning a fresh ~500-token cache write on every
cross-cohort first call.

These tests pin the contract at the source level so the conditional never
silently returns.  A richer end-to-end test would be nice but would require
exercising the entire streaming pipeline; for a contract this localised the
source assertion is tighter and costs nothing to run.
"""

import inspect
import re

_GATED_SUPPLEMENT_PATTERNS = [
    # Pattern 1: direct ternary on graphiti_enabled
    re.compile(r"get_graphiti_supplement\(\)\s+if\s+graphiti_enabled"),
    # Pattern 2: variable-assignment ternary
    re.compile(
        r"graphiti_supplement\s*=\s*get_graphiti_supplement\(\)\s+if\s+\w+\s+else\s+\"\""
    ),
]


def _assert_supplement_always_appended(src: str, path: str) -> None:
    for pat in _GATED_SUPPLEMENT_PATTERNS:
        assert not pat.search(src), (
            f"{path}: Graphiti supplement is flag-gated again — this forks the "
            f"Anthropic prompt cache per-user cohort.  Always append the "
            f"supplement; memory tools self-gate at handler level."
        )
    assert "get_graphiti_supplement()" in src, (
        f"{path}: Graphiti supplement call is missing — the memory instructions "
        f"must be present so every user's system prompt hashes identically."
    )


def test_baseline_graphiti_supplement_unconditionally_appended():
    from backend.copilot.baseline import service

    src = inspect.getsource(service.stream_chat_completion_baseline)
    _assert_supplement_always_appended(
        src, "baseline/service.py::stream_chat_completion_baseline"
    )


def test_sdk_graphiti_supplement_unconditionally_appended():
    from backend.copilot.sdk import service

    # SDK path: find the streaming entrypoint — the supplement assembly sits
    # inside one of a handful of top-level streaming coroutines.  We check all
    # async def declarations in the module so the guard doesn't rely on a
    # stable function name.
    src = inspect.getsource(service)
    _assert_supplement_always_appended(src, "sdk/service.py")
