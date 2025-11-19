# Document Preparation Module

Backend logic for article retrieval, PDF download, and parsing.

## Purpose

This module handles the core functionality of searching for papers, downloading PDFs, and parsing them into structured text. It is used by both the REST API (`src/api/`) and can be run standalone via CLI.

## Components

- `article_retriever.py` - Main orchestration: search, download, parse, upload
- `gcp_connector.py` - Google Cloud Storage integration
- `parser_adapter.py` - PDF parsing interface
- `pdf_parser_v2.py` - PDF text extraction

## How It Works

1. **Search**: Query OpenAlex API for relevant papers
2. **Download**: Cascade through PDF sources (Semantic Scholar, OpenAlex, Unpaywall)
3. **Parse**: Extract structured text from PDFs
4. **Upload**: Store parsed data in Google Cloud Storage

## API Sources

- **OpenAlex** - Paper search and metadata
- **Semantic Scholar** - Primary PDF source
- **Unpaywall** - Fallback PDF source

## Configuration

Set environment variables in `.env`:
```
SEMANTIC_SCHOLAR_KEY=your-api-key     # Optional, improves rate limits
GCP_BUCKET_NAME=your-bucket           # For cloud storage
GOOGLE_CLOUD_PROJECT=your-project-id  # GCP project
ENABLE_PERFORMANCE_LOGGING=false      # Toggle timing logs
```

## Usage

This module is primarily used through the REST API. See `../README.md` for API documentation.

### CLI Usage (Legacy)

```bash
# Basic example
python article_retriever.py --query "spider silk properties" --max-results 10

# With filters
python article_retriever.py --query "biomaterials" --year-min 2020 --max-results 20
```

For detailed CLI options, run: `python article_retriever.py --help`
