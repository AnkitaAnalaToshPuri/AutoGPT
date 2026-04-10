"""Unit tests for ChatConfig."""

import pytest

from .config import ChatConfig

# Env vars that the ChatConfig validators read — must be cleared so they don't
# override the explicit constructor values we pass in each test.
_ENV_VARS_TO_CLEAR = (
    "CHAT_USE_E2B_SANDBOX",
    "CHAT_E2B_API_KEY",
    "E2B_API_KEY",
    "CHAT_USE_OPENROUTER",
    "CHAT_API_KEY",
    "OPEN_ROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CHAT_BASE_URL",
    "OPENROUTER_BASE_URL",
    "OPENAI_BASE_URL",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)


class TestOpenrouterActive:
    """Tests for the openrouter_active property."""

    def test_enabled_with_credentials_returns_true(self):
        cfg = ChatConfig(
            use_openrouter=True,
            api_key="or-key",
            base_url="https://openrouter.ai/api/v1",
        )
        assert cfg.openrouter_active is True

    def test_enabled_but_missing_api_key_returns_false(self):
        cfg = ChatConfig(
            use_openrouter=True,
            api_key=None,
            base_url="https://openrouter.ai/api/v1",
        )
        assert cfg.openrouter_active is False

    def test_disabled_returns_false_despite_credentials(self):
        cfg = ChatConfig(
            use_openrouter=False,
            api_key="or-key",
            base_url="https://openrouter.ai/api/v1",
        )
        assert cfg.openrouter_active is False

    def test_strips_v1_suffix_and_still_valid(self):
        cfg = ChatConfig(
            use_openrouter=True,
            api_key="or-key",
            base_url="https://openrouter.ai/api/v1",
        )
        assert cfg.openrouter_active is True

    def test_invalid_base_url_returns_false(self):
        cfg = ChatConfig(
            use_openrouter=True,
            api_key="or-key",
            base_url="not-a-url",
        )
        assert cfg.openrouter_active is False


class TestAnthropicApiKey:
    """Tests for the anthropic_api_key field and validator."""

    def test_reads_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        cfg = ChatConfig()
        assert cfg.anthropic_api_key == "sk-ant-test"

    def test_none_when_not_set(self):
        cfg = ChatConfig()
        assert cfg.anthropic_api_key is None

    def test_explicit_value_overrides_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
        cfg = ChatConfig(anthropic_api_key="explicit")
        assert cfg.anthropic_api_key == "explicit"


class TestDefaultModelNames:
    """Default model names should use direct Anthropic IDs (not OpenRouter format)."""

    def test_default_model_is_direct_anthropic(self):
        cfg = ChatConfig()
        assert "/" not in cfg.model
        assert cfg.model.startswith("claude-")

    def test_fast_model_is_direct_anthropic(self):
        cfg = ChatConfig()
        assert "/" not in cfg.fast_model
        assert cfg.fast_model.startswith("claude-")


class TestE2BActive:
    """Tests for the e2b_active property — single source of truth for E2B usage."""

    def test_both_enabled_and_key_present_returns_true(self):
        """e2b_active is True when use_e2b_sandbox=True and e2b_api_key is set."""
        cfg = ChatConfig(use_e2b_sandbox=True, e2b_api_key="test-key")
        assert cfg.e2b_active is True

    def test_enabled_but_missing_key_returns_false(self):
        """e2b_active is False when use_e2b_sandbox=True but e2b_api_key is absent."""
        cfg = ChatConfig(use_e2b_sandbox=True, e2b_api_key=None)
        assert cfg.e2b_active is False

    def test_disabled_returns_false(self):
        """e2b_active is False when use_e2b_sandbox=False regardless of key."""
        cfg = ChatConfig(use_e2b_sandbox=False, e2b_api_key="test-key")
        assert cfg.e2b_active is False
