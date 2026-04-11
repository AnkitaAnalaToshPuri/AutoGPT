"""Tests for the unified MCP Write tool (file_tools.py).

Covers: normal write, large content warning, partial truncation,
complete truncation, path validation (no escape from working dir),
E2B delegation, and CLI built-in Write disallowance.
"""

import os

import pytest

from backend.copilot.sdk.tool_adapter import SDK_DISALLOWED_TOOLS

from .file_tools import (
    _LARGE_CONTENT_WARN_CHARS,
    WRITE_TOOL_NAME,
    WRITE_TOOL_SCHEMA,
    _handle_write_non_e2b,
)


@pytest.fixture
def sdk_cwd(tmp_path, monkeypatch):
    """Provide a temporary SDK working directory."""
    cwd = str(tmp_path / "copilot-test-session")
    os.makedirs(cwd, exist_ok=True)
    monkeypatch.setattr("backend.copilot.sdk.file_tools.get_sdk_cwd", lambda: cwd)
    # Patch is_allowed_local_path to allow paths under our tmp cwd

    def _patched_is_allowed(path: str, cwd_arg: str | None = None) -> bool:
        resolved = os.path.realpath(path)
        norm_cwd = os.path.realpath(cwd)
        return resolved == norm_cwd or resolved.startswith(norm_cwd + os.sep)

    monkeypatch.setattr(
        "backend.copilot.sdk.file_tools.is_allowed_local_path",
        _patched_is_allowed,
    )
    return cwd


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestWriteToolSchema:
    def test_file_path_is_first_property(self):
        """file_path should be listed first in schema so truncation preserves it."""
        props = list(WRITE_TOOL_SCHEMA["properties"].keys())
        assert props[0] == "file_path"

    def test_both_fields_required(self):
        assert "file_path" in WRITE_TOOL_SCHEMA["required"]
        assert "content" in WRITE_TOOL_SCHEMA["required"]


# ---------------------------------------------------------------------------
# Normal write
# ---------------------------------------------------------------------------


class TestNormalWrite:
    @pytest.mark.asyncio
    async def test_write_creates_file(self, sdk_cwd):
        result = await _handle_write_non_e2b(
            {"file_path": "hello.txt", "content": "Hello, world!"}
        )
        assert not result["isError"]
        written = open(os.path.join(sdk_cwd, "hello.txt")).read()
        assert written == "Hello, world!"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, sdk_cwd):
        result = await _handle_write_non_e2b(
            {"file_path": "sub/dir/file.py", "content": "print('hi')"}
        )
        assert not result["isError"]
        assert os.path.isfile(os.path.join(sdk_cwd, "sub", "dir", "file.py"))

    @pytest.mark.asyncio
    async def test_write_absolute_path_within_cwd(self, sdk_cwd):
        abs_path = os.path.join(sdk_cwd, "abs.txt")
        result = await _handle_write_non_e2b(
            {"file_path": abs_path, "content": "absolute"}
        )
        assert not result["isError"]
        assert open(abs_path).read() == "absolute"

    @pytest.mark.asyncio
    async def test_success_message_contains_path(self, sdk_cwd):
        result = await _handle_write_non_e2b({"file_path": "msg.txt", "content": "ok"})
        text = result["content"][0]["text"]
        assert "Successfully wrote" in text
        assert "msg.txt" in text


# ---------------------------------------------------------------------------
# Large content warning
# ---------------------------------------------------------------------------


class TestLargeContentWarning:
    @pytest.mark.asyncio
    async def test_large_content_warns(self, sdk_cwd):
        big_content = "x" * (_LARGE_CONTENT_WARN_CHARS + 1)
        result = await _handle_write_non_e2b(
            {"file_path": "big.txt", "content": big_content}
        )
        assert not result["isError"]
        text = result["content"][0]["text"]
        assert "WARNING" in text
        assert "large" in text.lower()

    @pytest.mark.asyncio
    async def test_normal_content_no_warning(self, sdk_cwd):
        result = await _handle_write_non_e2b(
            {"file_path": "small.txt", "content": "small"}
        )
        text = result["content"][0]["text"]
        assert "WARNING" not in text


# ---------------------------------------------------------------------------
# Truncation detection
# ---------------------------------------------------------------------------


class TestTruncationDetection:
    @pytest.mark.asyncio
    async def test_partial_truncation_content_no_path(self, sdk_cwd):
        """Simulates API truncating file_path but preserving content."""
        result = await _handle_write_non_e2b({"content": "some content here"})
        assert result["isError"]
        text = result["content"][0]["text"]
        assert "truncated" in text.lower()
        assert "file_path" in text.lower()

    @pytest.mark.asyncio
    async def test_complete_truncation_empty_args(self, sdk_cwd):
        """Simulates API truncating to empty args {}."""
        result = await _handle_write_non_e2b({})
        assert result["isError"]
        text = result["content"][0]["text"]
        assert "truncated" in text.lower()
        assert "smaller steps" in text.lower()

    @pytest.mark.asyncio
    async def test_empty_file_path_string(self, sdk_cwd):
        """Empty string file_path should trigger truncation error."""
        result = await _handle_write_non_e2b({"file_path": "", "content": "data"})
        assert result["isError"]


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


class TestPathValidation:
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, sdk_cwd):
        result = await _handle_write_non_e2b(
            {"file_path": "../../etc/passwd", "content": "evil"}
        )
        assert result["isError"]
        text = result["content"][0]["text"]
        assert "must be within" in text.lower()

    @pytest.mark.asyncio
    async def test_absolute_outside_cwd_blocked(self, sdk_cwd):
        result = await _handle_write_non_e2b(
            {"file_path": "/etc/passwd", "content": "evil"}
        )
        assert result["isError"]

    @pytest.mark.asyncio
    async def test_no_sdk_cwd_returns_error(self, monkeypatch):
        monkeypatch.setattr("backend.copilot.sdk.file_tools.get_sdk_cwd", lambda: "")
        result = await _handle_write_non_e2b({"file_path": "test.txt", "content": "hi"})
        assert result["isError"]
        text = result["content"][0]["text"]
        assert "working directory" in text.lower()


# ---------------------------------------------------------------------------
# CLI built-in Write is disallowed
# ---------------------------------------------------------------------------


class TestCliBuiltinWriteDisallowed:
    def test_write_in_disallowed_tools(self):
        assert "Write" in SDK_DISALLOWED_TOOLS

    def test_tool_name_is_write(self):
        assert WRITE_TOOL_NAME == "Write"
