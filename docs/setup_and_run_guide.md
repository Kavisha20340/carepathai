# CarepathAI Backend Setup & Run Guide

This guide documents the exact steps required to set up, run, and test the CarepathAI triage backend service in your local Windows environment. Following these steps manually will configure the environment and run the automated test suite successfully.

---

## Prerequisites

1. **Python 3.10+**:
   If Python is not globally installed on your system, you can use the Google Cloud SDK's bundled Python, located at:
   `C:\Users\kavgupta5\AppData\Local\Google\Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe`
2. **GCP Project Access**:
   Ensure you are logged into your Google Cloud account and have the active project set to `carepathai`.
   Run the following command in your terminal to verify:
   ```bash
   gcloud config list
   ```
   *The active project must be `carepathai` and your account must have permissions to invoke Vertex AI/AI Platform services.*

---

## 1. Virtual Environment Setup

From the root of the workspace (`C:\Users\kavgupta5\DEV\carepathai`), create a Python virtual environment to manage dependencies cleanly.

### Create the Virtual Environment:
```powershell
# Using the Google Cloud SDK's bundled Python
& "C:\Users\kavgupta5\AppData\Local\Google\Cloud SDK\google-cloud-sdk\platform\bundledpython\python.exe" -m venv .venv
```

### Activate the Virtual Environment:
```powershell
# In PowerShell:
.\.venv\Scripts\Activate.ps1
```

---

## 2. Dependency Installation

With the virtual environment active, install the required packages from the requirements file.

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

These packages provide:
- **fastapi**: High-performance web framework for endpoints.
- **uvicorn**: ASGI server for running the FastAPI application.
- **google-cloud-aiplatform**: Vertex AI SDK to communicate with Gemini.
- **google-cloud-speech**: Google Cloud SDK for Speech-to-Text translation.
- **python-dotenv**: Environment variable management.
- **python-multipart**: Required by FastAPI to process multipart file uploads.
- **httpx**: Required for the in-memory testing suite.


---

## 3. Running the Automated Integration Tests

An end-to-end integration test suite is provided to test the triage logic, deterministic red flags, specialist backstops, and live Gemini connectivity across multiple conversational turns (both in English and Hindi).

To execute the test suite, run:

```powershell
python backend/test_triage_flow.py
```

### Expected Output:
- The terminal should display logs showing Vertex AI initialization.
- You will see logs of individual test cases running.
- **Red Flag Tests** should display `status: "emergency"` and successfully short-circuit.
- **Specialist Backstop Tests** should show logs overriding a mismatched specialist recommendation to `general_physician`.
- **Live Gemini Tests** (Knee pain in English and Skin rash in Hindi) will contact Vertex AI and output real conversation turns.
- The run should end with: `All integration tests PASSED successfully!`

---

## 4. Running the Backend Server Locally

To spin up the local development server with live-reloading enabled, execute:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Verification:
Open your browser and navigate to:
- **Health Check**: `http://127.0.0.1:8000/health` (Should return `{"status": "healthy", ...}`)
- **Interactive API Docs (Swagger UI)**: `http://127.0.0.1:8000/docs` (An interactive playground to test the `/triage` POST endpoint with custom payloads).

---

## 5. Testing Speech-to-Text with an Audio Clip

To manually test the `/transcribe` endpoint with a real audio file:

1. **Record an Audio File**:
   Record a short 3-10 second clip on your phone or computer speaking in English or Hindi (e.g. `"My knee has been hurting for two days"` or `"मेरे पेट में बहुत दर्द है"`). Save it in your directory as `my_voice.wav` or `my_voice.webm` (any standard container works, as Google Speech-to-Text automatically detects the format).

2. **Send the File via `curl`**:
   Make sure the local server is running, then execute the following command in your terminal:
   ```bash
   curl -X POST -F "file=@my_voice.wav" http://127.0.0.1:8000/transcribe
   ```
   *(Note: Change `my_voice.wav` to your actual file name).*

3. **Verify the Response**:
   The response will return the transcribed text:
   ```json
   {
     "transcript": "My knee has been hurting for two days"
   }
   ```
   *The system dynamically detects whether you spoke in Hindi or English, transcribes it, and formats punctuation automatically.*

---

## Troubleshooting & Tips

- **Authentication Error (`403 Forbidden / Default Credentials`)**:
  If the application fails to authenticate with Vertex AI, run `gcloud auth application-default login` in your terminal to set up your local application credentials.
- **Model Not Found (`404 NOT_FOUND`)**:
  Ensure you are using `gemini-2.5-flash` in the `us-central1` region, as older models (such as standard `gemini-1.5-flash`) might require explicit publisher model enablement in certain newly-created projects.
