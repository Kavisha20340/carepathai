# CarePathAI — Full-Stack Deployment Guide

This guide details the deployment of **CarePathAI Frontend** (Vite + React + Nginx) and **CarePathAI Backend** (FastAPI + Python) to **Google Cloud Run** using **Google Cloud Build**, **Artifact Registry**, and **Google Cloud Secret Manager**.

---

## 1. Cloud Architecture Overview

```
[User Browser]
      │
      +---> (HTTPS) ---> [CarepathAI Frontend Cloud Run] (Port 80 via Nginx)
      │
      +---> (HTTPS) ---> [CarepathAI Backend Cloud Run] (Port 8080 via Uvicorn)
                             │
                             +---> Google Secret Manager (PLACES_API_KEY)
                             +---> Vertex AI Gemini 2.5 Flash API (Triage & Denoising)
                             +---> Google Cloud Speech-to-Text API (STT)
                             +---> Cloud Firestore (Session DB & Caching)
```

| Microservice | Container Base | Port | Deployment Mechanism |
|---|---|---|---|
| `carepathai-frontend` | `nginx:stable-alpine` | `80` | Google Cloud Build (`cloudbuild.yaml`) $\rightarrow$ Artifact Registry |
| `carepathai-backend` | `python:3.11-slim` | `8080` | Source-based Cloud Run Deploy (`gcloud run deploy --source=./backend`) |
| `medgemma-cpu` | `python:3.11-slim` + `llama-cpp-python` | `8080` | Standalone Docker build with baked GGUF weights $\rightarrow$ Cloud Run (8 vCPU / 8GiB) |

---

## 2. Step-by-Step Deployment

### Step 1: Authenticate with Google Cloud
```powershell
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### Step 2: Deploy Backend to Cloud Run
Run this command to containerize, configure environment variables, mount Secret Manager secrets, and deploy the backend to Cloud Run in `asia-south2`:

```powershell
gcloud run deploy carepathai-backend `
  --source=./backend `
  --region=asia-south2 `
  --allow-unauthenticated `
  --set-env-vars=GCP_PROJECT=<YOUR_GCP_PROJECT_ID>,MEDGEMMA_API_URL=https://medgemma-cpu-xxxxx.asia-south2.run.app/generate `
  --set-secrets=PLACES_API_KEY=PLACES_API_KEY:latest
```
*Note the returned Backend Service URL (e.g. `https://carepathai-backend-[PROJECT_NUMBER].asia-south2.run.app`).*

### Step 2b: Grant IAM Permissions
```powershell
gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_ID> `
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
  --role="roles/speech.client"
```

### Step 3: Configure Credentials with GCP Secret Manager
Sensitive keys (`PLACES_API_KEY`) are stored in Secret Manager and mounted dynamically.

1. **Create and Upload Secret:**
   ```powershell
   gcloud secrets create PLACES_API_KEY
   "your-google-places-api-key" | Set-Content -NoNewline -Encoding Ascii -Path secret.txt
   gcloud secrets versions add PLACES_API_KEY --data-file=secret.txt
   Remove-Item secret.txt
   ```

2. **Mount Secret to Backend Service:**
   ```powershell
   gcloud secrets add-iam-policy-binding PLACES_API_KEY `
     --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" `
     --role="roles/secretmanager.secretAccessor"

   gcloud run services update carepathai-backend `
     --region=asia-south2 `
     --set-secrets=PLACES_API_KEY=PLACES_API_KEY:latest
   ```

### Step 4: Deploy Frontend via Google Cloud Build
Build and deploy the frontend container, binding the backend API URL:

```powershell
gcloud builds submit --config=cloudbuild.yaml --substitutions=_VITE_API_BASE_URL="https://carepathai-backend-[PROJECT_NUMBER].asia-south2.run.app" .
```

---

## 3. Operational Troubleshooting & Management

| Symptom | Cause | Solution |
|---|---|---|
| **404 on Refresh in Frontend** | Single-page application route missing Nginx fallback | Solved by `/frontend/nginx.conf` (`try_files $uri $uri/ /index.html;`). |
| **CORS Error on API Call** | Cross-Origin Request blocked or URL mismatch | Ensure `_VITE_API_BASE_URL` uses `https://` backend URL during frontend Cloud Build. |
| **Google Places Invalid API Key** | Secret key corrupted by PowerShell newline encoding | Upload key as ASCII with `-NoNewline` via `Set-Content` file buffer. |
| **Cold Start Latency** | Cloud Run scaling to 0 idle instances | Scale to 1 warm min instance: `gcloud run services update carepathai-backend --region=asia-south2 --min-instances=1`. |

---

## 4. Cost Optimization & Management

* **Scale to 0 (Zero Idle Cost)**: Cloud Run shuts down idle containers automatically, incurring **$0.00** charges when inactive.
* **Pause Public Access**: Revoke unauthenticated invocation permissions to pause traffic:
  ```powershell
  gcloud run services remove-iam-policy-binding carepathai-backend --region=asia-south2 --member="allUsers" --role="roles/run.invoker"
  ```
* **Unpause Public Access**:
  ```powershell
  gcloud run services add-iam-policy-binding carepathai-backend --region=asia-south2 --member="allUsers" --role="roles/run.invoker"
  ```

---

## 5. Automated CI/CD (GitHub Triggers)

Connect your GitHub repository to GCP Cloud Build:
1. Go to **Cloud Build Console** $\rightarrow$ **Triggers** $\rightarrow$ **Create Trigger**.
2. Connect your GitHub repository and branch (`main` or `v2`).
3. Select **Cloud Build Configuration file (yaml)** pointing to `/cloudbuild.yaml`.
4. Add substitution variable `_VITE_API_BASE_URL` with your backend Cloud Run URL.
