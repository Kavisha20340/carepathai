# CarePathAI — Frontend Architecture & UI Documentation

The CarePathAI frontend is a voice-first Single-Page Application (SPA) built with **React 19**, **Vite**, **Tailwind CSS v4**, **Zustand**, and **React Router v7**.

---

## 1. UI Component Map & Hierarchy

```
App.jsx (Router, ErrorBoundary, Header, Footer, EmergencyOverlay)
 │
 ├── LandingPage.jsx (Route '/')
 │    └── Symmetric Language Selection Cards (English / हिंदी)
 │
 └── Triage Container (Route '/triage')
      │
      ├── Active Triage State (triageResult == null)
      │    ├── ConversationDisplay.jsx (Scroll-isolated chat history)
      │    └── MicInput.jsx (Voice mic button, auto-expanding textarea, 55s max cap)
      │
      └── Completed Triage State (triageResult != null)
           ├── TriageCard.jsx (Urgency badge, specialist tag, clinical reasoning, slot cards)
           └── DoctorSearch.jsx (Location GPS fetch, radius input, rating filter, doctor cards, Copy button)
```

| Component | Responsibility | UX & Design Rationale |
|---|---|---|
| `LandingPage.jsx` | Language entry portal with dual English / Hindi hero cards | Eliminates ambiguous language pickers by forcing explicit language choice before starting triage. |
| `MicInput.jsx` | 2-channel audio recording (`MediaRecorder`), auto-expanding text area, pulse animations | Supports both voice dictation and typed text input with a 55s duration auto-stop threshold safety modal. |
| `ConversationDisplay.jsx` | Renders conversational turn history | Uses internal container `scrollTop = scrollHeight` adjustment to lock scrolling to the box and prevent full-window jumping. |
| `TriageCard.jsx` | Displays urgency level, specialist recommendation, clinical reasoning, and extracted metadata slots | Uses skeleton loader states during translation/triage transitions and provides transparent clinical slot breakdown. |
| `DoctorSearch.jsx` | GPS location fetch, radius filter, rating bounds, real doctor cards with Maps links & Copy button | Enables one-touch calling (`tel:`) and directions without leaving the app; includes a copyable plain-text doctor list. |
| `EmergencyOverlay.jsx` | Full-screen red modal for critical symptoms (`urgency == 'emergency'`) | Locks body scroll (`overflow = hidden`) and provides direct one-touch dials for Indian emergency services (`112`, `108`, `102`, `104`, `1056`). |
| `ErrorBoundary.jsx` | React error boundary wrapper | Prevents total application crashes during unexpected runtime rendering exceptions. |

---

## 2. Zustand State Management (`useStore.js`)

State is managed globally in a unified Zustand store.

### State Schema

```javascript
{
  // Core Session State
  sessionId: "sess_...",
  language: "en" | "hi" | null,
  turnCount: 0,
  maxTurns: 3,
  sessionState: {
    chief_complaint: null,
    body_location: null,
    onset: null,
    duration: null,
    severity: null,
    associated_symptoms: [],
    aggravating_factors: null,
    relevant_history: null,
    red_flags_present: []
  },
  conversationHistory: [ { role, text, timestamp } ],
  triageResult: { urgency_level, specialist_type, confidence, reasoning_summary },
  triageResultCache: { en: null, hi: null }, // Dual-Language In-Memory Cache
  doctors: [ Doctor ],

  // UI / Hardware States
  isLoading: false,
  isDoctorsLoading: false,
  isRecording: false,
  error: null,
  emergencyMessage: null
}
```

### Key State Actions & Design Rationales

1. **Dual-Language In-Memory Cache (`triageResultCache`)**: When the user switches languages between English and Hindi, `useStore.setLanguage()` checks if the target language result is already cached in memory. If cached, it swaps the UI instantly without issuing network requests.
2. **Session Reset (`resetSession`)**: Re-initializes all session state, generates a new random `sessionId`, clears error modals, and restores initial greetings based on language preference stored in `localStorage`.
3. **Session Guard Validation**: Asynchronous request handlers (`submitTriageTurn`, `searchDoctors`) compare the active `sessionId` before updating state to discard stale network responses from previous sessions.

---

## 3. Hardware Integrations & Features

### A. Microphone Capture & 55s Safety Threshold
* Uses `navigator.mediaDevices.getUserMedia` with 2-channel audio configuration (`audioBitsPerSecond: 128000`).
* Enforces a 55-second timer. If audio recording exceeds 55 seconds, the recorder automatically stops, discards the audio, and displays a user-friendly 1-minute limit warning modal (`errMaxDuration`).

### B. Geolocation API (`navigator.geolocation`)
* Automatically prompts for location permissions upon entering the results view.
* If permission is granted, populates GPS coordinates (`lat`, `lng`) to power Google Places Doctor Search.

### C. Printable PDF Medical Report Generator (`reportGenerator.js`)
* Renders a styled HTML clinical document inside a hidden `iframe` and triggers `window.print()`.
* Automatically invokes `/save-report-trace` to log the download timestamp, language, and report content in Firestore.

