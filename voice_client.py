"""
Vapi voice client for AI patient simulation.

This module provides a minimal HTTP wrapper around a Vapi-like voice API.
It intentionally avoids using an external SDK so the integration is simple
and easy to test. Credentials and numbers are read from `.env`.
"""

import logging
import json
import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


class VoiceClient:
    """Minimal voice client wrapper for a Vapi-style HTTP voice API.

    Environment variables used:
    - VAPI_API_KEY (required)
    - VAPI_BASE_URL (optional, defaults to https://api.vapi.ai)
    - VAPI_ASSISTANT_ID (optional, Vapi assistant id for `/call` endpoint)
    - VAPI_PHONE_NUMBER_ID (optional, Vapi phoneNumberId for `/call` endpoint)
    - VAPI_SOURCE_NUMBER (optional)
    - TARGET_TEST_NUMBER (required)
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("VAPI_API_KEY")
        self.base_url = os.getenv("VAPI_BASE_URL", "https://api.vapi.ai")
        self.source_number = os.getenv("VAPI_SOURCE_NUMBER")
        self.assistant_id = os.getenv("VAPI_ASSISTANT_ID")
        self.phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")
        self.target_number = os.getenv("TARGET_TEST_NUMBER")
        # Optional override for providers with a custom endpoint path.
        self.call_path_override = os.getenv("VAPI_CALL_PATH")  # e.g. /voice/call or /v2/calls
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        missing = []
        if not self.api_key:
            missing.append("VAPI_API_KEY")
        if not self.target_number:
            missing.append("TARGET_TEST_NUMBER")

        if missing:
            raise ValueError(
                "Missing Vapi voice configuration. Please set the following "
                f"variables in .env: {', '.join(missing)}"
            )

    def _build_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def call_target(self, tts_text: str, language: str = "en-US", voice: str = "alloy") -> Dict[str, Any]:
        """Create an outbound VAPI phone call using a single supported payload structure."""
        endpoint_path = self.call_path_override or "/call"
        if not endpoint_path.startswith("/"):
            endpoint_path = f"/{endpoint_path}"
        url = f"{self.base_url.rstrip('/')}{endpoint_path}"

        payload: Dict[str, Any] = {
            "type": "outboundPhoneCall",
            "customer": {"number": self.target_number},
            "assistant": {"firstMessage": tts_text},
        }
        if self.assistant_id:
            payload["assistantId"] = self.assistant_id
        if self.phone_number_id:
            payload["phoneNumberId"] = self.phone_number_id

        headers = self._build_headers()

        print(f"VAPI payload being sent to {url}:")
        print(json.dumps(payload, indent=2))
        logger.info("Vapi request payload: %s", json.dumps(payload, indent=2))

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    data = resp.json()
                except ValueError:
                    data = {"raw_text": resp.text}
                call_id = data.get("id") or data.get("call_id") or data.get("sid") or data.get("callId")
                logger.info("Vapi call created at %s, id=%s", url, call_id)
                return {"call_id": call_id, "response": data}

            error_body = resp.text
            raise RuntimeError(
                f"Vapi call creation failed (status={resp.status_code}) at {url}. "
                f"Headers={headers} Payload={json.dumps(payload)} Response={error_body}"
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Vapi call creation request failed: {exc}") from exc

    def play_text_on_call(self, call_id: str, tts_text: str, language: str = "en-US", voice: str = "alloy") -> Dict[str, Any]:
        """Send a follow-up TTS action to an active call."""
        payload = {"action": "tts", "voice": {"language": language, "voice": voice, "text": tts_text}}
        url = f"{self.base_url.rstrip('/')}/calls/{call_id}/actions"
        try:
            resp = requests.post(url, json=payload, headers=self._build_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404 and "/v1" not in self.base_url.rstrip("/"):
                alt_url = f"{self.base_url.rstrip('/')}/v1/calls/{call_id}/actions"
                logger.info("Received 404 when sending action to %s, retrying with %s", url, alt_url)
                resp = requests.post(alt_url, json=payload, headers=self._build_headers(), timeout=30)
                try:
                    resp.raise_for_status()
                    data = resp.json()
                except requests.exceptions.HTTPError:
                    text = getattr(resp, "text", "")
                    raise requests.exceptions.HTTPError(f"Vapi action failed (status={resp.status_code}) at {alt_url}: {text}")
            else:
                text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
                raise requests.exceptions.HTTPError(f"Vapi action failed (status={status}) at {url}: {text}")

        logger.debug("Sent follow-up TTS to call %s", call_id)
        return data

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/calls/{call_id}"
        try:
            resp = requests.get(url, headers=self._build_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404 and "/v1" not in self.base_url.rstrip("/"):
                alt_url = f"{self.base_url.rstrip('/')}/v1/calls/{call_id}"
                logger.info("Received 404 when fetching status from %s, retrying with %s", url, alt_url)
                resp = requests.get(alt_url, headers=self._build_headers(), timeout=10)
                try:
                    resp.raise_for_status()
                    return resp.json()
                except requests.exceptions.HTTPError:
                    text = getattr(resp, "text", "")
                    raise requests.exceptions.HTTPError(f"Vapi status check failed (status={resp.status_code}) at {alt_url}: {text}")
            else:
                text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
                raise requests.exceptions.HTTPError(f"Vapi status check failed (status={status}) at {url}: {text}")
