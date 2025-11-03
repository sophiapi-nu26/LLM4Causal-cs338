# Article Retrieval System

Query-based article retrieval and PDF download system with intelligent multi-source PDF acquisition.

## Overview

This system allows you to search for academic papers using natural language queries and automatically download available open-access PDFs. It uses the free OpenAlex API for search and intelligently cascades through multiple PDF sources (Semantic Scholar → OpenAlex → Unpaywall) to maximize download success rates.

## Features

- **Query-based search**: Use natural language queries like "spider silk mechanical properties"
- **Automatic relevance ranking**: Results sorted by OpenAlex relevance score
- **Intelligent multi-source PDF download**: Cascades through sources with automatic fallback:
  1. **Semantic Scholar** (primary, with rate limit handling)
  2. **OpenAlex** (from search results)
  3. **Unpaywall** (fallback)
- **Flexible filtering**: Filter by year, citation count, and open access status
- **Open access by default**: Only retrieves papers with free PDFs available
- **Detailed metadata**: Saves comprehensive paper information to CSV manifest
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

## Output Files

### 1. PDFs (`./pdfs/` by default)

Downloaded PDFs are named using the format:
```
{year}_{first_author}_{title_slug}_{hash}.pdf
```

Example:
```
2012_Florence_Teulé_Silkworms_transformed_with_chimeric_silk_616f61.pdf
```

### 2. Manifest CSV (`./pdfs/manifest.csv`)

Contains detailed metadata for all retrieved papers:

| Column | Description |
|--------|-------------|
| `index` | Paper index in result set |
| `openalex_id` | OpenAlex work ID |
| `doi` | Digital Object Identifier |
| `title` | Paper title |
| `year` | Publication year |
| `authors` | Comma-separated author names |
| `cited_by_count` | Number of citations |
| `relevance_score` | OpenAlex relevance score |
| `abstract` | Paper abstract (if available) |
| `pdf_url` | URL where PDF was found |
| `pdf_source` | Source of PDF (`semantic_scholar`, `openalex`, `unpaywall`, or None) |
| `download_status` | Status: `downloaded`, `exists`, or `no-pdf-available` |
| `saved_path` | Local path to downloaded PDF |
| `venue` | Publication venue (journal/conference) |
| `open_access_status` | Open access classification |

### 3. Raw JSON (optional, `--save-raw-json`)

Raw OpenAlex API response saved to `./pdfs/raw_results.json`

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
Manifest saved        : /path/to/pdfs/manifest.csv
============================================================
```

## Tips for Better Results

1. **Be specific with queries**: "spider silk mechanical properties" is better than just "spider silk"

2. **Use appropriate filters**:
   - Use `--year-min` for recent research
   - Use `--min-citations` for well-established work

3. **Check the manifest**: The CSV contains abstracts and metadata to help you identify the most relevant papers

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
- Check the manifest CSV for `pdf_url` column to see if URLs are available

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
