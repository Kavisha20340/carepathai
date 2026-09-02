# CarepathAI: Backend Architecture & Design Rationale

This document serves as a logical memoir of the CarepathAI triage backend. It explains the design philosophy, technical architecture, safety guardrails, and unique selling points (USPs) of the system. It is written to be accessible and highly valuable for both technical developers and business stakeholders.

---

## 1. The Core Vision: Why this isn't "just another chatbot"

Standard LLM-powered healthcare apps let the model "freewheel"—asking arbitrary questions for an unlimited number of turns and returning paragraphs of generic medical text. This creates three critical issues in a clinical context:
1. **Infinite loops**: Patients get exhausted answering open-ended conversational questions.
2. **Clinical dilution**: The model fails to systematically gather essential clinical metrics (like pain scale and onset).
3. **Hallucinated routing**: The LLM might confidently assign a patient with a fractured bone to a dermatologist because of poor reasoning.

**CarepathAI is different.** It is built around a **bounded slot-filling protocol**. The conversation is merely the input method; the system itself behaves like a deterministic medical form. The model is highly restricted: it cannot decide *what* to ask, it can only fill in empty slots from a pre-defined schema, in a strictly hardcoded priority order, with a hard turn cap (3 follow-ups max), a deterministic safety layer that runs before any LLM execution, and a specialist-mapping verification table.

---

## 2. Core Backend USPs (Unique Selling Points)

The backend implementation achieves the vision through six unique engineering pillars:

### USP 1: Deterministic "Safety-First" Red Flag Layer
Safety is not outsourced to LLM judgment. A pattern-matching engine checks the transcript *on every single turn* before any call to the Gemini API is made. If a high-risk symptom (like "chest pain + breathlessness" or "severe bleeding") is detected, or if the patient rates their pain severity as a $\ge 9$, the backend immediately short-circuits. It bypasses Gemini entirely and returns a standardized, immediate emergency directive. This ensures zero risk of LLM jailbreaking or "talking around" a life-threatening emergency.

### USP 2: Voice-First Multilingual STT & Hinglish Support
In India, communication is fluid. Patients frequently combine English and Hindi words (transliteration / Hinglish) or use native Devanagari script. CarepathAI solves this through a dual-language Voice-First architecture:
- **Zero-Friction STT Auto-Detection**: The `/transcribe` endpoint calls Google Cloud Speech-to-Text configured with a primary locale of `en-IN` and alternative locales of `hi-IN`. This programmatically auto-detects whether the user is speaking in Hindi or English and outputs high-fidelity text with automatic punctuation.
- **Support for Hinglish and Devanagari**: The deterministic red-flag check and the Gemini slot extractor natively process standard English, Hindi Devanagari (e.g. `"सीने में दर्द"`), and Hinglish transliterations (e.g. `"sine me dard ho raha hai"`).
- **Linguistic Response Matching**: The backend automatically detects the input language and returns all subsequent follow-up questions and reasoning summaries in that *exact same language*.


### USP 3: Specialist Backstop Lookup Table
Rather than blindly trusting Gemini to recommend a medical specialist, the backend acts as a sanity check. If a patient describes symptoms matching known keyword categories (such as "joint pain" or "ear discharge"), the backend computes an expected specialist class.
- If the LLM output agrees with this expected class, the specialist is retained.
- If the LLM recommends `general_physician`, it is accepted as a safe default.
- If the LLM sharply disagrees (e.g. recommending `dermatologist` for "knee joint pain"), the backend overrides it to `general_physician`. This eliminates dangerous routing errors.

### USP 4: Bounded Slot-Filling & Hard Turn Cap
To prevent conversation fatigue, the backend enforces a strict **3-turn maximum follow-up cap**. The system prioritizing missing slots in a strict hierarchy:
1. `body_location` $\rightarrow$ 2. `severity` $\rightarrow$ 3. `onset` / `duration` $\rightarrow$ 4. `associated_symptoms` $\rightarrow$ 5. `aggravating_factors`.
If required fields are still missing when the turn cap is reached, the backend force-triages with the information it has, marking its clinical confidence as "moderate" or "low" instead of dragging out the session.

### USP 5: Structured JSON Outputs (Zero Parse Failures)
FastAPI expects structured outputs, and LLMs are notoriously prone to returning loose markdown blocks (e.g., ````json { ... } ````). By utilizing Vertex AI's native `response_mime_type="application/json"` generation configuration, the Gemini model is restricted at the API level to return *only* valid JSON. This guarantees zero JSON parsing failures.

### USP 6: Resilient Double-Pass Recovery
Even with schema guarantees, network glitches or unexpected model tokens can happen. The backend implements a resilient "double-pass" architecture:
- If the first attempt to retrieve or parse the JSON fails, the backend intercepts the error and runs a second, more assertive "retry" pass.
- If the retry fails, it activates a safe recovery fallback state that preserves the session and asks a generic conversational follow-up, ensuring the app never crashes for the user.

---

## 3. Core Data Flow & State Machine

The diagram below maps the precise decision tree executed by the backend on every `/triage` request:

```
                  ┌────────────────────────────────┐
                  │   User Voice → Text Transcript │
                  └───────────────┬────────────────┘
                                  │
                                  ▼
                  ┌────────────────────────────────┐
                  │ Deterministic Red Flag Check   │
                  │   (Keywords & Severity Guard)  │
                  └───────────────┬────────────────┘
                                  ├───────────────────────────────┐
                     (No Red Flags)                               │ (Red Flag Triggered)
                                  ▼                               ▼
                  ┌────────────────────────────────┐ ┌───────────────────────────┐
                  │ Bounded Slot Completeness      │ │ SHORT-CIRCUIT STATE       │
                  │   Check (Is Schema Filled?)    │ │                           │
                  └───────────────┬────────────────┘ │ Response: status=emergency│
                                  │                  │ Message: "Please go to ER"│
                 (Missing Slots & │                  └───────────────────────────┘
                  Turn Count < 3) ├───────────────────────────────┐
                                  ▼                               │ (All Slots Filled OR
                  ┌────────────────────────────────┐              │  Turn Count >= 3)
                  │ Call Gemini 2.5 Flash via      │              ▼
                  │   Vertex AI (Structured JSON)  │ ┌───────────────────────────┐
                  └───────────────┬────────────────┘ │ Final Triage Compilation  │
                                  │                  │                           │
                                  ▼                  │ - Model predicts specialist│
                  ┌────────────────────────────────┐ │   and urgency.            │
                  │ Language Detection & Matching  │ │ - Deterministic Specialist│
                  │ - Ask ONE targeted follow-up   │ │   Backstop verifies.      │
                  │ - Update session slots.        │ └────────────┬──────────────┘
                  └───────────────┬────────────────┘              │
                                  │                               ▼
                                  ▼                  ┌───────────────────────────┐
                  ┌────────────────────────────────┐ │ Response:                 │
                  │ Response: status=follow_up     │ │ status=triage_complete    │
                  │ - updated_session_state        │ │ - updated_session_state   │
                  │ - follow_up_question           │ │ - triage_result           │
                  └────────────────────────────────┘ └───────────────────────────┘
```

---

## 4. End-to-End Walkthrough: A Clinical Scenario

Let’s trace the journey of an elderly patient, Mr. Sharma, who uses CarepathAI to navigate his symptoms. This scenario is different from the tests and demonstrates the slot-filling loop and the specialist backstop in action.

### Turn 0 (Initial Complaint)
* **Patient says (transcribed Roman Hindi)**: `"Mujhe gala kharab lag raha hai aur subah se halki khansi hai"` (My throat is bad and I have a mild cough since morning)
* **Backend Processing**:
  1. *Red Flag Check*: None found.
  2. *Slot Extraction*:
     - `chief_complaint` $\rightarrow$ `"gala kharab aur khansi"`
     - `body_location` $\rightarrow$ `"throat"`
     - `associated_symptoms` $\rightarrow$ `["cough"]`
     - `onset` $\rightarrow$ `"hours ago"` / `"gradual"`
     - *Missing required slots*: `severity`.
  3. *Language Detection*: Hindi.
  4. *Next Question Selection*: Since `severity` is the highest-priority missing required slot, the backend prompts Gemini for a severity question.
* **Backend JSON Response**:
  ```json
  {
    "status": "follow_up",
    "updated_session_state": {
      "chief_complaint": "gala kharab aur khansi",
      "body_location": "throat",
      "onset": "gradual",
      "duration": "since morning",
      "severity": null,
      "associated_symptoms": ["cough"],
      "aggravating_factors": null
    },
    "follow_up_question": "तकलीफ कितनी गंभीर है? 1 से 10 के पैमाने पर बताएं, जहाँ 1 हल्का और 10 बहुत गंभीर है।"
  }


### Turn 1 (First Follow-Up)
* **Patient says**: `"Darasal dard ya taklif jyada nahi hai, lagbhag 3 ya 4 hai"` (Actually pain or discomfort is not much, around 3 or 4)
* **Backend Processing**:
  1. *Red Flag Check*: None found. (Severity is 3-4, which is below the emergency threshold of 9).
  2. *Slot Extraction & Merging*:
     - `severity` $\rightarrow$ `3` or `4`
     - *All required slots are now filled!* (`chief_complaint`, `body_location`, `severity`, `onset`, `associated_symptoms`).
  3. *State Evaluation*: Since all required fields are filled, the backend stops asking questions and transitions directly to `triage_complete`—skipping any unnecessary turns!
  4. *Specialist Recommendation*: Gemini suggests `specialist_type`: `ent`.
  5. *Specialist Backstop check*:
     - Symptoms: `"gala kharab aur khansi"`
     - Keyword "gala" matches `gala` (throat) under the `ent` keyword list.
     - Expected specialist matches Gemini's choice (`ent` == `ent`). The backstop approves the specialist selection!
* **Backend JSON Response**:
  ```json
  {
    "status": "triage_complete",
    "updated_session_state": {
      "chief_complaint": "gala kharab aur khansi",
      "body_location": "throat",
      "onset": "gradual",
      "duration": "since morning",
      "severity": 3,
      "associated_symptoms": ["cough"],
      "aggravating_factors": null
    },
    "triage_result": {
      "urgency_level": "self_care",
      "specialist_type": "ent",
      "confidence": "high",
      "red_flags_triggered": [],
      "reasoning_summary": "मरीज को आज सुबह से गले में हल्की तकलीफ और खांसी है, जिसकी तीव्रता बहुत कम (3) है। यह एक सामान्य वायरल इन्फेक्शन या गले की सूजन हो सकती है। इसके लिए ईएनटी (ENT) विशेषज्ञ से सलाह ली जा सकती है या घरेलू उपचार किया जा सकता है।"
    }
  }
  ```

---

## 5. Architectural Rationale (Why this stack was chosen)

The tech stack is selected for high performance, ease of deployment, and simplicity in a Proof-of-Concept (POC):

- **FastAPI**:
  - *Speed*: FastAPI is one of the fastest Python frameworks available, built on standard ASGI (Uvicorn).
  - *Auto-documentation*: Automatically generates interactive OpenAPI swagger UI (under `/docs`) from the code's Pydantic models. This makes frontend integration completely seamless.
- **Pydantic**:
  - *Data Integrity*: Forces strict type-checking on all request payloads. It prevents bad data formats from ever reaching the LLM layer.
- **Gemini 2.5 Flash on Vertex AI**:
  - *Multilingual Native Superiority*: Extremely high accuracy in Romanized Indian languages (Hinglish) and Devanagari Hindi.
  - *Ultra-Low Latency & Cost-Effective*: Flash is engineered for fast conversational response loops while keeping API resource consumption low.
- **In-Memory Testing Suite**:
  - *No Server Overhead*: The automated testing suite utilizes `fastapi.testclient`, meaning tests execute completely in-memory. This removes the friction of starting and stopping background processes in Windows environments, ensuring rapid local testing feedback.

  ```

