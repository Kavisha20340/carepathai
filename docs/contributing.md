# Contributing to CarePathAI

Thank you for your interest in contributing to CarePathAI! This guide will help you get your development environment set up and ready to go.

## Setting up the Development Environment

### Backend

**1. Virtual Environment Setup**

From the root of the workspace (`C:\Users\kavgupta5\DEV\carepathai`), create a Python virtual environment to manage dependencies cleanly.

*   **Create the Virtual Environment:**

    ```powershell
    # Using the Google Cloud SDK's bundled Python
    & "C:\Users\kavgupta5\AppData\Local\Google\Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe" -m venv .venv
    ```

*   **Activate the Virtual Environment:**

    ```powershell
    # In PowerShell:
    .\.venv\Scripts\Activate.ps1
    ```

**2. Dependency Installation**

With the virtual environment active, install the required packages from the requirements file.

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

**3. Running the Automated Integration Tests**

An end-to-end integration test suite is provided to test the triage logic, deterministic red flags, specialist backstops, and live Gemini connectivity across multiple conversational turns (both in English and Hindi).

To execute the test suite, run:

```powershell
python backend/test_triage_flow.py
```

**4. Running the Backend Server Locally**

To spin up the local development server with live-reloading enabled, execute:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

1.  **Install the dependencies:**

    ```
    npm install
    ```

2.  **Run the frontend development server:**

    ```
    npm run dev
    ```

## Project Conventions

- **Code Style:** Please follow the PEP 8 style guide for Python and the Prettier style guide for JavaScript and React.
- **Commit Messages:** Please use the Conventional Commits specification for your commit messages.
- **Branching:** Please create a new branch for each feature or bug fix.

## Submitting a Pull Request

When you are ready to submit your changes, please open a pull request with a clear and concise description of the changes you have made. Please also include a link to any relevant issues or documentation.
