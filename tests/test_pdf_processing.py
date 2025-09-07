"""
Integration test for processing a single PDF through the pipeline.
"""

import os
from pathlib import Path
import pytest
from matsci_llm_causality import CausalityExtractor, ModelConfig

# Constants
TEST_DATA_DIR = Path(__file__).parent / "data"

def test_process_single_pdf():
    """
    Test processing a single PDF file through the entire pipeline.
    
    To use this test:
    1. Place your PDF in the tests/data directory
    2. Update PDF_NAME to match your file
    3. Run with: pytest tests/test_pdf_processing.py -v
    """
    # Configuration
    PDF_NAME = "your_test_paper.pdf"  # Replace with your PDF filename
    pdf_path = TEST_DATA_DIR / PDF_NAME
    
    # Skip if PDF doesn't exist
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}. Please add a PDF file to run this test.")
    
    # Initialize extractor with FLAN-T5 (CPU-friendly default)
    config = ModelConfig(
        model_type="flan-t5",
        temperature=0.7,
        max_length=512,
        device="cpu"
    )
    extractor = CausalityExtractor(model="flan-t5", model_config=config)
    
    # Process the PDF
    results = extractor.process_pdf(pdf_path)
    
    # Basic validation
    assert results is not None
    assert hasattr(results, 'entities')
    assert hasattr(results, 'relationships')
    
    # Print results for inspection
    print("\nExtracted Entities:")
    for entity in results.entities:
        print(f"- {entity.text} ({entity.type})")
    
    print("\nExtracted Relationships:")
    for rel in results.relationships:
        print(f"- {rel.subject.text} {rel.relation_type} {rel.object.text} "
              f"(confidence: {rel.confidence:.2f})")
        print(f"  Evidence: {rel.evidence}")
    
    # Additional assertions
    if results.entities:
        assert all(hasattr(e, 'text') and hasattr(e, 'type') for e in results.entities)
    
    if results.relationships:
        for rel in results.relationships:
            assert hasattr(rel, 'subject')
            assert hasattr(rel, 'object')
            assert hasattr(rel, 'confidence')
            assert 0 <= rel.confidence <= 1
            assert hasattr(rel, 'evidence')

def test_process_pdf_with_sections():
    """Test processing a PDF with section awareness."""
    PDF_NAME = "your_test_paper.pdf"  # Replace with your PDF filename
    pdf_path = TEST_DATA_DIR / PDF_NAME
    
    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found at {pdf_path}")
    
    config = ModelConfig(
        model_type="flan-t5",
        temperature=0.7,
        max_length=512
    )
    extractor = CausalityExtractor(model="flan-t5", model_config=config)
    
    # Process sections separately
    sections = extractor.pdf_processor.extract_sections(pdf_path)
    
    # Process each section
    for section_name, section_text in sections.items():
        print(f"\nProcessing section: {section_name}")
        results = extractor.process_text(section_text)
        
        # Print section-specific results
        if results.relationships:
            print(f"\nRelationships found in {section_name}:")
            for rel in results.relationships:
                print(f"- {rel.subject.text} {rel.relation_type} {rel.object.text}")
                print(f"  Evidence: {rel.evidence}")

if __name__ == "__main__":
    # This allows running the test file directly with more detailed output
    pytest.main([__file__, "-v", "--capture=no"])
