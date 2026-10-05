# CarePathAI — Backend API & Subsystems Documentation

The CarePathAI backend is built with **FastAPI** and **Pydantic v2**. It handles authentication, audio transcription, acoustic denoising, clinical triage reasoning, doctor searches, dual-language translation, and session persistence.

---

## 1. REST API Endpoint Specification

| Endpoint | Method | Auth Required | Input Payload | Output Response | Description |
|---|---|---|---|---|---|
| `/health` | `GET` | No | None | `{"status": "ok"}` | Service health probe. |
| `/transcribe` | `POST` | Yes | Multipart Form (`file`, `session_id`, `language`) | `{"transcript": str}` | Converts voice audio (`audio/webm`) into text using Google Speech-to-Text (`latest_long` model), followed by Gemini Flash acoustic denoising. |
| `/triage` | `POST` | Yes | `TriageRequest` (JSON) | `FollowUpResponse` \| `TriageCompleteResponse` \| `EmergencyResponse` | Processes user symptom turn, evaluates red flags, queries MedGemma 4B CPU service, updates Firestore, and returns follow-up question or triage summary. |
| `/doctors` | `POST` | Yes | `DoctorSearchRequest` (JSON) | `DoctorSearchResponse` (JSON) | Queries Google Places Nearby Search & Place Details for real doctors filtered by specialist type, GPS coordinates, radius, and rating range. |
| `/translate-results` | `POST` | Yes | Query Params (`session_id`, `language`) | `TranslateResultsResponse` (JSON) | Translates completed triage summary and extracted slots between English and Hindi on-the-fly using parallel async translation and Firestore caching. |
| `/save-report-trace` | `POST` | Yes | `SaveReportTraceRequest` (JSON) | `{"status": "success"}` | Records printable PDF report download metadata and raw report content into Firestore `sessions/{sessionId}` document `download_history`. |

---

## 2. Request & Response Payload Data Models

### A. `TriageRequest` Schema
```json
{
  "transcript": "I have severe chest pain spreading to my left arm",
  "session_id": "sess_x89f2a9",
  "turn_count": 1,
  "max_turns": 3,
  "language": "en",
  "input_modality": "voice"
}
```

### B. `TriageCompleteResponse` Schema
```json
{
  "status": "triage_complete",
  "updated_session_state": {
    "chief_complaint": "Chest pain spreading to left arm",
    "body_location": "Chest, left arm",
    "onset": "Sudden",
    "duration": "30 minutes",
    "severity": "Severe",
    "associated_symptoms": ["Sweating", "Shortness of breath"],
    "aggravating_factors": "Exertion",
    "red_flags_present": []
  },
  "triage_result": {
    "urgency_level": "emergency",
    "specialist_type": "cardiologist",
    "confidence": "high",
    "red_flags_triggered": [],
    "reasoning_summary": "Symptoms strongly suggest potential acute coronary syndrome requiring immediate emergency evaluation."
  },
  "denoised_transcript": "I have severe chest pain spreading to my left arm"
}
```

### C. `DoctorSearchRequest` & `Doctor` Schema
```json
{
  "specialist_type": "cardiologist",
  "lat": 19.0760,
  "lng": 72.8777,
  "radius_km": 10.0,
  "max_results": 5,
  "min_rating": 4.0,
  "max_rating": 5.0
}
```

---

## 3. Core Subsystems & Design Rationales

### 1. Bounded Multi-Turn Clinical Reasoning Engine
* **Protocol**: Enforces a strict maximum turn cap (`max_turns`, default 3).
* **Rationale**: Open-ended chatbots cause user fatigue and high drop-off rates during medical distress. Bounding intake to 3 turns balances intake thoroughness with speed.
* **MedGemma Client**: Communicates via HTTP POST with the `medgemma-cpu` microservice running `medgemma-4b-it-Q5_K_M.gguf`. Normalizes output fields and handles model aliases (`summary` $\rightarrow$ `final_summary`).

### 2. "Safety-First" Red-Flag Intercept Layer
* **Mechanism**: Evaluates raw/denoised transcripts against deterministic red-flag keywords before calling the LLM.
* **Rationale**: Eliminates LLM latency and potential hallucinations for life-threatening conditions (e.g. cardiac arrest, stroke, severe anaphylaxis). Instantly triggers `EmergencyResponse`.

### 3. Context-Aware Acoustic Denoising
* **Mechanism**: Combines Google Speech-to-Text (`latest_long` model) with Gemini 2.5 Flash (`denoise_transcript_with_context`).
* **Rationale**: Indian English and Hindi speech often produce phonetic misrecognitions over lossy web audio (e.g., "climbing D stears" or "stomach aching since morning"). Gemini Flash uses conversation history to clean phonetics without changing user intent.

### 4. Specialist Alias Sanitizer
* **Mechanism**: `_sanitize_specialist_type()` maps raw LLM specialist recommendations into 19 standardized categories (`cardiologist`, `dermatologist`, `orthopedic`, `pulmonologist`, etc.).
* **Rationale**: Ensures exact matching against Google Places API keyword queries and frontend translations even if the LLM emits non-standard terms like "Heart Specialist" or "Skin Doctor".

### 5. Parallel Async Translation & Firestore Caching
* **Mechanism**: `async_translate_text()` executes translation tasks concurrently via `asyncio.gather()`. Results are cached in Firestore under the `translation_cache` collection using MD5 text hashes.
* **Rationale**: Cuts response latency by 60-80% during multi-field translation and reduces Google Translate API costs to zero for repeated phrases.

### 6. Firebase Authentication & Local Bypass
* **Mechanism**: `verify_id_token()` dependency validates Firebase ID tokens via `firebase_admin.auth`.
* **Developer Bypass**: Accepts `'Authorization': 'Bearer mock_token_abc'` for local unit testing and development without live Firebase tokens.

