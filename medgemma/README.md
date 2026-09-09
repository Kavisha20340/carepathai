# MedGemma 4B — CPU-Only Cloud Run Service

This document provides a complete guide for building, deploying, scaling, and testing the **MedGemma 4B CPU Inference Service** (`medgemma-cpu`) as a standalone microservice on **Google Cloud Platform (GCP)**.

---

## 1. Architecture Overview

MedGemma is deployed as an independent containerized service running a CPU-quantized version of the MedGemma 4B medical LLM (`unsloth/medgemma-4b-it-GGUF`) served via **FastAPI** and **llama-cpp-python**.

```
[ CarePathAI Backend ] 
         |
         +---> (HTTP POST /generate) ---> [ MedGemma Cloud Run Service ] (asia-south2)
                                                     |
                                                     +---> FastAPI App (main.py)
                                                     +---> llama-cpp-python
                                                     +---> GGUF Model (/models/medgemma-4b-it-Q5_K_M.gguf)
```

---

## 2. Model Selection

The default configuration in the `Dockerfile` uses `unsloth/medgemma-4b-it-GGUF` (`medgemma-4b-it-Q5_K_M.gguf`), which is baked into the image during the build step. You can swap `MODEL_REPO` or `MODEL_FILE` build arguments in `Dockerfile` if you want to use a different GGUF quantization.

---

## 3. Prerequisites

1. **Google Cloud SDK (`gcloud` CLI)** installed and logged in:
   ```bash
   gcloud auth login
   gcloud config set project carepathai
   ```
2. Open Google Cloud SDK Shell or Terminal and enter the `medgemma` directory:
   ```bash
   cd medgemma
   ```

---

## 4. Deployment Instructions

### Step 1: Create Artifact Registry Repository (One-Time Setup)
Create a Docker repository in Google Artifact Registry in the `asia-south2` region:

```bash
gcloud artifacts repositories create medgemma-repo --repository-format=docker --location=asia-south2
```

### Step 2: Configure Docker Authentication
Configure `gcloud` as a credential helper for Docker authentication:

```bash
gcloud auth configure-docker asia-south2-docker.pkg.dev
```

### Step 3: Enable Cloud Build API
Ensure the Cloud Build API service is enabled on your project:

```bash
gcloud services enable cloudbuild.googleapis.com
```

### Step 4: Build and Push Image via Google Cloud Build
Submit the build context from the `medgemma` directory to Google Cloud Build. This downloads the quantized model and builds the container image in GCP:

```bash
gcloud builds submit --tag asia-south2-docker.pkg.dev/carepathai/medgemma-repo/medgemma-cpu --timeout=1800s .
```

### Step 5: Deploy to Google Cloud Run
Deploy the container to Cloud Run with 8 vCPUs, 8GiB RAM, CPU boost, and 8 inference threads:

```bash
gcloud run deploy medgemma-cpu --image=asia-south2-docker.pkg.dev/carepathai/medgemma-repo/medgemma-cpu --region=asia-south2 --cpu=8 --memory=8Gi --timeout=300 --concurrency=1 --min-instances=1 --max-instances=2 --cpu-boost --set-env-vars=N_THREADS=8 --allow-unauthenticated
```

#### Deployment Flags Explained:
- `--region=asia-south2`: Deploys to the Delhi region.
- `--cpu=8` & `--memory=8Gi`: Allocates maximum CPU resources for fast inference without GPU requirements.
- `--cpu-boost`: Speeds up container boot and model loading.
- `--concurrency=1`: Limits each container instance to 1 concurrent request to prevent CPU thrashing.
- `--min-instances=1`: Keeps 1 instance warm to eliminate cold-start latency (~15-20s model load into RAM) during active testing.
- `--set-env-vars=N_THREADS=8`: Instructs `llama-cpp-python` to utilize all 8 allocated CPU cores.

---

## 5. Scaling Operations (Cost & Performance Management)

Scale minimum instances up or down based on your usage needs:

### Scale Down to 0 (Idle / Zero Cost Mode)
When not actively testing or demonstrating, scale minimum instances down to `0`. Cloud Run will automatically scale to zero when idle, incurring **$0.00** charges:

```bash
gcloud run services update medgemma-cpu --region=asia-south2 --min-instances=0
```
> *Note: With `min-instances=0`, the first request after an idle period will experience a ~15–20s cold start while the container boots and loads the GGUF model into memory.*

### Scale Up to 1 (Warm Demo / Active Mode)
During active development, testing, or demonstrations, set minimum instances to `1` for immediate responses without cold starts:

```bash
gcloud run services update medgemma-cpu --region=asia-south2 --min-instances=1
```

---

## 6. Backend Integration & Verification

### Connecting to CarePathAI Backend
Set the `MEDGEMMA_API_URL` environment variable on your backend Cloud Run instance or local `.env`:

```bash
MEDGEMMA_API_URL=https://medgemma-cpu-xxxxx-el.a.run.app/generate
```

### Testing the Service Endpoint

```bash
SERVICE_URL=$(gcloud run services describe medgemma-cpu --region=asia-south2 --format='value(status.url)')

curl -X POST "$SERVICE_URL/generate" \
  -F "prompt=What are the primary symptoms of dengue fever?"
```

---

## 7. Quick Reference: All Commands in Sequence

```bash
# 1. Create Repository
gcloud artifacts repositories create medgemma-repo --repository-format=docker --location=asia-south2

# 2. Configure Docker Auth
gcloud auth configure-docker asia-south2-docker.pkg.dev

# 3. Enable Cloud Build API
gcloud services enable cloudbuild.googleapis.com

# 4. Build & Push Image (run from medgemma directory)
gcloud builds submit --tag asia-south2-docker.pkg.dev/carepathai/medgemma-repo/medgemma-cpu --timeout=1800s .

# 5. Deploy Service
gcloud run deploy medgemma-cpu --image=asia-south2-docker.pkg.dev/carepathai/medgemma-repo/medgemma-cpu --region=asia-south2 --cpu=8 --memory=8Gi --timeout=300 --concurrency=1 --min-instances=1 --max-instances=2 --cpu-boost --set-env-vars=N_THREADS=8 --allow-unauthenticated

# 6. Scale Down (Cost-saving, min instances = 0)
gcloud run services update medgemma-cpu --region=asia-south2 --min-instances=0

# 7. Scale Up (Warm instance, min instances = 1)
gcloud run services update medgemma-cpu --region=asia-south2 --min-instances=1
```


