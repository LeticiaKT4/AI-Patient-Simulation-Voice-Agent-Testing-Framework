"""
Patient profile management for simulation scenarios.

Defines patient data structures and utilities for creating
realistic patient personas for testing.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class InsuranceProvider(str, Enum):
    """Common insurance providers."""
    BLUE_CROSS = "Blue Cross Blue Shield"
    AETNA = "Aetna"
    CIGNA = "Cigna"
    UNITED = "United Health"
    MEDICARE = "Medicare"
    MEDICAID = "Medicaid"
    UNINSURED = "Uninsured"


@dataclass
class MedicalHistory:
    """Patient's medical conditions and history."""
    chronic_conditions: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    current_medications: list[str] = field(default_factory=list)
    previous_surgeries: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ContactInfo:
    """Patient contact details."""
    phone_number: str
    email: Optional[str] = None
    preferred_contact_method: str = "phone"  # phone, email, text


@dataclass
class PatientProfile:
    """
    Complete patient profile for simulation.
    
    This profile is maintained by the patient agent throughout
    a conversation and used to generate consistent responses.
    """
    # Demographics
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str  # YYYY-MM-DD
    gender: str  # M, F, Other
    
    # Contact
    contact_info: ContactInfo
    
    # Medical
    medical_history: MedicalHistory
    insurance_provider: InsuranceProvider
    insurance_id: str
    
    # Office relationship
    primary_physician: str
    last_visit_date: Optional[str] = None
    
    # Personality traits (for realistic conversations)
    personality_traits: list[str] = field(default_factory=list)
    speaking_style: str = "casual"  # casual, formal, technical, etc.
    communication_challenges: list[str] = field(default_factory=list)
    
    def get_age(self, current_year: int = 2024) -> int:
        """Calculate patient age from date of birth."""
        birth_year = int(self.date_of_birth.split("-")[0])
        return current_year - birth_year
    
    def to_context_string(self) -> str:
        """
        Generate a context string for the LLM about this patient.
        
        This is used as part of the system prompt to help the patient
        agent stay consistent with their profile.
        
        Returns:
            Formatted patient information string
        """
        age = self.get_age()
        meds = ", ".join(self.medical_history.current_medications) or "None listed"
        allergies = ", ".join(self.medical_history.allergies) or "None listed"
        
        return f"""
Patient Profile:
- Name: {self.first_name} {self.last_name}
- Age: {age}
- Insurance: {self.insurance_provider.value}
- Primary Physician: {self.primary_physician}
- Current Medications: {meds}
- Allergies: {allergies}
- Communication Style: {self.speaking_style}
- Personality: {', '.join(self.personality_traits) if self.personality_traits else 'standard'}
"""


# Sample patient profiles for testing
def create_sample_patient(patient_type: str = "standard") -> PatientProfile:
    """
    Create sample patient profiles for testing.
    
    Args:
        patient_type: Type of patient to create
        
    Returns:
        PatientProfile instance
    """
    if patient_type == "anxious":
        return PatientProfile(
            patient_id="P001",
            first_name="Sarah",
            last_name="Chen",
            date_of_birth="1985-03-15",
            gender="F",
            contact_info=ContactInfo(
                phone_number="555-0101",
                email="s.chen@email.com",
            ),
            medical_history=MedicalHistory(
                chronic_conditions=["Anxiety", "Seasonal Allergies"],
                allergies=["Penicillin"],
                current_medications=["Sertraline 50mg", "Loratadine"],
                previous_surgeries=["Appendectomy (2015)"],
            ),
            insurance_provider=InsuranceProvider.BLUE_CROSS,
            insurance_id="BC12345678",
            primary_physician="Dr. Martinez",
            last_visit_date="2024-01-20",
            personality_traits=["Worried", "Inquisitive", "Polite"],
            speaking_style="formal",
            communication_challenges=["Often asks for reassurance", "Repeats questions when anxious"],
        )
    
    elif patient_type == "impatient":
        return PatientProfile(
            patient_id="P002",
            first_name="James",
            last_name="Williams",
            date_of_birth="1978-07-22",
            gender="M",
            contact_info=ContactInfo(
                phone_number="555-0102",
                email="j.williams@email.com",
                preferred_contact_method="text",
            ),
            medical_history=MedicalHistory(
                chronic_conditions=["Hypertension"],
                allergies=[],
                current_medications=["Lisinopril 10mg"],
                previous_surgeries=["Knee surgery (2019)"],
            ),
            insurance_provider=InsuranceProvider.AETNA,
            insurance_id="AE87654321",
            primary_physician="Dr. Johnson",
            last_visit_date="2024-02-10",
            personality_traits=["Busy", "Direct", "Impatient"],
            speaking_style="casual",
            communication_challenges=["Interrupts", "Doesn't listen fully", "Wants quick answers"],
        )
    
    elif patient_type == "elderly":
        return PatientProfile(
            patient_id="P003",
            first_name="Robert",
            last_name="Thompson",
            date_of_birth="1940-11-05",
            gender="M",
            contact_info=ContactInfo(
                phone_number="555-0103",
                email="r.thompson@email.com",
            ),
            medical_history=MedicalHistory(
                chronic_conditions=["Type 2 Diabetes", "Arthritis", "COPD"],
                allergies=["Sulfonamides"],
                current_medications=["Metformin 1000mg", "Albuterol inhaler", "Naproxen"],
                previous_surgeries=["Hip replacement (2018)", "Cataract surgery (2020)"],
            ),
            insurance_provider=InsuranceProvider.MEDICARE,
            insurance_id="MED123456789",
            primary_physician="Dr. Lee",
            last_visit_date="2024-01-05",
            personality_traits=["Patient", "Forgetful", "Friendly", "Detailed"],
            speaking_style="formal",
            communication_challenges=["Hearing difficulties", "Forgets medications", "Slow to process info"],
        )
    
    else:  # standard
        return PatientProfile(
            patient_id="P000",
            first_name="Alex",
            last_name="Rodriguez",
            date_of_birth="1990-06-12",
            gender="M",
            contact_info=ContactInfo(
                phone_number="555-0100",
                email="a.rodriguez@email.com",
            ),
            medical_history=MedicalHistory(
                chronic_conditions=[],
                allergies=["Latex"],
                current_medications=["Multivitamin"],
                previous_surgeries=[],
            ),
            insurance_provider=InsuranceProvider.CIGNA,
            insurance_id="CG11223344",
            primary_physician="Dr. Patel",
            last_visit_date="2024-02-15",
            personality_traits=["Friendly", "Organized", "Patient"],
            speaking_style="casual",
            communication_challenges=[],
        )
