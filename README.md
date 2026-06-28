
# AI Patient Simulation System

A Python framework for testing conversational AI medical receptionists using realistic patient personas. Features voice integration for real call simulation and local-only legacy testing.

## 📋 Project Overview

This system generates lifelike simulated patient calls to test and evaluate AI receptionist systems. It supports:

- **Rich patient profiles:** Personalities, health history, demographics
- **Flexible medical scenarios:** Scheduling, billing, medication, etc.
- **Centralized LLM client:** Easy model swaps
- **Phone call orchestration:** Make real test calls (Vapi integration)
- **Automated transcript & evaluation logging**
- **Optional local-only conversation simulator (legacy)**

## 🏗️ Architecture

### Core Files & Roles

```
├── voice_scenario.py          # MAIN ENTRY: voice-enabled patient simulation for production/test
├── patient_agent.py           # Simulates patient behavior using LLM and context
├── patient_profiles.py        # Patient data structures and persona generation
├── scenario_generator.py      # Generates medical/office scenarios
├── llm_client.py              # Centralized LLM (OpenRouter) client
├── voice_client.py            # Thin wrapper for Vapi HTTP voice API
├── evaluation_client.py       # Scores calls using LLM transcript analysis
├── conversation_simulator.py  # Legacy/local text testing only (**deprecated**)
├── requirements.txt           # Dependencies
├── README.md
├── logs/                      # Output transcripts, metadata, and evaluation files
```
    
## 🚀 Quick Start

### 1. Setup

```bash
# Clone/navigate to project folder
cd ai-patient-simulation

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Or (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API

```bash
# Copy example env file
### 3. Run Local Test

```bash
python conversation_simulator.py
```

This launches an interactive prompt where YOU play the receptionist.

### 4. Voice Call Orchestration (**Key Feature: `voice_scenario.py`**)

```bash
python voice_scenario.py
```

This is the most important script in the project. It lets you:

- **Select patient personality** (e.g., Standard, Anxious, Impatient, Elderly)
- **Select scenario type and difficulty** from rich options (appointment, refill, billing, etc.)
- **Place a real voice call** (using Vapi or other provider) to the configured test number
- **Stream a full multi-turn conversation** between the simulated patient and a receptionist LLM
- **Automatically record** the transcript, metadata, evaluation

**What happens?**

1. You are interactively prompted:
    - Pick the personality and type/difficulty of scenario
2. The patient and scenario profiles are built as you choose
3. The AI patient calls the target number and speaks as configured
4. The AI receptionist (LLM) replies; you can tune its prompt in code
5. Every turn is recorded (text), analyzed and scored by the built-in evaluator
6. All logs, recordings, and evaluation reports are saved in `logs/` (see below)

**Sample Run:**
```text
🏥 AI Patient Voice Simulation

Select patient personality:
1. Standard
2. Anxious
3. Impatient
4. Elderly
Enter number [1]: 2

Select scenario type:
1. Appointment scheduling
2. Appointment cancellation
3. Appointment rescheduling
...etc...
Enter number [1]: 3

Select scenario difficulty:
1. Easy
2. Medium
3. Hard
Enter number [2]: 1

Placing outbound call... streaming multi-turn conversation...
```

#### How logs are saved (after every session):
```
logs/
├── transcript_<timestamp>.txt            # Conversation transcript
├── metadata_<timestamp>.json             # Patient, scenario, and session info
├── evaluation_<timestamp>.json           # Raw LLM evaluation
├── evaluation_summary_<timestamp>.txt    # Human-readable summary
```

**Tuning**: Both the patient and scenario logic can be easily extended or tweaked in the respective Python files (`patient_profiles.py`, `scenario_generator.py`).

---

### 🤖 Conversation Evaluator (`evaluation_client.py`)

After a simulated call, this tool automatically runs an LLM-based evaluation over the generated transcript and metadata. The output — including scores and qualitative summary — is saved as both JSON and a readable `.txt` in the `logs` folder (see above).

**Why?**
- This lets you quickly measure realism, completeness, and accuracy of the call, using scalable LLM evaluation — no human review required unless you want it.

Run after every call session for a full testing and research loop.

========================================================================
PATIENT SIMULATION STARTING
========================================================================
Patient: Sarah Chen
Scenario: appointment_scheduling
Goal: Schedule urgent appointment
========================================================================

Type receptionist responses (or 'quit' to end, 'transcript' to see full call):

🔔 Phone ringing...
Patient: Hi, I'm calling because I've been having chest pain for the last couple hours and I'm really worried. I need to see someone today if possible.

Receptionist (your response): 
```

## 📁 File Purposes

### `llm_client.py`
**Purpose:** Centralized LLM API interaction

**Key Features:**
- Wraps OpenRouter API calls
- Configurable model selection (GPT, Claude, Gemini, etc.)
- Environment-based configuration
- Error handling & logging
- Global client instance for reuse

**Example Usage:**
```python
from llm_client import get_llm_client

client = get_llm_client(model="openai/gpt-4")
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}],
    system_prompt="You are a helpful assistant"
)
```

### `patient_profiles.py`
**Purpose:** Define patient data structures and sample personas

**Key Components:**
- `PatientProfile`: Complete patient demographic & medical data
- `MedicalHistory`: Conditions, allergies, medications
- `ContactInfo`: Phone, email, preferences
- Sample patients (standard, anxious, impatient, elderly)

**Example Usage:**
```python
from patient_profiles import create_sample_patient

patient = create_sample_patient("anxious")
print(f"{patient.first_name} is {patient.get_age()} years old")
print(patient.to_context_string())  # For LLM prompts
```

### `scenario_generator.py`
**Purpose:** Generate realistic testing scenarios

**Scenario Types:**
- Appointment scheduling/cancellation/rescheduling
- Medication refills
- Office information queries
- Test results
- Billing inquiries

**Difficulty Levels:**
- Easy: Straightforward requests
- Medium: Some complications
- Hard: Multiple issues, edge cases

**Example Usage:**
```python
from scenario_generator import generate_scenario, ScenarioType, ScenarioDifficulty

scenario = generate_scenario(
    ScenarioType.APPOINTMENT_SCHEDULING,
    ScenarioDifficulty.HARD
)
print(f"Goal: {scenario.primary_goal}")
print(f"Complications: {scenario.complications}")
```

### `patient_agent.py`
**Purpose:** AI patient brain that simulates realistic behavior

**Key Methods:**
- `initiate_call()`: Patient opens the conversation
- `respond_to_receptionist(msg)`: Generate patient response
- `get_transcript()`: Read-friendly conversation record

**How It Works:**
1. Builds system prompt from patient profile + scenario
2. Maintains conversation history
3. Uses LLM to generate realistic responses
4. Stays in character throughout

**Example Usage:**
```python
from patient_agent import PatientAgent
from patient_profiles import create_sample_patient
from scenario_generator import create_scenario_for_testing

patient = PatientAgent(
    patient_profile=create_sample_patient(),
    scenario=create_scenario_for_testing()
)

opening = patient.initiate_call()
print(f"Patient: {opening}")

response = patient.respond_to_receptionist("Hi, how can I help you?")
print(f"Patient: {response}")
```

### `conversation_simulator.py`
**Purpose:** Local testing interface without phone integration

**Modes:**
- **Interactive:** You type receptionist responses in real-time
- **Auto:** Provide predefined receptionist responses for repeatable tests

**Commands in Interactive Mode:**
- Type receptionist message normally
- `quit` - End conversation
- `transcript` - View full transcript

## 🎯 Workflow Example

### Local Development Loop
1. Run simulator
2. Test conversation as receptionist
3. Identify issues (misunderstandings, logic errors)
4. Adjust scenarios or system prompts
5. Re-test with different patient types
6. Save transcripts for analysis

### What to Test
- ✅ Does patient stay consistent with profile?
- ✅ Does patient pursue their goal?
- ✅ Does patient react realistically to common questions?
- ✅ Does patient handle misunderstandings well?
- ✅ Do personality traits show through?
- ✅ Is conversation natural and human-like?

## 🔧 Configuration & Customization

### Switching LLM Models

In code:
```python
from llm_client import get_llm_client

client = get_llm_client(model="anthropic/claude-3-opus")
```

In `.env`:
```
LLM_MODEL=anthropic/claude-3-sonnet
```

### Adjusting Patient Behavior

Edit `patient_profiles.py` to add new patient types:
```python
def create_sample_patient(patient_type: str = "standard") -> PatientProfile:
    if patient_type == "your_type":
        return PatientProfile(
            # ... configuration
        )
```

### Creating New Scenarios

Edit `scenario_generator.py`:
```python
ScenarioType.YOUR_SCENARIO = "your_scenario"

# Add to scenarios_db in generate_scenario():
ScenarioType.YOUR_SCENARIO: {
    ScenarioDifficulty.EASY: Scenario(
        scenario_id="YS_001",
        scenario_type=ScenarioType.YOUR_SCENARIO,
        primary_goal="Your goal here",
        context="Background info",
    )
}
```

## 📊 Output & Analysis

### Transcripts
Saved as `transcript_P001_APT_SCH_001.txt` with format:
```
============================================================
PATIENT SIMULATION TRANSCRIPT
============================================================

Patient: Sarah Chen
Scenario: appointment_scheduling
Goal: Schedule urgent appointment

============================================================
CONVERSATION
============================================================

Patient: Hi, I'm calling because I've been having chest pain...

Receptionist: I understand you're experiencing chest pain. Have you called 911?
...
```


## 🐛 Troubleshooting

### "OPENROUTER_API_KEY not found"
- ✅ Check `.env` file exists and is readable
- ✅ Verify API key is set: `echo $OPENROUTER_API_KEY`
- ✅ Restart terminal after creating .env

### "API request failed"
- ✅ Check internet connection
- ✅ Verify API key is valid
- ✅ Check OpenRouter status: https://status.openrouter.io
- ✅ Ensure model name is valid

### Patient responses are repetitive/robotic
- ✅ Increase `LLM_TEMPERATURE` (0.7-1.0 for more variation)
- ✅ Adjust system prompt in `patient_agent.py`
- ✅ Try different model (GPT-4 for better personality)

### Slow responses
- ✅ Reduce `LLM_MAX_TOKENS` (default 1000 is conservative)
- ✅ Switch to faster model like gpt-3.5-turbo
- ✅ Check internet connection

## 📞 API Reference

See individual files for detailed docstrings:
- `llm_client.py` - LLMClient class
- `patient_profiles.py` - PatientProfile, MedicalHistory
- `scenario_generator.py` - Scenario, ScenarioType
- `patient_agent.py` - PatientAgent class
- `conversation_simulator.py` - ConversationSimulator class

## 📝 License

This project is for educational and testing purposes.

---

**Ready to test?** Run `python conversation_simulator.py` now!
