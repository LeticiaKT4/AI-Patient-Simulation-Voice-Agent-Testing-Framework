# AI Patient Simulation System

A Python-based framework for testing AI medical office receptionists through realistic patient simulations. Start with text-based conversations locally, then scale to real phone calls.

## 📋 Project Overview

This system simulates realistic patient behavior during medical office calls to test and debug voice AI systems. It includes:

- **Consistent patient personas** with medical history and personality traits
- **Realistic scenarios** (appointment scheduling, medication refills, etc.)
- **Centralized LLM integration** via OpenRouter (easy to swap models)
- **Local text-based testing** before phone integration
- **Transcript analysis** for identifying issues

## 🏗️ Architecture

### File Structure

```
ai-patient-simulation/
├── llm_client.py              # Centralized LLM/API client
├── patient_profiles.py        # Patient data structures & samples
├── scenario_generator.py      # Scenario creation logic
├── patient_agent.py           # AI patient behavior engine
├── conversation_simulator.py  # Local text-based testing
├── voice_client.py            # Vapi voice call helper
├── voice_scenario.py          # Voice call orchestration and transcript saving (Vapi)
├── requirements.txt           # Python dependencies
├── .env.example              # Configuration template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

### How Files Connect

```
┌─────────────────────────────┐
│   conversation_simulator.py  │  ← User Interface (local testing)
└────────────┬────────────────┘
             │
┌────────────▼────────────────┐
│    patient_agent.py         │  ← AI Patient Brain
│  (uses LLM + Context)       │
└────┬──────────────┬─────────┘
     │              │
     ▼              ▼
┌──────────────┐  ┌──────────────────────┐
│ llm_client.py│  │ patient_profiles.py  │
│ (OpenRouter) │  │ + scenario_generator │
└──────────────┘  └──────────────────────┘
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
cp .env.example .env

# Edit .env with your OpenRouter API key
# Get one at: https://openrouter.io
```

`.env` should look like:
```
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.io/api/v1
LLM_MODEL=openai/gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
```

### 3. Run Local Test

```bash
python conversation_simulator.py
```

This launches an interactive prompt where YOU play the receptionist.

### 4. Run Voice Call Test

```bash
python voice_scenario.py
```

This places a single outbound call to the configured `TARGET_TEST_NUMBER`, plays the patient opening prompt via the configured voice provider (Vapi), and records the simulated multi-turn conversation into a transcript file.

> Note: This flow reads `VAPI_API_KEY` and `TARGET_TEST_NUMBER` from `.env` and will only call the test number configured by `TARGET_TEST_NUMBER`.

```
🏥 AI Patient Simulation - Conversation Tester

Select patient type:
1. Standard (healthy, organized)
2. Anxious (worried, asks for reassurance)
3. Impatient (busy, direct)
4. Elderly (forgetful, detailed)

Enter choice (1-4): 2

Select scenario:
1. Appointment Scheduling - Easy
2. Appointment Scheduling - Medium
3. Appointment Scheduling - Hard
4. Medication Refill - Easy
5. Office Information - Easy

Enter choice (1-5): 3

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

### Next Steps (Future)
- Parse transcripts for common issues
- Generate error reports
- Track success rates by scenario type
- Integrate with real phone systems (Vapi, Twilio)

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

## 📚 Next Steps in Development

1. ✅ **Foundation (this phase)**
   - Core LLM client
   - Patient profiles
   - Scenario generation
   - Local testing

2. 🔄 **Phone Integration**
   - Vapi or Twilio integration
   - Real phone call simulation
   - Audio recording/transcription

3. 📈 **Analysis & Reporting**
   - Transcript parsing
   - Bug detection (repeated questions, misunderstandings)
   - Success/failure metrics
   - Report generation

4. 🎯 **Advanced Features**
   - Multi-turn complex scenarios
   - Patient interruptions
   - Background noise simulation
   - Multiple patient types in one conversation

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
