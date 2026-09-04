# Google Cloud Platform (GCP) Deployment & CI/CD Guide
## CarepathAI Frontend Application

This guide contains complete documentation of the architecture, configuration, step-by-step setup, troubleshooting logs, and day-to-day operations for deploying and hosting the **CarepathAI Frontend** (Vite + React) on **Google Cloud Run** using **Google Cloud Build** and **Artifact Registry**.

---

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

1. **Build Stage (Node.js)**: Installs production and development dependencies, runs `vite build`, and generates optimized static assets under `/frontend/dist`.
2. **Production Stage (Nginx)**: Discards Node.js completely. It copies only the compiled static assets into a lightweight, high-performance **Nginx** server, along with a custom router configuration.
3. **Hosting (Cloud Run)**: A fully managed, serverless execution environment that automatically scales down to zero when there is no traffic and scales up instantly upon request.

---

## 2. Configuration Files Created

To containerize, optimize, and automate the deployment pipeline, we created four critical configuration files in the repository:

### A. Custom Web Server Configuration
**File:** `/frontend/nginx.conf`  
**Purpose:** Solves the "404 on Refresh" problem. Since React is a Single Page Application (SPA) using `react-router-dom` for client-side routing, Nginx must serve `/index.html` for any request it cannot find physically on the disk.

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
```

### B. Multi-Stage Containerization
**File:** `/frontend/Dockerfile`  
**Purpose:** Defines how to build and package your React application. Keeps the final production container extremely lightweight (~25MB instead of 500MB+) by excluding Node.js and source files from the final image.

```dockerfile
# Use an official Node.js runtime as a parent image
FROM node:20-slim as build

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the Vite project
RUN npm run build

# Use a lightweight web server to serve the static files
FROM nginx:stable-alpine

# Copy the custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start the web server
CMD ["nginx", "-g", "daemon off;"]

### C. Build Pipeline Automator
**File:** `/cloudbuild.yaml`  
**Purpose:** Automates the CI/CD pipeline on Google Cloud Build. It orchestrates building the docker image from `/frontend`, pushing it to Artifact Registry, and deploying it to Cloud Run.

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'asia-south1-docker.pkg.dev/carepathai/carepathai-repo/carepathai-frontend:$BUILD_ID', './frontend']

  # Push the container image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'asia-south1-docker.pkg.dev/carepathai/carepathai-repo/carepathai-frontend:$BUILD_ID']

  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'carepathai-frontend'
      - '--image=asia-south1-docker.pkg.dev/carepathai/carepathai-repo/carepathai-frontend:$BUILD_ID'
      - '--region=asia-south1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--port=80'

images:
  - 'asia-south1-docker.pkg.dev/carepathai/carepathai-repo/carepathai-frontend:$BUILD_ID'
```

### D. Cloud Build Performance Optimizer
**File:** `/.gcloudignore`  
**Purpose:** Tells Google Cloud SDK which files to ignore during transfer. By ignoring large development folders (`node_modules`, `.venv`, `.pytest_cache`), we shrunk the upload payload from hundreds of megabytes to just **378 KiB**, reducing build initialization from several minutes to under 5 seconds.

```text
# Ignore git folder
.git/
.gitignore

# Ignore node modules and build outputs
node_modules/
dist/
build/

# Ignore local environment variables
.env
.env.local
.env.production
.env.development

# Ignore python virtual environments and cache
.venv/
venv/
__pycache__/
.pytest_cache/
.ipynb_checkpoints/
*.pyc

# Ignore IDE settings
.vscode/
.idea/
```

---

## 3. Deployment Steps Executed (Windows Environment)

Here are the precise commands run to prepare and deploy your application.

### Step 1: Initialize Project Configuration
Before initiating any builds, the Google Cloud CLI was configured to point to your specific project:
```powershell
gcloud config set project carepathai
```

### Step 2: Enable Necessary GCP Services
Google Cloud APIs were activated to authorize the required managed microservices:
```powershell
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### Step 3: Create the Docker Repository
We created a secure Docker image repository in the Google Artifact Registry located in the `asia-south1` region:
```powershell
gcloud artifacts repositories create carepathai-repo --repository-format=docker --location=asia-south1
```

### Step 4: Grant Service Account Permissions
We resolved the Windows-specific syntax differences to query the project number and bind permissions.

In PowerShell:
```powershell
# Store the project number in a variable
$projNum = (gcloud projects describe carepathai --format="value(projectNumber)").Trim()

# Grant Cloud Run administrator rights to the active Compute service account
gcloud projects add-iam-policy-binding carepathai --member="serviceAccount:$projNum-compute@developer.gserviceaccount.com" --role="roles/run.admin"

# Grant registry write authorization to push built images
gcloud projects add-iam-policy-binding carepathai --member="serviceAccount:$projNum-compute@developer.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

### Step 5: Submit Deployment Build
From the project root (`c:\Users\kavgupta5\DEV\carepathai`), we submitted the local source code directly to Cloud Build to initiate compile-test-deploy:
```powershell
gcloud builds submit
```

---

## 4. Troubleshooting Log & Solutions

During deployment, we encountered standard GCP/CI-CD errors. Here is how they were analyzed and permanently resolved:

### Issue 1: Unrecognized Parameter Error (`$(gcloud...)` execution error)
* **Symptom:** Running Unix-style command substitution (`$(gcloud projects describe...)`) inside Windows PowerShell/CMD caused immediate syntax errors.
* **Analysis:** Windows command line environments (CMD and PowerShell) do not support the POSIX `$()` command evaluation format.
* **Solution:** We structured Windows-native PowerShell scripts to capture variables (using `$projNum = (...)` syntax) and then pass them as PowerShell variables to the commands.

### Issue 2: Invalid Image Reference (`carepathai-frontend:`)
* **Symptom:** Cloud Build failed immediately with:
  `invalid image name "asia-south1-docker.pkg.dev/.../carepathai-frontend:": could not parse reference`
* **Analysis:** The `cloudbuild.yaml` originally utilized the `$COMMIT_SHA` variable. However, because we ran a manual upload build via `gcloud builds submit` (instead of triggering the build directly through Git repository webhooks), the `$COMMIT_SHA` environment variable evaluated as empty.
* **Solution:** We changed `$COMMIT_SHA` to `$BUILD_ID` in `cloudbuild.yaml`. `$BUILD_ID` is a globally available variable on Cloud Build that is guaranteed to always generate a unique alphanumeric tag for any type of build run.

### Issue 3: Permission Denied (`run.services.get` on Service Account)
* **Symptom:** Cloud Build step failed at the deployment stage reporting:
  `PERMISSION_DENIED: Permission 'run.services.get' denied on resource... Authenticated as 923604271747-compute@developer.gserviceaccount.com`
* **Analysis:** Modern GCP configurations route Cloud Build execution steps through the Default Compute Service Account (`YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com`) instead of the legacy Cloud Build service account. The active Compute service account lacked permissions to create or alter Cloud Run instances.
* **Solution:** We granted both `roles/run.admin` (Cloud Run Administrator) and `roles/iam.serviceAccountUser` (Service Account User) permissions to the default Compute service account.

### Issue 4: Revision Health Check / Container Start Failure
* **Symptom:** Cloud Run revision creation failed with:
  `The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable`
* **Analysis:** Cloud Run defaults to forwarding web traffic to port `8080`. However, the standard Nginx Alpine web server exposes and listens on port `80` by default.
* **Solution:** Instead of modifying the lightweight Nginx config, we modified `cloudbuild.yaml` to pass the `--port=80` flag in the `gcloud run deploy` step. This seamlessly instructs Cloud Run to bind and forward inbound traffic directly to Nginx's native port `80`.

---

## 5. Operations: Scaling, Costs, and Management

### A. Is This Setup Billable?
Yes, but you will almost certainly incur **$0.00** in bills for development and testing. Under GCP's standard **Free Tier**:
* **Cloud Run**: Gives you **2 Million requests** free per month and ample compute seconds.
* **Artifact Registry**: Provides **0.5 GB** free storage. The Nginx image is exceptionally small (~30MB), staying well within the limit.
* **Cloud Build**: Gives you **120 free build minutes** per day. A typical compile only takes ~2 minutes.

---

### B. Scale Down (Turn Completely OFF)
To avoid any compute execution, put the service on "pause" so that no container instances can boot up under any conditions:
```powershell
gcloud run services update carepathai-frontend --region=asia-south1 --max-instances=0
```
*Visiting your site's URL in this state will return a `503 Service Unavailable` error, consuming $0.00 resources.*

---

### C. Scale Up (Turn Back ON)
To re-enable your public endpoint and set normal parameters:
```powershell
gcloud run services update carepathai-frontend --region=asia-south1 --max-instances=10
```

---

### D. Cold Start Optimization
Cloud Run scales down to zero instances when inactive. When a user visits after a quiet period, they will experience a "cold start" (3-5 seconds delay) as a new container boots up.

* **To eliminate cold starts (Keep 1 instance active):**
  ```powershell
  gcloud run services update carepathai-frontend --region=asia-south1 --min-instances=1
  ```
* **To return to maximum cost-savings (Allow scale-to-zero):**
  ```powershell
  gcloud run services update carepathai-frontend --region=asia-south1 --min-instances=0
  ```

---

### E. Teardown / Deletion
To completely clean up and delete the deployment:
```powershell
gcloud run services delete carepathai-frontend --region=asia-south1 --quiet
```

---

## 6. Upgrading to Automated CI/CD (GitHub Trigger)

Once you commit these files to your Git repository (GitHub/GitLab/Bitbucket), you can configure fully automatic deployments so that every `git push` to your master/main branch triggers a rebuild and deploy:

1. Go to the **Google Cloud Console**.
2. Search for and navigate to **Cloud Build** > **Triggers**.
3. Click **Create Trigger**.
4. Select your **Repository** (e.g., connect your GitHub account and select your repository).
5. Set the **Event** to: `Push to a branch`.
6. Set the **Branch** pattern to: `^main$` (or `^master$`).
7. Set the **Configuration** to: `Cloud Build configuration file (yaml or json)` and ensure it points to `/cloudbuild.yaml`.
8. Click **Create**.

Now, you never have to run `gcloud builds submit` manually. Simply push your code changes to GitHub, and Google Cloud Build will automatically build, test, and release your updated container to Cloud Run!
```
