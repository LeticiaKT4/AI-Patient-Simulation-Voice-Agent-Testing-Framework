"""
Voice scenario orchestration for patient and receptionist conversation using Vapi.

Creates an outbound call to the configured `TARGET_TEST_NUMBER`, streams
patient speech to the call, runs a multi-turn conversation between the
patient agent and a receptionist LLM, and saves both transcript text and
call metadata in `logs/`.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from llm_client import get_llm_client
from patient_agent import PatientAgent
from patient_profiles import create_sample_patient, PatientProfile
from scenario_generator import Scenario, create_scenario_for_testing
from voice_client import VoiceClient

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class ReceptionistAgent:
    """Simple receptionist LLM wrapper for multi-turn replies."""

    def __init__(self, llm_client: Any):
        self.llm_client = llm_client
        self.conversation_history: list[dict[str, str]] = []

    def _build_system_prompt(self) -> str:
        return (
            "You are a polite medical office receptionist answering patient calls. "
            "Ask clarifying questions, confirm details, and help the patient achieve their goal. "
            "Keep responses professional and natural."
        )

    def respond_to_patient(self, patient_message: str) -> str:
        self.conversation_history.append({"role": "user", "content": patient_message})
        reply = self.llm_client.chat_completion(messages=self.conversation_history, system_prompt=self._build_system_prompt())
        self.conversation_history.append({"role": "assistant", "content": reply})
        logger.debug("Receptionist: %s", reply)
        return reply


class VoiceSession:
    """Manage a voice-enabled patient simulation session."""

    def __init__(self, patient_profile: Optional[PatientProfile] = None, scenario: Optional[Scenario] = None):
        self.patient_profile = patient_profile or create_sample_patient()
        self.scenario = scenario or create_scenario_for_testing()
        self.llm_client = get_llm_client()
        self.patient_agent = PatientAgent(patient_profile=self.patient_profile, scenario=self.scenario, llm_client=self.llm_client)
        self.receptionist_agent = ReceptionistAgent(self.llm_client)
        self.voice_client = VoiceClient()
        self.transcript_lines: list[str] = []
        self.call_metadata: dict[str, Any] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def _format_line(self, speaker: str, text: str) -> str:
        return f"{speaker}: {text}"

    def _save_artifacts(self) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        transcript_path = LOGS_DIR / f"transcript_{timestamp}.txt"
        metadata_path = LOGS_DIR / f"metadata_{timestamp}.json"

        transcript_path.write_text("\n".join(self.transcript_lines), encoding="utf-8")
        self.call_metadata["transcript_path"] = str(transcript_path)
        self.call_metadata["metadata_path"] = str(metadata_path)

        metadata = {
            "patient_id": self.patient_profile.patient_id,
            "patient_name": f"{self.patient_profile.first_name} {self.patient_profile.last_name}",
            "scenario_id": self.scenario.scenario_id,
            "scenario_type": self.scenario.scenario_type.value,
            "difficulty": self.scenario.difficulty.value,
            "target_number": self.voice_client.target_number,
            "started_at": self.start_time.isoformat() if self.start_time else None,
            "ended_at": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": None,
            "call_metadata": self.call_metadata,
        }

        if self.start_time and self.end_time:
            metadata["duration_seconds"] = int((self.end_time - self.start_time).total_seconds())

        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info("Saved transcript to %s", transcript_path)
        logger.info("Saved metadata to %s", metadata_path)

        return {"transcript_path": str(transcript_path), "metadata_path": str(metadata_path)}

    def start_call(self) -> Optional[str]:
        """Start a voice call to the configured test number and speak opening.

        Returns call_id or None.
        """
        self.start_time = datetime.now(timezone.utc)
        opening = self.patient_agent.initiate_call()
        self.transcript_lines.append(self._format_line("Patient", opening))

        call_data = self.voice_client.call_target(tts_text=opening)
        call_id = call_data.get("call_id")
        self.call_metadata = {
            "call_id": call_id,
            "call_response": call_data.get("response"),
            "source_number": self.voice_client.source_number,
            "target_number": self.voice_client.target_number,
        }
        self.transcript_lines.append(self._format_line("System", f"Call created with ID: {call_id}"))
        return call_id

    def continue_conversation(self, max_exchanges: int = 12, delay_seconds: float = 3.0) -> str:
        """Run a simulated live conversation between patient and receptionist.

        Each exchange consists of receptionist reply then patient reply. The
        loop sleeps between turns and attempts to stream patient speech to
        the call so audio is heard live. By default this runs long enough
        to exceed one minute (12 exchanges × 6s approx).
        """
        if not self.patient_agent.conversation_history:
            raise RuntimeError("Patient call has not been started.")

        patient_message = self.patient_agent.conversation_history[-1]["content"]
        for exchange in range(max_exchanges):
            receptionist_message = self.receptionist_agent.respond_to_patient(patient_message)
            self.transcript_lines.append(self._format_line("Receptionist", receptionist_message))
            time.sleep(delay_seconds)

            patient_message = self.patient_agent.respond_to_receptionist(receptionist_message)
            self.transcript_lines.append(self._format_line("Patient", patient_message))
            time.sleep(delay_seconds)

            call_id = self.call_metadata.get("call_id")
            if call_id:
                try:
                    self.voice_client.play_text_on_call(call_id, patient_message)
                except Exception as exc:
                    logger.warning("Unable to stream follow-up text to call: %s", exc)

        return self.get_transcript()

    def get_transcript(self) -> str:
        return "\n".join(self.transcript_lines)

    def finish(self) -> dict[str, str]:
        """Persist transcript and metadata to logs and return paths."""
        self.end_time = datetime.now(timezone.utc)
        return self._save_artifacts()


def main() -> None:
    """CLI flow for manual voice session testing with Vapi."""
    print("\n🏥 AI Patient Voice Simulation\n")
    print("This will place a single outbound call to the configured TARGET_TEST_NUMBER.")
    print("The patient AI opening prompt is spoken over Vapi, and the full simulated conversation is logged.")

    patient_profile = create_sample_patient("standard")
    scenario = create_scenario_for_testing()
    session = VoiceSession(patient_profile=patient_profile, scenario=scenario)

    call_id = session.start_call()
    print(f"Call started. ID: {call_id}")
    print("Streaming a multi-turn conversation between patient and receptionist AI...")

    transcript = session.continue_conversation(max_exchanges=12, delay_seconds=3.0)
    artifacts = session.finish()

    print("\nConversation complete.")
    print(f"Transcript saved: {artifacts['transcript_path']}")
    print(f"Metadata saved: {artifacts['metadata_path']}")
    print("\nSample transcript: \n")
    print(transcript)


if __name__ == "__main__":
    main()
