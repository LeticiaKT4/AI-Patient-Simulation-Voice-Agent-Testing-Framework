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
        # Optional overrides for providers with custom paths/payloads
        self.call_path_override = os.getenv("VAPI_CALL_PATH")  # e.g. /voice/call or /v2/calls
        self.auth_header_name = os.getenv("VAPI_AUTH_HEADER_NAME", "Authorization")
        # Optional JSON template with placeholders {to},{from},{text},{language},{voice}
        self.call_json_template = os.getenv("VAPI_CALL_JSON_TEMPLATE")
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
        # Allow provider to expect a different header name via VAPI_AUTH_HEADER_NAME
        return {self.auth_header_name: f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def call_target(self, tts_text: str, language: str = "en-US", voice: str = "alloy") -> Dict[str, Any]:
        """Create an outbound call and speak the initial TTS text.

        Returns a dict with `call_id` and the raw provider response.
        """
        # Candidate endpoint paths to try (Vapi standard `/call` prioritized).
        # Removed `/calls/outbound` which is not supported by Vapi.
        candidates = [
            "/calls",
            "/call",
            "/v1/call",
            "/v1/calls",
            "/calls/create",
            "/v1/calls/create",
            "/voice/calls",
            "/v1/voice/calls",
            "/voice/call",
            "/v1/voice/call",
        ]
        # If user provided an explicit path, try it first
        if self.call_path_override:
            if not self.call_path_override.startswith("/"):
                self.call_path_override = f"/{self.call_path_override}"
            candidates.insert(0, self.call_path_override)

        # Candidate header styles
        header_variants = [
            {self.auth_header_name: f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {"X-API-Key": self.api_key, "Content-Type": "application/json"},
            {self.auth_header_name: f"Bearer {self.api_key}", "X-API-Key": self.api_key, "Content-Type": "application/json"},
        ]

        # Candidate payload shapes
        payload_variants = []
        # If user provided a JSON template, format and use it as highest priority
        if self.call_json_template:
            try:
                tpl = self.call_json_template.format(to=self.target_number, from_=self.source_number or "", text=tts_text, language=language, voice=voice)
                # Allow templates to use {from} by replacing placeholder name
                tpl = tpl.replace("{from}", self.source_number or "")
                payload_variants.append(json.loads(tpl))
            except Exception as e:
                logger.warning("Failed to parse VAPI_CALL_JSON_TEMPLATE: %s", e)

        # Vapi-specific payload (preferred when assistant/phone ids are set)
        if self.assistant_id and self.phone_number_id:
            vapi_payload = {
                "assistantId": self.assistant_id,
                "customer": {"phoneNumber": self.target_number},
                "phoneNumberId": self.phone_number_id,
                "instructions": tts_text,
            }
            payload_variants.append(vapi_payload)

        # Generic payload shapes (fallbacks)
        p1 = {"to": self.target_number, "voice": {"language": language, "voice": voice, "text": tts_text}}
        if self.source_number:
            p1["from"] = self.source_number
        payload_variants.append(p1)

        p2 = {"to": self.target_number, "from": self.source_number or "", "actions": [{"type": "tts", "text": tts_text, "language": language, "voice": voice}]}
        payload_variants.append(p2)

        p3 = {"destination": self.target_number, "caller": self.source_number or "", "tts": tts_text}
        payload_variants.append(p3)

        p4 = {"phone": self.target_number, "from": self.source_number or "", "message": tts_text}
        payload_variants.append(p4)

        p5 = {"type": "call", "target": self.target_number, "speech": {"text": tts_text, "language": language, "voice": voice}}
        payload_variants.append(p5)

        errors = []
        # Try combinations until one succeeds
        for path in candidates:
            url = f"{self.base_url.rstrip('/')}{path}"
            for headers in header_variants:
                for payload in payload_variants:
                    try:
                        logger.debug("Trying Vapi POST %s with headers=%s payload=%s", url, list(headers.keys()), {k: (v if k not in ['voice','actions'] else '...') for k,v in payload.items()})
                        resp = requests.post(url, json=payload, headers=headers, timeout=30)
                        # Log non-2xx responses and continue; capture body
                        if resp.status_code >= 200 and resp.status_code < 300:
                            try:
                                data = resp.json()
                            except ValueError:
                                data = {"raw_text": resp.text}
                            call_id = data.get("id") or data.get("call_id") or data.get("sid") or data.get("callId")
                            logger.info("Vapi call created at %s, id=%s", url, call_id)
                            return {"call_id": call_id, "response": data}
                        else:
                            text = resp.text
                            errors.append({"url": url, "status": resp.status_code, "body": text, "headers": list(headers.keys())})
                            logger.debug("Vapi attempt failed %s status=%s body=%s", url, resp.status_code, text)
                    except requests.RequestException as e:
                        errors.append({"url": url, "error": str(e)})

        # If we reached here, no candidate worked
        details = json.dumps(errors, indent=2)
        raise RuntimeError(f"Vapi call creation failed. Tried multiple endpoints/payloads. Details: {details}")

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
