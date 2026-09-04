# Backend Documentation

This document provides a comprehensive overview of the CarePathAI backend, including the API specification, safety features, multilingual capabilities, and architectural rationale.

## API Specification

The backend exposes the following endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Checks the health of the backend service. |
| `/transcribe` | `POST` | Transcribes audio to text, with support for English and Hindi. |
| `/triage` | `POST` | Processes the patient's symptoms and returns a triage decision. |
| `/doctors` | `POST` | Searches for nearby doctors based on the patient's location and the recommended specialist. |

For a detailed API specification, please refer to the OpenAPI (Swagger) documentation, available at the `/docs` endpoint of the running backend service.

## Core Features

### "Safety-First" Red-Flag Layer

A pattern-matching engine that checks for high-risk symptoms on every turn. If a red flag is detected, the system immediately short-circuits and returns an emergency directive, bypassing the AI entirely.

### Bounded Slot-Filling Protocol

Instead of letting the AI engage in open-ended conversation, the system follows a structured, deterministic protocol to gather essential clinical information. The AI's role is limited to filling in a predefined schema of clinical slots, ensuring that the triage process is systematic and efficient.

### Multilingual Support

The backend is designed to be fully multilingual, with support for English, Hindi, and "Hinglish" (a mix of Hindi and English). The system automatically detects the language of the user's input and responds in the same language.

### Specialist Backstop

To ensure the accuracy of the AI's specialist recommendations, the system includes a "specialist backstop" that sanity-checks the AI's output against a predefined set of rules.

## Architectural Rationale

The backend is built with the following technologies:

- **FastAPI:** A high-performance Python web framework for building APIs.
- **Pydantic:** A data validation library that ensures the integrity of the data passed to the API.
- **Gemini on Vertex AI:** Google's latest generation of large language models, used for the core triage logic.
- **Google Cloud Speech-to-Text:** Used for transcribing audio to text.
- **Google Cloud Places API:** Used for finding nearby healthcare providers.
