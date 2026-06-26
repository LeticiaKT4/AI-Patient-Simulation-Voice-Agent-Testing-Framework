import os
from unittest.mock import patch

from voice_client import VoiceClient


def test_play_text_on_call_uses_control_url_from_call_monitor():
    with patch.dict(os.environ, {"VAPI_API_KEY": "test-key", "TARGET_TEST_NUMBER": "+15551234567"}, clear=False):
        client = VoiceClient()

    with patch("voice_client.requests.get") as mock_get, patch("voice_client.requests.post") as mock_post:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "monitor": {"controlUrl": "https://control.example.test/call-123/control"}
        }
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"status": "ok"}

        result = client.play_text_on_call("call-123", "Hello there")

        assert result == {"status": "ok"}
        mock_get.assert_called_once_with(
            "https://api.vapi.ai/call/call-123",
            headers=client._build_headers(),
            timeout=10,
        )
        mock_post.assert_called_once_with(
            "https://control.example.test/call-123/control",
            json={"type": "say", "content": "Hello there", "endCallAfterSpoken": False},
            headers=client._build_headers(),
            timeout=30,
        )
