"""
Patient AI agent that simulates realistic patient behavior.

This module ties together:
- LLM client for model interactions
- Patient profiles for personality consistency
- Scenario context for goal-directed behavior
"""

import logging
from typing import Optional

from llm_client import LLMClient, get_llm_client
from patient_profiles import PatientProfile
from scenario_generator import Scenario

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatientAgent:
    """
    AI patient that simulates realistic patient behavior in conversations.
    
    Maintains consistency through:
    - Patient profile (demographics, medical history, personality)
    - Scenario context (current goal, complications)
    - Conversation history (for context retention)
    """
    
    def __init__(
        self,
        patient_profile: PatientProfile,
        scenario: Scenario,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize a patient agent.
        
        Args:
            patient_profile: Patient's demographics and medical info
            scenario: Current testing scenario with goals
            llm_client: LLM client (uses global if None)
        """
        self.profile = patient_profile
        self.scenario = scenario
        self.llm_client = llm_client or get_llm_client()
        
        # Conversation state
        self.conversation_history: list[dict] = []
        self.message_count = 0
        
        logger.info(
            f"PatientAgent initialized: {patient_profile.first_name} "
            f"({scenario.scenario_type.value})"
        )
    
    def _build_system_prompt(self) -> str:
        """
        STRONG role-locked prompt: patient ONLY, never an AI/assistant/chatbot.
        """
        # Patient/persona details
        personality_str = ", ".join(self.profile.personality_traits) or "realistic"
        challenges_str = ", ".join(self.profile.communication_challenges) or "none"

        system_prompt = f"""
You are simulating a PATIENT in a phone call with a medical clinic receptionist.

CRITICAL RULES:
- You are NOT an AI assistant.
- You are NOT a chatbot.
- You must NEVER mention being an AI.
- You must stay fully in character as a human patient at all times.
- You must NEVER explain system behavior or how you work.

Identity:
- You are a real patient named according to the scenario below.
- You do NOT have access to system information.

Behavior:
- Speak like a real human on a phone call.
- Keep responses short and natural (1-2 sentences typical).
- Do not be overly formal or explanatory.
- If asked about identity, respond as a patient would, NOT as an AI.

GOAL: Complete the medical interaction (appointment, question, refill, etc.) NATURALLY and stay in character at all times!

--- YOUR PATIENT PROFILE ---
Name: {self.profile.first_name} {self.profile.last_name}
Phone: {self.profile.contact_info.phone_number}
Insurance: {self.profile.insurance_provider.value}
Primary Doctor: {self.profile.primary_physician}

Personality Traits: {personality_str}
Communication Challenges: {challenges_str}
Speaking Style: {self.profile.speaking_style}

--- MEDICAL HISTORY ---
{self.profile.medical_history.notes if self.profile.medical_history.notes else "No specific notes"}
Current Medications: {', '.join(self.profile.medical_history.current_medications) or 'None'}
Allergies: {', '.join(self.profile.medical_history.allergies) or 'None'}
Chronic Conditions: {', '.join(self.profile.medical_history.chronic_conditions) or 'None'}

--- CURRENT SCENARIO ---
Goal: {self.scenario.primary_goal}
Context: {self.scenario.context}
{f'Complications to address: {', '.join(self.scenario.complications)}' if self.scenario.complications else ''}
"""
        return system_prompt
    
    def respond_to_receptionist(self, receptionist_message: str) -> str:
        """
        Generate patient response to receptionist.
        
        Args:
            receptionist_message: What the receptionist said
            
        Returns:
            Patient's response
        """
        self.message_count += 1
        
        # Add receptionist message to history as user input
        self.conversation_history.append({
            "role": "user",
            "content": receptionist_message,
        })
        
        # Generate patient response
        try:
            response = self.llm_client.chat_completion(
                messages=self.conversation_history,
                system_prompt=self._build_system_prompt(),
            )
            
            # Add patient response to history as assistant output
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
            })
            
            logger.debug(f"[{self.message_count}] Patient: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating patient response: {e}")
            raise
    
    def initiate_call(self) -> str:
        """
        Generate the patient's opening statement when calling.
        
        Returns:
            Patient's initial greeting/request
        """
        self.message_count = 0
        self.conversation_history = []
        
        opening_prompt = f"""Generate a realistic opening statement for a patient calling a medical office.

The patient wants to: {self.scenario.primary_goal}

Make it natural and concise (2-3 sentences max). Start with a greeting or a direct statement of purpose.
Don't be overly formal - speak like a real person calling their doctor's office."""
        
        # Create a simple message list for just the opening
        messages = [{"role": "user", "content": opening_prompt}]
        
        try:
            opening = self.llm_client.chat_completion(
                messages=messages,
                system_prompt=self._build_system_prompt(),
            )
            
            # Add patient's opening statement as assistant output
            self.conversation_history.append({
                "role": "assistant",
                "content": opening,
            })
            
            logger.info(f"Call initiated by patient: {opening[:80]}...")
            return opening
            
        except Exception as e:
            logger.error(f"Error generating opening statement: {e}")
            raise
    
    def get_conversation_history(self) -> list[dict]:
        """Get the full conversation history."""
        return self.conversation_history.copy()
    
    def get_transcript(self) -> str:
        """
        Generate a readable transcript of the conversation.
        
        Returns:
            Formatted conversation transcript
        """
        transcript = f"""
{'='*60}
PATIENT SIMULATION TRANSCRIPT
{'='*60}

Patient: {self.profile.first_name} {self.profile.last_name}
Scenario: {self.scenario.scenario_type.value}
Difficulty: {self.scenario.difficulty.value}
Goal: {self.scenario.primary_goal}

{'='*60}
CONVERSATION
{'='*60}
"""
        for msg in self.conversation_history:
            role = "Receptionist" if msg["role"] == "user" else "Patient"
            transcript += f"\n{role}: {msg['content']}\n"
        
        return transcript
    
    def reset_conversation(self) -> None:
        """Reset conversation history for a new call."""
        self.conversation_history = []
        self.message_count = 0
        logger.info("Conversation reset")
