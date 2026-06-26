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
        Build the system prompt that defines patient behavior.
        
        This prompt ensures the AI stays in character and addresses
        the scenario's goals consistently.
        
        Returns:
            System prompt string
        """
        personality_str = ", ".join(self.profile.personality_traits) or "realistic"
        challenges_str = ", ".join(self.profile.communication_challenges) or "none"
        
        system_prompt = f"""You are a patient calling a medical office receptionist.

=== PATIENT PROFILE ===
Name: {self.profile.first_name} {self.profile.last_name}
Phone: {self.profile.contact_info.phone_number}
Insurance: {self.profile.insurance_provider.value}
Primary Doctor: {self.profile.primary_physician}

=== PERSONALITY & COMMUNICATION ===
Communication Style: {self.profile.speaking_style}
Personality Traits: {personality_str}
Communication Challenges: {challenges_str}

=== MEDICAL HISTORY ===
{self.profile.medical_history.notes if self.profile.medical_history.notes else "No specific notes"}
Current Medications: {', '.join(self.profile.medical_history.current_medications) or 'None'}
Allergies: {', '.join(self.profile.medical_history.allergies) or 'None'}
Chronic Conditions: {', '.join(self.profile.medical_history.chronic_conditions) or 'None'}

=== CURRENT SCENARIO ===
Your Goal: {self.scenario.primary_goal}
Context: {self.scenario.context}

{f"Complications to address: {', '.join(self.scenario.complications)}" if self.scenario.complications else ""}

=== INSTRUCTIONS ===
1. Stay in character as this patient throughout the conversation
2. Your goal is to accomplish: {self.scenario.primary_goal}
3. Respond naturally - you're calling a real office, not an AI
4. If the receptionist misunderstands or forgets information, react realistically (clarify, repeat, get frustrated if appropriate)
5. Keep responses concise (1-2 sentences typically) - this is a phone call, not an interview
6. Use your personality traits to influence how you communicate
7. If you achieve your goal, you can wrap up the conversation
8. Don't give up easily - be persistent but realistic

Remember: You're a real patient with real concerns, not a robotic test scenario.
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
