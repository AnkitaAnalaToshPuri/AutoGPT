"""Tests for fire-and-forget Web Push delivery."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.api.model import NotificationPayload
from backend.data import push_sender


@pytest.fixture(autouse=True)
def clear_debounce():
    """Reset the per-user debounce state between tests."""
    push_sender._user_last_push.clear()
    yield
    push_sender._user_last_push.clear()


def _make_settings(
    private: str = "vapid-private",
    public: str = "vapid-public",
    email: str = "mailto:push@agpt.co",
) -> MagicMock:
    settings = MagicMock()
    settings.secrets.vapid_private_key = private
    settings.secrets.vapid_public_key = public
    settings.secrets.vapid_claim_email = email
    return settings


def _make_subscription(
    user_id: str = "user-1",
    endpoint: str = "https://push.example.com/sub/1",
    p256dh: str = "test-p256dh",
    auth: str = "test-auth",
) -> MagicMock:
    sub = MagicMock()
    sub.userId = user_id
    sub.endpoint = endpoint
    sub.p256dh = p256dh
    sub.auth = auth
    return sub


def _make_payload(**kwargs) -> NotificationPayload:
    defaults = {"type": "agent_run", "event": "completed"}
    defaults.update(kwargs)
    return NotificationPayload(**defaults)


class TestBuildPushPayload:
    def test_includes_type_and_event(self):
        payload = _make_payload(type="agent_run", event="completed")

        result = push_sender._build_push_payload(payload)

        import json

        parsed = json.loads(result)
        assert parsed["type"] == "agent_run"
        assert parsed["event"] == "completed"

    def test_forwards_known_fields(self):
        payload = _make_payload(
            execution_id="exec-1",
            graph_id="graph-1",
            status="completed",
        )

        result = push_sender._build_push_payload(payload)

        import json

        parsed = json.loads(result)
        assert parsed["execution_id"] == "exec-1"
        assert parsed["graph_id"] == "graph-1"
        assert parsed["status"] == "completed"

    def test_excludes_unknown_fields(self):
        payload = _make_payload(
            custom_field="should-not-appear",
        )

        result = push_sender._build_push_payload(payload)

        import json

        parsed = json.loads(result)
        assert "custom_field" not in parsed

    def test_uses_model_dump_json_mode(self):
        """Ensure model_dump(mode='json') serializes enums to strings."""
        payload = _make_payload(type="agent_run", event="completed")

        result = push_sender._build_push_payload(payload)

        import json

        parsed = json.loads(result)
        assert isinstance(parsed["type"], str)
        assert isinstance(parsed["event"], str)


class TestSendPushForUser:
    @pytest.mark.asyncio
    async def test_skips_when_vapid_private_key_missing(self, mocker):
        mocker.patch.object(
            push_sender,
            "_settings",
            _make_settings(private=""),
        )
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_vapid_public_key_missing(self, mocker):
        mocker.patch.object(
            push_sender,
            "_settings",
            _make_settings(public=""),
        )
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_when_vapid_email_missing(self, mocker):
        mocker.patch.object(
            push_sender,
            "_settings",
            _make_settings(email=""),
        )
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_debounces_rapid_calls(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[],
        )

        await push_sender.send_push_for_user("user-1", _make_payload())
        assert mock_get.await_count == 1

        await push_sender.send_push_for_user("user-1", _make_payload())
        assert mock_get.await_count == 1

    @pytest.mark.asyncio
    async def test_different_users_not_debounced(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[],
        )

        await push_sender.send_push_for_user("user-1", _make_payload())
        await push_sender.send_push_for_user("user-2", _make_payload())

        assert mock_get.await_count == 2

    @pytest.mark.asyncio
    async def test_returns_early_when_no_subscriptions(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[],
        )
        mock_webpush = mocker.patch(
            "backend.data.push_sender.webpush",
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_webpush.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_webpush_for_each_subscription(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub1 = _make_subscription(endpoint="https://push.example.com/sub/1")
        sub2 = _make_subscription(endpoint="https://push.example.com/sub/2")
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub1, sub2],
        )
        mock_webpush = mocker.patch("backend.data.push_sender.webpush")

        await push_sender.send_push_for_user("user-1", _make_payload())

        assert mock_webpush.call_count == 2

        calls = mock_webpush.call_args_list
        endpoints_called = [c.kwargs["subscription_info"]["endpoint"] for c in calls]
        assert "https://push.example.com/sub/1" in endpoints_called
        assert "https://push.example.com/sub/2" in endpoints_called

    @pytest.mark.asyncio
    async def test_webpush_called_with_correct_args(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription(
            user_id="user-1",
            endpoint="https://push.example.com/sub/1",
            p256dh="key-p256dh",
            auth="key-auth",
        )
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )
        mock_webpush = mocker.patch("backend.data.push_sender.webpush")

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_webpush.assert_called_once()
        call_kwargs = mock_webpush.call_args.kwargs
        assert call_kwargs["subscription_info"] == {
            "endpoint": "https://push.example.com/sub/1",
            "keys": {"p256dh": "key-p256dh", "auth": "key-auth"},
        }
        assert call_kwargs["vapid_private_key"] == "vapid-private"
        assert call_kwargs["vapid_claims"] == {"sub": "mailto:push@agpt.co"}
        assert isinstance(call_kwargs["data"], str)

    @pytest.mark.asyncio
    async def test_removes_subscription_on_410_gone(self, mocker):
        from pywebpush import WebPushException

        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription()
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )

        mock_response = MagicMock()
        mock_response.status_code = 410
        exc = WebPushException("Gone", response=mock_response)
        mocker.patch(
            "backend.data.push_sender.webpush",
            side_effect=exc,
        )
        mock_delete = mocker.patch(
            "backend.data.push_sender.delete_push_subscription_by_endpoint",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_delete.assert_awaited_once_with(sub.userId, sub.endpoint)

    @pytest.mark.asyncio
    async def test_removes_subscription_on_404(self, mocker):
        from pywebpush import WebPushException

        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription()
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        exc = WebPushException("Not Found", response=mock_response)
        mocker.patch(
            "backend.data.push_sender.webpush",
            side_effect=exc,
        )
        mock_delete = mocker.patch(
            "backend.data.push_sender.delete_push_subscription_by_endpoint",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_delete.assert_awaited_once_with(sub.userId, sub.endpoint)

    @pytest.mark.asyncio
    async def test_increments_fail_count_on_other_webpush_error(self, mocker):
        from pywebpush import WebPushException

        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription()
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        exc = WebPushException("Too Many Requests", response=mock_response)
        mocker.patch(
            "backend.data.push_sender.webpush",
            side_effect=exc,
        )
        mock_increment = mocker.patch(
            "backend.data.push_sender.increment_fail_count",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_increment.assert_awaited_once_with(sub.userId, sub.endpoint)

    @pytest.mark.asyncio
    async def test_increments_fail_count_when_no_response_object(self, mocker):
        from pywebpush import WebPushException

        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription()
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )

        exc = WebPushException("Connection error")
        mocker.patch(
            "backend.data.push_sender.webpush",
            side_effect=exc,
        )
        mock_increment = mocker.patch(
            "backend.data.push_sender.increment_fail_count",
            new_callable=AsyncMock,
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

        mock_increment.assert_awaited_once_with(sub.userId, sub.endpoint)

    @pytest.mark.asyncio
    async def test_handles_unexpected_exception_gracefully(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        sub = _make_subscription()
        mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[sub],
        )
        mocker.patch(
            "backend.data.push_sender.webpush",
            side_effect=RuntimeError("network down"),
        )

        await push_sender.send_push_for_user("user-1", _make_payload())

    @pytest.mark.asyncio
    async def test_debounce_expires_after_threshold(self, mocker):
        mocker.patch.object(push_sender, "_settings", _make_settings())
        mock_get = mocker.patch(
            "backend.data.push_sender.get_user_push_subscriptions",
            new_callable=AsyncMock,
            return_value=[],
        )

        await push_sender.send_push_for_user("user-1", _make_payload())
        assert mock_get.await_count == 1

        push_sender._user_last_push["user-1"] -= push_sender.DEBOUNCE_SECONDS + 1

        await push_sender.send_push_for_user("user-1", _make_payload())
        assert mock_get.await_count == 2
