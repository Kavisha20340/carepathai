# Full-Stack Deployment Guide

This guide contains complete documentation of the architecture, configuration, step-by-step setup, troubleshooting logs, and day-to-day operations for deploying and hosting the **CarepathAI Frontend** (Vite + React) and **CarepathAI Backend** (FastAPI + Python) on **Google Cloud Run** using **Google Cloud Build**, **Artifact Registry**, and **Google Cloud Secret Manager**.

---

## 1. Architectural Overview

In production, the application is deployed as a secure, high-performance, decoupled dual-service architecture on Google Cloud Run:

```
[User Browser]
      |
      +---> (HTTPS) ---> [CarepathAI Frontend] (Serves static assets via Nginx on Port 80)
      |
      +---> (HTTPS) ---> [CarepathAI Backend] (Runs FastAPI via Uvicorn on Port 8080)
                             |
                             +---> Google Cloud Secret Manager (Fetches PLACES_API_KEY)
                             +---> Vertex AI / Gemini API (Symptom Triage)
                             +---> Google Cloud Speech-to-Text (Transcription)
                             +---> Cloud Firestore (Session Recovery & Storage)
```

1.  **CarepathAI Frontend (Cloud Run)**: A lightweight, containerized **Nginx** server hosting optimized static React assets. It routes client-side pages seamlessly and communicates with the backend over secure HTTPS.
2.  **CarepathAI Backend (Cloud Run)**: A serverless **FastAPI** web server running on Uvicorn. It executes symptom triage logic, interacts with GCP platform services (Vertex AI, Speech-to-Text, Firestore) natively using application-default credentials, and pulls third-party API keys securely from **GCP Secret Manager**.

---

## 2. Configuration Files

To containerize, optimize, and automate the deployment pipeline, we utilize the following critical files:

### a. Custom Web Server Configuration
*   **File:** `/frontend/nginx.conf`
*   **Purpose:** Solves the "404 on Refresh" problem by configuring Nginx to serve `/index.html` for any client-side routes requested directly.

### b. Frontend Multi-Stage Containerization
*   **File:** `/frontend/Dockerfile`
*   **Purpose:** Builds React assets in a clean Node.js stage, compiles them, and packages only the final static assets into Nginx. It supports the `VITE_API_BASE_URL` build argument to dynamically link the backend during compilation.

### c. Backend Containerization
*   **File:** `/backend/Dockerfile`
*   **Purpose:** Installs the Python runtime and project dependencies. Packages code inside `/app/backend` to guarantee absolute import resolutions (e.g., `from backend.models import ...`) are fully maintained at runtime.

### d. Automated Build Pipeline
*   **File:** `/cloudbuild.yaml`
*   **Purpose:** Automates building the frontend image via Google Cloud Build and pushing it to Artifact Registry.

---

## 3. Step-by-Step Deployment

Follow these steps to deploy both the backend and frontend to a secure, live production environment.

### Step 1: Authenticate with Google Cloud
Ensure your local CLI is logged in and pointed to your active GCP project:
```powershell
gcloud auth login
gcloud config set project your-gcp-project-id
```

### Step 2: Deploy the Backend to Cloud Run
Run this command from your root directory to upload your source code, containerize it, and deploy it to Cloud Run:
```powershell
gcloud run deploy carepathai-backend --source=./backend --region=asia-south1 --allow-unauthenticated
```
Once deployed, Cloud Run will output your backend's secure Service URL. Note this URL, as it will look like:
👉 `https://carepathai-backend-[YOUR_PROJECT_NUMBER].asia-south1.run.app`

### Step 2b: Grant GCP IAM Permissions to the Service Account
Because modern Google Cloud projects enforce "least privilege by default", the default Cloud Run service account has no active roles initially. You must grant it explicit permissions to access Vertex AI (Gemini), Cloud Firestore, Speech-to-Text, and Cloud Translation.

Run these 4 commands in your terminal (replace `your-gcp-project-id` with your active project ID and `[PROJECT_NUMBER]` with your GCP project number):

```powershell
# 1. Grant access to Vertex AI (Gemini)
gcloud projects add-iam-policy-binding your-gcp-project-id `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/aiplatform.user"

# 2. Grant access to Cloud Firestore
gcloud projects add-iam-policy-binding your-gcp-project-id `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/datastore.user"

# 3. Grant access to Google Cloud Speech-to-Text
gcloud projects add-iam-policy-binding your-gcp-project-id `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/speech.client"

# 4. Grant access to Google Cloud Translation
gcloud projects add-iam-policy-binding your-gcp-project-id `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/cloudtranslate.user"
```

### Step 3: Configure Credentials with GCP Secret Manager
Sensitive keys (like `PLACES_API_KEY`) must not be hardcoded or written in plain-text environment variables. Use **Secret Manager** to store them securely.

1.  **Enable the Secret Manager API:**
    ```powershell
    gcloud services enable secretmanager.googleapis.com
    ```
2.  **Create and Upload the Secret containing your API Key:**
    *Note: Standard pipelines (like `echo "key" | gcloud ...`) or byte conversions in Windows PowerShell automatically append literal quotes, Carriage Returns (`\r\n`), or Byte Order Marks (BOM), which will corrupt the API key inside a Linux container. Follow this clean, multi-step process instead:*
    
    First, create the secret placeholder in Secret Manager:
    ```powershell
    gcloud secrets create PLACES_API_KEY
    ```
    
    Next, write your actual unquoted key (replace `your-google-places-api-key` with your active Google Places key) to a clean temporary file, upload it, and delete the temporary file:
    ```powershell
    "your-google-places-api-key" | Set-Content -NoNewline -Encoding Ascii -Path secret.txt
    gcloud secrets versions add PLACES_API_KEY --data-file=secret.txt
    Remove-Item secret.txt
    ```
3.  **Grant Secret Access to your Cloud Run Service Account:**
    Get your GCP project number:
    ```powershell
    gcloud projects describe $(gcloud config get project) --format="value(projectNumber)"
    ```
    Bind the **Secret Accessor** role to your default compute service account (replace `[PROJECT_NUMBER]` with your actual project number):
    ```powershell
    gcloud secrets add-iam-policy-binding PLACES_API_KEY `
      --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
      --role="roles/secretmanager.secretAccessor"
    ```
4.  **Mount the Secret into the Backend:**
    Update the backend configuration to safely pull this secret as an environment variable at startup:
    ```powershell
    gcloud run services update carepathai-backend `
      --region=asia-south1 `
      --set-secrets=PLACES_API_KEY=PLACES_API_KEY:latest
    ```

### Step 4: Deploy the Frontend with Build-Time Backend URL Binding
Now, build and deploy the frontend. We will inject your deployed backend URL (from Step 2) so that the compiled React build knows where to send requests.

Run the build submission command (replace the URL with your actual backend Service URL):
```powershell
gcloud builds submit --config=cloudbuild.yaml --substitutions=_VITE_API_BASE_URL="https://carepathai-backend-[YOUR_PROJECT_NUMBER].asia-south1.run.app" .
```

The frontend will compile, containerize, and host itself on its own secure URL:
👉 `https://carepathai-frontend-[YOUR_PROJECT_NUMBER].asia-south1.run.app`

---

## 4. Troubleshooting

### a. "This site wants to access other services on this device" (Local Network Warning)
*   **Symptom:** After giving microphone permission and speaking, the browser prompts for permission to access other services or local network devices.
*   **Diagnosis:** The deployed frontend is hosted on a secure `https://` URL, but the frontend's backend API URL is pointing to a local `http://127.0.0.1:8000` address. Modern browsers block secure public pages from requesting local services (Private Network Access policy) and prompt the user.
*   **Solution:** Re-deploy the frontend (Step 4) and ensure that `_VITE_API_BASE_URL` is set to your deployed backend's secure `https://` URL.

### b. Permission Denied to Artifact Registry
*   **Symptom:** The Cloud Build pipeline fails with `Permission "artifactregistry.repositories.uploadArtifacts" denied`.
*   **Solution:** Grant the **Artifact Registry Writer** role to the Cloud Build service account in your GCP IAM panel.

### c. Container Start Failure (FastAPI / Nginx)
*   **Symptom:** Cloud Run revision creation fails with: `The user-provided container failed to start and listen on the port...`
*   **Solution:** Check container configurations. 
    *   The frontend expects port `80` (managed automatically via Nginx configurations in `cloudbuild.yaml`).
    *   The backend expects port `8080`. Ensure that the `CMD` in `backend/Dockerfile` dynamically binds to the `$PORT` environment variable:
        ```dockerfile
        CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
        ```

### d. "googlemaps client is not initialized" / "Invalid API key provided"
*   **Symptom:** The list of doctors does not load when clicking the "Find Specialists" button, and logs report `Failed to initialize Google Maps client: Invalid API key provided.` or `googlemaps client is not initialized.`
*   **Diagnosis:** Piping raw values or converting byte arrays in Windows PowerShell automatically inserts extra quotes, Carriage Returns (`\r\n`), or Byte Order Marks (BOM), or converts bytes into lists of decimals. When GCP mounts these corrupted values as environment variables, the Python `googlemaps` library's local key format validator rejects them.
*   **Solution:** Re-upload a clean unquoted version of your key to GCP Secret Manager by creating a temporary ASCII file, uploading it, and removing the file (see Step 3, Point 2).

---

## 5. Operations: Scaling, Costs, and Management

Google Cloud Run is highly cost-efficient and automatically scales down to zero when idle, keeping development and testing costs at **$0.00**.

*   **How Billing/Scaling Works (Scale Down to 0 automatically):**
    Google Cloud Run automatically shuts down all active container instances when there is no incoming traffic. Therefore, if no one is visiting your website, the service **already scales down to 0 active instances naturally**, costing you exactly **$0.00** without you having to run any commands!
    
*   **Pause Services Completely (Disable public internet access):**
    Because the Knative autoscaler requires `max-instances` to be a positive integer (>= 1), setting `--max-instances=0` is invalid and will throw an error. If you want to **fully disable public traffic** to make the services private (preventing anyone from using them), revoke the public invoke permissions:
    ```powershell
    gcloud run services remove-iam-policy-binding carepathai-frontend --region=asia-south1 --member="allUsers" --role="roles/run.invoker"
    gcloud run services remove-iam-policy-binding carepathai-backend --region=asia-south1 --member="allUsers" --role="roles/run.invoker"
    ```
    
*   **Unpause Services (Restore public internet access):**
    ```powershell
    gcloud run services add-iam-policy-binding carepathai-frontend --region=asia-south1 --member="allUsers" --role="roles/run.invoker"
    gcloud run services add-iam-policy-binding carepathai-backend --region=asia-south1 --member="allUsers" --role="roles/run.invoker"
    ```
*   **Optimize Cold Start Latency (Keep minimum 1 warm instance online):**
    *Note: Keeping a minimum instance active does bypass scaling to zero, which may incur slight billing costs.*
    ```powershell
    gcloud run services update carepathai-backend --region=asia-south1 --min-instances=1
    ```

---

## 6. Automated CI/CD (GitHub Trigger)

Once you commit these files to your Git repository, you can configure fully automatic deployments so that every `git push` to your master/main branch triggers a rebuild:
1.  Go to the **Cloud Build** Console.
2.  Click **Triggers** -> **Create Trigger**.
3.  Connect your GitHub repository and choose your main branch.
4.  Select **Cloud Build Configuration file (yaml)** and point to `/cloudbuild.yaml`.
5.  Under **Advanced / Substitution variables**, define `_VITE_API_BASE_URL` with your backend URL to ensure automated builds are correctly compiled.
