import json
from unittest.mock import patch

from voice_client import VoiceClient


def test_call_target_uses_vapi_payload_shape(monkeypatch):
    monkeypatch.setenv("VAPI_API_KEY", "test-key")
    monkeypatch.setenv("TARGET_TEST_NUMBER", "+15551234567")
    monkeypatch.setenv("VAPI_ASSISTANT_ID", "assistant-id")
    monkeypatch.setenv("VAPI_PHONE_NUMBER_ID", "phone-id")

    client = VoiceClient()

    with patch("voice_client.requests.post") as post_mock:
        response = type("Resp", (), {"status_code": 200, "json": lambda self: {"id": "call-123"}, "text": ""})()
        post_mock.return_value = response

        result = client.call_target("hello")

    assert result["call_id"] == "call-123"
    payload = post_mock.call_args.kwargs["json"]
    assert payload["type"] == "outboundPhoneCall"
    assert payload["assistantId"] == "assistant-id"
    assert payload["phoneNumberId"] == "phone-id"
    assert payload["customer"]["number"] == "+15551234567"
    assert payload["assistant"]["firstMessage"] == "hello"
    assert "target" not in payload
    assert "speech" not in payload
