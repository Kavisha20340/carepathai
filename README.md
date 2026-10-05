# CarePathAI — Multilingual Voice-First Healthcare Navigator

**CarePathAI** is a voice-first, AI-powered healthcare triage navigator designed for India. It listens to patient symptoms in English or Hindi (including Hinglish), conducts adaptive multi-turn intake, safely assesses clinical urgency, and connects patients with nearby verified medical specialists.

---

## Key Capabilities

| Capability | Technical Realization | Design Rationale |
|---|---|---|
| **Voice Intake & Denoising** | `MediaRecorder` API + Google Speech-to-Text (`latest_long`) + Gemini Flash Acoustic Denoising | Fixes phonetic STT misrecognitions (e.g. "climbing D stears") before clinical reasoning. |
| **Clinical Triage Engine** | MedGemma 4B GGUF (`Q5_K_M`) CPU service on Cloud Run | Provides specialized medical reasoning without expensive GPU infrastructure or privacy exposure. |
| **Safety Intercept** | Deterministic Red-Flag Pattern Matching | Short-circuits AI to trigger immediate Emergency Overlay for life-threatening symptoms (e.g. chest pain). |
| **Specialist Search** | Google Places Nearby Search & Place Details API | Finds real, top-rated local doctors (sorted by distance & rating) with one-click Maps directions. |
| **Dual-Language Engine** | Parallel Async Translation (Google Translate + Gemini Fallback) & Firestore Caching | Enables instant EN ↔ HI toggling with dual-language in-memory caching and sub-second UI switches. |
| **Medical Report Audit** | Printable HTML Report Generator (`window.print()`) + Firestore Trace Logging | Produces clean clinical summaries for doctors and audits download traces in Firestore (`/save-report-trace`). |

---

## Technical Stack

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACE                                   |
|               React 19 + Vite | Tailwind CSS v4 | Zustand | React Router v7      |
+-----------------------------------------------------------------------------------+
                                         |
                                  (HTTPS / REST API)
                                         |
+-----------------------------------------------------------------------------------+
|                                 FASTAPI BACKEND                                   |
|            FastAPI | Pydantic v2 | Firebase Auth | Asyncio Thread Pool          |
+-----------------------------------------------------------------------------------+
       |                        |                       |                     |
  (Speech STT)           (Clinical AI)             (Location)             (Caching)
       |                        |                       |                     |
+---------------+    +--------------------+     +---------------+     +---------------+
| Google Speech |    |   MedGemma 4B CPU  |     | Google Places |     | Google Cloud  |
|  to-Text API  |    | (llama-cpp-python) |     |  & Details    |     | Firestore DB  |
+---------------+    +--------------------+     +---------------+     +---------------+
```

---

## Documentation Index

- [**Architecture Guide**](./docs/architecture.md): Complete system flow diagrams, component interaction, and design rationales.
- [**Backend Documentation**](./docs/backend.md): Full API specifications (`/triage`, `/transcribe`, `/doctors`, `/translate-results`, `/save-report-trace`), safety layer, and data validation models.
- [**Frontend Documentation**](./docs/frontend.md): SPA architecture, Zustand store state machine, UI component hierarchy, hardware integrations, and UX isolation.
- [**Deployment Guide**](./docs/deployment.md): Step-by-step GCP Cloud Run dual-service deployment with Cloud Build (`$PROJECT_ID`) and Secret Manager.
- [**MedGemma Service**](./medgemma/README.md): Dockerization, GGUF model baking, and Cloud Run CPU scaling (`min-instances` cost management).
- [**Contributing Guide**](./docs/contributing.md): Local environment setup, virtual environments, unit/integration testing suite, and conventions.

