#!/usr/bin/env python3
"""
Unpaywall PDF Downloader
------------------------
Given a CSV listing papers (e.g., an OpenAlex export), fetch Unpaywall records
for each DOI and download the best available Open Access PDF (if any).

The script is robust to common CSV variants and tries to be polite to APIs.

Usage
-----
pip install requests pandas

python unpaywall_pdf_downloader.py \
  --csv works-2025-09-12T06-12-48.csv \
  --mailto "you@northwestern.edu" \
  --outdir ./pdfs \
  --doi-column doi \
  --title-column title \
  --year-column publication_year \
  --sleep 0.25

Notes
-----
* Unpaywall requires a contact email. Pass it via --mailto.
* Only DOIs can be queried. Rows without a DOI will be skipped.
* Filenames are constructed from Year_Title[_DOIhash].pdf to avoid collisions.
* A manifest CSV is saved with per-row status and the chosen PDF URL.
"""

import argparse
import csv
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

try:
    import pandas as pd
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except Exception as e:
    print("This script needs 'pandas' and 'requests'. Install with:\n  pip install pandas requests", file=sys.stderr)
    raise

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
USER_AGENT = "Unpaywall-PDF-Downloader/1.0 (+python script; contact via mailto)"
DEFAULT_SLEEP = 0.25

def slugify(text: str, max_len: int = 80) -> str:
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = text.replace(" ", "_")
    text = re.sub("_+", "_", text)
    return (text or "untitled")[:max_len]

def norm_doi(doi: Optional[str]) -> Optional[str]:
    if not doi or not isinstance(doi, str):
        return None
    d = doi.strip()
    # Strip URL prefix if present
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.IGNORECASE)
    # Lowercase and strip trailing punctuation
    d = d.strip().strip(" .;")
    return d or None

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=32)
    s.headers.update({"User-Agent": USER_AGENT})
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

@dataclass
class RowResult:
    index: int
    doi: Optional[str]
    title: str
    year: Optional[str]
    best_pdf_url: Optional[str]
    status: str
    saved_path: Optional[str]
    http_status: Optional[int]

def pick_best_pdf_location(upa: Dict) -> Optional[str]:
    """
    From an Unpaywall JSON record, choose a direct PDF URL if available.
    Preference order: best_oa_location.url_for_pdf -> any oa_locations.url_for_pdf -> best_oa_location.url (if .pdf)
    """
    best = upa.get("best_oa_location") or {}
    url_for_pdf = best.get("url_for_pdf")
    url = best.get("url")
    if url_for_pdf:
        return url_for_pdf
    if url and url.lower().endswith(".pdf"):
        return url
    for loc in upa.get("oa_locations", []) or []:
        if loc.get("url_for_pdf"):
            return loc["url_for_pdf"]
        u = loc.get("url")
        if u and u.lower().endswith(".pdf"):
            return u
    return None

def save_pdf(session: requests.Session, pdf_url: str, path: str) -> bool:
    try:
        with session.get(pdf_url, stream=True, timeout=45, headers={"Accept": "application/pdf,*/*"}) as r:
            if r.status_code != 200:
                return False
            # write stream
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 18):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser(description="Download PDFs via Unpaywall using a CSV of works (needs DOI column).")
    ap.add_argument("--csv", required=True, help="Input CSV containing a DOI column.")
    ap.add_argument("--mailto", default="gourav.kumbhojkar@gmail.com", help="Your contact email (Unpaywall requires this).")
    ap.add_argument("--outdir", default="../", help="Directory to save PDFs and manifest.")
    ap.add_argument("--doi-column", default="doi", help="Name of the DOI column (default: doi).")
    ap.add_argument("--title-column", default="title", help="Optional title column for nicer filenames.")
    ap.add_argument("--year-column", default="publication_year", help="Optional year column.")
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Seconds to sleep between Unpaywall requests.")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    manifest_path = os.path.join(args.outdir, "manifest.csv")

    # Load CSV with pandas to be tolerant of encodings and weird delimiters.
    try:
        df = pd.read_csv(args.csv)
    except Exception:
        df = pd.read_csv(args.csv, sep=";")
    cols_lower = {c.lower(): c for c in df.columns}

    # Resolve column names (case-insensitive)
    doi_col = cols_lower.get(args.doi_column.lower())
    title_col = cols_lower.get(args.title_column.lower()) if args.title_column else None
    year_col = cols_lower.get(args.year_column.lower()) if args.year_column else None

    # Try common fallbacks if DOI column wasn't found
    if doi_col is None:
        for cand in ["doi", "DOI", "paper_doi", "work_doi"]:
            if cand in df.columns:
                doi_col = cand
                break
    if doi_col is None:
        print("ERROR: Could not locate a DOI column. Use --doi-column to specify.", file=sys.stderr)
        sys.exit(2)

    session = make_session()

    results: List[RowResult] = []
    total = len(df)
    print(f"Found {total} rows. Starting Unpaywall lookups...")

    for idx, row in df.iterrows():
        raw_doi = row.get(doi_col)
        doi = norm_doi(str(raw_doi) if not pd.isna(raw_doi) else None)
        title = ""
        if title_col and title_col in row and not pd.isna(row.get(title_col)):
            title = str(row.get(title_col))
        elif "display_name" in df.columns and not pd.isna(row.get("display_name")):
            title = str(row.get("display_name"))
        year = None
        if year_col and year_col in row and not pd.isna(row.get(year_col)):
            year = str(row.get(year_col))

        if not doi:
            results.append(RowResult(index=idx, doi=None, title=title, year=year,
                                     best_pdf_url=None, status="no-doi", saved_path=None, http_status=None))
            print(f"[{idx+1}/{total}] Skipping (no DOI). Title: {title[:60]}")
            continue

        upa_url = f"{UNPAYWALL_BASE}/{doi}"
        try:
            r = session.get(upa_url, params={"email": args.mailto}, timeout=30)
            status_code = r.status_code
            if status_code == 404:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=None, status="not-found", saved_path=None, http_status=404))
                print(f"[{idx+1}/{total}] 404 Not Found for DOI {doi}")
                time.sleep(args.sleep)
                continue
            if status_code != 200:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=None, status=f"http-{status_code}", saved_path=None, http_status=status_code))
                print(f"[{idx+1}/{total}] HTTP {status_code} for DOI {doi}")
                time.sleep(args.sleep)
                continue

            upa = r.json()
            pdf_url = pick_best_pdf_location(upa)

            if not pdf_url:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=None, status="no-pdf-url", saved_path=None, http_status=200))
                print(f"[{idx+1}/{total}] No PDF URL in Unpaywall. DOI {doi}")
                time.sleep(args.sleep)
                continue

            # Build filename
            y = (year or "NA")
            base = f"{y}_{slugify(title)}"
            # add DOI hash to avoid collisions for same title/year
            doi_hash = hashlib.md5(doi.encode("utf-8")).hexdigest()[:8]
            fname = f"{base}_{doi_hash}.pdf"
            dest = os.path.join(args.outdir, fname)

            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=pdf_url, status="exists", saved_path=dest, http_status=200))
                print(f"[{idx+1}/{total}] Exists: {fname}")
                time.sleep(args.sleep)
                continue

            ok = save_pdf(session, pdf_url, dest)
            if ok:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=pdf_url, status="downloaded", saved_path=dest, http_status=200))
                print(f"[{idx+1}/{total}] ✓ Downloaded -> {fname}")
            else:
                results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                         best_pdf_url=pdf_url, status="download-failed", saved_path=None, http_status=200))
                print(f"[{idx+1}/{total}] ✗ Failed to download PDF for DOI {doi}")

            time.sleep(args.sleep)

        except Exception as e:
            results.append(RowResult(index=idx, doi=doi, title=title, year=year,
                                     best_pdf_url=None, status=f"error:{e}", saved_path=None, http_status=None))
            print(f"[{idx+1}/{total}] ERROR for DOI {doi}: {e}")
            time.sleep(args.sleep)

    # Write manifest
    manifest_rows = [asdict(r) for r in results]
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()) if manifest_rows else
                                ["index","doi","title","year","best_pdf_url","status","saved_path","http_status"])
        writer.writeheader()
        for r in manifest_rows:
            writer.writerow(r)

    # Summary
    downloaded = sum(1 for r in results if r.status == "downloaded")
    exists = sum(1 for r in results if r.status == "exists")
    no_doi = sum(1 for r in results if r.status == "no-doi")
    no_pdf = sum(1 for r in results if r.status == "no-pdf-url")
    failed = sum(1 for r in results if r.status == "download-failed")
    not_found = sum(1 for r in results if r.status == "not-found")
    print("\nSummary")
    print("-------")
    print(f"Total rows      : {total}")
    print(f"Downloaded new  : {downloaded}")
    print(f"Already existed : {exists}")
    print(f"No DOI          : {no_doi}")
    print(f"No PDF in UPW   : {no_pdf}")
    print(f"404 Not Found   : {not_found}")
    print(f"Download failed : {failed}")
    print(f"\nManifest saved  : {manifest_path}")
    print(f"PDFs directory  : {os.path.abspath(args.outdir)}")

if __name__ == "__main__":
    main()
