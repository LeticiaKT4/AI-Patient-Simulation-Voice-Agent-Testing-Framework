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
    """
    Minimal voice client wrapper for a Vapi-style HTTP voice API.
    """

    def get_call_transcript(self, call_id: str) -> str | None:
        """Fetch transcript for a completed call from Vapi, if available. Prints raw status for debugging. Handles retry/timing and speaker preservation."""
        import time
        attempts = 5
        last_status = None
        for attempt in range(1, attempts + 1):
            try:
                status = self.get_call_status(call_id)
                last_status = status
                logger.debug(f"[VAPI get_call_status attempt {attempt}/{attempts}] Raw status: {json.dumps(status, indent=2, ensure_ascii=False)}")
                # Try multiple possible field names
                transcript_data = None
                for k in ["transcript", "transcription", "full_transcript", "fullTranscription"]:
                    transcript_data = status.get(k)
                    if transcript_data:
                        break
                if transcript_data:
                    if isinstance(transcript_data, str):
                        logger.info(f"Call {call_id}: transcript found (string, source=Vapi, key={k}).")
                        return transcript_data.strip()
                    elif isinstance(transcript_data, list):
                        logger.info(f"Call {call_id}: transcript found (list, source=Vapi, key={k}).")
                        return "\n".join(map(str, transcript_data)).strip()
                    logger.info(f"Call {call_id}: transcript found (other type, key={k}).")
                        
                # Try reconstructing from event logs, preserving speakers
                events = status.get("events") or status.get("call_events") or []
                dialogue = []
                for ev in events:
                    speaker = ev.get("speaker") or ev.get("role") or ev.get("from")
                    text = ev.get("transcript") or ev.get("text") or ev.get("utterance")
                    if speaker and text:
                        dialogue.append(f"{speaker}: {text.strip()}")
                if dialogue:
                    logger.info(f"Call {call_id}: transcript reconstructed from events, with speakers preserved.")
                    return "\n".join(dialogue)
                # Otherwise, transcript still not available; wait and retry
                if attempt < attempts:
                    logger.info(f"Call {call_id}: transcript not yet available, retrying in 5s (attempt {attempt}/{attempts})...")
                    time.sleep(5)
            except Exception as e:
                logger.warning(f"Failed to fetch real transcript for call {call_id} on attempt {attempt}: {e}")
                if attempt < attempts:
                    time.sleep(5)
        # Final fallback after retries
        logger.warning(f"Real transcript unavailable for call {call_id} after {attempts} attempts. Last status: {json.dumps(last_status, indent=2, ensure_ascii=False) if last_status else 'No status'}")
        return None



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
        """Create an outbound Vapi call and print/log full response and call_id."""
        # Always use /call endpoint, do not guess/version/pluralize.
        endpoint_path = "/call"
        url = f"{self.base_url.rstrip('/')}" + endpoint_path

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

        print(f"[VAPI REQUEST] POST {url}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.info("Vapi request payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            logger.info("[VAPI RESPONSE] Status=%d, content=%s", resp.status_code, resp.text)
            print(f"\n[VAPI RESPONSE] Status: {resp.status_code}")
            print(resp.text)
            if resp.status_code >= 200 and resp.status_code < 300:
                try:
                    data = resp.json()
                except ValueError:
                    data = {"raw_text": resp.text}
                call_id = data.get("id")
                print(f"[VAPI] Extracted call_id: {call_id}")
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
        """Send a follow-up message to an active Vapi call using live call control."""
        lookup_url = f"{self.base_url.rstrip('/')}/call/{call_id}"
        try:
            resp = requests.get(lookup_url, headers=self._build_headers(), timeout=10)
            resp.raise_for_status()
            call_data = resp.json()
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
            raise requests.exceptions.HTTPError(f"Vapi call lookup failed (status={status}) at {lookup_url}: {text}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Vapi call lookup request failed: {exc}") from exc

        monitor = call_data.get("monitor") or {}
        control_url = monitor.get("controlUrl") or monitor.get("control_url")
        if not control_url:
            raise RuntimeError(f"Vapi call {call_id} did not return a controlUrl. Response={call_data}")

        payload = {"type": "say", "content": tts_text, "endCallAfterSpoken": False}
        try:
            resp = requests.post(control_url, json=payload, headers=self._build_headers(), timeout=30)
            resp.raise_for_status()
            try:
                data = resp.json()
            except ValueError:
                data = {"raw_text": resp.text}
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
            raise requests.exceptions.HTTPError(f"Vapi action failed (status={status}) at {control_url}: {text}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Vapi action request failed: {exc}") from exc

        logger.debug("Sent follow-up message to call %s via %s", call_id, control_url)
        return data

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        # Use ONLY the official singular /call/{id} endpoint per docs—never guess, version, or pluralize
        url = f"{self.base_url.rstrip('/')}/call/{call_id}"
        try:
            resp = requests.get(url, headers=self._build_headers(), timeout=10)
            logger.info(f"[VAPI GET CALL] GET {url} Status={resp.status_code}")
            print(f"[VAPI GET CALL] GET {url} Status={resp.status_code}")
            print(resp.text)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                logger.error("Failed to decode call status JSON, returning text.")
                return {"raw_text": resp.text}
        except requests.exceptions.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            text = getattr(exc.response, "text", "") if getattr(exc, "response", None) else ""
            logger.error(f"Vapi status check failed (status={status}) at {url}: {text}")
            print(f"Vapi status check failed (status={status}) at {url}: {text}")
            raise
