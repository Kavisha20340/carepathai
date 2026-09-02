# CarepathAI Triage API Specification

This document details the API specifications for the CarepathAI backend triage service. This API orchestrates the bounded slot-filling protocol, manages deterministic red flags, and verifies medical specialists using a backend backstop table.

---

## Base Configuration

- **Development Base URL**: `http://127.0.0.1:8000`
- **Headers**: `Content-Type: application/json`
- **CORS**: Configured to accept all origins (`*`) to facilitate local testing and direct integrations with static frontend platforms like Firebase Hosting.

---

## Endpoints

### 1. Health Check
Checks the status of the backend API.

- **URL**: `/health`
- **Method**: `GET`
- **Auth Required**: No
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "carepathai-backend"
  }
  ```

---

### 2. Transcribe Audio to Text
Transcribes a raw voice recording from the frontend microphone into text. Supports auto-detection between English (`en-IN`) and Hindi (`hi-IN`) and formats punctuation automatically.

- **URL**: `/transcribe`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Request Parameters**:
  - `file` (binary file): The recorded audio blob (WebM, WAV, MP3, etc.).
- **Response**:
  ```json
  {
    "transcript": "string (the transcribed text content)"
  }
  ```

---

### 3. Process Triage Turn
This is the core endpoint of the application. It processes the patient's spoken transcript, performs deterministic red-flag validation, updates conversational slots, and either generates a targeted follow-up question or concludes the session with a structured triage card.

- **URL**: `/triage`
- **Method**: `POST`
- **Auth Required**: No (Anonymous session is tracked on the client side and sent inside payloads)
- **Request Body Schema**:
  ```json
  {
    "transcript": "string (the latest statement spoken by the patient)",
    "session_state": {
      "chief_complaint": "string or null",
      "body_location": "string or null",
      "onset": "sudden | gradual | unknown or null",
      "duration": "string or null",
      "severity": "integer (1-10) or null",
      "associated_symptoms": ["string"],
      "aggravating_factors": "string or null",
      "red_flags_present": ["string"],
      "relevant_history": "string or null"
    },
    "turn_count": "integer (starts at 0 on Turn 0)",
    "max_turns": "integer (defaults to 3)"
  }
  ```

- **Possible Responses**:

#### A. Emergency Short-Circuit Response
Triggered immediately if deterministic keyword or severity rules ($\ge 9$) are met. No Gemini calls are made in this scenario.

- **Status Code**: `200 OK`
- **Body Schema**:
  ```json
  {
    "status": "emergency",
    "message": "This may be a medical emergency. Please call emergency services or go to the nearest ER immediately."
  }
  ```

#### B. Conversational Follow-Up Response
Returned when there are missing required fields (`chief_complaint`, `body_location`, `severity`, `onset`, `associated_symptoms`) and the turn count is still below the turn cap.

- **Status Code**: `200 OK`
- **Body Schema**:
  ```json
  {
    "status": "follow_up",
    "updated_session_state": {
      "chief_complaint": "string",
      "body_location": "string",
      "onset": "sudden | gradual | unknown | null",
      "duration": "string | null",
      "severity": "integer | null",
      "associated_symptoms": ["string"],
      "aggravating_factors": "string | null",
      "red_flags_present": ["string"],
      "relevant_history": "string | null"
    },
    "follow_up_question": "string (one short, targeted question in the detected language of the transcript)"
  }
  ```

#### C. Triage Complete Response
Returned when all required slot fields are filled OR the turn cap (`turn_count >= max_turns`) is hit.

- **Status Code**: `200 OK`
- **Body Schema**:
  ```json
  {
    "status": "triage_complete",
    "updated_session_state": {
      "chief_complaint": "string",
      "body_location": "string",
      "onset": "sudden | gradual | unknown",
      "duration": "string",
      "severity": "integer",
      "associated_symptoms": ["string"],
      "aggravating_factors": "string | null",
      "red_flags_present": ["string"],
      "relevant_history": "string | null"
    },
    "triage_result": {
      "urgency_level": "emergency | urgent | routine | self_care",
      "specialist_type": "general_physician | orthopedic | dermatologist | pulmonologist | cardiologist | gastroenterologist | ent | gynecologist | pediatrician | ophthalmologist | psychiatrist",
      "confidence": "high | moderate | low",
      "red_flags_triggered": ["string"],
      "reasoning_summary": "string (2-3 sentences explaining the clinical rationale, written in the detected language)"
    }
  }
  ```

---

## Schema Enum Reference Values

### `specialist_type` Enums:
`general_physician | orthopedic | dermatologist | pulmonologist | cardiologist | gastroenterologist | ent | gynecologist | pediatrician | ophthalmologist | psychiatrist`

### `urgency_level` Enums:
`emergency | urgent | routine | self_care`

### `onset` Enums:
`sudden | gradual | unknown`
