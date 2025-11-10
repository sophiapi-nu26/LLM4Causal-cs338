#!/usr/bin/env python3
"""
Parser Adapter for PDF Text Extraction
---------------------------------------
Provides a unified interface for different PDF parsers, handling both
file paths and in-memory PDF bytes.

This adapter wraps the ScientificPDFExtractor (v2) to make it compatible with
cloud storage streaming (bytes) while maintaining file path support.
"""

import logging
import tempfile
import os
from typing import Dict, Optional, Union
from pathlib import Path
from datetime import datetime

# Configure module logger
logger = logging.getLogger(__name__)


class ParserInterface:
    """
    Abstract interface for PDF parsers.

    Any parser implementation must implement the parse() method.
    This makes parsers hot-swappable - just change which class you use!
    """

    def parse(self, pdf_source: Union[str, bytes]) -> Dict:
        """
        Parse a PDF and return structured data.

        Args:
            pdf_source: Either a file path (str) or PDF bytes (bytes)

        Returns:
            Dictionary with parsed data (structure defined by implementation)
        """
        raise NotImplementedError("Subclasses must implement parse()")


class PDFParserAdapter(ParserInterface):
    """
    Adapter for ScientificPDFExtractor (v2).

    Handles the complexity of working with file paths vs bytes,
    making the parser compatible with cloud streaming workflows.

    Usage:
        # From file path
        parser = PDFParserAdapter()
        result = parser.parse("/path/to/paper.pdf")

        # From bytes (cloud download)
        pdf_bytes = download_from_cloud(...)
        result = parser.parse(pdf_bytes)
    """

    def __init__(self):
        """Initialize the adapter."""
        logger.debug("Initializing PDF Parser (v2)")
        # Import PDF parser v2
        from pdf_parser_v2 import (
            ScientificPDFExtractor,
            extract_for_causal_analysis
        )
        self.extractor_class = ScientificPDFExtractor
        self.extract_causal = extract_for_causal_analysis
        logger.debug("PDF Parser (v2) initialized successfully")

    def parse(self, pdf_source: Union[str, bytes], paper_id: Optional[str] = None) -> Dict:
        """
        Parse PDF from file path or bytes.

        Args:
            pdf_source: File path (str) or PDF bytes (bytes)
            paper_id: Optional identifier for the paper (for metadata)

        Returns:
            Dictionary with:
                - full_text: Complete extracted text
                - sections: Dict of section_name -> section_text
                - metadata: PDF metadata (title, author, pages, etc.)
                - causal_optimized_text: Text optimized for causal extraction
                - paper_id: Identifier (if provided)
                - extraction_timestamp: When parsing occurred

        Raises:
            ValueError: If pdf_source is neither str nor bytes
            Exception: If parsing fails (PDF corrupt, etc.)
        """
        temp_file_path = None

        try:
            # Determine if we have a file path or bytes
            if isinstance(pdf_source, str):
                # File path provided - use directly
                logger.debug(f"Parsing PDF from file path: {pdf_source}")
                pdf_path = pdf_source

            elif isinstance(pdf_source, bytes):
                # Bytes provided - write to temp file
                # Note: PyMuPDF (fitz) works best with file paths
                logger.debug(f"Parsing PDF from bytes ({len(pdf_source)} bytes)")
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".pdf",
                    delete=False  # We'll delete manually for error handling
                )
                temp_file_path = temp_file.name
                temp_file.write(pdf_source)
                temp_file.close()
                pdf_path = temp_file_path
                logger.debug(f"Created temp file: {temp_file_path}")

            else:
                error_msg = f"pdf_source must be str (file path) or bytes, got {type(pdf_source)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Parse using Ken's extractor
            logger.debug("Extracting text from PDF")
            extractor = self.extractor_class(pdf_path)
            result = extractor.extract_text()

            # Also get causal-optimized text
            logger.debug("Extracting causal-optimized text")
            extractor_causal = self.extractor_class(pdf_path)
            causal_text = self._extract_causal_text(extractor_causal)
            extractor_causal.close()

            extractor.close()

            # Build structured output
            parsed_data = {
                "full_text": result["full_text"],
                "sections": result["sections"],
                "metadata": result["metadata"],
                "causal_optimized_text": causal_text,
                "paper_id": paper_id,
                "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
                "parser_version": "KenScientificPDFExtractor_v1.0"
            }

            logger.info(f"Successfully parsed PDF (paper_id={paper_id}): {len(result['full_text'])} chars, {len(result['sections'])} sections")
            return parsed_data

        finally:
            # Clean up temp file if we created one
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    # Log but don't fail if cleanup fails
                    logger.warning(f"Could not delete temp file {temp_file_path}: {e}")

    def _extract_causal_text(self, extractor) -> str:
        """
        Extract text optimized for causal analysis.

        This is a helper that replicates extract_for_causal_analysis logic
        but works with an already-initialized extractor.
        """
        import re

        result = extractor.extract_text()
        text = result['full_text']

        # Remove references section
        ref_match = re.search(
            r'\n(REFERENCES?|BIBLIOGRAPHY)\s*\n',
            text,
            re.IGNORECASE
        )
        if ref_match:
            text = text[:ref_match.start()]

        return text


class ParsingError(Exception):
    """
    Exception raised when PDF parsing fails.

    This allows calling code to distinguish parsing failures from other errors.
    """
    pass


def create_parser(parser_type: str = "v2") -> ParserInterface:
    """
    Factory function to create parser instances.

    This makes it easy to switch between different parsers.

    Args:
        parser_type: Type of parser to create. Options:
            - "v2": ScientificPDFExtractor v2 (default)
            - Future: "advanced", "fast", etc.

    Returns:
        Parser instance implementing ParserInterface

    Example:
        parser = create_parser("v2")
        result = parser.parse(pdf_bytes)
    """
    if parser_type.lower() in ["v2", "default"]:
        return PDFParserAdapter()
    else:
        raise ValueError(f"Unknown parser type: {parser_type}. Options: 'v2', 'default'")


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser_adapter.py <pdf_path>")
        print("\nTests the parser adapter with a PDF file")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print("\n" + "="*60)
    print("Parser Adapter Test")
    print("="*60 + "\n")

    # Test 1: Parse from file path
    print("TEST 1: Parsing from file path...")
    parser = PDFParserAdapter()

    try:
        result = parser.parse(pdf_path, paper_id="test-paper-001")

        print("✓ Parsing successful!")
        print(f"\nMetadata:")
        for key, value in result['metadata'].items():
            print(f"  {key}: {value}")

        print(f"\nSections found:")
        for section in result['sections'].keys():
            print(f"  - {section}")

        print(f"\nFull text length: {len(result['full_text'])} characters")
        print(f"Causal text length: {len(result['causal_optimized_text'])} characters")

        print(f"\nFirst 200 chars of full text:")
        print(result['full_text'][:200])

    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        sys.exit(1)

    # Test 2: Parse from bytes (simulate cloud download)
    print("\n" + "="*60)
    print("TEST 2: Parsing from bytes (simulating cloud download)...")
    print("="*60 + "\n")

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    print(f"PDF size: {len(pdf_bytes):,} bytes")

    try:
        result = parser.parse(pdf_bytes, paper_id="test-paper-002")
        print("✓ Parsing from bytes successful!")
        print(f"  Sections: {list(result['sections'].keys())}")

    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\nThe parser adapter is working correctly.")
    print("It can handle both file paths and in-memory PDF bytes.\n")
