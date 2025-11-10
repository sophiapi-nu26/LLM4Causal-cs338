# Cloud-Native Article Retrieval Pipeline

Complete guide for setting up and using the cloud-native workflow with Google Cloud Storage.

---

## Overview

This system supports a cloud-native streaming architecture that:
- **Parses PDFs** using Ken's ScientificPDFExtractor
- **Uploads parsed data** to Google Cloud Storage (no local PDF storage)
- **Streams through memory** for infinite scalability

---

## Setup Google Cloud Storage

### Step 1: Create a GCP Project and Bucket

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Navigate to **Cloud Storage** → **Buckets**
4. Click **Create Bucket**:
   - Name: `your-bucket-name` (e.g., `mcg-pdf-bucket`)
   - Location: Choose region closest to you
   - Storage class: Standard
   - Access control: Uniform
5. Click **Create**

### Step 2: Create Service Account

1. Navigate to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**:
   - Name: `pdf-retrieval-service`
   - Description: "Article retrieval and PDF parsing service"
3. Click **Create and Continue**
4. Grant role: **Storage Admin**
5. Click **Continue** → **Done**

### Step 3: Generate Service Account Key

1. Click on the newly created service account
2. Go to **Keys** tab → **Add Key** → **Create New Key**
3. Choose **JSON** format
4. Click **Create** (downloads JSON file)
5. Save the JSON file securely:
   ```bash
   # Create .gcp directory in project root
   mkdir -p ../../.gcp

   # Move downloaded key (replace with your actual filename)
   mv ~/Downloads/your-project-xxxxx.json ../../.gcp/service-account-key.json

   # Secure the file
   chmod 600 ../../.gcp/service-account-key.json
   ```

### Step 4: Configure Environment Variables

Update your `.env` file (in project root: `LLM4Causal-cs338/.env`) with GCP configuration:

```bash
# Semantic Scholar API (optional)
SEMANTIC_SCHOLAR_KEY="your-semantic-scholar-key"

# Google Cloud Platform (required for cloud storage)
GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/LLM4Causal-cs338/.gcp/service-account-key.json"
GCP_BUCKET_NAME="your-bucket-name"
```

**Important:** Use **absolute paths** for `GOOGLE_APPLICATION_CREDENTIALS`.

Example:
```bash
GOOGLE_APPLICATION_CREDENTIALS="/Users/yourname/Documents/GitHub/LLM4Causal-cs338/.gcp/service-account-key.json"
GCP_BUCKET_NAME="mcg-pdf-bucket"
```

### Step 5: Install Additional Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install cloud storage
pip install google-cloud-storage

# Install the matsci_llm_causality package (for PDF parsing)
cd ../..  # Go to project root
pip install -e .
cd data/article_retrieval  # Back to working directory
```

### Step 6: Verify Setup

```bash
# Test GCP connection
python -c "
from gcp_connector import GCPBucketConnector
connector = GCPBucketConnector()
print(f'✓ Connected to bucket: {connector.bucket_name}')
"
```

If you see `✓ Connected to bucket: your-bucket-name`, you're all set!

---

## Usage Examples

### 1. Cloud-Native Workflow (Recommended)

Download, parse, and upload to cloud with **NO local PDFs**:

```bash
python article_retriever.py \
  --query "graphene oxide composite materials" \
  --max-results 10 \
  --parse-pdfs \
  --cloud-storage \
  --year-min 2020
```

**What happens:**
1. Searches OpenAlex for relevant papers
2. Downloads PDFs to memory (not disk)
3. Parses PDFs using ScientificPDFExtractor
4. Uploads parsed JSON to GCS
5. **No local PDFs saved** - everything streams through memory

### 2. Parse-Only (Local Storage)

Parse PDFs but save locally without cloud upload:

```bash
python article_retriever.py \
  --query "titanium alloy biomedical" \
  --max-results 5 \
  --parse-pdfs
```

### 3. Traditional Workflow (Backward Compatible)

Just download PDFs locally without parsing:

```bash
python article_retriever.py \
  --query "spider silk" \
  --max-results 10
```

---

## Cloud Storage Structure

```
gs://your-bucket/
├── parsed/                    # Parsed JSON data (main storage)
│   ├── W4286628163/
│   │   └── extracted.json
│   └── W4386248280/
│       └── extracted.json
└── failed_pdfs/               # PDFs that failed parsing
    └── W1234567890.pdf
```

---

## Accessing Parsed Data

### From Python

```python
from gcp_connector import GCPBucketConnector

# Initialize connector
connector = GCPBucketConnector()

# Download parsed data
paper_id = "W4286628163"
data = connector.download_parsed_data(paper_id)

print(f"Title: {data['metadata']['title']}")
print(f"Full text: {len(data['full_text'])} characters")
print(f"Sections: {list(data['sections'].keys())}")
```

### List Recent Uploads

```python
from gcp_connector import GCPBucketConnector

connector = GCPBucketConnector()

blobs = list(connector.bucket.list_blobs(prefix='parsed/', max_results=10))
blobs.sort(key=lambda b: b.updated, reverse=True)

for blob in blobs[:5]:
    print(f'{blob.name} - {blob.size / 1024:.1f} KB')
```

---

## Manifest CSV with Cloud URIs

The manifest.csv includes cloud tracking columns:

| Column | Description |
|--------|-------------|
| `parsed_data_uri` | Cloud storage URI (e.g., `gs://bucket/parsed/W123/extracted.json`) |
| `parse_status` | `success`, `failed`, or `None` |
| `failed_pdf_uri` | Cloud URI for failed PDFs |

---

## Cost Considerations

### Google Cloud Storage Pricing (2024)

- **Storage:** ~$0.02/GB/month
- **Operations:** Minimal for this use case
- **Free tier:** 5 GB storage/month

**Example:** 10,000 papers (~5GB) = ~$0.10/month

---

## Security Best Practices

### 1. Never Commit Credentials

```bash
# Add to .gitignore
echo ".gcp/" >> ../../.gitignore
echo ".env" >> ../../.gitignore
```

### 2. Use Minimal Permissions

- Service account should **only** have "Storage Admin" on specific bucket
- Don't use "Owner" or "Editor" roles

### 3. Rotate Keys Every 90 Days

1. Create new key in GCP Console
2. Update .env with new path
3. Delete old key

### 4. Secure Key File

```bash
chmod 600 ../../.gcp/service-account-key.json
```

---

## Troubleshooting

### Error: "Failed to initialize cloud storage"

1. Check `.env` file:
   ```bash
   cat ../../.env | grep GCP
   ```

2. Verify credentials file exists:
   ```bash
   ls -la $GOOGLE_APPLICATION_CREDENTIALS
   ```

3. Test connection:
   ```bash
   python -c "from gcp_connector import GCPBucketConnector; c = GCPBucketConnector(); print('Connected!')"
   ```

### Error: "403 Forbidden"

1. Grant "Storage Admin" role to service account in GCP Console
2. Wait 30-60 seconds for permissions to propagate
3. Verify bucket name matches `.env`

### Error: "Bucket doesn't exist"

1. Check bucket name in GCP Console
2. Update `.env` with correct name

---

## Quick Reference

### Essential Commands

```bash
# Cloud-native workflow
python article_retriever.py --query "your query" --max-results 20 --parse-pdfs --cloud-storage

# Test GCP connection
python -c "from gcp_connector import GCPBucketConnector; c = GCPBucketConnector(); print('✓')"

# List uploads
python -c "from gcp_connector import GCPBucketConnector; c = GCPBucketConnector(); [print(b.name) for b in list(c.bucket.list_blobs(prefix='parsed/', max_results=5))]"
```

### Environment Variables

```bash
GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/.gcp/service-account-key.json"
GCP_BUCKET_NAME="your-bucket-name"
SEMANTIC_SCHOLAR_KEY="your-api-key"  # Optional
```

---

## Support

For comprehensive testing commands, see [TESTING.md](TESTING.md).

**Happy cloud processing! 🎉**
