import os
from unittest.mock import patch

from voice_scenario import VoiceSession


def test_finish_saves_evaluation_when_evaluator_succeeds(tmp_path, monkeypatch):
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "TARGET_TEST_NUMBER": "+15551234567",
        "LLM_EVALUATOR_MODEL": "openai/gpt-4",
    }, clear=False):
        session = VoiceSession()

    session.transcript_lines = ["Patient: Hello", "Receptionist: Hi, how can I help?"]

    with patch("voice_scenario.ReceptionistEvaluator.evaluate_transcript") as mock_evaluate:
        mock_evaluate.return_value = "Final score: 8/10\nActionable improvements: ..."
        artifacts = session.finish()

    assert "evaluation_path" in artifacts
    assert artifacts["evaluation_path"] is not None
    assert os.path.exists(artifacts["evaluation_path"])


def test_finish_continues_if_evaluation_fails(tmp_path, monkeypatch):
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "TARGET_TEST_NUMBER": "+15551234567",
        "LLM_EVALUATOR_MODEL": "openai/gpt-4",
    }, clear=False):
        session = VoiceSession()

    session.transcript_lines = ["Patient: Hello", "Receptionist: Hi, how can I help?"]

    with patch("voice_scenario.ReceptionistEvaluator.evaluate_transcript") as mock_evaluate:
        mock_evaluate.side_effect = RuntimeError("Evaluation service unavailable")
        artifacts = session.finish()

    assert artifacts["transcript_path"] is not None
    assert artifacts["metadata_path"] is not None
    assert "evaluation_path" in artifacts and artifacts["evaluation_path"] is None
