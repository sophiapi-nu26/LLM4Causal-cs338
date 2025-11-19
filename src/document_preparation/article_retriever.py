#!/usr/bin/env python3
"""
Article Retriever with Multi-Source PDF Download
-------------------------------------------------
Query-based article retrieval system that searches OpenAlex for relevant papers
and automatically downloads available open access PDFs from multiple sources.

Usage
-----
pip install requests

# Basic usage
python article_retriever.py --query "spider silk mechanical properties"

# Advanced usage with filters
python article_retriever.py \
  --query "spider silk tensile strength" \
  --max-results 20 \
  --year-min 2015 \
  --min-citations 10 \
  --outdir ./my_papers \
  --mailto "you@email.com"

Features
--------
* Query-based search using OpenAlex API (no API key needed)
* Automatic relevance ranking
* Multi-source PDF download with intelligent cascading:
  - Semantic Scholar (primary, with rate limit handling)
  - OpenAlex
  - Unpaywall (fallback)
* PDF parsing (v2) with multi-column support
* Cloud storage integration (Google Cloud Storage)
* Timestamp-based run grouping with metadata tracking
* Filtering by year, citations, and open access status (default: open access only)
* Optional local PDF storage with --save-pdfs-locally flag
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import quote

# Configure module logger
logger = logging.getLogger(__name__)

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    # Can't use logger here since logging may not be configured yet
    print("This script needs 'requests'. Install with:\n  pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if present
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# API Configuration
OPENALEX_BASE = "https://api.openalex.org"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
USER_AGENT = "ArticleRetriever/1.0 (mailto:{})"
DEFAULT_SLEEP = 0.1  # OpenAlex allows 10 req/sec, so 0.1s is safe
DEFAULT_MAX_RESULTS = 20
DEFAULT_MAILTO = "user@gmail.com"  # Avoid .edu email addresses

# Rate limiting configuration for Semantic Scholar
SS_RATE_LIMIT_THRESHOLD = 3  # Number of consecutive 429s before circuit break
SS_CIRCUIT_BREAK_DURATION = 300  # Seconds to wait after circuit break (5 minutes)

# Performance monitoring toggle
ENABLE_TIMERS = os.getenv("ENABLE_PERFORMANCE_LOGGING", "false").lower() == "true"

# Performance Timing Utilities
class Timer:
    """Context manager for timing code blocks and logging performance.

    Controlled by ENABLE_PERFORMANCE_LOGGING environment variable.
    Set to "true" to enable timing logs, "false" to disable.
    """

    def __init__(self, operation_name: str, paper_index: Optional[int] = None, log_level: int = logging.DEBUG):
        self.operation_name = operation_name
        self.paper_index = paper_index
        self.log_level = log_level
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Skip timing if disabled
        if not ENABLE_TIMERS:
            return

        self.elapsed = time.time() - self.start_time

        # Build log message
        if self.paper_index is not None:
            prefix = f"[Paper {self.paper_index}]"
        else:
            prefix = ""

        msg = f"{prefix} TIMER {self.operation_name}: {self.elapsed:.2f}s"
        logger.log(self.log_level, msg)


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to filesystem-safe string."""
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = text.replace(" ", "_")
    text = re.sub("_+", "_", text)
    return (text or "untitled")[:max_len]


def norm_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize DOI string."""
    if not doi or not isinstance(doi, str):
        return None
    d = doi.strip()
    # Strip URL prefix if present
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.IGNORECASE)
    d = d.strip().strip(" .;")
    return d or None


def make_session(mailto: str) -> requests.Session:
    """Create a requests session with retry logic."""
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=32)
    s.headers.update({"User-Agent": USER_AGENT.format(mailto)})
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


@dataclass
class Paper:
    """Represents a paper with metadata and cloud storage tracking."""
    index: int
    openalex_id: str
    doi: Optional[str]
    title: str
    year: Optional[int]
    authors: str  # Comma-separated author names
    cited_by_count: int
    relevance_score: float
    abstract: Optional[str]
    pdf_url: Optional[str]
    pdf_source: Optional[str]  # 'openalex', 'unpaywall', 'semantic_scholar', or None
    download_status: str
    saved_path: Optional[str]
    venue: Optional[str]
    open_access_status: Optional[str]
    # Cloud storage tracking
    parsed_data_uri: Optional[str] = None  # gs://bucket/parsed/{id}/extracted.json
    failed_pdf_uri: Optional[str] = None   # gs://bucket/failed_pdfs/{id}.pdf
    parse_status: Optional[str] = None     # 'success', 'failed', or None

class SemanticScholarSearcher:
    """Handles Semantic Scholar API interactions for PDF retrieval."""

    def __init__(self, session: requests.Session, api_key: Optional[str] = None):
        self.session = session
        self.api_key = api_key
        self.consecutive_429s = 0
        self.circuit_broken = False
        self.circuit_break_time = None

        # Configure session with API key if available
        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})

    def is_circuit_broken(self) -> bool:
        """Check if circuit breaker is active."""
        if not self.circuit_broken:
            return False

        # Check if enough time has passed to retry
        if time.time() - self.circuit_break_time > SS_CIRCUIT_BREAK_DURATION:
            self.circuit_broken = False
            self.consecutive_429s = 0
            return False

        return True

    def get_pdf_url(self, doi: Optional[str]) -> Optional[str]:
        """
        Get PDF URL from Semantic Scholar using DOI lookup.

        Returns:
            PDF URL if available and open access, None otherwise
        """
        if not doi or self.is_circuit_broken():
            return None

        # Use DOI lookup endpoint
        url = f"{SEMANTIC_SCHOLAR_BASE}/paper/DOI:{doi}"
        params = {
            "fields": "isOpenAccess,openAccessPdf"
        }

        try:
            with Timer("Semantic Scholar API lookup"):
                response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 429:
                self.consecutive_429s += 1
                if self.consecutive_429s >= SS_RATE_LIMIT_THRESHOLD:
                    self.circuit_broken = True
                    self.circuit_break_time = time.time()
                    logger.warning("Semantic Scholar rate limit hit - switching to fallback sources")
                return None

            if response.status_code == 200:
                # Reset rate limit counter on success
                self.consecutive_429s = 0
                data = response.json()

                # Only return if open access
                if data.get("isOpenAccess"):
                    pdf_info = data.get("openAccessPdf") or {}
                    pdf_url = pdf_info.get("url")
                    return pdf_url

            return None

        except Exception:
            return None


class OpenAlexSearcher:
    """Handles OpenAlex API interactions for paper search."""

    def __init__(self, session: requests.Session, mailto: str):
        self.session = session
        self.mailto = mailto

    def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        min_citations: Optional[int] = None,
        open_access_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search OpenAlex for papers matching the query.

        Returns:
            List of paper metadata dicts from OpenAlex API
        """
        # Build filter string
        filters = []

        if open_access_only:
            filters.append("open_access.is_oa:true")

        if year_min and year_max:
            # Range filter
            filters.append(f"publication_year:{year_min}-{year_max}")
        elif year_min:
            # From year onwards (format: YYYY-)
            filters.append(f"from_publication_date:{year_min}-01-01")
        elif year_max:
            # Up to year (format: -YYYY)
            filters.append(f"to_publication_date:{year_max}-12-31")

        if min_citations is not None:
            filters.append(f"cited_by_count:>{min_citations-1}")

        filter_str = ",".join(filters) if filters else None

        # Build API request
        params = {
            "search": query,
            "per-page": min(max_results, 200),  # OpenAlex max is 200 per page
            "mailto": self.mailto
        }

        if filter_str:
            params["filter"] = filter_str

        # Note: OpenAlex automatically sorts by relevance_score when using search parameter
        # Adding explicit sort can cause issues with certain filters

        url = f"{OPENALEX_BASE}/works"

        logger.info(f"Searching OpenAlex for: \"{query}\"")
        if filter_str:
            logger.info(f"Filters: {filter_str.replace(',', ', ')}")

        try:
            with Timer("OpenAlex API search", log_level=logging.INFO):
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

            results = data.get("results", [])
            total_count = data.get("meta", {}).get("count", 0)

            logger.info(f"Found {total_count:,} matching papers")
            logger.info(f"Retrieving top {len(results)} by relevance\n")

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search OpenAlex: {e}")
            return []

    def extract_pdf_url(self, work: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """
        Extract PDF URL from OpenAlex work record.

        Returns:
            (pdf_url, source) tuple where source is 'openalex' or None
        """
        # Try best_oa_location first
        best_loc = work.get("best_oa_location") or {}
        pdf_url = best_loc.get("pdf_url")
        if pdf_url:
            return (pdf_url, "openalex")

        # Try primary_location
        primary_loc = work.get("primary_location") or {}
        pdf_url = primary_loc.get("pdf_url")
        if pdf_url:
            return (pdf_url, "openalex")

        # Try all locations
        for loc in work.get("locations", []):
            pdf_url = loc.get("pdf_url")
            if pdf_url:
                return (pdf_url, "openalex")

        return (None, None)

    def parse_work(self, work: Dict[str, Any], index: int) -> Paper:
        """Parse an OpenAlex work record into a Paper object."""
        # Extract basic metadata
        openalex_id = work.get("id", "").replace("https://openalex.org/", "")
        doi = norm_doi(work.get("doi", ""))
        title = work.get("title") or work.get("display_name") or "Untitled"
        year = work.get("publication_year")
        cited_by_count = work.get("cited_by_count", 0)
        relevance_score = work.get("relevance_score", 0.0)

        # Extract authors
        authorships = work.get("authorships", [])
        authors = ", ".join([
            auth.get("author", {}).get("display_name", "Unknown")
            for auth in authorships[:5]  # Limit to first 5 authors
        ])
        if len(authorships) > 5:
            authors += ", et al."

        # Extract abstract (may be inverted index format)
        abstract_inverted = work.get("abstract_inverted_index")
        abstract = None
        if abstract_inverted:
            # Reconstruct abstract from inverted index
            word_positions = []
            for word, positions in abstract_inverted.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join([word for _, word in word_positions])
            # Truncate if too long
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."

        # Extract venue
        venue = None
        primary_loc = work.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        venue = source.get("display_name")

        # Extract open access status
        oa_info = work.get("open_access") or {}
        oa_status = oa_info.get("oa_status")

        # Extract PDF URL
        pdf_url, pdf_source = self.extract_pdf_url(work)

        return Paper(
            index=index,
            openalex_id=openalex_id,
            doi=doi,
            title=title,
            year=year,
            authors=authors,
            cited_by_count=cited_by_count,
            relevance_score=relevance_score,
            abstract=abstract,
            pdf_url=pdf_url,
            pdf_source=pdf_source,
            download_status="pending",
            saved_path=None,
            venue=venue,
            open_access_status=oa_status
        )


class PDFDownloader:
    """Handles PDF downloading from multiple sources with cascade fallback.

    Optionally supports parsing PDFs and uploading to cloud storage.
    """

    def __init__(self, session: requests.Session, mailto: str, outdir: str = None,
                 semantic_scholar: Optional[SemanticScholarSearcher] = None,
                 parser=None, gcp_connector=None, run_id: str = None,
                 save_pdfs_locally: bool = False):
        """
        Initialize PDF downloader.

        Args:
            session: Requests session for downloads
            mailto: Email for API requests
            outdir: Local directory for PDFs (optional if using cloud storage)
            semantic_scholar: Optional Semantic Scholar searcher
            parser: Optional parser adapter (e.g., PDFParserAdapter)
            gcp_connector: Optional GCP storage connector
            run_id: Optional run identifier for grouping cloud uploads
            save_pdfs_locally: Whether to save PDFs to local filesystem (default: False)
        """
        self.session = session
        self.mailto = mailto
        self.outdir = outdir
        self.semantic_scholar = semantic_scholar
        self.run_id = run_id
        self.parser = parser
        self.gcp_connector = gcp_connector
        self.save_pdfs_locally = save_pdfs_locally

        # Only create outdir if we're saving PDFs locally
        if outdir and save_pdfs_locally:
            os.makedirs(outdir, exist_ok=True)

    def create_filename(self, paper: Paper) -> str:
        """Generate a filesystem-safe filename for the paper."""
        year = str(paper.year) if paper.year else "NA"

        # Get first author last name if possible
        first_author = paper.authors.split(",")[0].strip() if paper.authors else "Unknown"
        author_slug = slugify(first_author, max_len=20)

        # Get title slug
        title_slug = slugify(paper.title, max_len=40)

        # Add hash to avoid collisions
        hash_input = f"{paper.openalex_id}{paper.doi or paper.title}"
        hash_str = hashlib.md5(hash_input.encode("utf-8")).hexdigest()[:6]

        filename = f"{year}_{author_slug}_{title_slug}_{hash_str}.pdf"
        return filename

    def download_pdf_bytes(self, pdf_url: str) -> Optional[bytes]:
        """Download PDF to memory and return bytes (for cloud-only workflow)."""
        try:
            response = self.session.get(
                pdf_url,
                timeout=60,
                headers={"Accept": "application/pdf,*/*"}
            )

            if response.status_code != 200:
                return None

            pdf_bytes = response.content

            # Verify we got content
            if len(pdf_bytes) > 0:
                return pdf_bytes
            else:
                return None

        except Exception as e:
            return None

    def save_pdf(self, pdf_url: str, filepath: str) -> bool:
        """Download and save a PDF from a URL, for testing - local save"""
        try:
            with self.session.get(
                pdf_url,
                stream=True,
                timeout=60,
                headers={"Accept": "application/pdf,*/*"}
            ) as response:
                if response.status_code != 200:
                    return False

                # Write in chunks
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=262144):  # 256KB chunks
                        if chunk:
                            f.write(chunk)

                # Verify file was written and has content
                if os.path.getsize(filepath) > 0:
                    return True
                else:
                    os.remove(filepath)
                    return False

        except Exception as e:
            # Clean up partial download
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return False

    def try_unpaywall(self, doi: str) -> Optional[str]:
        """Try to get PDF URL from Unpaywall API."""
        if not doi:
            return None

        url = f"{UNPAYWALL_BASE}/{doi}"
        params = {"email": self.mailto}

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()

                # Try best_oa_location first
                best = data.get("best_oa_location") or {}
                pdf_url = best.get("url_for_pdf")
                if pdf_url:
                    return pdf_url

                # Try any oa_locations
                for loc in data.get("oa_locations", []) or []:
                    pdf_url = loc.get("url_for_pdf")
                    if pdf_url:
                        return pdf_url
        except:
            pass

        return None

    def download(self, paper: Paper) -> Paper:
        """
        Attempt to download PDF for a paper using cascade approach:
        1. Semantic Scholar (if available and not rate-limited)
        2. OpenAlex (from search results)
        3. Unpaywall (fallback)

        Updates paper object with download status and path.
        Note: Requires outdir to be set (for local PDF storage).
        """
        if not self.outdir:
            logger.error("download() requires outdir to be set")
            paper.download_status = "no-pdf-available"
            return paper

        filename = self.create_filename(paper)
        filepath = os.path.join(self.outdir, filename)

        # Check if already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            paper.download_status = "exists"
            paper.saved_path = filepath
            return paper

        # Source 1: Try Semantic Scholar first (if enabled)
        if self.semantic_scholar and paper.doi:
            logger.debug(f"Trying Semantic Scholar for DOI: {paper.doi}")
            ss_url = self.semantic_scholar.get_pdf_url(paper.doi)
            if ss_url:
                logger.debug(f"✓ Found PDF via Semantic Scholar")
                if self.save_pdf(ss_url, filepath):
                    paper.download_status = "downloaded"
                    paper.saved_path = filepath
                    paper.pdf_url = ss_url
                    paper.pdf_source = "semantic_scholar"
                    return paper

        # Source 2: Try OpenAlex URL from search results
        if paper.pdf_url:
            logger.debug(f"Trying OpenAlex URL from search results")
            if self.save_pdf(paper.pdf_url, filepath):
                logger.debug(f"✓ Downloaded via OpenAlex")
                paper.download_status = "downloaded"
                paper.saved_path = filepath
                # pdf_source already set during parsing
                return paper

        # Source 3: Try Unpaywall as final fallback
        if paper.doi:
            logger.debug(f"Trying Unpaywall for DOI: {paper.doi}")
            unpaywall_url = self.try_unpaywall(paper.doi)
            if unpaywall_url:
                logger.debug(f"✓ Found PDF via Unpaywall")
                if self.save_pdf(unpaywall_url, filepath):
                    paper.download_status = "downloaded"
                    paper.saved_path = filepath
                    paper.pdf_url = unpaywall_url
                    paper.pdf_source = "unpaywall"
                    return paper

        # No PDF available from any source
        logger.debug("✗ No PDF available from any source")
        paper.download_status = "no-pdf-available"
        return paper

    def download_parse_and_upload(self, paper: Paper) -> Paper:
        """
        Download PDF to memory, parse it, and upload parsed data to cloud.

        Cloud-native streaming workflow:
        1. Find PDF URL (Semantic Scholar → OpenAlex → Unpaywall)
        2. Download PDF bytes to memory (no local file)
        3. Parse PDF from bytes
        4. Upload parsed JSON to cloud
        5. If parse fails → upload failed PDF to cloud for debugging

        No local PDF storage - everything streams through memory.

        Args:
            paper: Paper object to process

        Returns:
            Updated Paper object with parse_status and cloud URIs
        """
        if not self.parser:
            # No parser configured, fall back to regular download
            return self.download(paper)

        # Create paper ID from OpenAlex ID
        paper_id = paper.openalex_id.replace("https://openalex.org/", "")

        # Step 1: Find PDF URL (cascade through sources)
        pdf_url = None
        pdf_source = None

        # Try Semantic Scholar first
        if self.semantic_scholar and paper.doi:
            logger.debug(f"Trying Semantic Scholar for DOI: {paper.doi}")
            pdf_url = self.semantic_scholar.get_pdf_url(paper.doi)
            if pdf_url:
                pdf_source = "semantic_scholar"
                logger.debug(f"✓ Found PDF via Semantic Scholar")

        # Try OpenAlex URL from search results
        if not pdf_url and paper.pdf_url:
            logger.debug(f"Trying OpenAlex URL from search results")
            pdf_url = paper.pdf_url
            pdf_source = paper.pdf_source  # Already set during parsing
            logger.debug(f"✓ Using OpenAlex PDF URL")

        # Try Unpaywall as final fallback
        if not pdf_url and paper.doi:
            logger.debug(f"Trying Unpaywall for DOI: {paper.doi}")
            pdf_url = self.try_unpaywall(paper.doi)
            if pdf_url:
                pdf_source = "unpaywall"
                logger.debug(f"✓ Found PDF via Unpaywall")

        if not pdf_url:
            logger.debug("✗ No PDF URL found from any source")
            paper.download_status = "no-pdf-available"
            return paper

        # Step 2: Download PDF to memory
        logger.info(f"Downloading and parsing {paper.title[:50]}...")
        with Timer(f"PDF download from {pdf_source}", paper_index=paper.index, log_level=logging.INFO):
            pdf_bytes = self.download_pdf_bytes(pdf_url)

        if not pdf_bytes:
            paper.download_status = "download-failed"
            return paper

        paper.download_status = "downloaded"
        paper.pdf_url = pdf_url
        paper.pdf_source = pdf_source

        # Optionally save PDF to local filesystem
        if self.save_pdfs_locally and self.outdir:
            try:
                filename = self.create_filename(paper)
                filepath = os.path.join(self.outdir, filename)
                with open(filepath, 'wb') as f:
                    f.write(pdf_bytes)
                paper.saved_path = filepath
                logger.debug(f"Saved PDF locally: {filename}")
            except Exception as e:
                logger.warning(f"Failed to save PDF locally: {e}")

        # Step 3: Parse PDF from bytes
        try:
            with Timer("PDF parsing", paper_index=paper.index, log_level=logging.INFO):
                parsed_data = self.parser.parse(pdf_bytes, paper_id=paper_id)

            # Step 4: Upload parsed data to cloud
            if self.gcp_connector:
                try:
                    with Timer("GCS upload (parsed data)", paper_index=paper.index, log_level=logging.INFO):
                        uri = self.gcp_connector.upload_parsed_data(parsed_data, paper_id, self.run_id)
                    paper.parsed_data_uri = uri
                    paper.parse_status = "success"
                    logger.info("Parsed and uploaded to cloud")
                except Exception as e:
                    logger.error(f"Cloud upload failed: {e}")
                    paper.parse_status = "upload_failed"
            else:
                # Parser succeeded but no cloud storage
                paper.parse_status = "success"
                logger.info("Parsed successfully (no cloud upload)")

        except Exception as e:
            # Parsing failed
            logger.error(f"Parsing failed: {e}")
            paper.parse_status = "failed"

            # Upload failed PDF to cloud for debugging
            if self.gcp_connector:
                try:
                    uri = self.gcp_connector.upload_failed_pdf(
                        pdf_bytes,
                        paper_id,
                        error_msg=str(e)
                    )
                    paper.failed_pdf_uri = uri
                    logger.info("Uploaded failed PDF to cloud for debugging")
                except Exception as upload_err:
                    logger.warning(f"Failed to upload failed PDF: {upload_err}")

        return paper


class ResultsManager:
    """Handles generating summary reports."""

    @staticmethod
    def print_summary(papers: List[Paper], outdir: str = None):
        """Print summary statistics."""
        downloaded = sum(1 for p in papers if p.download_status == "downloaded")
        exists = sum(1 for p in papers if p.download_status == "exists")
        no_pdf = sum(1 for p in papers if p.download_status == "no-pdf-available")

        # Count by source
        ss_count = sum(1 for p in papers if p.pdf_source == "semantic_scholar")
        oa_count = sum(1 for p in papers if p.pdf_source == "openalex")
        up_count = sum(1 for p in papers if p.pdf_source == "unpaywall")

        total_with_pdf = downloaded + exists

        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Papers retrieved      : {len(papers)}")
        logger.info(f"PDFs downloaded       : {downloaded}")
        logger.info(f"PDFs already existed  : {exists}")
        logger.info(f"PDFs unavailable      : {no_pdf}")
        if papers:
            success_rate = (total_with_pdf / len(papers)) * 100
            logger.info(f"Success rate          : {success_rate:.1f}%")

        # Show source breakdown if any PDFs were obtained
        if total_with_pdf > 0:
            logger.info(f"\nPDF Sources:")
            if ss_count > 0:
                logger.info(f"  Semantic Scholar    : {ss_count}")
            if oa_count > 0:
                logger.info(f"  OpenAlex            : {oa_count}")
            if up_count > 0:
                logger.info(f"  Unpaywall           : {up_count}")

        if outdir:
            logger.info(f"\nOutput directory      : {os.path.abspath(outdir)}")
        logger.info("=" * 60)

def _create_components(mailto: str, ss_api_key: Optional[str] = None,
                       outdir: Optional[str] = None, save_pdfs_locally: bool = False,
                       run_id: Optional[str] = None, parse_pdfs: bool = True,
                       use_cloud_storage: bool = False):
    """
    Create and initialize all components needed for article retrieval.

    Args:
        mailto: Email for API requests
        ss_api_key: Optional Semantic Scholar API key
        outdir: Optional local directory for PDFs
        save_pdfs_locally: Whether to save PDFs to local filesystem
        run_id: Run identifier for grouping cloud uploads
        parse_pdfs: Whether to enable PDF parsing
        use_cloud_storage: Whether to upload to cloud storage

    Returns:
        Tuple of (session, searcher, downloader, parser, gcp_connector)
    """
    # Initialize session and searcher
    session = make_session(mailto)
    searcher = OpenAlexSearcher(session, mailto)
    semantic_scholar = SemanticScholarSearcher(session, api_key=ss_api_key)

    # Initialize parser if requested
    pdf_parser = None
    if parse_pdfs:
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from parser_adapter import PDFParserAdapter
            pdf_parser = PDFParserAdapter()
            logger.debug("PDF parser initialized")
        except ImportError as e:
            logger.warning(f"Failed to import parser: {e}")

    # Initialize cloud storage if requested
    gcp_connector = None
    if use_cloud_storage:
        try:
            from gcp_connector import GCPBucketConnector
            gcp_connector = GCPBucketConnector()
            logger.debug(f"Cloud storage initialized (bucket: {gcp_connector.bucket_name})")
        except Exception as e:
            logger.warning(f"Failed to initialize cloud storage: {e}")

    # Initialize downloader
    downloader = PDFDownloader(
        session,
        mailto,
        outdir,
        semantic_scholar,
        parser=pdf_parser,
        gcp_connector=gcp_connector,
        run_id=run_id,
        save_pdfs_locally=save_pdfs_locally
    )

    return session, searcher, downloader, pdf_parser, gcp_connector


def _search_papers(searcher: OpenAlexSearcher, query: str, max_results: int = DEFAULT_MAX_RESULTS,
                   year_min: Optional[int] = None, year_max: Optional[int] = None,
                   min_citations: Optional[int] = None, include_closed_access: bool = False) -> List[Paper]:
    """
    Search OpenAlex and return Paper objects.

    Args:
        searcher: OpenAlexSearcher instance
        query: Search query string
        max_results: Maximum number of papers to retrieve
        year_min: Minimum publication year filter
        year_max: Maximum publication year filter
        min_citations: Minimum citation count filter
        include_closed_access: Whether to include closed access papers

    Returns:
        List of Paper objects
    """
    open_access_only = not include_closed_access

    works = searcher.search(
        query=query,
        max_results=max_results,
        year_min=year_min,
        year_max=year_max,
        min_citations=min_citations,
        open_access_only=open_access_only
    )

    if not works:
        logger.warning("No papers found")
        return []

    # Parse works into Paper objects
    papers = [searcher.parse_work(work, i) for i, work in enumerate(works)]
    return papers


def _process_papers(papers: List[Paper], downloader: PDFDownloader, parse_pdfs: bool = True,
                    sleep_time: float = DEFAULT_SLEEP, progress_callback=None) -> List[Paper]:
    """
    Download and optionally parse papers with progress tracking.

    Args:
        papers: List of Paper objects to process
        downloader: PDFDownloader instance
        parse_pdfs: Whether to parse PDFs (vs. just download)
        sleep_time: Seconds to sleep between requests
        progress_callback: Optional callback(current, total, paper_title)

    Returns:
        Updated list of Paper objects
    """
    for i, paper in enumerate(papers, 1):
        # Call progress callback if provided
        if progress_callback:
            progress_callback(i, len(papers), paper.title)

        # Choose download method based on parse_pdfs flag
        if parse_pdfs:
            papers[i-1] = downloader.download_parse_and_upload(paper)
        else:
            papers[i-1] = downloader.download(paper)

        # Rate limiting
        if i < len(papers):
            time.sleep(sleep_time)

    return papers


def _upload_run_metadata(papers: List[Paper], gcp_connector, run_id: str, query: str,
                         year_min: Optional[int] = None, year_max: Optional[int] = None,
                         min_citations: Optional[int] = None, include_closed_access: bool = False):
    """
    Upload run metadata to cloud storage.

    Args:
        papers: List of processed Paper objects
        gcp_connector: GCPBucketConnector instance
        run_id: Run identifier
        query: Original search query
        year_min: Minimum year filter used
        year_max: Maximum year filter used
        min_citations: Minimum citations filter used
        include_closed_access: Whether closed access was included
    """
    if not gcp_connector:
        return

    try:
        from datetime import datetime, UTC

        # Calculate statistics
        parsed_count = sum(1 for p in papers if p.parse_status == "success")
        failed_count = sum(1 for p in papers if p.parse_status == "failed")
        downloaded_count = sum(1 for p in papers if p.download_status in ["downloaded", "exists"])

        # Build metadata dictionary
        run_metadata = {
            "query": query,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "run_id": run_id,
            "filters": {
                "year_min": year_min,
                "year_max": year_max,
                "min_citations": min_citations,
                "include_closed_access": include_closed_access
            },
            "results": {
                "papers_retrieved": len(papers),
                "pdfs_downloaded": downloaded_count,
                "papers_parsed": parsed_count,
                "papers_failed": failed_count
            }
        }

        # Upload metadata
        gcp_connector.upload_run_metadata(run_id, run_metadata)
        logger.info(f"Run metadata uploaded (run_id: {run_id})")
    except Exception as e:
        logger.warning(f"Failed to upload run metadata: {e}")


def run_retrieval(query: str, max_results: int = 20, year_min: Optional[int] = None,
                  parse_pdfs: bool = True, progress_callback=None) -> dict:
    """
    API-friendly entry point for article retrieval.

    Downloads papers, parses them, uploads to cloud storage, and returns full parsed data.

    Args:
        query: Search query string
        max_results: Maximum number of papers to retrieve (default: 20)
        year_min: Optional minimum publication year filter
        parse_pdfs: Whether to parse PDFs and upload to cloud (default: True)
        progress_callback: Optional callback(current, total, paper_title) for progress updates

    Returns:
        Dictionary with:
        {
            "papers": [...],  # List of paper dicts with full parsed JSON data
            "summary": {...},  # Statistics summary
            "run_metadata": {...},  # Query and filter info
            "gcs_path": "parsed/run_XXX/"  # GCS location
        }
    """
    from datetime import datetime, UTC

    # Generate run ID
    run_id = datetime.now(UTC).strftime("run_%Y-%m-%d_%H%M%S")

    # Get Semantic Scholar API key from environment
    ss_api_key = os.getenv("SEMANTIC_SCHOLAR_KEY")
    mailto = os.getenv("MAILTO", DEFAULT_MAILTO)

    # Create components (cloud-only mode: no local PDFs)
    session, searcher, downloader, pdf_parser, gcp_connector = _create_components(
        mailto=mailto,
        ss_api_key=ss_api_key,
        outdir=None,
        save_pdfs_locally=False,
        run_id=run_id,
        parse_pdfs=parse_pdfs,
        use_cloud_storage=True
    )

    # Search for papers
    papers = _search_papers(
        searcher=searcher,
        query=query,
        max_results=max_results,
        year_min=year_min,
        include_closed_access=False
    )

    if not papers:
        return {
            "papers": [],
            "summary": {"total": 0, "downloaded": 0, "parsed": 0, "failed": 0},
            "run_metadata": {"query": query, "run_id": run_id},
            "gcs_path": f"parsed/{run_id}/"
        }

    # Process papers (download, parse, upload)
    papers = _process_papers(
        papers=papers,
        downloader=downloader,
        parse_pdfs=parse_pdfs,
        sleep_time=DEFAULT_SLEEP,
        progress_callback=progress_callback
    )

    # Upload run metadata
    _upload_run_metadata(
        papers=papers,
        gcp_connector=gcp_connector,
        run_id=run_id,
        query=query,
        year_min=year_min,
        include_closed_access=False
    )

    # Download parsed data from GCS and build response
    paper_results = []
    for paper in papers:
        paper_dict = {
            "paper_id": paper.openalex_id,
            "doi": paper.doi,
            "title": paper.title,
            "year": paper.year,
            "authors": paper.authors,
            "cited_by_count": paper.cited_by_count,
            "relevance_score": paper.relevance_score,
            "abstract": paper.abstract,
            "venue": paper.venue,
            "open_access_status": paper.open_access_status,
            "download_status": paper.download_status,
            "parse_status": paper.parse_status,
            "pdf_source": paper.pdf_source,
            "parsed_data_uri": paper.parsed_data_uri,
            "failed_pdf_uri": paper.failed_pdf_uri,
            "parsed_data": None
        }

        # Download parsed data from GCS if available
        if paper.parse_status == "success" and paper.parsed_data_uri and gcp_connector:
            try:
                paper_id = paper.openalex_id.replace("https://openalex.org/", "")
                parsed_data = gcp_connector.download_parsed_data_from_run(run_id, paper_id)
                paper_dict["parsed_data"] = parsed_data
            except Exception as e:
                logger.warning(f"Failed to download parsed data for {paper_id}: {e}")

        paper_results.append(paper_dict)

    # Calculate summary statistics
    summary = {
        "total": len(papers),
        "downloaded": sum(1 for p in papers if p.download_status in ["downloaded", "exists"]),
        "parsed": sum(1 for p in papers if p.parse_status == "success"),
        "failed": sum(1 for p in papers if p.parse_status == "failed"),
        "no_pdf": sum(1 for p in papers if p.download_status == "no-pdf-available")
    }

    return {
        "papers": paper_results,
        "summary": summary,
        "run_metadata": {
            "query": query,
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "filters": {
                "year_min": year_min,
                "max_results": max_results
            }
        },
        "gcs_path": f"parsed/{run_id}/"
    }

def main():
    parser = argparse.ArgumentParser(
        description="Query-based article retrieval with automatic PDF download using OpenAlex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic search
  python article_retriever.py --query "spider silk mechanical properties"

  # Advanced search with filters
  python article_retriever.py \\
    --query "biomaterials tensile strength" \\
    --max-results 30 \\
    --year-min 2018 \\
    --min-citations 10 \\
    --outdir ./papers
        """
    )

    # Required arguments
    parser.add_argument(
        "--query",
        required=True,
        help="Search query (e.g., 'spider silk mechanical properties')"
    )

    # Optional search parameters
    parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum number of papers to retrieve (default: {DEFAULT_MAX_RESULTS})"
    )
    parser.add_argument(
        "--year-min",
        type=int,
        help="Minimum publication year (e.g., 2015)"
    )
    parser.add_argument(
        "--year-max",
        type=int,
        help="Maximum publication year (e.g., 2024)"
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        help="Minimum citation count"
    )
    parser.add_argument(
        "--open-access-only",
        action="store_true",
        default=True,
        help="Only retrieve open access papers (default: True)"
    )
    parser.add_argument(
        "--include-closed-access",
        action="store_true",
        help="Include closed access papers (overrides --open-access-only)"
    )

    # Output options
    parser.add_argument(
        "--outdir",
        default=None,
        help="Directory to save PDFs (optional when using --cloud-storage, default: ./pdfs)"
    )
    parser.add_argument(
        "--mailto",
        default=DEFAULT_MAILTO,
        help=f"Contact email for API requests (default: {DEFAULT_MAILTO})"
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP,
        help=f"Seconds to sleep between requests (default: {DEFAULT_SLEEP})"
    )

    # Advanced options
    parser.add_argument(
        "--save-raw-json",
        action="store_true",
        help="Save raw OpenAlex API response to JSON file"
    )
    parser.add_argument(
        "--parse-pdfs",
        action="store_true",
        help="Parse downloaded PDFs and extract structured text"
    )
    parser.add_argument(
        "--cloud-storage",
        action="store_true",
        help="Upload parsed data to Google Cloud Storage (requires --parse-pdfs and GCP credentials)"
    )
    parser.add_argument(
        "--save-pdfs-locally",
        action="store_true",
        help="Save PDFs locally even when using cloud storage (requires --outdir)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logging based on user's choice
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Validate outdir requirements
    if args.save_pdfs_locally and not args.outdir:
        logger.error("--save-pdfs-locally requires --outdir to be specified")
        sys.exit(1)

    # Set default outdir if needed (backward compatibility for non-cloud mode)
    if not args.cloud_storage and not args.outdir:
        args.outdir = "./pdfs"
        logger.debug("Using default outdir: ./pdfs")

    # Validate that user has enabled at least one storage method when parsing
    if args.parse_pdfs and not args.cloud_storage and not args.save_pdfs_locally:
        logger.warning("Parsing enabled but neither --cloud-storage nor --save-pdfs-locally specified")
        logger.warning("Parsed data will not be saved anywhere!")

    # Generate run ID for cloud storage grouping
    from datetime import datetime, UTC
    run_id = datetime.now(UTC).strftime("run_%Y-%m-%d_%H%M%S")
    logger.debug(f"Generated run_id: {run_id}")

    # Handle open access flag
    open_access_only = args.open_access_only and not args.include_closed_access

    # Load Semantic Scholar API key from environment
    ss_api_key = os.getenv("SEMANTIC_SCHOLAR_KEY")
    if ss_api_key:
        logger.info("Using Semantic Scholar API key for enhanced rate limits\n")

    # Create components using helper function
    session, searcher, downloader, pdf_parser, gcp_connector = _create_components(
        mailto=args.mailto,
        ss_api_key=ss_api_key,
        outdir=args.outdir,
        save_pdfs_locally=args.save_pdfs_locally,
        run_id=run_id,
        parse_pdfs=args.parse_pdfs,
        use_cloud_storage=args.cloud_storage
    )

    # Show status messages based on configuration
    if args.parse_pdfs:
        if pdf_parser:
            logger.info("PDF parser initialized (ScientificPDFExtractor v2)")
        else:
            logger.error("Failed to initialize PDF parser")
            sys.exit(1)

        if args.cloud_storage:
            if gcp_connector:
                logger.info(f"Cloud storage initialized (bucket: {gcp_connector.bucket_name})\n")
            else:
                logger.error("Failed to initialize cloud storage")
                logger.error("Check GCP credentials and .env configuration")
                sys.exit(1)
        else:
            logger.info("Parsed data will NOT be uploaded to cloud\n")

    # Search for papers using helper function
    papers = _search_papers(
        searcher=searcher,
        query=args.query,
        max_results=args.max_results,
        year_min=args.year_min,
        year_max=args.year_max,
        min_citations=args.min_citations,
        include_closed_access=args.include_closed_access
    )

    if not papers:
        logger.info("No papers found. Try adjusting your query or filters.")
        return

    # Save raw JSON if requested (optional feature not in helper functions)
    if args.save_raw_json:
        # Re-fetch works for raw JSON (not stored in Paper objects)
        works = searcher.search(
            query=args.query,
            max_results=args.max_results,
            year_min=args.year_min,
            year_max=args.year_max,
            min_citations=args.min_citations,
            open_access_only=open_access_only
        )
        json_path = os.path.join(args.outdir, "raw_results.json")
        os.makedirs(args.outdir, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(works, f, indent=2)
        logger.info(f"Raw JSON saved: {json_path}\n")

    # Download PDFs with CLI-specific progress display
    if args.parse_pdfs:
        logger.info("Downloading and parsing PDFs...\n")
    else:
        logger.info("Downloading PDFs...\n")

    # Define CLI progress callback
    def cli_progress_display(current, total, paper_title):
        """Display progress for CLI users"""
        paper = papers[current - 1]  # Get current paper
        logger.info(f"[{current}/{total}] {paper.title[:70]}")
        logger.info(f"Year: {paper.year or 'N/A'} | Citations: {paper.cited_by_count} | Score: {paper.relevance_score:.1f}")

    # Process papers using helper function
    papers = _process_papers(
        papers=papers,
        downloader=downloader,
        parse_pdfs=args.parse_pdfs,
        sleep_time=args.sleep,
        progress_callback=cli_progress_display
    )

    # Display results (CLI-specific formatting)
    for i, paper in enumerate(papers, 1):
        # Display download status
        if paper.download_status == "downloaded":
            source_label = f" (via {paper.pdf_source})" if paper.pdf_source else ""
            if paper.saved_path:
                logger.info(f"✓ PDF downloaded{source_label} -> {os.path.basename(paper.saved_path)}")
            else:
                logger.info(f"✓ PDF downloaded{source_label} (streamed to cloud)")
        elif paper.download_status == "exists":
            logger.info(f"✓ PDF already exists -> {os.path.basename(paper.saved_path)}")
        else:
            logger.info(f"✗ No PDF available")

        # Display parse status if applicable
        if args.parse_pdfs and paper.parse_status:
            if paper.parse_status == "success":
                logger.info("Parsed successfully")
                if paper.parsed_data_uri:
                    logger.info("Uploaded to cloud")
            elif paper.parse_status == "failed":
                logger.error("Parsing failed")
                if paper.failed_pdf_uri:
                    logger.info("Failed PDF saved to cloud")

        logger.info("")  # Empty line for readability

    # Upload run metadata using helper function
    if args.cloud_storage and gcp_connector:
        _upload_run_metadata(
            papers=papers,
            gcp_connector=gcp_connector,
            run_id=run_id,
            query=args.query,
            year_min=args.year_min,
            year_max=args.year_max,
            min_citations=args.min_citations,
            include_closed_access=args.include_closed_access
        )

    # Print summary
    ResultsManager.print_summary(papers, args.outdir)


if __name__ == "__main__":
    main()
