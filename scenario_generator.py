"""
Scenario generator for patient AI simulations.

Creates realistic, varied scenarios that test different
aspects of an AI receptionist system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ScenarioType(str, Enum):
    """Types of scenarios to simulate."""
    APPOINTMENT_SCHEDULING = "appointment_scheduling"
    APPOINTMENT_CANCELLATION = "appointment_cancellation"
    APPOINTMENT_RESCHEDULING = "appointment_rescheduling"
    MEDICATION_REFILL = "medication_refill"
    OFFICE_INFORMATION = "office_information"  # hours, location, insurance
    TEST_RESULTS = "test_results"
    PRESCRIPTION_ISSUE = "prescription_issue"
    BILLING_INQUIRY = "billing_inquiry"


class ScenarioDifficulty(str, Enum):
    """Difficulty level of the scenario."""
    EASY = "easy"              # Straightforward request
    MEDIUM = "medium"          # Some complications
    HARD = "hard"              # Multiple issues, edge cases


@dataclass
class Scenario:
    """
    A testing scenario for the patient agent.
    
    Provides the patient with a goal and context while
    remaining flexible for natural conversation flow.
    """
    scenario_id: str
    scenario_type: ScenarioType
    difficulty: ScenarioDifficulty
    
    # Patient's goal/motivation
    primary_goal: str
    context: str  # Background info for the patient
    
    # Optional complications to introduce
    complications: list[str] = None
    
    # Expected outcomes (for transcript analysis)
    success_criteria: list[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.complications is None:
            self.complications = []
        if self.success_criteria is None:
            self.success_criteria = []


def generate_scenario(
    scenario_type: ScenarioType,
    difficulty: ScenarioDifficulty = ScenarioDifficulty.MEDIUM,
) -> Scenario:
    """
    Generate a realistic scenario based on type and difficulty.
    
    Args:
        scenario_type: Type of scenario to generate
        difficulty: How challenging the scenario should be
        
    Returns:
        Scenario object with goal, context, and criteria
    """
    
    scenarios_db = {
        ScenarioType.APPOINTMENT_SCHEDULING: {
            ScenarioDifficulty.EASY: Scenario(
                scenario_id="APT_SCH_001",
                scenario_type=ScenarioType.APPOINTMENT_SCHEDULING,
                difficulty=ScenarioDifficulty.EASY,
                primary_goal="Schedule a routine checkup with Dr. Martinez",
                context="You've been feeling well and just need your annual physical.",
                success_criteria=[
                    "Appointment date is confirmed",
                    "Time is confirmed",
                    "Patient receives confirmation details",
                ],
            ),
            ScenarioDifficulty.MEDIUM: Scenario(
                scenario_id="APT_SCH_002",
                scenario_type=ScenarioType.APPOINTMENT_SCHEDULING,
                difficulty=ScenarioDifficulty.MEDIUM,
                primary_goal="Schedule an appointment for a specific health concern",
                context="You have persistent headaches for the past week and need to see the doctor this week.",
                complications=[
                    "Doctor might not have availability",
                    "You have limited availability (only evenings)",
                ],
                success_criteria=[
                    "Appointment is scheduled or wait list option offered",
                    "Scheduling works around your availability constraint",
                ],
            ),
            ScenarioDifficulty.HARD: Scenario(
                scenario_id="APT_SCH_003",
                scenario_type=ScenarioType.APPOINTMENT_SCHEDULING,
                difficulty=ScenarioDifficulty.HARD,
                primary_goal="Schedule urgent appointment",
                context="You're experiencing chest pain and need to be seen today.",
                complications=[
                    "Your preferred doctor isn't available",
                    "No same-day appointments exist",
                    "Receptionist might recommend ER instead",
                    "You're unsure if this is ER-level urgent",
                ],
                success_criteria=[
                    "Receptionist appropriately handles urgency",
                    "Patient is directed to ER or urgent care if needed",
                ],
            ),
        },
        
        ScenarioType.APPOINTMENT_CANCELLATION: {
            ScenarioDifficulty.EASY: Scenario(
                scenario_id="APT_CAN_001",
                scenario_type=ScenarioType.APPOINTMENT_CANCELLATION,
                difficulty=ScenarioDifficulty.EASY,
                primary_goal="Cancel an upcoming appointment",
                context="You need to cancel your appointment next Friday due to work conflict.",
                success_criteria=[
                    "Appointment is cancelled",
                    "Patient receives confirmation",
                    "Receptionist may ask if you want to reschedule",
                ],
            ),
            ScenarioDifficulty.MEDIUM: Scenario(
                scenario_id="APT_CAN_002",
                scenario_type=ScenarioType.APPOINTMENT_CANCELLATION,
                difficulty=ScenarioDifficulty.MEDIUM,
                primary_goal="Cancel appointment with complication",
                context="You need to cancel your appointment but are unsure which one (you might have multiple).",
                complications=[
                    "Patient has multiple appointments",
                    "Patient forgets exact date",
                    "Receptionist needs to clarify which appointment",
                ],
                success_criteria=[
                    "Correct appointment is identified and cancelled",
                    "Patient is clear on what was cancelled",
                ],
            ),
        },
        
        ScenarioType.MEDICATION_REFILL: {
            ScenarioDifficulty.EASY: Scenario(
                scenario_id="MED_REF_001",
                scenario_type=ScenarioType.MEDICATION_REFILL,
                difficulty=ScenarioDifficulty.EASY,
                primary_goal="Request a refill on your routine blood pressure medication",
                context="You're out of your Lisinopril and need it refilled. You've been on it for years.",
                success_criteria=[
                    "Medication is identified correctly",
                    "Refill is approved or forwarded to doctor",
                    "Patient knows when/where to pick up",
                ],
            ),
            ScenarioDifficulty.MEDIUM: Scenario(
                scenario_id="MED_REF_002",
                scenario_type=ScenarioType.MEDICATION_REFILL,
                difficulty=ScenarioDifficulty.MEDIUM,
                primary_goal="Request medication refill with insurance issue",
                context="You need your allergy medication refilled but you're not sure if your insurance covers it.",
                complications=[
                    "Insurance questions need clarification",
                    "Receptionist may need to check coverage",
                ],
                success_criteria=[
                    "Medication request is processed",
                    "Insurance information is handled correctly",
                ],
            ),
        },
        
        ScenarioType.OFFICE_INFORMATION: {
            ScenarioDifficulty.EASY: Scenario(
                scenario_id="OFF_INF_001",
                scenario_type=ScenarioType.OFFICE_INFORMATION,
                difficulty=ScenarioDifficulty.EASY,
                primary_goal="Find out office hours",
                context="You need to know if the office is open on Saturday.",
                success_criteria=[
                    "Office hours are clearly stated",
                    "Patient knows Saturday availability",
                ],
            ),
            ScenarioDifficulty.MEDIUM: Scenario(
                scenario_id="OFF_INF_002",
                scenario_type=ScenarioType.OFFICE_INFORMATION,
                difficulty=ScenarioDifficulty.MEDIUM,
                primary_goal="Verify insurance acceptance",
                context="You have a new insurance plan and need to confirm the office accepts it.",
                complications=[
                    "Insurance verification might be unclear",
                    "Office might need to check",
                ],
                success_criteria=[
                    "Insurance status is confirmed or path to confirmation provided",
                ],
            ),
        },
    }
    
    # Get the scenario, or create a generic one if not found
    if scenario_type in scenarios_db:
        if difficulty in scenarios_db[scenario_type]:
            return scenarios_db[scenario_type][difficulty]
    
    # Fallback to generic scenario
    return Scenario(
        scenario_id=f"{scenario_type.value}_generic",
        scenario_type=scenario_type,
        difficulty=difficulty,
        primary_goal=f"Handle {scenario_type.value}",
        context="You need help with a medical office task.",
    )


def get_all_scenario_types() -> list[ScenarioType]:
    """Get list of available scenario types."""
    return list(ScenarioType)


def create_scenario_for_testing(
    scenario_type: Optional[ScenarioType] = None,
    difficulty: Optional[ScenarioDifficulty] = None,
) -> Scenario:
    """
    Create a scenario for immediate testing.
    
    Args:
        scenario_type: Type of scenario (defaults to appointment scheduling)
        difficulty: Difficulty level (defaults to medium)
        
    Returns:
        Ready-to-use Scenario
    """
    scenario_type = scenario_type or ScenarioType.APPOINTMENT_SCHEDULING
    difficulty = difficulty or ScenarioDifficulty.MEDIUM
    
    return generate_scenario(scenario_type, difficulty)
