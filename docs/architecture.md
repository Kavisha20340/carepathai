# Application Architecture

The CarePathAI application is designed with a modern, decoupled architecture, consisting of a React-based frontend and a Python-based backend. This separation of concerns allows for independent development, scaling, and deployment of the two components.

## High-Level Application Flow

The following diagram illustrates the end-to-end user journey, from initiating a triage session to finding a nearby healthcare provider.

```mermaid
graph TD
    A[User Arrives at Landing Page] --> B{Mic Permission};
    B --> |Granted| C[User Records Symptoms];
    B --> |Denied| D[User Types Symptoms];
    C --> E{Audio Blob};
    D --> F[Text Input];
    E --> G[/transcribe API];
    G --> H[Transcribed Text];
    F --> H;
    H --> I[/triage API];
    I --> J{Triage Logic};
    J --> |Emergency| K[Emergency Overlay];
    J --> |Follow-up| L[Follow-up Question];
    L --> C;
    J --> |Triage Complete| M[Triage Card];
    M --> N[User Searches for Doctors];
    N --> O[/doctors API];
    O --> P[List of Nearby Doctors];
    P --> Q[User Views Doctors on Map];
```

## Core Components

### Frontend

- **Framework:** Vite + React
- **State Management:** Zustand
- **Key Features:**
    - Voice-first interaction using `MediaRecorder`.
    - Geolocation for finding nearby doctors.
    - Mock token authorization for seamless local development.
    - Responsive and intuitive user interface.

### Backend

- **Framework:** FastAPI (Python)
- **Key Features:**
    - **Bounded Slot-Filling Protocol:** A structured approach to conversational AI that ensures systematic data collection.
    - **"Safety-First" Red-Flag Layer:** A deterministic pattern-matching engine that identifies high-risk symptoms and triggers an emergency response.
    - **Multilingual Support:** Auto-detection of English and Hindi, with support for "Hinglish".
    - **Specialist Backstop:** A sanity check to ensure the AI's specialist recommendations are accurate.
    - **Google Cloud Integration:** Utilizes Google Cloud Speech-to-Text, Vertex AI (for Gemini), and Places API.
