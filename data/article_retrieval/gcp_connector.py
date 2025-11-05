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
        # Get bucket name
        self.bucket_name = bucket_name or os.getenv("GCP_BUCKET_NAME")

        # Validate bucket name early
        if not self.bucket_name:
            raise ValueError("No bucket name provided or in .env as 'GCP_BUCKET_NAME'")

        # Create GCP storage client
        try:
            self.client = storage.Client()
        except Exception as e:
            raise ConnectionError(f"Unable to create GCP client: {e}")

        # Get bucket object and verify it exists
        try:
            self.bucket = self.client.bucket(self.bucket_name)
            if not self.bucket.exists():
                raise ConnectionError(f"Bucket '{self.bucket_name}' doesn't exist")
        except Exception as e:
            raise ConnectionError(f"Can't connect to bucket '{self.bucket_name}': {e}")

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

        # Create blob reference (this doesn't upload yet!)
        blob = self.bucket.blob(blob_name)

        # Upload the file
        try:
            blob.upload_from_filename(pdf_path, timeout=60)
            print(f"✓ Uploaded: {blob_name}")

            # Return cloud storage URI
            return f"gs://{self.bucket_name}/{blob_name}"

        except Exception as e:
            raise IOError(f"Failed to upload {pdf_path}: {e}")

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

        # Check if blob exists before attempting download
        if not blob.exists():
            raise FileNotFoundError(
                f"PDF not found in cloud storage: gs://{self.bucket_name}/{blob_name}"
            )

        # Download to local file
        try:
            blob.download_to_filename(destination_path)
            print(f"✓ Downloaded: {blob_name} → {destination_path}")
        except Exception as e:
            raise IOError(f"Failed to download {blob_name}: {e}")

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

if __name__ == "__main__":
    cwd = os.getcwd()
    # quick test
    bucketConn = GCPBucketConnector()
    bucketConn.upload_pdf(pdf_path=f"{cwd}/2018_Recombinant_Spidroins.pdf", paper_id="912381294572")

    if bucketConn.pdf_exists(paper_id="912381294572"):
        print("found paper in list!")
    else:
        print("didnt find paper in list")
