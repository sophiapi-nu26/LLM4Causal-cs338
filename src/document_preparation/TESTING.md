# Testing Guide for Article Retrieval Pipeline

This guide provides comprehensive testing commands to verify all components of the article retrieval and cloud storage pipeline.

## Prerequisites

```bash
# Activate virtual environment
source venv/bin/activate

# Verify Python environment
python --version  # Should be 3.11+

# Verify installations
pip list | grep -E "(google-cloud-storage|pymupdf|requests|python-dotenv)"
```

## 1. Basic Article Retrieval (No Cloud)

Test the traditional PDF download workflow without parsing or cloud storage.

```bash
# Test 1: Basic retrieval with local PDF storage
python article_retriever.py \
  --query "graphene oxide composite" \
  --max-results 3 \
  --outdir ./test_basic \
  --year-min 2023

# Verify outputs:
ls ./test_basic/          # Should contain PDFs and manifest.csv
cat ./test_basic/manifest.csv | head -n 2  # Check CSV format

# Cleanup
rm -rf ./test_basic
```

**Expected:** 3 PDFs downloaded locally, manifest.csv created with metadata.

---

## 2. Parser-Only Testing (No Cloud)

Test PDF parsing without cloud upload.

```bash
# Test 2: Parse PDFs without cloud storage
python article_retriever.py \
  --query "titanium alloy biomedical" \
  --max-results 2 \
  --outdir ./test_parse_only \
  --year-min 2023 \
  --parse-pdfs

# Verify:
ls ./test_parse_only/     # Should contain PDFs (saved locally when no cloud)
grep "parse_status" ./test_parse_only/manifest.csv  # Check parse status column

# Cleanup
rm -rf ./test_parse_only
```

**Expected:** PDFs downloaded, parsed successfully, no cloud upload, `parse_status=success` in manifest.

---

## 3. Cloud-Native Streaming Workflow

Test the complete cloud pipeline with NO local PDF storage.

```bash
# Test 3: Full cloud streaming (recommended workflow)
python article_retriever.py \
  --query "polymer nanocomposites" \
  --max-results 3 \
  --outdir ./test_cloud_streaming \
  --year-min 2022 \
  --parse-pdfs \
  --cloud-storage

# Verify local directory (should have NO PDFs):
ls ./test_cloud_streaming/     # Should ONLY contain manifest.csv

# Check manifest for cloud URIs:
cat ./test_cloud_streaming/manifest.csv | grep "gs://"

# Cleanup
rm -rf ./test_cloud_streaming
```

**Expected:**
- No local PDFs (everything streamed to cloud)
- manifest.csv contains `parsed_data_uri` with `gs://...` URLs
- Output shows: "PDF downloaded (streamed to cloud)"

---

## 4. GCP Cloud Storage Verification

Verify that parsed data was actually uploaded to Google Cloud Storage.

```bash
# Test 4a: List recent uploads in cloud
python -c "
from gcp_connector import GCPBucketConnector

connector = GCPBucketConnector()
print('Recent parsed data in GCS:')
print('=' * 70)

blobs = list(connector.bucket.list_blobs(prefix='parsed/', max_results=10))
blobs.sort(key=lambda b: b.updated, reverse=True)

for i, blob in enumerate(blobs[:5], 1):
    size_kb = blob.size / 1024
    print(f'{i}. {blob.name}')
    print(f'   Size: {size_kb:.1f} KB | Updated: {blob.updated}')
"

# Test 4b: Download and verify parsed data
python -c "
from gcp_connector import GCPBucketConnector

connector = GCPBucketConnector()

# Get the most recent paper ID (from manifest)
import csv
with open('./test_cloud_streaming/manifest.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['parsed_data_uri']:
            paper_id = row['openalex_id'].replace('https://openalex.org/', '')
            break

# Download parsed data
data = connector.download_parsed_data(paper_id)

print(f'Downloaded parsed data for: {paper_id}')
print(f'  Title: {data.get(\"metadata\", {}).get(\"title\", \"N/A\")}')
print(f'  Full text length: {len(data.get(\"full_text\", \"\"))} chars')
print(f'  Sections: {list(data.get(\"sections\", {}).keys())}')
"
```

**Expected:**
- List shows recently uploaded JSON files
- Download retrieves structured parsed data with full_text, sections, metadata

---

## 5. Parser Adapter Testing

Test the parser adapter directly with a local PDF.

```bash
# Test 5: Direct parser testing
python -c "
from parser_adapter import KenParserAdapter

parser = KenParserAdapter()

# Test with local PDF (use any PDF you have)
result = parser.parse('../../2018_Recombinant_Spidroins.pdf', paper_id='test-direct')

print('Parser Test Results:')
print('=' * 60)
print(f'Full text length: {len(result[\"full_text\"])} characters')
print(f'Sections found: {list(result[\"sections\"].keys())}')
print(f'Metadata: {result[\"metadata\"]}')
print(f'Parser version: {result[\"parser_version\"]}')
print('\nFirst 200 chars:', result[\"full_text\"][:200])
"
```

**Expected:** PDF parsed successfully, returns dict with full_text, sections, metadata.

---

## 6. GCP Connector Testing

Test GCP upload/download directly.

```bash
# Test 6: GCP connector operations
python -c "
from gcp_connector import GCPBucketConnector

connector = GCPBucketConnector()

print('GCP Connector Test')
print('=' * 60)

# Test data
test_data = {
    'full_text': 'Test paper content',
    'sections': {'abstract': 'Test abstract'},
    'metadata': {'title': 'Test Paper'},
    'paper_id': 'test-gcp-123'
}

# Upload
print('1. Uploading test data...')
uri = connector.upload_parsed_data(test_data, 'test-gcp-123')
print(f'   Uploaded to: {uri}')

# Check existence
print('\n2. Checking if exists...')
exists = connector.parsed_data_exists('test-gcp-123')
print(f'   Exists: {exists}')

# Download
print('\n3. Downloading data...')
downloaded = connector.download_parsed_data('test-gcp-123')
print(f'   Downloaded successfully')
print(f'   Full text matches: {downloaded[\"full_text\"] == test_data[\"full_text\"]}')

print('\n✅ GCP connector working correctly!')
"
```

**Expected:** Upload, check, download all succeed. Data integrity maintained.

---

## 7. Failed PDF Handling

Test that failed PDFs are saved to cloud for debugging.

```bash
# Test 7: Simulate a parsing failure
# (This test requires manually corrupting a PDF or using a non-PDF file)

# Create a fake "corrupted" PDF
echo "This is not a real PDF" > ./fake_paper.pdf

python -c "
from gcp_connector import GCPBucketConnector

connector = GCPBucketConnector()

# Upload as failed PDF
with open('./fake_paper.pdf', 'rb') as f:
    pdf_bytes = f.read()

uri = connector.upload_failed_pdf(
    pdf_bytes,
    'test-failed-123',
    error_msg='PyMuPDF: file structure error'
)

print(f'Failed PDF uploaded to: {uri}')
"

# Cleanup
rm ./fake_paper.pdf
```

**Expected:** Failed PDF saved to `gs://bucket/failed_pdfs/test-failed-123.pdf` with error metadata.

---

## 8. End-to-End Integration Test

Complete workflow test with multiple papers.

```bash
# Test 8: Full pipeline with diverse queries
python article_retriever.py \
  --query "machine learning materials discovery" \
  --max-results 5 \
  --outdir ./test_integration \
  --year-min 2023 \
  --parse-pdfs \
  --cloud-storage

# Verify results:
echo "=== Local Files ==="
ls -lh ./test_integration/

echo -e "\n=== Manifest Summary ==="
python -c "
import csv

with open('./test_integration/manifest.csv', 'r') as f:
    reader = csv.DictReader(f)
    papers = list(reader)

total = len(papers)
downloaded = sum(1 for p in papers if p['download_status'] == 'downloaded')
parsed = sum(1 for p in papers if p['parse_status'] == 'success')
cloud_stored = sum(1 for p in papers if p['parsed_data_uri'])

print(f'Total papers: {total}')
print(f'Downloaded: {downloaded}')
print(f'Parsed successfully: {parsed}')
print(f'Stored in cloud: {cloud_stored}')
"

# Cleanup
rm -rf ./test_integration
```

**Expected:**
- 5 papers processed
- All successful downloads parsed and uploaded to cloud
- No local PDFs
- manifest.csv shows cloud URIs and parse status

---

## 9. Backward Compatibility Test

Verify old workflow still works without new flags.

```bash
# Test 9: Old workflow (no parsing, local storage)
python article_retriever.py \
  --query "graphene" \
  --max-results 2 \
  --outdir ./test_backward_compat

# Verify:
ls ./test_backward_compat/*.pdf   # PDFs should exist
grep "parse_status" ./test_backward_compat/manifest.csv || echo "No parse_status column (expected)"

# Cleanup
rm -rf ./test_backward_compat
```

**Expected:** Traditional workflow works unchanged, PDFs saved locally, no parsing.

---

## 10. Performance and Error Handling

Test rate limiting, retries, and error recovery.

```bash
# Test 10a: Large batch (test rate limiting)
python article_retriever.py \
  --query "materials science" \
  --max-results 20 \
  --outdir ./test_large_batch \
  --year-min 2023 \
  --parse-pdfs \
  --cloud-storage \
  --sleep 0.2

# Monitor output for:
# - Rate limit handling (Semantic Scholar circuit breaker)
# - Retry logic
# - Failed PDF uploads

# Cleanup
rm -rf ./test_large_batch
```

**Expected:**
- Pipeline handles rate limits gracefully
- Retries on transient failures
- Failed papers tracked in manifest

---

## Common Issues and Solutions

### Issue 1: `ModuleNotFoundError: No module named 'matsci_llm_causality'`

**Solution:**
```bash
pip install -e ../../  # From LLM4Causal-cs338 root
```

### Issue 2: `ConnectionError: Can't connect to bucket`

**Solution:**
```bash
# Check .env file exists
cat ../../.env | grep GCP_BUCKET_NAME

# Verify credentials
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test connection
python -c "from gcp_connector import GCPBucketConnector; c = GCPBucketConnector(); print('Connected!')"
```

### Issue 3: No PDFs downloaded (all "no-pdf-available")

**Solution:**
```bash
# Try different query or loosen filters
python article_retriever.py \
  --query "machine learning" \
  --max-results 5 \
  --include-closed-access  # Include non-open-access papers
```

### Issue 4: Parsing failures

**Solution:**
```bash
# Check failed PDFs in cloud
python -c "
from gcp_connector import GCPBucketConnector
c = GCPBucketConnector()
blobs = list(c.bucket.list_blobs(prefix='failed_pdfs/', max_results=10))
for b in blobs:
    print(f'{b.name}: {b.metadata}')
"
```

---

## Quick Smoke Test

Run this single command to verify everything works:

```bash
python article_retriever.py \
  --query "graphene" \
  --max-results 2 \
  --outdir ./smoke_test \
  --year-min 2023 \
  --parse-pdfs \
  --cloud-storage && \
ls ./smoke_test/ && \
cat ./smoke_test/manifest.csv | grep "gs://" && \
echo "✅ SMOKE TEST PASSED" && \
rm -rf ./smoke_test
```

If this succeeds, your pipeline is working correctly!

---

## Environment Verification

Run this to check your complete setup:

```bash
python -c "
import sys
print('Python version:', sys.version)

try:
    from google.cloud import storage
    print('✓ google-cloud-storage installed')
except:
    print('✗ google-cloud-storage missing')

try:
    import fitz
    print('✓ PyMuPDF installed')
except:
    print('✗ PyMuPDF missing')

try:
    from matsci_llm_causality.extraction.Ken_PDF_text_Parsing import ScientificPDFExtractor
    print('✓ matsci_llm_causality installed')
except:
    print('✗ matsci_llm_causality missing')

try:
    from parser_adapter import KenParserAdapter
    from gcp_connector import GCPBucketConnector
    print('✓ parser_adapter and gcp_connector importable')
except:
    print('✗ Local modules not in path')

import os
if os.path.exists('.env'):
    print('✓ .env file exists')
else:
    print('✗ .env file missing')
"
```

---

## Success Criteria

Your pipeline is working correctly if:

1. ✅ Articles retrieved from OpenAlex
2. ✅ PDFs downloaded from multiple sources (Semantic Scholar, OpenAlex, Unpaywall)
3. ✅ PDFs parsed successfully (no local storage with `--cloud-storage`)
4. ✅ Parsed JSON uploaded to GCS
5. ✅ manifest.csv contains `parsed_data_uri` with `gs://` URIs
6. ✅ Failed PDFs saved to cloud with error metadata
7. ✅ Cloud storage lists show recent uploads
8. ✅ Downloaded parsed data matches uploaded data

If all tests pass, your cloud-native article retrieval pipeline is production-ready! 🎉
