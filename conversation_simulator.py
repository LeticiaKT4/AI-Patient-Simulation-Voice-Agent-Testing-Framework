"""
Local conversation simulator for testing patient agent.

This allows text-based testing of the patient AI without using
actual phone systems. Useful for development and debugging.
"""

import logging
from typing import Optional

from patient_agent import PatientAgent
from patient_profiles import PatientProfile, create_sample_patient
from scenario_generator import (
    Scenario,
    ScenarioType,
    ScenarioDifficulty,
    create_scenario_for_testing,
)
from llm_client import get_llm_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConversationSimulator:
    """
    Simulates a conversation between a patient and receptionist.
    
    Used for local testing without real phone systems.
    """
    
    def __init__(
        self,
        patient_profile: Optional[PatientProfile] = None,
        scenario: Optional[Scenario] = None,
    ):
        """
        Initialize simulator with optional patient and scenario.
        
        Args:
            patient_profile: Patient to simulate (creates default if None)
            scenario: Scenario to use (creates default if None)
        """
        self.patient_profile = patient_profile or create_sample_patient()
        self.scenario = scenario or create_scenario_for_testing()
        
        # Initialize patient agent
        self.patient = PatientAgent(
            patient_profile=self.patient_profile,
            scenario=self.scenario,
            llm_client=get_llm_client(),
        )
        
        logger.info(f"Simulator ready: {self.patient_profile.first_name} "
                   f"({self.scenario.scenario_type.value})")
    
    def simulate_conversation(self, max_turns: int = 10) -> str:
        """
        Run an interactive conversation between patient and receptionist.
        
        Args:
            max_turns: Maximum exchanges before auto-ending
            
        Returns:
            Transcript of the conversation
        """
        print("\n" + "="*70)
        print("PATIENT SIMULATION STARTING")
        print("="*70)
        print(f"Patient: {self.patient_profile.first_name} {self.patient_profile.last_name}")
        print(f"Scenario: {self.scenario.primary_goal}")
        print(f"Goal: {self.scenario.primary_goal}")
        print("="*70)
        print("\nType receptionist responses (or 'quit' to end, 'transcript' to see full call):\n")
        
        # Patient initiates call
        print("🔔 Phone ringing...")
        opening = self.patient.initiate_call()
        print(f"Patient: {opening}\n")
        
        turn_count = 0
        
        try:
            while turn_count < max_turns:
                turn_count += 1
                
                # Get receptionist input
                receptionist_input = input("Receptionist (your response): ").strip()
                
                if not receptionist_input:
                    continue
                
                if receptionist_input.lower() == "quit":
                    print("\n[Ending conversation]")
                    break
                
                if receptionist_input.lower() == "transcript":
                    print(self.patient.get_transcript())
                    continue
                
                # Get patient response
                print("\n⏳ Patient thinking...\n")
                patient_response = self.patient.respond_to_receptionist(receptionist_input)
                print(f"Patient: {patient_response}\n")
        
        except KeyboardInterrupt:
            print("\n\n[Conversation interrupted by user]")
        
        except Exception as e:
            logger.error(f"Error during simulation: {e}")
            print(f"\n❌ Error: {e}")
        
        # Return full transcript
        return self.patient.get_transcript()
    
    def auto_conversation(self, receptionist_responses: list[str]) -> str:
        """
        Run automated conversation with predefined receptionist responses.
        
        Useful for repeatable testing scenarios.
        
        Args:
            receptionist_responses: List of receptionist messages
            
        Returns:
            Transcript of the conversation
        """
        print("\n" + "="*70)
        print("AUTO SIMULATION")
        print("="*70)
        print(f"Patient: {self.patient_profile.first_name}")
        print(f"Scenario: {self.scenario.scenario_type.value}")
        print("="*70 + "\n")
        
        # Patient opens
        opening = self.patient.initiate_call()
        print(f"Patient: {opening}\n")
        
        # Receptionist responses
        for i, receptionist_msg in enumerate(receptionist_responses, 1):
            print(f"Receptionist: {receptionist_msg}")
            
            patient_response = self.patient.respond_to_receptionist(receptionist_msg)
            print(f"Patient: {patient_response}\n")
        
        return self.patient.get_transcript()
    
    def get_transcript(self) -> str:
        """Get the conversation transcript."""
        return self.patient.get_transcript()


def main():
    """Main entry point for testing."""
    print("\n🏥 AI Patient Simulation - Conversation Tester\n")
    
    # Choose patient type
    print("Select patient type:")
    print("1. Standard (healthy, organized)")
    print("2. Anxious (worried, asks for reassurance)")
    print("3. Impatient (busy, direct)")
    print("4. Elderly (forgetful, detailed)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    patient_type_map = {
        "1": "standard",
        "2": "anxious",
        "3": "impatient",
        "4": "elderly",
    }
    
    patient_type = patient_type_map.get(choice, "standard")
    patient = create_sample_patient(patient_type)
    
    # Choose scenario
    print("\nSelect scenario:")
    print("1. Appointment Scheduling - Easy")
    print("2. Appointment Scheduling - Medium")
    print("3. Appointment Scheduling - Hard")
    print("4. Medication Refill - Easy")
    print("5. Office Information - Easy")
    
    scenario_choice = input("\nEnter choice (1-5): ").strip()
    
    scenario_map = {
        "1": (ScenarioType.APPOINTMENT_SCHEDULING, ScenarioDifficulty.EASY),
        "2": (ScenarioType.APPOINTMENT_SCHEDULING, ScenarioDifficulty.MEDIUM),
        "3": (ScenarioType.APPOINTMENT_SCHEDULING, ScenarioDifficulty.HARD),
        "4": (ScenarioType.MEDICATION_REFILL, ScenarioDifficulty.EASY),
        "5": (ScenarioType.OFFICE_INFORMATION, ScenarioDifficulty.EASY),
    }
    
    scenario_type, difficulty = scenario_map.get(scenario_choice, (ScenarioType.APPOINTMENT_SCHEDULING, ScenarioDifficulty.MEDIUM))
    
    from scenario_generator import generate_scenario
    scenario = generate_scenario(scenario_type, difficulty)
    
    # Run simulation
    simulator = ConversationSimulator(patient_profile=patient, scenario=scenario)
    transcript = simulator.simulate_conversation()
    
    # Offer to save transcript
    save = input("\n\nSave transcript? (y/n): ").strip().lower()
    if save == "y":
        filename = f"transcript_{patient.patient_id}_{scenario.scenario_id}.txt"
        with open(filename, "w") as f:
            f.write(transcript)
        print(f"✅ Saved to: {filename}")


if __name__ == "__main__":
    main()
