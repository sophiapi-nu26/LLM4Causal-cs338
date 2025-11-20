# GCP Cloud Run Deployment Guide

Guide for deploying the Article Retrieval API to Google Cloud Run.

## Prerequisites

### 1. GCP Account & Project
- Active GCP account with billing enabled
- Existing GCP project (or create new one)
- Project ID handy (e.g., `llm4causal-prod`)

### 2. Local Tools
- **gcloud CLI** installed and configured
- **Docker** installed (for building images)
- **Git** for version control

### 3. Existing Resources
- Google Cloud Storage bucket
- Service account with GCS access

---

## Step 1: Install & Configure gcloud CLI

### Install gcloud

**macOS:**
```bash
# Download and install
curl https://sdk.cloud.google.com | bash

# Restart shell
exec -l $SHELL

# Verify installation
gcloud version
```

**Alternative (Homebrew):**
```bash
brew install --cask google-cloud-sdk
```

### Initialize gcloud

```bash
# Login to your Google account
gcloud auth login

# Set your project (replace with your actual project ID)
gcloud config set project YOUR_PROJECT_ID

# Verify configuration
gcloud config list

# Configure Docker to use gcloud credentials
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Find your project ID:**
```bash
# List all your projects
gcloud projects list

# Example output:
# PROJECT_ID              NAME                PROJECT_NUMBER
# llm4causal-12345        LLM4Causal          123456789
```

---

## Step 2: Enable Required GCP APIs

```bash
# Enable all required APIs in one command
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    storage-api.googleapis.com

# Verify APIs are enabled (this takes ~1 minute)
gcloud services list --enabled | grep -E 'run|artifact|build|secret|storage'
```

**What each API does:**
- `run.googleapis.com` - Cloud Run (runs your containers)
- `artifactregistry.googleapis.com` - Stores Docker images
- `cloudbuild.googleapis.com` - Builds Docker images in cloud
- `secretmanager.googleapis.com` - Stores API keys securely
- `storage-api.googleapis.com` - Access to Cloud Storage

---

## Step 3: Create Artifact Registry Repository

This is where your Docker images will be stored.

```bash
# Set variables for reuse
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"  # Change if you prefer different region
export REPO_NAME="llm4causal-api"

# Create Docker repository
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Article Retrieval API Docker images"

# Verify creation
gcloud artifacts repositories list

# Should show:
# REPOSITORY: llm4causal-api
# FORMAT: DOCKER
# LOCATION: us-central1
```

---

## Step 4: Create Secrets in Secret Manager

**DO NOT** put secrets in environment variables or Dockerfile!

### Create Secrets

```bash
# 1. Semantic Scholar API Key (optional but recommended)
echo -n "YOUR_SEMANTIC_SCHOLAR_KEY" | \
    gcloud secrets create semantic-scholar-key \
    --data-file=- \
    --replication-policy="automatic"

# 2. GCP Bucket Name
echo -n "YOUR_BUCKET_NAME" | \
    gcloud secrets create gcp-bucket-name \
    --data-file=- \
    --replication-policy="automatic"

# Verify secrets were created
gcloud secrets list

# Example output:
# NAME                     CREATED              REPLICATION_POLICY
# semantic-scholar-key     2025-11-16T12:00:00  automatic
# gcp-bucket-name          2025-11-16T12:00:00  automatic
# api-mailto               2025-11-16T12:00:00  automatic
```

**Note:** Replace `YOUR_SEMANTIC_SCHOLAR_KEY` and `YOUR_BUCKET_NAME` with actual values!

### Grant Cloud Run Access to Secrets

```bash
# Get the Cloud Run service account email
# (this is created automatically when you first deploy)
export SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

# Grant secret access
gcloud secrets add-iam-policy-binding semantic-scholar-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gcp-bucket-name \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding api-mailto \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

---

## Step 5: Build & Push Docker Image

### Build Locally

```bash
# Navigate to src directory
cd /path/to/LLM4Causal-cs338/src

# Set image tag
export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/api:latest"

# Build the production Docker image
docker build --platform linux/amd64 -t $IMAGE_TAG -f Dockerfile .

# Test locally (optional but recommended!)
docker run -p 8080:8080 \
  --env-file ../.env \
  -v $(pwd)/../.gcp:/app/.gcp:ro \
  $IMAGE_TAG

# In another terminal, test the API
curl http://localhost:8080/swagger.json

# If it works, stop the container (Ctrl+C)
```

### Push to Artifact Registry

```bash
# Push image to GCP
docker push $IMAGE_TAG

# This will take 2-5 minutes depending on your internet speed
# You'll see output like:
# latest: digest: sha256:abc123... size: 1234
```

### Verify Image

```bash
# List images in repository
gcloud artifacts docker images list \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}

# Should show your pushed image with timestamp
```

---

## Step 6: Deploy to Cloud Run

### Deploy Command

```bash
# Deploy to Cloud Run
gcloud run deploy llm4causal-api \
    --image=$IMAGE_TAG \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --port=8080 \
    --timeout=3600 \
    --memory=4Gi \
    --cpu=4 \
    --no-cpu-throttling \
    --concurrency=1 \
    --min-instances=0 \
    --max-instances=10 \
    --set-secrets="SEMANTIC_SCHOLAR_KEY=semantic-scholar-key:latest,GCP_BUCKET_NAME=gcp-bucket-name:latest \
    --service-account="${SERVICE_ACCOUNT}"

# This takes 1-2 minutes
```

**Parameter explanations:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `--allow-unauthenticated` | Public access | Your team can access without GCP login |
| `--port=8080` | 8080 | Matches Dockerfile EXPOSE port |
| `--timeout=1800` | 30 minutes | Long PDF downloads/parsing |
| `--memory=2Gi` | 2 GB RAM | Enough for PDF parsing |
| `--cpu=2` | 2 CPUs | Matches gunicorn workers (2) |
| `--no-cpu-throttling` | CPU remains allocated during request | Necessary for downloading & parsing speed |
| `--concurrency=1` | Allow 1 job per CPU | Spins up more CPU (higher cost - better performance) |
| `--min-instances=0` | Scale to zero | Save money when not in use |
| `--max-instances=10` | Max 10 containers | Prevent runaway costs |
| `--set-secrets` | From Secret Manager | Inject secrets as env vars |

### Deployment Output

```
Deploying container to Cloud Run service [llm4causal-api] in project [YOUR_PROJECT] region [us-central1]
✓ Deploying new service... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.
Service [llm4causal-api] revision [llm4causal-api-00001-abc] has been deployed and is serving 100 percent of traffic.
Service URL: https://llm4causal-api-ABC123-uc.a.run.app
```

**Save this URL!** This is your production API endpoint.

---

## Step 7: Test Deployed API

### Test Swagger UI

Open in browser:
```
https://llm4causal-api-ABC123-uc.a.run.app/
```

You should see the Swagger UI!

### Test API Endpoint

```bash
# Set your Cloud Run URL
export API_URL="https://llm4causal-api-ABC123-uc.a.run.app"

# Submit a test job
curl -X POST ${API_URL}/api/v1/retrieve \
    -H "Content-Type: application/json" \
    -d '{
        "query": "machine learning",
        "max_results": 2,
        "year_min": 2020
    }'

# Should return:
# {
#   "job_id": "run_2025-11-16_143022",
#   "status": "queued",
#   "status_url": "/api/v1/jobs/run_2025-11-16_143022"
# }

# Check job status (replace JOB_ID)
curl ${API_URL}/api/v1/jobs/run_2025-11-16_143022
```

### View Logs

```bash
# Stream live logs from Cloud Run
gcloud run services logs read llm4causal-api \
    --region=$REGION \
    --limit=50 \
    --format="table(timestamp,severity,textPayload)"

# Follow logs in real-time
gcloud run services logs tail llm4causal-api \
    --region=$REGION
```

---

## Updating the Deployment

### When you make code changes:

```bash
# 1. Navigate to src
cd /path/to/LLM4Causal-cs338/src

# 2. Rebuild image
docker build -t $IMAGE_TAG -f Dockerfile .

# 3. Push new image
docker push $IMAGE_TAG

# 4. Deploy update (reuses most settings)
gcloud run deploy llm4causal-api \
    --image=$IMAGE_TAG \
    --region=$REGION

# Cloud Run will create a new revision and route traffic automatically
# Old revision is kept for rollback if needed
```

### Rollback to previous version:

```bash
# List revisions
gcloud run revisions list --service=llm4causal-api --region=$REGION

# Route traffic to specific revision
gcloud run services update-traffic llm4causal-api \
    --to-revisions=llm4causal-api-00001-abc=100 \
    --region=$REGION
```

