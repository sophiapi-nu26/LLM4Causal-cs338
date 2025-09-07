"""
Tests for PDF processing and text extraction.
"""

import pytest
from pathlib import Path
import fitz  # PyMuPDF
from matsci_llm_causality.extraction.pdf import PDFProcessor

# Test data paths
TEST_DATA = Path(__file__).parent.parent / "data"
SAMPLE_TEXT = """
The crystallinity of silk fibroin increases with temperature. Higher beta-sheet content
leads to improved mechanical properties. The addition of glycerol decreases the glass
transition temperature.
"""

@pytest.fixture
def pdf_processor():
    """Fixture for PDFProcessor instance."""
    return PDFProcessor()

@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF with known content."""
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), SAMPLE_TEXT)
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_pdf_text_extraction(pdf_processor, sample_pdf):
    """Test basic text extraction from PDF."""
    extracted_text = pdf_processor.extract_text(sample_pdf)
    assert extracted_text.strip()
    assert "silk fibroin" in extracted_text
    assert "crystallinity" in extracted_text

def test_pdf_section_extraction(pdf_processor, sample_pdf):
    """Test section-aware text extraction."""
    sections = pdf_processor.extract_sections(sample_pdf)
    assert sections
    assert isinstance(sections, dict)
    assert any(text.strip() for text in sections.values())

def test_invalid_pdf_handling(pdf_processor, tmp_path):
    """Test handling of invalid or corrupted PDFs."""
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("This is not a PDF file")
    
    with pytest.raises(Exception) as exc_info:
        pdf_processor.extract_text(invalid_pdf)
    assert "PDF" in str(exc_info.value)

def test_empty_pdf_handling(pdf_processor, tmp_path):
    """Test handling of empty PDFs."""
    empty_pdf = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.save(empty_pdf)
    doc.close()
    
    text = pdf_processor.extract_text(empty_pdf)
    assert text.strip() == ""

def test_pdf_with_images(pdf_processor, tmp_path):
    """Test PDF with images (should skip images but process text)."""
    # TODO: Create a PDF with both text and images
    pass

def test_pdf_with_tables(pdf_processor, tmp_path):
    """Test PDF with tables."""
    # TODO: Create a PDF with tables
    pass

def test_large_pdf_handling(pdf_processor, tmp_path):
    """Test handling of large PDFs (memory efficiency)."""
    # Create a large PDF
    large_pdf = tmp_path / "large.pdf"
    doc = fitz.open()
    for _ in range(100):  # 100 pages
        page = doc.new_page()
        page.insert_text((50, 50), SAMPLE_TEXT)
    doc.save(large_pdf)
    doc.close()
    
    text = pdf_processor.extract_text(large_pdf)
    assert text.strip()
    assert len(text.split("\n")) > 100
