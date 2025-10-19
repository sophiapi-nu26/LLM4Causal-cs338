#!/usr/bin/env python3
"""
OpenAlex Article Retriever
---------------------------
Query-based article retrieval system that searches OpenAlex for relevant papers
and automatically downloads available open access PDFs.

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

# Enable Core.ac.uk for additional coverage (slower)
python article_retriever.py \
  --query "biomaterials" \
  --use-core \
  --mailto "you@email.com"

Features
--------
* Query-based search using OpenAlex API (no API key needed)
* Automatic relevance ranking
* Multi-source PDF download (OpenAlex + Unpaywall + optional Core.ac.uk)
* Filtering by year, citations, and open access status
* Detailed manifest CSV with metadata and download status
* Optional Core.ac.uk integration (--use-core flag, adds latency but may find more PDFs)
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from urllib.parse import quote

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("This script needs 'requests'. Install with:\n  pip install requests", file=sys.stderr)
    sys.exit(1)

# API Configuration
OPENALEX_BASE = "https://api.openalex.org"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
CORE_BASE = "https://api.core.ac.uk/v3/search/works"
USER_AGENT = "OpenAlexArticleRetriever/1.0 (mailto:{})"
DEFAULT_SLEEP = 0.1  # OpenAlex allows 10 req/sec, so 0.1s is safe
DEFAULT_MAX_RESULTS = 20
DEFAULT_MAILTO = "user@gmail.com"  # Avoid .edu email addresses


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
    """Represents a paper with metadata."""
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
    pdf_source: Optional[str]  # 'openalex', 'unpaywall', or None
    download_status: str
    saved_path: Optional[str]
    venue: Optional[str]
    open_access_status: Optional[str]


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

        print(f"Searching OpenAlex for: \"{query}\"")
        if filter_str:
            print(f"   Filters: {filter_str.replace(',', ', ')}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            total_count = data.get("meta", {}).get("count", 0)

            print(f"Found {total_count:,} matching papers")
            print(f"Retrieving top {len(results)} by relevance...\n")

            return results

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to search OpenAlex: {e}", file=sys.stderr)
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
    """Handles PDF downloading from multiple sources."""

    def __init__(self, session: requests.Session, mailto: str, outdir: str, use_core: bool = False):
        self.session = session
        self.mailto = mailto
        self.outdir = outdir
        self.use_core = use_core  # Core.ac.uk is opt-in due to latency
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

    def save_pdf(self, pdf_url: str, filepath: str) -> bool:
        """Download and save a PDF from a URL."""
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

    def try_core(self, doi: str, title: str) -> Optional[str]:
        """Try to get PDF URL from CORE API (DOI search only for speed)."""
        # Only try DOI search (title search is slow and less reliable)
        if not doi:
            return None

        try:
            params = {"q": f"doi:{doi}", "limit": 1}
            # Reduced timeout from 30s to 10s to prevent hanging
            response = self.session.get(CORE_BASE, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results and len(results) > 0:
                    pdf_url = results[0].get("downloadUrl")
                    if pdf_url and pdf_url.strip():
                        return pdf_url
        except:
            # Silently fail on any error (timeout, network, etc.)
            pass

        return None

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
        Attempt to download PDF for a paper.
        Updates paper object with download status and path.
        """
        filename = self.create_filename(paper)
        filepath = os.path.join(self.outdir, filename)

        # Check if already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            paper.download_status = "exists"
            paper.saved_path = filepath
            return paper

        # Try OpenAlex URL first
        if paper.pdf_url:
            if self.save_pdf(paper.pdf_url, filepath):
                paper.download_status = "downloaded"
                paper.saved_path = filepath
                return paper

        # Try CORE if enabled (opt-in due to latency concerns)
        if self.use_core:
            core_url = self.try_core(paper.doi, paper.title)
            if core_url:
                if self.save_pdf(core_url, filepath):
                    paper.download_status = "downloaded"
                    paper.saved_path = filepath
                    paper.pdf_url = core_url
                    paper.pdf_source = "core"
                    return paper

        # Try Unpaywall as fallback
        if paper.doi:
            unpaywall_url = self.try_unpaywall(paper.doi)
            if unpaywall_url:
                if self.save_pdf(unpaywall_url, filepath):
                    paper.download_status = "downloaded"
                    paper.saved_path = filepath
                    paper.pdf_url = unpaywall_url
                    paper.pdf_source = "unpaywall"
                    return paper

        # No PDF available
        paper.download_status = "no-pdf-available"
        return paper


class ResultsManager:
    """Handles saving results and generating reports."""

    @staticmethod
    def save_manifest(papers: List[Paper], outdir: str) -> str:
        """Save paper metadata and download status to CSV."""
        manifest_path = os.path.join(outdir, "manifest.csv")

        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            if papers:
                writer = csv.DictWriter(f, fieldnames=list(asdict(papers[0]).keys()))
                writer.writeheader()
                for paper in papers:
                    writer.writerow(asdict(paper))
            else:
                # Empty file with headers
                writer = csv.DictWriter(f, fieldnames=[
                    "index", "openalex_id", "doi", "title", "year", "authors",
                    "cited_by_count", "relevance_score", "abstract", "pdf_url",
                    "pdf_source", "download_status", "saved_path", "venue",
                    "open_access_status"
                ])
                writer.writeheader()

        return manifest_path

    @staticmethod
    def print_summary(papers: List[Paper], outdir: str, manifest_path: str):
        """Print summary statistics."""
        downloaded = sum(1 for p in papers if p.download_status == "downloaded")
        exists = sum(1 for p in papers if p.download_status == "exists")
        no_pdf = sum(1 for p in papers if p.download_status == "no-pdf-available")

        total_with_pdf = downloaded + exists

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Papers retrieved      : {len(papers)}")
        print(f"PDFs downloaded       : {downloaded}")
        print(f"PDFs already existed  : {exists}")
        print(f"PDFs unavailable      : {no_pdf}")
        if papers:
            success_rate = (total_with_pdf / len(papers)) * 100
            print(f"Success rate          : {success_rate:.1f}%")
        print(f"\nOutput directory      : {os.path.abspath(outdir)}")
        print(f"Manifest saved        : {os.path.abspath(manifest_path)}")
        print("=" * 60)


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
        default="./pdfs",
        help="Directory to save PDFs and manifest (default: ./pdfs)"
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
        "--use-core",
        action="store_true",
        help="Enable CORE.ac.uk as additional PDF source (slower but may find more papers)"
    )

    args = parser.parse_args()

    # Handle open access flag
    open_access_only = args.open_access_only and not args.include_closed_access

    # Initialize components
    session = make_session(args.mailto)
    searcher = OpenAlexSearcher(session, args.mailto)
    downloader = PDFDownloader(session, args.mailto, args.outdir, use_core=args.use_core)

    # Search for papers
    works = searcher.search(
        query=args.query,
        max_results=args.max_results,
        year_min=args.year_min,
        year_max=args.year_max,
        min_citations=args.min_citations,
        open_access_only=open_access_only
    )

    if not works:
        print("No papers found. Try adjusting your query or filters.")
        return

    # Save raw JSON if requested
    if args.save_raw_json:
        json_path = os.path.join(args.outdir, "raw_results.json")
        os.makedirs(args.outdir, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(works, f, indent=2)
        print(f"Raw JSON saved: {json_path}\n")

    # Parse works into Paper objects
    papers = [searcher.parse_work(work, i) for i, work in enumerate(works)]

    # Download PDFs
    print("Downloading PDFs...\n")
    for i, paper in enumerate(papers, 1):
        print(f"[{i}/{len(papers)}] {paper.title[:70]}")
        print(f"        Year: {paper.year or 'N/A'} | Citations: {paper.cited_by_count} | Score: {paper.relevance_score:.1f}")

        paper = downloader.download(paper)

        if paper.download_status == "downloaded":
            print(f"        PDF downloaded -> {os.path.basename(paper.saved_path)}")
        elif paper.download_status == "exists":
            print(f"        PDF already exists -> {os.path.basename(paper.saved_path)}")
        else:
            print(f"        No PDF available")

        print()
        time.sleep(args.sleep)

    # Save manifest
    manifest_path = ResultsManager.save_manifest(papers, args.outdir)

    # Print summary
    ResultsManager.print_summary(papers, args.outdir, manifest_path)


if __name__ == "__main__":
    main()
