# Article Retrieval & Parsing API

REST API for retrieving and parsing scientific papers from OpenAlex with automatic PDF download and text extraction.

## Features

- Query-based paper search via OpenAlex API
- Multi-source PDF download (Semantic Scholar, OpenAlex, Unpaywall)
- PDF parsing with text extraction and section detection
- Google Cloud Storage integration for parsed data (stateless architecture)
- Asynchronous job processing for long-running queries
- Interactive Swagger UI for API testing
- Fully containerized with Docker

## Documentation

- **Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment to Google Cloud Run
- **Module Documentation**: See [document_preparation/README.md](document_preparation/README.md) for backend implementation details

## Quick Start

### Prerequisites

- Docker Desktop
- GCP Account with Cloud Storage bucket
- gcloud CLI

### Setup

1. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Configure environment** (create `.env` in project root):
   ```bash
   GCP_BUCKET_NAME=your-bucket-name
   GOOGLE_CLOUD_PROJECT=your-project-id
   SEMANTIC_SCHOLAR_KEY=your-api-key-here  # Optional
   ENABLE_PERFORMANCE_LOGGING=false        # Set to "true" for detailed timing logs
   ```

3. **Run locally**:
   ```bash
   cd src
   docker-compose build
   docker-compose up
   ```

4. **Access Swagger UI**: http://localhost:5001/

## API Usage

### Submit a Retrieval Job

```bash
POST /api/v1/retrieve
```

Request:
```json
{
  "query": "spider silk mechanical properties",
  "max_results": 10,
  "year_min": 2019,
  "parse_pdfs": true
}
```

Response:
```json
{
  "job_id": "run_2025-11-17_143022",
  "status": "queued",
  "status_url": "/api/v1/jobs/run_2025-11-17_143022"
}
```

### Check Job Status

```bash
GET /api/v1/jobs/{job_id}
```

Response:
```json
{
  "job_id": "run_2025-11-17_143022",
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
  "created_at": "2025-11-17T14:30:22Z",
  "updated_at": "2025-11-17T14:33:15Z"
}
```

Status values: `queued`, `running`, `completed`, `failed`

## Performance Monitoring

Toggle detailed timing logs with the `ENABLE_PERFORMANCE_LOGGING` environment variable:

```bash
# Enable timing logs (development/debugging)
ENABLE_PERFORMANCE_LOGGING=true

# Disable timing logs (production, default)
ENABLE_PERFORMANCE_LOGGING=false
```

When enabled, logs include timing for:
- OpenAlex API search
- Semantic Scholar PDF lookups
- PDF downloads
- PDF parsing
- GCS operations
- Total job execution time

Filter timing logs:
```bash
docker-compose logs -f | grep "TIMER"
```

## Project Structure

```
src/
├── api/                        # Flask REST API
│   ├── app.py                 # Application factory
│   ├── routes.py              # API endpoints
│   ├── job_manager.py         # Job state management (GCS-backed)
│   ├── worker.py              # Background job processing
│   └── schemas.py             # Request/response validation
│
├── document_preparation/       # Core retrieval logic
│   ├── article_retriever.py   # Main orchestration
│   ├── gcp_connector.py       # GCS interface
│   ├── parser_adapter.py      # PDF parsing wrapper
│   └── pdf_parser_v2.py       # Text extraction
│
├── Dockerfile.dev             # Development container
├── Dockerfile                 # Production container (optimized)
├── docker-compose.yml         # Local development
└── requirements.txt           # Python dependencies
```

## Development

**Hot reload enabled** - code changes are reflected without rebuilding.

```bash
# Start with logs
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild (when dependencies change)
docker-compose build --no-cache
```

## Storage Architecture

Job metadata stored in GCS for stateless Cloud Run deployment:

```
gs://your-bucket/
├── jobs/
│   └── run_2025-11-17_143022/
│       └── job_metadata.json      # Status, progress, results
│
└── parsed/
    └── run_2025-11-17_143022/
        ├── run_metadata.json      # Query info, statistics
        ├── W12345_extracted.json  # Parsed paper data
        └── W67890_extracted.json
```

### Credentials error
```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials file exists
ls ~/.config/gcloud/application_default_credentials.json

# Rebuild container
docker-compose build --no-cache
```

### GCS access denied
```bash
# Check GCP_BUCKET_NAME in .env matches your bucket
# Verify GOOGLE_CLOUD_PROJECT is set correctly
```

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions on deploying to Google Cloud Run, including:
- GCP service setup
- Secrets management
- Container registry configuration
- Cloud Run deployment
- Monitoring and logs
