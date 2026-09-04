# Frontend Documentation

This document provides a comprehensive overview of the CarePathAI frontend, including its architecture, state management, and hardware integration.

## Architecture

The frontend is a modern Single-Page Application (SPA) built with Vite and React. This combination provides a fast and efficient development experience, as well as a highly performant user interface.

## State Management

To manage the application's state, the frontend uses Zustand, a lightweight and easy-to-use state management library. The entire application state is stored in a single, unified store, which can be accessed and updated from any component.

## Hardware Integration

The frontend integrates with the user's hardware to provide a seamless and intuitive user experience:

- **Microphone:** The `MediaRecorder` API is used to capture audio from the user's microphone, which is then sent to the backend for transcription.
- **Geolocation:** The `navigator.geolocation` API is used to get the user's current location, which is then used to find nearby healthcare providers.

## UI/UX

The user interface is designed to be simple, intuitive, and easy to use. The application's flow is designed to guide the user through the triage process in a clear and concise manner, with a focus on providing a positive and reassuring user experience.
