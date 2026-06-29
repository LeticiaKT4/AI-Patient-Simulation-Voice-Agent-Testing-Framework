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




class VoiceSession:
    """Manage a voice-enabled patient simulation session."""

    def __init__(self, patient_profile: Optional[PatientProfile] = None, scenario: Optional[Scenario] = None):
        self.patient_profile = patient_profile or create_sample_patient()
        self.scenario = scenario or create_scenario_for_testing()
        self.llm_client = get_llm_client()
        self.patient_agent = PatientAgent(patient_profile=self.patient_profile, scenario=self.scenario, llm_client=get_llm_client())
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
        # Real Vapi conversation occurs outside this logic; nothing is done here.
        return self.get_transcript()

    def get_transcript(self) -> str:
        return "\n".join(self.transcript_lines)

    def finish(self) -> dict[str, str]:
        """Poll for call completion, then persist transcript and metadata to logs; returns artifacts."""
        import time
        self.end_time = datetime.now(timezone.utc)

        call_id = self.call_metadata.get("call_id")
        if not call_id:
            logger.error("No call_id available; cannot fetch transcript.")
            return {}

        # Poll call status until finished or timeout (10 minutes)
        timeout = 600  # seconds
        poll_interval = 5
        waited = 0
        terminal_statuses = {"ended", "completed", "finished"}
        while waited < timeout:
            status_response = self.voice_client.get_call_status(call_id)
            call_status = (status_response.get("status") or status_response.get("call_status") or "").lower()
            logger.info(f"Call {call_id} status: {call_status} (waited {waited}s)")
            if call_status in terminal_statuses:
                break
            if call_status in {"queued", "ringing", "in-progress"}:
                time.sleep(poll_interval)
                waited += poll_interval
            else:
                # Unknown/unexpected status; treat as terminal
                logger.error(f"Encountered unexpected call status '{call_status}', proceeding to fetch transcript.")
                break
        else:
            logger.error(f"Timeout waiting for call to finish (waited {timeout}s). Proceeding anyway.")

        transcript_source = "real_vapi"
        real_transcript = self.voice_client.get_call_transcript(call_id)
        if real_transcript:
            logger.info(f"Using real transcript from Vapi for call {call_id} (source=real_vapi)")
            self.transcript_lines = [line for line in real_transcript.splitlines() if line.strip()]
        else:
            logger.error(f"No transcript available after call finished for call {call_id}.")
            self.transcript_lines = []

        artifacts = self._save_artifacts()

        # ==== Post-call evaluation (only runs if transcript is nonempty) ====
        if self.transcript_lines:
            try:
                from evaluation_client import ReceptionistEvaluator
                evaluator = ReceptionistEvaluator()
                transcript = self.get_transcript()
                evaluation_result = evaluator.evaluate(transcript)
                evaluation_result["_transcript_source"] = transcript_source

                # Save evaluation to logs/evaluation_<timestamp>.json
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                import json
                eval_path = LOGS_DIR / f"evaluation_{timestamp}.json"
                eval_path.write_text(json.dumps(evaluation_result, indent=2, ensure_ascii=False), encoding="utf-8")
                artifacts["evaluation_path"] = str(eval_path)
                logging.info(f"Saved evaluation to {eval_path}")

                # Save summary txt
                summary_path = LOGS_DIR / f"evaluation_summary_{timestamp}.txt"
                def render_summary(data):
                    if "error" in data:
                        return "[Evaluation error] " + str(data["error"])
                    if "raw_output" in data:
                        return "[Malformed LLM output, raw below:]\n\n" + data["raw_output"]
                    parts = []
                    source = data.get('_transcript_source', '?')
                    parts.append(f"Receptionist Evaluation (score: {data.get('score', '?')}/10, transcript_source: {source})\n")
                    if q := data.get('questions_asked'):
                        parts.append(f"Questions asked:\n{q}\n")
                    if m := data.get('missed_or_incorrect'):
                        parts.append(f"Missed or incorrect responses:\n{m}\n")
                    if u := data.get('urgency_handling'):
                        parts.append(f"Urgency and personality handling:\n{u}\n")
                    if c := data.get('communication_quality'):
                        parts.append(f"Communication quality:\n{c}\n")
                    if i := data.get('improvements'):
                        parts.append(f"Actionable improvements:\n{i}\n")
                    return "\n".join(parts)
                summary_txt = render_summary(evaluation_result)
                summary_path.write_text(summary_txt, encoding="utf-8")
                artifacts["evaluation_summary_path"] = str(summary_path)
                logging.info(f"Saved evaluation summary to {summary_path}")
            except Exception as exc:
                logging.error(f"Evaluation failed: {exc}")

        # Print out the final transcript to ensure console, file, and evaluation match
        print("\n======= FINAL TRANSCRIPT (source: {}):\n".format(transcript_source))
        print(self.get_transcript())

        return artifacts

        artifacts = self._save_artifacts()

        # ==== Post-call evaluation ====
        try:
            from evaluation_client import ReceptionistEvaluator
            evaluator = ReceptionistEvaluator()
            transcript = self.get_transcript()
            evaluation_result = evaluator.evaluate(transcript)
            evaluation_result["_transcript_source"] = transcript_source

            # Save evaluation to logs/evaluation_<timestamp>.json
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            import json
            eval_path = LOGS_DIR / f"evaluation_{timestamp}.json"
            eval_path.write_text(json.dumps(evaluation_result, indent=2, ensure_ascii=False), encoding="utf-8")
            artifacts["evaluation_path"] = str(eval_path)
            logging.info(f"Saved evaluation to {eval_path}")

            # Save summary txt
            summary_path = LOGS_DIR / f"evaluation_summary_{timestamp}.txt"
            def render_summary(data):
                if "error" in data:
                    return "[Evaluation error] " + str(data["error"])
                if "raw_output" in data:
                    return "[Malformed LLM output, raw below:]\n\n" + data["raw_output"]
                parts = []
                source = data.get('_transcript_source', '?')
                parts.append(f"Receptionist Evaluation (score: {data.get('score', '?')}/10, transcript_source: {source})\n")
                if q := data.get('questions_asked'):
                    parts.append(f"Questions asked:\n{q}\n")
                if m := data.get('missed_or_incorrect'):
                    parts.append(f"Missed or incorrect responses:\n{m}\n")
                if u := data.get('urgency_handling'):
                    parts.append(f"Urgency and personality handling:\n{u}\n")
                if c := data.get('communication_quality'):
                    parts.append(f"Communication quality:\n{c}\n")
                if i := data.get('improvements'):
                    parts.append(f"Actionable improvements:\n{i}\n")
                return "\n".join(parts)
            summary_txt = render_summary(evaluation_result)
            summary_path.write_text(summary_txt, encoding="utf-8")
            artifacts["evaluation_summary_path"] = str(summary_path)
            logging.info(f"Saved evaluation summary to {summary_path}")
        except Exception as exc:
            logging.error(f"Evaluation failed: {exc}")
        return artifacts


def main() -> None:
    """CLI flow for manual voice session testing with Vapi."""
    print("\n🏥 AI Patient Voice Simulation\n")
    print("This will place a single outbound call to the configured TARGET_TEST_NUMBER.")
    print("The patient AI opening prompt is spoken over Vapi, and the full simulated conversation is logged.")


    # ---- Personality selection ----
    personalities = ["standard", "anxious", "impatient", "elderly"]
    print("\nSelect patient personality:")
    for i, p in enumerate(personalities, 1):
        print(f"{i}. {p.capitalize()}")
    personality_idx = int(input("Enter number [1]: ") or "1") - 1
    patient_profile = create_sample_patient(personalities[personality_idx])

    # ---- Scenario type selection ----
    from scenario_generator import ScenarioType, ScenarioDifficulty  # Ensure enums are imported
    scenario_types = list(ScenarioType)
    print("\nSelect scenario type:")
    for i, s in enumerate(scenario_types, 1):
        print(f"{i}. {s.value.replace('_', ' ').capitalize()}")
    scenario_idx = int(input("Enter number [1]: ") or "1") - 1
    scenario_type = scenario_types[scenario_idx]

    # ---- Scenario difficulty selection ----
    difficulties = list(ScenarioDifficulty)
    print("\nSelect scenario difficulty:")
    for i, d in enumerate(difficulties, 1):
        print(f"{i}. {d.value.capitalize()}")
    diff_idx = int(input("Enter number [2]: ") or "2") - 1
    difficulty = difficulties[diff_idx]

    scenario = create_scenario_for_testing(scenario_type, difficulty)
    session = VoiceSession(patient_profile=patient_profile, scenario=scenario)

    call_id = session.start_call()
    print(f"Call started. ID: {call_id}")
    print("Streaming a multi-turn conversation between patient and receptionist AI...")

    transcript = session.continue_conversation(max_exchanges=12, delay_seconds=3.0)
    artifacts = session.finish()

    print("\nConversation complete.")
    print(f"Transcript saved: {artifacts['transcript_path']}")
    print(f"Metadata saved: {artifacts['metadata_path']}")


if __name__ == "__main__":
    main()
