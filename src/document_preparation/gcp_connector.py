#!/usr/bin/env python3
"""
GCP Storage Connection Test
----------------------------
Tests connection to Google Cloud Storage and verifies credentials.
"""

from google.cloud import storage
from dotenv import load_dotenv
from typing import Optional
import os
import sys
import logging

# Configure module logger
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def test_gcs_connection():
    """Tests connection to a Google Cloud Storage bucket with detailed debugging."""

    bucket_name = os.getenv("GCP_BUCKET_NAME")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    print(f"Bucket name: {bucket_name}")
    print(f"Credentials path: {creds_path}")

    try:
        client = storage.Client()
        print(f"  Project ID: {client.project}")
    except Exception as e:
        print(f"\n✗ ERROR creating client: {type(e).__name__}")
        sys.exit(1)

    # Access bucket
    try:
        print(f"Attempting to access bucket '{bucket_name}'...")
        bucket = client.get_bucket(bucket_name)

        print(f"  Name: {bucket.name}")
        print(f"  Location: {bucket.location}")
        print(f"  Storage class: {bucket.storage_class}")
        print(f"  Created: {bucket.time_created}")
    except Exception as e:
        print(f"\n✗ ERROR accessing bucket: {type(e).__name__}")
        sys.exit(1)
    
    # fetch files
    try:
        print("Fetching first 5 files...")
        blobs = list(bucket.list_blobs(max_results=5))

        if blobs:
            print(f"Found {len(blobs)} file(s):")
            for i, blob in enumerate(blobs, 1):
                size_mb = blob.size / (1024 * 1024)
                print(f"  {i}. {blob.name}")
                print(f"     Size: {size_mb:.2f} MB")
                print(f"     Updated: {blob.updated}")
        else:
            print("✓ Bucket is empty (no files yet)")

    except Exception as e:
        print(f"\n✗ ERROR listing files: {type(e).__name__}")
        sys.exit(1)

class GCPBucketConnector:
    """
    Google Cloud Storage connector for PDF upload/download operations.
        
    Usage Example:
    connector = GCPBucketConnector()  # Uses GCP_BUCKET_NAME from .env

    # Upload creates blob "pdfs/paper1.pdf"
    connector.upload_pdf("local.pdf", paper_id="paper1")

    # Upload creates blob "pdfs/paper2.pdf" (different blob!)
    connector.upload_pdf("another.pdf", paper_id="paper2")

    # Download from existing blob
    connector.download_pdf("paper1", "./downloaded.pdf")
    """

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize connection to GCP Cloud Storage bucket.

        Args:
            bucket_name: GCS bucket name. If None, reads from GCP_BUCKET_NAME env var.

        Raises:
            ValueError: If bucket_name not provided and not in environment
            ConnectionError: If unable to connect to GCP or access bucket
        """
        logger.debug("Initializing GCPBucketConnector")

        # Get bucket name
        self.bucket_name = bucket_name or os.getenv("GCP_BUCKET_NAME")

        # Validate bucket name early
        if not self.bucket_name:
            error_msg = "No bucket name provided or in .env as 'GCP_BUCKET_NAME'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(f"Using bucket: {self.bucket_name}")

        # Create GCP storage client
        try:
            self.client = storage.Client()
            logger.debug(f"GCP client created (project: {self.client.project})")
        except Exception as e:
            error_msg = f"Unable to create GCP client: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        # Get bucket object and verify it exists
        try:
            self.bucket = self.client.bucket(self.bucket_name)
            if not self.bucket.exists():
                error_msg = f"Bucket '{self.bucket_name}' doesn't exist"
                logger.error(error_msg)
                raise ConnectionError(error_msg)
            logger.info(f"Connected to GCS bucket: {self.bucket_name}")
        except Exception as e:
            error_msg = f"Can't connect to bucket '{self.bucket_name}': {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

    def upload_pdf(self, pdf_path: str, paper_id: str):
        """
        Upload a PDF to cloud storage.

        Args:
          pdf_path: Local path to PDF file
          paper_id: Unique identifier for this paper (used to name the blob)

        Returns:
          Cloud storage URI (gs://bucket/path)
        """
        # Create unique blob name for this paper
        blob_name = f"pdfs/{paper_id}.pdf"
        logger.debug(f"Uploading PDF to {blob_name}")

        # Create blob reference (this doesn't upload yet!)
        blob = self.bucket.blob(blob_name)

        # Upload the file
        try:
            blob.upload_from_filename(pdf_path, timeout=60)
            uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.info(f"Uploaded PDF: {blob_name}")

            # Return cloud storage URI
            return uri

        except Exception as e:
            error_msg = f"Failed to upload {pdf_path}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def download_pdf(self, paper_id: str, destination_path: str) -> None:
        """
        Download a PDF from cloud storage to local filesystem.

        Args:
            paper_id: Unique identifier for the paper (same ID used during upload)
            destination_path: Local filesystem path where PDF should be saved

        Raises:
            FileNotFoundError: If PDF doesn't exist in cloud storage
            IOError: If download fails

        Example:
            connector.download_pdf("10.1234-science.2024", "./downloads/paper.pdf")
            # Downloads from: gs://bucket/pdfs/10.1234-science.2024.pdf
        """
        # Construct blob name (must match upload format!)
        blob_name = f"pdfs/{paper_id}.pdf"
        blob = self.bucket.blob(blob_name)
        logger.debug(f"Downloading PDF from {blob_name}")

        # Check if blob exists before attempting download
        if not blob.exists():
            error_msg = f"PDF not found in cloud storage: gs://{self.bucket_name}/{blob_name}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Download to local file
        try:
            blob.download_to_filename(destination_path)
            logger.info(f"Downloaded PDF: {blob_name} → {destination_path}")
        except Exception as e:
            error_msg = f"Failed to download {blob_name}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def pdf_exists(self, paper_id: str) -> bool:
        """
        Check if a PDF exists in cloud storage.

        Useful for avoiding duplicate uploads or checking before download.

        Args:
            paper_id: Unique identifier for the paper

        Returns:
            True if PDF exists in storage, False otherwise

        Example:
            if not connector.pdf_exists("paper1"):
                connector.upload_pdf("paper.pdf", "paper1")
        """
        blob_name = f"pdfs/{paper_id}.pdf"
        blob = self.bucket.blob(blob_name)
        return blob.exists()

    def list_pdfs(self, max_results: int = 100) -> list:
        """
        List PDFs stored in the bucket.

        Args:
            max_results: Maximum number of PDFs to return (default: 100)

        Returns:
            List of blob names (file paths) in the bucket

        Example:
            pdfs = connector.list_pdfs(max_results=10)
            for pdf_path in pdfs:
                print(pdf_path)  # e.g., "pdfs/paper1.pdf"
        """
        # List blobs with prefix "pdfs/" to only get PDF files
        blobs = self.bucket.list_blobs(prefix="pdfs/", max_results=max_results)
        return [blob.name for blob in blobs]

    def upload_parsed_data(self, parsed_data: dict, paper_id: str, run_id: str = None) -> str:
        """
        Upload parsed paper data (JSON) to cloud storage.

        This is the primary storage method for processed papers.

        Args:
            parsed_data: Dictionary containing parsed text, sections, metadata
            paper_id: Unique identifier for this paper
            run_id: Optional run identifier to group papers from same query/run

        Returns:
            Cloud storage URI (gs://bucket/path)

        Raises:
            IOError: If upload fails

        Example:
            parsed = parser.parse(pdf_bytes, paper_id="paper1")
            uri = connector.upload_parsed_data(parsed, "paper1", "run_2025-11-06_143022")
            # Creates: gs://bucket/parsed/run_2025-11-06_143022/paper1_extracted.json
        """
        import json

        # Create blob path for parsed data
        if run_id:
            blob_name = f"parsed/{run_id}/{paper_id}_extracted.json"
        else:
            # Fallback to old structure if no run_id provided
            blob_name = f"parsed/{paper_id}/extracted.json"

        blob = self.bucket.blob(blob_name)
        logger.debug(f"Uploading parsed data to {blob_name}")

        try:
            # Upload as JSON string
            json_string = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            blob.upload_from_string(
                json_string,
                content_type="application/json",
                timeout=60
            )
            uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.info(f"Uploaded parsed data: {blob_name} ({len(json_string)} bytes)")

            return uri

        except Exception as e:
            error_msg = f"Failed to upload parsed data for {paper_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def download_parsed_data(self, paper_id: str) -> dict:
        """
        Download parsed paper data from cloud storage.

        Args:
            paper_id: Unique identifier for the paper

        Returns:
            Dictionary with parsed data (full_text, sections, metadata, etc.)

        Raises:
            FileNotFoundError: If parsed data doesn't exist
            IOError: If download or JSON parsing fails

        Example:
            data = connector.download_parsed_data("paper1")
            print(data["full_text"][:100])
        """
        import json

        blob_name = f"parsed/{paper_id}/extracted.json"
        blob = self.bucket.blob(blob_name)
        logger.debug(f"Downloading parsed data from {blob_name}")

        if not blob.exists():
            error_msg = f"Parsed data not found: gs://{self.bucket_name}/{blob_name}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            json_string = blob.download_as_text()
            parsed_data = json.loads(json_string)
            logger.info(f"Downloaded parsed data: {blob_name} ({len(json_string)} bytes)")
            return parsed_data

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON for {paper_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)
        except Exception as e:
            error_msg = f"Failed to download parsed data for {paper_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def download_parsed_data_from_run(self, run_id: str, paper_id: str) -> dict:
        """
        Download parsed paper data from a specific retrieval run.

        This method is designed for the run-grouped storage structure where
        papers from the same query are grouped under a common run_id.

        Args:
            run_id: Run identifier (e.g., "run_2025-11-06_143022")
            paper_id: Unique identifier for the paper (OpenAlex ID like "W2123456789")

        Returns:
            Dictionary with parsed data (full_text, sections, metadata, etc.)

        Raises:
            FileNotFoundError: If parsed data doesn't exist in cloud storage
            IOError: If download or JSON parsing fails

        Example:
            data = connector.download_parsed_data_from_run("run_2025-11-06_143022", "W2123456789")
            print(data["metadata"]["title"])
            print(data["full_text"][:100])
        """
        import json

        # Construct blob name using run-grouped structure
        blob_name = f"parsed/{run_id}/{paper_id}_extracted.json"
        blob = self.bucket.blob(blob_name)
        logger.debug(f"Downloading parsed data from {blob_name}")

        if not blob.exists():
            error_msg = f"Parsed data not found: gs://{self.bucket_name}/{blob_name}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            json_string = blob.download_as_text()
            parsed_data = json.loads(json_string)
            logger.debug(f"Downloaded parsed data: {blob_name} ({len(json_string)} bytes)")
            return parsed_data

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON for {paper_id} in run {run_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)
        except Exception as e:
            error_msg = f"Failed to download parsed data for {paper_id} in run {run_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def upload_failed_pdf(self, pdf_bytes: bytes, paper_id: str, error_msg: str = "") -> str:
        """
        Upload a PDF that failed parsing to cloud storage for debugging.

        This helps track which PDFs couldn't be processed and why.

        Args:
            pdf_bytes: Raw PDF file bytes
            paper_id: Unique identifier for this paper
            error_msg: Optional error message describing what went wrong

        Returns:
            Cloud storage URI (gs://bucket/path)

        Raises:
            IOError: If upload fails

        Example:
            try:
                parsed = parser.parse(pdf_bytes)
            except Exception as e:
                uri = connector.upload_failed_pdf(pdf_bytes, "paper1", str(e))
        """
        blob_name = f"failed_pdfs/{paper_id}.pdf"
        blob = self.bucket.blob(blob_name)
        logger.debug(f"Uploading failed PDF to {blob_name}")

        try:
            # Upload PDF bytes
            blob.upload_from_string(
                pdf_bytes,
                content_type="application/pdf",
                timeout=60
            )

            # Optionally store error message as metadata
            if error_msg:
                blob.metadata = {"error": error_msg[:1000]}  # GCP metadata limit
                blob.patch()

            uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.warning(f"Uploaded failed PDF: {blob_name} (reason: {error_msg[:100]})")
            return uri

        except Exception as e:
            upload_error = f"Failed to upload failed PDF for {paper_id}: {e}"
            logger.error(upload_error)
            raise IOError(upload_error)

    def upload_run_metadata(self, run_id: str, metadata: dict) -> str:
        """
        Upload metadata for a retrieval run to cloud storage.

        This stores information about the query, filters, and results for debugging.

        Args:
            run_id: Run identifier (e.g., "run_2025-11-06_143022")
            metadata: Dictionary with run information:
                - query: Search query used
                - timestamp: ISO timestamp of run
                - filters: Dict of filters applied (year_min, etc.)
                - papers_retrieved: Total papers found
                - papers_parsed: Successfully parsed count
                - papers_failed: Failed parse count

        Returns:
            Cloud storage URI (gs://bucket/path)

        Raises:
            IOError: If upload fails

        Example:
            metadata = {
                "query": "graphene oxide",
                "timestamp": "2025-11-06T14:30:22Z",
                "filters": {"year_min": 2023},
                "papers_retrieved": 10,
                "papers_parsed": 8,
                "papers_failed": 2
            }
            uri = connector.upload_run_metadata("run_2025-11-06_143022", metadata)
        """
        import json

        blob_name = f"parsed/{run_id}/run_metadata.json"
        blob = self.bucket.blob(blob_name)
        logger.debug(f"Uploading run metadata to {blob_name}")

        try:
            json_string = json.dumps(metadata, indent=2, ensure_ascii=False)
            blob.upload_from_string(
                json_string,
                content_type="application/json",
                timeout=60
            )
            uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.info(f"Uploaded run metadata: {blob_name}")

            return uri

        except Exception as e:
            error_msg = f"Failed to upload run metadata for {run_id}: {e}"
            logger.error(error_msg)
            raise IOError(error_msg)

    def parsed_data_exists(self, paper_id: str) -> bool:
        """
        Check if parsed data exists in cloud storage.

        Args:
            paper_id: Unique identifier for the paper

        Returns:
            True if parsed data exists, False otherwise

        Example:
            if connector.parsed_data_exists("paper1"):
                data = connector.download_parsed_data("paper1")
        """
        blob_name = f"parsed/{paper_id}/extracted.json"
        blob = self.bucket.blob(blob_name)
        return blob.exists()

if __name__ == "__main__":
    cwd = os.getcwd()
    # quick test
    bucketConn = GCPBucketConnector()
    bucketConn.upload_pdf(pdf_path=f"{cwd}/2018_Recombinant_Spidroins.pdf", paper_id="912381294572")

    if bucketConn.pdf_exists(paper_id="912381294572"):
        print("found paper in list!")
    else:
        print("didnt find paper in list")
