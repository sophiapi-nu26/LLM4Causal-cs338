# MCG Retrieval API Documentation

**Version:** 1.0
**Base URL:** https://llm4causal-api-470387906928.us-central1.run.app
**Last Updated:** November 2025
**Status:** Production
**Audience:** Internal Team

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
   - [POST /api/v1/retrieve](#post-apiv1retrieve)
   - [GET /api/v1/jobs/{job_id}](#get-apiv1jobsjob_id)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Cloud Storage Integration](#cloud-storage-integration)
7. [Performance & Rate Limits](#performance--rate-limits)
8. [Testing Examples](#testing-examples)
9. [Troubleshooting](#troubleshooting)
10. [Appendices](#appendices)

---

## Overview

### Purpose

The MCG Retrieval API is a REST API for retrieving and parsing scientific papers from materials science literature. It provides:

- Query-based paper search via OpenAlex API
- Multi-source PDF download (OpenAlex, Semantic Scholar, Unpaywall)
- Automatic PDF parsing and text extraction
- Cloud storage integration (Google Cloud Storage)
- Asynchronous job processing for long-running queries

### Architecture

```
Client Request
     ↓
Flask-RESTX API (Cloud Run)
     ↓
Job Manager (GCS-backed state)
     ↓
Background Worker (async processing)
     ↓
Article Retriever (OpenAlex + PDF sources)
     ↓
PDF Parser + GCS Upload
     ↓
Results stored in GCS bucket
```

**Key Components:**
- **Flask-RESTX:** REST API framework with Swagger UI
- **Cloud Run:** Serverless container deployment
- **Google Cloud Storage:** Job state persistence and parsed data storage
- **Background Worker:** Asynchronous job processing

### Base URL

```
https://llm4causal-api-470387906928.us-central1.run.app
```

### Versioning

Current API version: **v1**

All endpoints are prefixed with `/api/v1/`

### Authentication

**Current:** No authentication required (internal use)
**Future:** API key authentication may be added for external access

---

## Quick Start

### Step 1: Submit a Retrieval Job

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "graphene oxide composite materials",
    "max_results": 10,
    "year_min": 2019
  }'
```

**Response:**
```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "queued",
  "status_url": "/api/v1/jobs/run_2025-11-20_143022"
}
```

### Step 2: Check Job Status

```bash
curl https://llm4causal-api-470387906928.us-central1.run.app/api/v1/jobs/run_2025-11-20_143022
```

**Response (In Progress):**
```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "running",
  "progress": {
    "total_papers": 10,
    "processed": 3,
    "current_paper": "Graphene oxide-polymer nanocomposites..."
  },
  "results": null,
  "error": null,
  "created_at": "2025-11-20T14:30:22Z",
  "updated_at": "2025-11-20T14:31:15Z"
}
```

**Response (Completed):**
```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "completed",
  "progress": {
    "total_papers": 10,
    "processed": 10
  },
  "results": {
    "papers": [...],
    "summary": {
      "total": 10,
      "downloaded": 8,
      "parsed": 7
    }
  },
  "error": null,
  "created_at": "2025-11-20T14:30:22Z",
  "updated_at": "2025-11-20T14:35:42Z"
}
```

---

## API Endpoints

### POST /api/v1/retrieve

Submit a new article retrieval and parsing job. Jobs are processed asynchronously in the background.

**HTTP Method:** `POST`
**URL:** `https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve`
**Content-Type:** `application/json`

#### Request Parameters

| Parameter    | Type    | Required | Default | Constraints      | Description                                    |
|--------------|---------|----------|---------|------------------|------------------------------------------------|
| query        | string  | Yes      | -       | 1-500 chars      | Search query for OpenAlex API                  |
| max_results  | integer | No       | 20      | 1-100            | Maximum number of papers to retrieve           |
| year_min     | integer | No       | null    | 1950-2100        | Minimum publication year filter                |
| parse_pdfs   | boolean | No       | true    | -                | Whether to parse downloaded PDFs               |

#### Request Body Example

```json
{
  "query": "spider silk mechanical properties",
  "max_results": 20,
  "year_min": 2019,
  "parse_pdfs": true
}
```

#### Success Response (202 Accepted)

Job has been queued for processing.

**Status Code:** `202 Accepted`

```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "queued",
  "status_url": "/api/v1/jobs/run_2025-11-20_143022"
}
```

**Response Fields:**

| Field       | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| job_id      | string | Unique job identifier (format: run_YYYY-MM-DD_HHMMSS) |
| status      | string | Initial status: "queued"                       |
| status_url  | string | Relative URL to poll for job status            |

#### Error Response (400 Bad Request)

Request validation failed.

**Status Code:** `400 Bad Request`

```json
{
  "message": "Validation error: query must be between 1 and 500 characters"
}
```

**Common Validation Errors:**
- Query string too short (< 1 char) or too long (> 500 chars)
- max_results out of range (< 1 or > 100)
- year_min out of valid range (< 1950 or > 2100)
- Invalid JSON format

#### Example Request (curl)

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "titanium alloy biomedical applications",
    "max_results": 15,
    "year_min": 2020,
    "parse_pdfs": true
  }'
```

#### Example Request (Python)

```python
import requests

url = "https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve"
payload = {
    "query": "titanium alloy biomedical applications",
    "max_results": 15,
    "year_min": 2020,
    "parse_pdfs": True
}

response = requests.post(url, json=payload)
job_data = response.json()
print(f"Job ID: {job_data['job_id']}")
print(f"Status URL: {job_data['status_url']}")
```

#### Notes

- Job processing is **asynchronous** - the API returns immediately with a job ID
- Poll the status URL to check job completion
- Job IDs follow the format: `run_YYYY-MM-DD_HHMMSS` (based on submission timestamp)
- Results are stored in GCS bucket at `parsed/{job_id}/`
- Average processing time: 10-30 seconds per paper (depending on PDF size)

---

### GET /api/v1/jobs/{job_id}

Retrieve the current status and results of a submitted job.

**HTTP Method:** `GET`
**URL:** `https://llm4causal-api-470387906928.us-central1.run.app/api/v1/jobs/{job_id}`

#### Path Parameters

| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| job_id    | string | Yes      | Job identifier from POST response |

#### Success Response (200 OK)

**Status Code:** `200 OK`

```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "completed",
  "progress": {
    "total_papers": 10,
    "processed": 10,
    "current_paper": null
  },
  "results": {
    "papers": [
      {
        "paper_id": "W1234567890",
        "doi": "10.1234/example",
        "title": "Graphene Oxide Composite Materials for Advanced Applications",
        "year": 2020,
        "authors": "Smith, J., Johnson, A., et al.",
        "cited_by_count": 156,
        "relevance_score": 78.5,
        "abstract": "This paper investigates...",
        "venue": "Advanced Materials",
        "open_access_status": "gold",
        "download_status": "downloaded",
        "parse_status": "success",
        "pdf_source": "openalex",
        "parsed_data_uri": "gs://bucket/parsed/run_2025-11-20_143022/W1234567890_extracted.json",
        "failed_pdf_uri": null,
        "parsed_data": {
          "title": "Graphene Oxide Composite Materials...",
          "abstract": "...",
          "sections": [...]
        }
      }
    ],
    "summary": {
      "total": 10,
      "downloaded": 8,
      "parsed": 7,
      "failed": 1,
      "no_pdf": 2
    }
  },
  "error": null,
  "created_at": "2025-11-20T14:30:22Z",
  "updated_at": "2025-11-20T14:35:42Z"
}
```

**Response Fields:**

| Field       | Type   | Description                                         |
|-------------|--------|-----------------------------------------------------|
| job_id      | string | Job identifier                                      |
| status      | string | Job status (see Status Values below)                |
| progress    | object | Processing progress information                     |
| results     | object | Job results (null until completed)                  |
| error       | string | Error message (null if no error)                    |
| created_at  | string | ISO 8601 timestamp of job creation                  |
| updated_at  | string | ISO 8601 timestamp of last update                   |

**Status Values:**

| Status    | Description                                              |
|-----------|----------------------------------------------------------|
| queued    | Job is waiting to be processed                          |
| running   | Job is currently being processed                        |
| completed | Job finished successfully                               |
| failed    | Job encountered an error and could not complete         |

**Progress Object:**

| Field          | Type   | Description                                |
|----------------|--------|--------------------------------------------|
| total_papers   | int    | Total number of papers to process          |
| processed      | int    | Number of papers processed so far          |
| current_paper  | string | Title of paper currently being processed   |

#### Error Response (404 Not Found)

Job ID does not exist.

**Status Code:** `404 Not Found`

```json
{
  "message": "Job not found"
}
```

#### Example Request (curl)

```bash
curl https://llm4causal-api-470387906928.us-central1.run.app/api/v1/jobs/run_2025-11-20_143022
```

#### Example Request (Python - Polling)

```python
import requests
import time

url = "https://llm4causal-api-470387906928.us-central1.run.app/api/v1/jobs/run_2025-11-20_143022"

while True:
    response = requests.get(url)
    job = response.json()

    print(f"Status: {job['status']}")

    if job['status'] in ['completed', 'failed']:
        print("Job finished!")
        print(f"Results: {job.get('results', {}).get('summary')}")
        break

    # Show progress
    progress = job.get('progress', {})
    if progress:
        print(f"Progress: {progress.get('processed', 0)}/{progress.get('total_papers', 0)}")

    time.sleep(5)  # Poll every 5 seconds
```

#### Notes

- Job status is persisted to GCS, so it survives Cloud Run container restarts
- Progress updates occur after each paper is processed
- Results include full parsed paper data when `parse_pdfs=true`
- Failed jobs will have an error message in the `error` field
- Job metadata is stored in GCS at `jobs/{job_id}/job_metadata.json`

---

## Data Models

### RetrieveRequest

Request body schema for `POST /api/v1/retrieve`

```json
{
  "query": "string (1-500 chars, required)",
  "max_results": "integer (1-100, optional, default: 20)",
  "year_min": "integer (1950-2100, optional, default: null)",
  "parse_pdfs": "boolean (optional, default: true)"
}
```

**Field Descriptions:**

| Field       | Type    | Constraints         | Default | Description                          |
|-------------|---------|---------------------|---------|--------------------------------------|
| query       | string  | 1-500 chars         | -       | Search query for academic papers     |
| max_results | integer | 1-100               | 20      | Max papers to retrieve               |
| year_min    | integer | 1950-2100           | null    | Filter papers published after year   |
| parse_pdfs  | boolean | -                   | true    | Enable PDF parsing and extraction    |

### JobResponse

Response schema for `POST /api/v1/retrieve`

```json
{
  "job_id": "string",
  "status": "string (queued|running|completed|failed)",
  "status_url": "string"
}
```

### Job

Full job object returned by `GET /api/v1/jobs/{job_id}`

```json
{
  "job_id": "string",
  "status": "string (queued|running|completed|failed)",
  "progress": {
    "total_papers": "integer",
    "processed": "integer",
    "current_paper": "string|null"
  },
  "results": {
    "papers": "array",
    "summary": {
      "total": "integer",
      "downloaded": "integer",
      "parsed": "integer",
      "failed": "integer",
      "no_pdf": "integer"
    }
  },
  "error": "string|null",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### Paper Object

Individual paper within results array:

```json
{
  "paper_id": "string (OpenAlex ID)",
  "doi": "string|null",
  "title": "string",
  "year": "integer|null",
  "authors": "string (comma-separated)",
  "cited_by_count": "integer",
  "relevance_score": "float",
  "abstract": "string|null",
  "venue": "string|null",
  "open_access_status": "string|null",
  "download_status": "string (downloaded|no-pdf-available|download-failed)",
  "parse_status": "string|null (success|failed|upload_failed)",
  "pdf_source": "string|null (openalex|semantic_scholar|unpaywall)",
  "parsed_data_uri": "string|null (GCS URI)",
  "failed_pdf_uri": "string|null (GCS URI)",
  "parsed_data": "object|null (full parsed JSON)"
}
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Meaning              | When It Occurs                           |
|-------------|----------------------|------------------------------------------|
| 200         | OK                   | Successful job status retrieval          |
| 202         | Accepted             | Job successfully queued                  |
| 400         | Bad Request          | Request validation failed                |
| 404         | Not Found            | Job ID does not exist                    |
| 500         | Internal Server Error| Unexpected server error                  |

### Error Response Format

All error responses follow this format:

```json
{
  "message": "Human-readable error description"
}
```

### Common Error Scenarios

#### 400 Bad Request - Invalid Query

```json
{
  "message": "Validation error: query must be between 1 and 500 characters"
}
```

**Cause:** Query string is empty or exceeds 500 characters

**Solution:** Provide a valid query string

#### 400 Bad Request - Invalid max_results

```json
{
  "message": "Validation error: max_results must be between 1 and 100"
}
```

**Cause:** max_results is less than 1 or greater than 100

**Solution:** Use a value between 1-100

#### 400 Bad Request - Invalid year_min

```json
{
  "message": "Validation error: year_min must be between 1950 and 2100"
}
```

**Cause:** year_min is outside valid range

**Solution:** Use a year between 1950-2100

#### 404 Not Found - Job Does Not Exist

```json
{
  "message": "Job not found"
}
```

**Cause:** Job ID does not exist or was never created

**Solution:** Verify the job_id from the POST response

#### 500 Internal Server Error

```json
{
  "message": "Internal server error"
}
```

**Cause:** Unexpected error in backend processing

**Solution:** Check Cloud Run logs, retry request, or contact team

---

## Cloud Storage Integration

### GCS Bucket Structure

All data is stored in the configured GCS bucket (environment variable: `GCP_BUCKET_NAME`)

```
gs://your-bucket/
├── jobs/
│   └── run_2025-11-20_143022/
│       └── job_metadata.json          # Job state and results
│
└── parsed/
    └── run_2025-11-20_143022/
        ├── run_metadata.json          # Query and statistics
        ├── W1234567890_extracted.json # Parsed paper #1
        ├── W9876543210_extracted.json # Parsed paper #2
        └── ...
```

### Job Metadata Location

**Path:** `gs://bucket/jobs/{job_id}/job_metadata.json`

**Purpose:** Stores job state, progress, and results for persistence across Cloud Run restarts

**Format:**
```json
{
  "job_id": "run_2025-11-20_143022",
  "status": "completed",
  "query": "graphene oxide composite materials",
  "progress": {...},
  "results": {...},
  "error": null,
  "created_at": "2025-11-20T14:30:22Z",
  "updated_at": "2025-11-20T14:35:42Z"
}
```

### Parsed Data Location

**Path:** `gs://bucket/parsed/{run_id}/{paper_id}_extracted.json`

**Purpose:** Stores extracted text and metadata from parsed PDFs

**Format:**
```json
{
  "paper_id": "W1234567890",
  "title": "...",
  "abstract": "...",
  "sections": [
    {
      "heading": "Introduction",
      "text": "..."
    }
  ],
  "metadata": {...}
}
```

### Run Metadata

**Path:** `gs://bucket/parsed/{run_id}/run_metadata.json`

**Purpose:** Stores query parameters and summary statistics

**Format:**
```json
{
  "query": "graphene oxide composite materials",
  "timestamp": "2025-11-20T14:30:22Z",
  "run_id": "run_2025-11-20_143022",
  "filters": {
    "year_min": 2019,
    "year_max": null,
    "min_citations": null,
    "include_closed_access": false
  },
  "results": {
    "papers_retrieved": 10,
    "pdfs_downloaded": 8,
    "papers_parsed": 7,
    "papers_failed": 1
  }
}
```

### Accessing GCS Data

#### Using gsutil (Command Line)

```bash
# List jobs
gsutil ls gs://your-bucket/jobs/

# Download job metadata
gsutil cp gs://your-bucket/jobs/run_2025-11-20_143022/job_metadata.json .

# List parsed papers
gsutil ls gs://your-bucket/parsed/run_2025-11-20_143022/

# Download parsed paper
gsutil cp gs://your-bucket/parsed/run_2025-11-20_143022/W1234567890_extracted.json .
```

#### Using Python

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('your-bucket')

# Download job metadata
blob = bucket.blob('jobs/run_2025-11-20_143022/job_metadata.json')
job_data = json.loads(blob.download_as_text())

# Download parsed paper
blob = bucket.blob('parsed/run_2025-11-20_143022/W1234567890_extracted.json')
paper_data = json.loads(blob.download_as_text())
```

---

## Performance & Rate Limits

### Expected Response Times

| Operation            | Avg Time  | Notes                                    |
|----------------------|-----------|------------------------------------------|
| POST /api/v1/retrieve| <1s       | Returns immediately (async job)          |
| GET /api/v1/jobs/... | <1s       | Fast read from GCS                       |
| Job processing       | 10-30s/paper | Depends on PDF size and availability  |

### Job Processing Times

**Factors affecting processing time:**
- Number of papers requested (max_results)
- PDF download speed (varies by source)
- PDF parsing complexity (multi-column layouts slower)
- Network latency to external APIs (OpenAlex, Semantic Scholar, Unpaywall)

**Typical processing times:**
- 5 papers: 1-2 minutes
- 10 papers: 2-4 minutes
- 20 papers: 4-8 minutes
- 50 papers: 10-20 minutes

### Rate Limits

**API Rate Limits:**
- No rate limits currently enforced on API endpoints (internal use)
- Consider implementing rate limiting if exposed externally

**External API Rate Limits:**
- **OpenAlex:** 10 requests/second (handled with 0.1s sleep)
- **Semantic Scholar:** ~100 requests/5 minutes (circuit breaker implemented)
- **Unpaywall:** No strict limits (polite crawling with delays)

### Concurrency

- **Single worker thread:** Jobs are processed sequentially (one at a time)
- **Multiple concurrent requests:** Multiple jobs can be queued, but process one-by-one
- **Future scaling:** Worker can be scaled to multiple threads/containers if needed

### Performance Optimization

**Enabled via environment variable:**
```bash
ENABLE_PERFORMANCE_LOGGING=true
```

**Provides timing logs for:**
- OpenAlex API search
- Semantic Scholar PDF lookups
- PDF downloads
- PDF parsing
- GCS operations
- Total job execution time

**Filter timing logs:**
```bash
gcloud run logs read --service=your-service --filter="TIMER"
```

---

## Testing Examples

### Example 1: Quick Test (Small Query)

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "graphene",
    "max_results": 3,
    "year_min": 2023
  }'
```

**Expected:** 3 papers, ~30-60 seconds processing time

### Example 2: Standard Query (Materials Science)

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "polymer nanocomposites mechanical properties",
    "max_results": 10,
    "year_min": 2020
  }'
```

**Expected:** 10 papers, ~2-4 minutes processing time

### Example 3: Large Query (Comprehensive)

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "titanium alloy biomedical applications",
    "max_results": 50,
    "year_min": 2019
  }'
```

**Expected:** 50 papers, ~10-20 minutes processing time

### Example 4: Without PDF Parsing

```bash
curl -X POST https://llm4causal-api-470387906928.us-central1.run.app/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ceramic matrix composites",
    "max_results": 20,
    "parse_pdfs": false
  }'
```

**Expected:** Faster processing (no PDF parsing step)

### Testing Workflow with Python

```python
import requests
import time
import json

# Base URL
BASE_URL = "https://llm4causal-api-470387906928.us-central1.run.app"

# Step 1: Submit job
response = requests.post(
    f"{BASE_URL}/api/v1/retrieve",
    json={
        "query": "carbon fiber reinforced polymers",
        "max_results": 10,
        "year_min": 2020
    }
)

job = response.json()
job_id = job['job_id']
print(f"Job submitted: {job_id}")

# Step 2: Poll for completion
while True:
    response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
    job_status = response.json()

    status = job_status['status']
    print(f"Status: {status}")

    # Check if completed
    if status in ['completed', 'failed']:
        break

    # Show progress
    progress = job_status.get('progress', {})
    processed = progress.get('processed', 0)
    total = progress.get('total_papers', 0)
    print(f"Progress: {processed}/{total}")

    time.sleep(5)

# Step 3: Process results
if job_status['status'] == 'completed':
    results = job_status['results']
    summary = results['summary']

    print(f"\nResults:")
    print(f"Total papers: {summary['total']}")
    print(f"Downloaded: {summary['downloaded']}")
    print(f"Parsed: {summary['parsed']}")

    # Save results to file
    with open(f'{job_id}_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {job_id}_results.json")
else:
    print(f"Job failed: {job_status.get('error')}")
```

---

## Troubleshooting

### Job Stuck in "queued" Status

**Symptoms:**
- Job status remains "queued" for extended period
- No progress updates

**Possible Causes:**
1. Worker thread not started
2. Worker thread crashed
3. Previous job is blocking the queue

**Solutions:**
1. Check Cloud Run logs for worker errors:
   ```bash
   gcloud run logs read --service=your-service --limit=100
   ```
2. Restart the service:
   ```bash
   gcloud run services update your-service --region=us-central1
   ```
3. Submit a new job to test if queue is responsive

### Job Status is "failed"

**Symptoms:**
- Job status shows "failed"
- Error message in `error` field

**Common Error Messages:**

#### "Failed to search OpenAlex"
**Cause:** OpenAlex API unavailable or query invalid

**Solution:**
- Verify OpenAlex API status
- Check query formatting
- Retry with simpler query

#### "Failed to initialize cloud storage"
**Cause:** GCS credentials or bucket misconfigured

**Solution:**
- Verify `GCP_BUCKET_NAME` environment variable
- Check service account permissions
- Confirm bucket exists

#### "No papers found"
**Cause:** Query returned zero results from OpenAlex

**Solution:**
- Broaden search query
- Remove year_min filter
- Try different keywords

### Low PDF Download Success Rate

**Symptoms:**
- Many papers show `download_status: "no-pdf-available"`
- Low `downloaded` count in summary

**Possible Causes:**
1. Papers are not truly open access
2. PDF URLs are broken/expired
3. Network connectivity issues

**Solutions:**
1. Check `open_access_status` field in results
2. Verify papers have `pdf_source` populated
3. Try querying more recent papers (better OA compliance)
4. Check Cloud Run network egress settings

### Parsing Failed for Downloaded PDFs

**Symptoms:**
- PDFs downloaded successfully
- `parse_status: "failed"`
- Papers have `failed_pdf_uri` set

**Possible Causes:**
1. PDF is corrupted or encrypted
2. PDF has complex layout (tables, images)
3. Parser timeout

**Solutions:**
1. Download failed PDF from GCS for manual inspection:
   ```bash
   gsutil cp gs://bucket/failed_pdfs/W1234567890.pdf .
   ```
2. Check parser logs for specific error
3. Increase parser timeout if needed
4. Report problematic PDFs to team

### Slow Job Processing

**Symptoms:**
- Job takes significantly longer than expected
- Progress updates are slow

**Possible Causes:**
1. Large number of papers requested
2. Slow PDF download from external sources
3. Complex PDF parsing

**Solutions:**
1. Enable performance logging to identify bottleneck:
   ```bash
   ENABLE_PERFORMANCE_LOGGING=true
   ```
2. Check which PDF sources are being used (OpenAlex vs Semantic Scholar)
3. Reduce `max_results` for faster testing
4. Set `parse_pdfs: false` to skip parsing step

### Cannot Access Results in GCS

**Symptoms:**
- Job completed successfully
- Cannot download results from GCS

**Possible Causes:**
1. GCS permissions issue
2. Wrong bucket name
3. Results not uploaded due to GCS error

**Solutions:**
1. Verify GCS bucket permissions:
   ```bash
   gsutil ls gs://your-bucket/parsed/
   ```
2. Check `parsed_data_uri` field in results for correct path
3. Review Cloud Run logs for GCS upload errors
4. Results are also returned in API response (no need to access GCS directly)

---

## Appendices

### A. Changelog

**Version 1.0** (November 2025)
- Initial production release
- POST /api/v1/retrieve endpoint
- GET /api/v1/jobs/{job_id} endpoint
- GCS-backed job persistence
- Asynchronous job processing
- Multi-source PDF download (OpenAlex, Semantic Scholar, Unpaywall)
- PDF parsing and text extraction
- Performance monitoring toggle

### B. Related Documentation

- [Main Repository README](../README.md) - Project overview and installation
- [API README](README.md) - Local development and Docker setup
- [Deployment Guide](DEPLOYMENT.md) - Production deployment to Cloud Run
- [Document Preparation Module](document_preparation/README.md) - Backend logic details

### C. External APIs

**OpenAlex API**
- Documentation: https://docs.openalex.org/
- Rate limits: 10 requests/second (polite usage)
- No API key required

**Semantic Scholar API**
- Documentation: https://api.semanticscholar.org/
- Rate limits: ~100 requests/5 minutes without key
- API key recommended for higher limits

**Unpaywall API**
- Documentation: https://unpaywall.org/products/api
- Rate limits: Polite crawling (100k requests/day)
- Requires email parameter

### D. Environment Variables

| Variable                     | Required | Description                           |
|------------------------------|----------|---------------------------------------|
| GCP_BUCKET_NAME              | Yes      | Google Cloud Storage bucket name      |
| GOOGLE_CLOUD_PROJECT         | Yes      | GCP project ID                        |
| SEMANTIC_SCHOLAR_KEY         | No       | API key for higher rate limits        |
| ENABLE_PERFORMANCE_LOGGING   | No       | Enable timing logs (default: false)   |

### E. Interactive API Documentation (Swagger UI)

Access the interactive Swagger UI for testing endpoints directly in your browser:

**URL:** https://llm4causal-api-470387906928.us-central1.run.app/

Features:
- Interactive API explorer
- Try endpoints directly from browser
- Auto-generated request/response examples
- Schema validation

### F. Support and Contact

For questions, issues, or feedback:

- **GitHub Issues:** [Repository Issues Page](https://github.com/your-org/your-repo/issues)
- **Team Contact:** [Your Team Email or Slack Channel]
- **Cloud Run Logs:** Access via GCP Console or `gcloud` CLI

---

## Converting to PDF

### Using Pandoc (Recommended)

```bash
# Install pandoc (macOS)
brew install pandoc

# Convert to PDF with table of contents
pandoc API_DOCUMENTATION.md -o API_DOCUMENTATION.pdf \
  --toc \
  --toc-depth=3 \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V linkcolor=blue \
  --highlight-style=tango \
  --pdf-engine=xelatex
```

### Using Markdown to HTML to PDF

```bash
# Step 1: Convert to HTML
pandoc API_DOCUMENTATION.md -o API_DOCUMENTATION.html \
  --standalone \
  --toc \
  --css=style.css

# Step 2: HTML to PDF (requires wkhtmltopdf)
wkhtmltopdf API_DOCUMENTATION.html API_DOCUMENTATION.pdf
```

### Using Python

```python
import markdown
from weasyprint import HTML

with open('API_DOCUMENTATION.md') as f:
    html = markdown.markdown(
        f.read(),
        extensions=['tables', 'fenced_code', 'toc']
    )

HTML(string=html).write_pdf('API_DOCUMENTATION.pdf')
```

---

**End of Documentation**
