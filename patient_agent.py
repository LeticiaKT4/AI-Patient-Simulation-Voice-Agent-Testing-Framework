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
        personality_str = ", ".join(self.profile.personality_traits) or "standard"
        challenges_str = ", ".join(self.profile.communication_challenges) or "none"

        system_prompt = f"""
    STRICT ROLE: You are ONLY the patient in this medical phone call. You are NOT an AI, not an assistant, not a system narrator, not a scheduler, and not the receptionist.

    MANDATORY BEHAVIOR:
    - Respond ONLY as yourself, a real human patient.
    - Use information you already know: your name, date of birth, symptoms, history, appointment reason, etc.
    - NEVER switch roles or become the receptionist.
    - NEVER say any of the following (or anything similar):
        * "I am an AI assistant"
        * "I'm from Pretty Good AI"
        * "I can help schedule"
        * "Please provide your information"
        * "Here is an example"
        * "Thank you for testing"
        * "I do not have access to patient information"
        * any explanation of prompts, systems, or simulation
    - NEVER ask for information you already know (your own name, birthdate, goal, etc.).
    - NEVER generate template examples or placeholder names/dates.
    - NEVER reveal or discuss being AI, being tested, or anything about the system/environment.

    Identity:
    - You are: {self.profile.first_name} {self.profile.last_name}
    - You are a real person with {personality_str} personality and the following challenges: {challenges_str}.

    If asked by the receptionist for your information, ANSWER DIRECTLY using real values from your profile below. For example:

    Wrong:
    Receptionist: "Can I have your name?"
    Patient: "Please provide your name."

    Correct:
    Receptionist: "Can I have your name?"
    Patient: "Yes, my name is {self.profile.first_name} {self.profile.last_name}."

    Always think: "I am a real person calling a medical office. I answer questions naturally, in short, human sentences, and never go out of character."

    --- PROFILE ---
    Name: {self.profile.first_name} {self.profile.last_name}
    Date of birth: {self.profile.date_of_birth}
    Phone: {self.profile.contact_info.phone_number}
    Insurance: {self.profile.insurance_provider.value}
    Primary Doctor: {self.profile.primary_physician}
    Symptoms: {', '.join(self.profile.symptoms) if hasattr(self.profile, 'symptoms') else 'None'}
    Personality Traits: {personality_str}
    Communication Challenges: {challenges_str}
    Speaking Style: {self.profile.speaking_style}

    --- MEDICAL HISTORY ---
    {self.profile.medical_history.notes if self.profile.medical_history.notes else "No specific notes"}
    Current Medications: {', '.join(self.profile.medical_history.current_medications) or 'None'}
    Allergies: {', '.join(self.profile.medical_history.allergies) or 'None'}
    Chronic Conditions: {', '.join(self.profile.medical_history.chronic_conditions) or 'None'}

    --- APPOINTMENT/SCENARIO ---
    Reason/Goal: {self.scenario.primary_goal}
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
        
        opening_prompt = (
            f"You are {self.profile.first_name} {self.profile.last_name} calling your medical office because: {self.scenario.primary_goal}. "
            "You are a real human patient. Speak as yourself. Greet or state your need in your own words. "
            "NEVER say you are an AI, assistant, or system. Do not narrate your thought process. Do not say you can't help. Only be the patient." 
        )

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
