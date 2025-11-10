# Document Preparation Pipeline

Query-based article retrieval, PDF download, and parsing system with intelligent multi-source PDF acquisition and cloud storage integration.

**Location**: `src/document_preparation/`

## Overview

This system allows you to search for academic papers using natural language queries, automatically download available open-access PDFs, parse them into structured text, and optionally upload to cloud storage. It uses the free OpenAlex API for search and intelligently cascades through multiple PDF sources (Semantic Scholar → OpenAlex → Unpaywall) to maximize download success rates.

## Features

- **Query-based search**: Use natural language queries like "spider silk mechanical properties"
- **Automatic relevance ranking**: Results sorted by OpenAlex relevance score
- **Intelligent multi-source PDF download**: Cascades through sources with automatic fallback:
  1. **Semantic Scholar** (primary, with rate limit handling)
  2. **OpenAlex** (from search results)
  3. **Unpaywall** (fallback)
- **PDF parsing (v2)**: Extract structured text from scientific PDFs with multi-column support
- **Cloud storage integration**: Upload parsed data to Google Cloud Storage
- **Flexible filtering**: Filter by year, citation count, and open access status
- **Open access by default**: Only retrieves papers with free PDFs available
- **Detailed metadata**: Saves comprehensive paper information to CSV manifest
- **Comprehensive logging**: Configurable log levels for debugging and production use
- **No API key required**: Uses free APIs from OpenAlex, Semantic Scholar, and Unpaywall
- **Circuit breaker**: Automatically switches to fallback sources when rate limits are hit

## Installation

```bash
# Install required dependency
pip install requests
```

### Optional: Semantic Scholar API Key

To improve rate limits and reliability, you can optionally provide a Semantic Scholar API key:

1. Get a free API key from: https://www.semanticscholar.org/product/api
2. Create a `.env` file in the project root:
   ```bash
   SEMANTIC_SCHOLAR_KEY="your-api-key-here"
   ```

The script will automatically detect and use the API key if present. With an API key, you get significantly higher rate limits (up to 100 requests/second vs. ~100 requests/5 minutes without).

## Basic Usage

```bash
# Simple search for 20 papers (default)
python article_retriever.py --query "spider silk properties"

# Search with custom result limit
python article_retriever.py --query "biomaterials" --max-results 10

# Add your email (recommended for better API rate limits)
python article_retriever.py --query "spider silk" --mailto "your@email.com"
```

## Advanced Usage

### Filter by Publication Year

```bash
# Papers from 2018 onwards
python article_retriever.py \
  --query "spider silk tensile strength" \
  --year-min 2018

# Papers within a specific range
python article_retriever.py \
  --query "biomaterials" \
  --year-min 2015 \
  --year-max 2023
```

### Filter by Citation Count

```bash
# Only highly-cited papers (10+ citations)
python article_retriever.py \
  --query "spider silk" \
  --min-citations 10
```

### Include Closed Access Papers

```bash
# By default, only open access papers are retrieved
# To include all papers (may not be able to download PDFs):
python article_retriever.py \
  --query "spider silk" \
  --include-closed-access
```

### Custom Output Directory

```bash
# Save to a specific directory
python article_retriever.py \
  --query "spider silk" \
  --outdir ./my_papers
```

### Save Raw API Response

```bash
# Save the raw OpenAlex JSON response for debugging
python article_retriever.py \
  --query "spider silk" \
  --save-raw-json
```

### Logging Configuration

Control the verbosity of output using the `--log-level` flag:

```bash
# INFO level (default) - Shows key progress messages
python article_retriever.py \
  --query "spider silk" \
  --log-level INFO

# DEBUG level - Shows detailed tracing for debugging
python article_retriever.py \
  --query "spider silk" \
  --log-level DEBUG

# WARNING level - Shows only warnings and errors (minimal output)
python article_retriever.py \
  --query "spider silk" \
  --log-level WARNING

# ERROR level - Shows only critical errors
python article_retriever.py \
  --query "spider silk" \
  --log-level ERROR
```

**Log Levels:**
- `DEBUG`: Detailed tracing (file paths, API calls, parser operations)
- `INFO` (default): User-facing progress messages (downloads, uploads, summaries)
- `WARNING`: Warnings and recoverable issues (rate limits, failed uploads)
- `ERROR`: Only critical errors

**Use Cases:**
- **Production/API**: Use `WARNING` or `ERROR` to minimize log noise
- **Debugging**: Use `DEBUG` to diagnose PDF parsing or cloud upload issues
- **Default usage**: `INFO` provides good visibility into progress


## Complete Example

```bash
python article_retriever.py \
  --query "spider silk mechanical properties tensile strength" \
  --max-results 20 \
  --year-min 2015 \
  --min-citations 5 \
  --outdir ./spider_silk_papers \
  --mailto "researcher@university.edu"
```

## Cloud Storage Integration

When using `--cloud-storage` and `--parse-pdfs`, parsed papers are automatically uploaded to Google Cloud Storage with the following structure:

```
gs://your-bucket/
├── parsed/
│   └── run_2025-11-09_143022/          # Timestamp-based run folder
│       ├── run_metadata.json            # Query info, filters, statistics
│       ├── W2123456789_extracted.json   # Parsed paper 1
│       ├── W2987654321_extracted.json   # Parsed paper 2
│       └── ...
└── failed_pdfs/
    ├── W2111111111.pdf                  # Failed parse (for debugging)
    └── ...
```

### Run Metadata

Each retrieval run creates a `run_metadata.json` file containing:
- Query text and filters used
- Timestamp of retrieval
- Statistics (papers retrieved, parsed, failed)

### Local PDF Storage (Optional)

By default, PDFs are **not** saved locally when using cloud storage—they stream through memory for parsing.

To save PDFs locally in addition to cloud upload:
```bash
python article_retriever.py \
  --query "spider silk" \
  --cloud-storage \
  --parse-pdfs \
  --save-pdfs-locally \
  --outdir ./local_pdfs
```

PDFs are named using the format:
```
{year}_{first_author}_{title_slug}_{hash}.pdf
```

Example:
```
2012_Florence_Teulé_Silkworms_transformed_with_chimeric_silk_616f61.pdf
```

## Sample Output

```
$ python article_retriever.py --query "spider silk properties" --max-results 5

🔍 Searching OpenAlex for: "spider silk properties"
   Filters: open_access.is_oa:true
✓ Found 7,759 matching papers
📥 Retrieving top 5 by relevance...

Downloading PDFs...

[1/5] Silkworms transformed with chimeric silkworm/spider silk genes...
        Year: 2012 | Citations: 267 | Score: 772.1
        ✓ PDF downloaded -> 2012_Florence_Teulé_Silkworms_transformed.pdf

[2/5] Design of Superior Spider Silk: From Nanostructure to Mechanical...
        Year: 2006 | Citations: 344 | Score: 754.9
        ✓ PDF downloaded -> 2006_Ning_Du_Design_of_Superior_Spider_Silk.pdf

[3/5] Spider Silk Proteins – Mechanical Property and Gene Sequence
        Year: 2005 | Citations: 168 | Score: 671.6
        ✓ PDF downloaded -> 2005_Anna_Rising_Spider_Silk_Proteins.pdf

============================================================
SUMMARY
============================================================
Papers retrieved      : 5
PDFs downloaded       : 4
PDFs already existed  : 0
PDFs unavailable      : 1
Success rate          : 80.0%

Output directory      : /path/to/pdfs
============================================================
```

## Tips for Better Results

1. **Be specific with queries**: "spider silk mechanical properties" is better than just "spider silk"

2. **Use appropriate filters**:
   - Use `--year-min` for recent research
   - Use `--min-citations` for well-established work

3. **Use cloud storage**: Enable `--cloud-storage --parse-pdfs` to automatically parse and store papers in GCS with run metadata

4. **Open access only**: By default, only open access papers are retrieved. This maximizes your PDF download success rate.

5. **Provide your email**: Use `--mailto` with your real email for better API rate limits and to comply with OpenAlex's polite pool

## Troubleshooting

### No papers found
- Try a broader query
- Remove or reduce filters (year, citations)
- Use `--include-closed-access` to expand search

### Low PDF success rate
- Ensure you're using `--open-access-only` (default)
- Some open access papers may have broken links
- Enable cloud storage to track failed PDFs for debugging

### Rate limiting
- The script includes automatic retry logic
- Default sleep time is 0.1s (well within OpenAlex's 10 req/sec limit)
- Increase `--sleep` if you encounter issues

## Comparison with Old System

| Old (`pdf_downloader.py`) | New (`article_retriever.py`) |
|---------------------------|------------------------------|
| Requires manual CSV input | Query-based search |
| Two-step process | Single command |
| Unpaywall only | Multi-source cascade (SS → OpenAlex → Unpaywall) |
| No filtering | Year, citations, OA filters |
| No relevance ranking | Sorted by relevance score |
| Static paper list | Dynamic search results |

## API Information

- **OpenAlex API**: https://docs.openalex.org/
  - Free, no API key required
  - Rate limit: 10 requests/second (100,000/day)
  - Polite pool (with email): 10 req/sec, no daily limit
  - Used for: Paper search and initial PDF URLs

- **Semantic Scholar API**: https://api.semanticscholar.org/
  - Free, API key optional but recommended
  - Rate limit (without key): ~100 requests/5 minutes
  - Rate limit (with key): Up to 100 requests/second
  - Get API key: https://www.semanticscholar.org/product/api
  - Used for: Primary PDF source with circuit breaker on rate limits
  - API key configured via `.env` file (see Installation section)

- **Unpaywall API**: https://unpaywall.org/api
  - Free, requires email
  - Used for: Final fallback PDF acquisition

## License

This tool is for academic research purposes. Please respect publishers' copyright and only download papers you have legitimate access to.
