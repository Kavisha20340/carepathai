# Deployment Guide

This guide contains complete documentation of the architecture, configuration, step-by-step setup, troubleshooting logs, and day-to-day operations for deploying and hosting the **CarepathAI Frontend** (Vite + React) on **Google Cloud Run** using **Google Cloud Build** and **Artifact Registry**.

## 1. Architectural Overview

The CarepathAI Frontend is a modern React Single Page Application (SPA) built using Vite. When deploying to production, serving the application dynamically via Node.js is inefficient. Instead, we use a **two-stage Docker containerization** approach:

```
[Local Source] --(gcloud builds submit)--> [GCP Cloud Build]
                                                    |
                                            (1. Builds React assets via Node.js)
                                            (2. Packages assets inside Nginx)
                                                    |
                                                    v
[GCP Cloud Run] <--(Serves via Port 80)-- [Artifact Registry]
```

1.  **Build Stage (Node.js)**: Installs production and development dependencies, runs `vite build`, and generates optimized static assets under `/frontend/dist`.
2.  **Production Stage (Nginx)**: Discards Node.js completely. It copies only the compiled static assets into a lightweight, high-performance **Nginx** server, along with a custom router configuration.
3.  **Hosting (Cloud Run)**: A fully managed, serverless execution environment that automatically scales down to zero when there is no traffic and scales up instantly upon request.

## 2. Configuration Files

To containerize, optimize, and automate the deployment pipeline, we created four critical configuration files in the repository:

### a. Custom Web Server Configuration

*   **File:** `/frontend/nginx.conf`
*   **Purpose:** Solves the "404 on Refresh" problem. Since React is a Single Page Application (SPA) using `react-router-dom` for client-side routing, Nginx must serve `/index.html` for any request it cannot find physically on the disk.

### b. Multi-Stage Containerization

*   **File:** `/frontend/Dockerfile`
*   **Purpose:** Defines how to build and package your React application. Keeps the final production container extremely lightweight (~25MB instead of 500MB+) by excluding Node.js and source files from the final image.

## 3. Step-by-Step Deployment

**Step 1: Authenticate with Google Cloud**

```powershell
gcloud auth login
gcloud config set project your-gcp-project-id
```

**Step 2: Submit the Build to Cloud Build**

```powershell
gcloud builds submit --config=cloudbuild.yaml .
```

This command will automatically:

1.  Upload your source code.
2.  Execute the steps in `cloudbuild.yaml`.
3.  Build the Docker image.
4.  Push it to Artifact Registry.
5.  Deploy the new version to Cloud Run.

## 4. Troubleshooting

### a. Permission Denied to Artifact Registry

*   **Symptom:** The build fails with `Permission "artifactregistry.repositories.uploadArtifacts" denied`.
*   **Solution:** Grant the **Artifact Registry Writer** role to the Cloud Build service account.

### b. IAM Service Account Permissions

*   **Symptom:** `You are not authorized to deploy to the service`.
*   **Solution:** Grant the **Cloud Run Admin** and **Service Account User** roles to the default Compute service account.

### c. Container Start Failure

*   **Symptom:** Cloud Run revision creation failed with: `The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable`
*   **Solution:** Modify `cloudbuild.yaml` to pass the `--port=80` flag in the `gcloud run deploy` step.

## 5. Operations: Scaling, Costs, and Management

*   **Is This Setup Billable?** Yes, but you will almost certainly incur **$0.00** in bills for development and testing.
*   **Scale Down (Turn Completely OFF):** `gcloud run services update carepathai-frontend --region=asia-south1 --max-instances=0`
*   **Scale Up (Turn Back ON):** `gcloud run services update carepathai-frontend --region=asia-south1 --max-instances=10`
*   **Cold Start Optimization:** `gcloud run services update carepathai-frontend --region=asia-south1 --min-instances=1`

## 6. Automated CI/CD (GitHub Trigger)

Once you commit these files to your Git repository, you can configure fully automatic deployments so that every `git push` to your master/main branch triggers a rebuild and deploy by creating a trigger in the Google Cloud Console.
