"""
Main extraction interface for the package.
"""

from pathlib import Path
from typing import Optional, Union
from .pdf import PDFProcessor
from ..models import create_model
from ..schema import ExtractionResult, ModelConfig

class CausalityExtractor:
    """Main interface for extracting causal relationships from materials science text."""
    
    def __init__(
        self,
        model: str = "flan-t5",
        model_config: Optional[ModelConfig] = None
    ):
        """
        Initialize the extractor.
        
        Args:
            model: Name of the LLM model to use
            model_config: Optional configuration for the model
        """
        self.pdf_processor = PDFProcessor()
        self.model = create_model(model, model_config)
    
    def process_pdf(
        self,
        pdf_path: Union[str, Path],
        batch_size: Optional[int] = None
    ) -> ExtractionResult:
        """
        Process a PDF file to extract causal relationships.
        
        Args:
            pdf_path: Path to the PDF file
            batch_size: Optional batch size for processing
            
        Returns:
            Extraction results containing entities and relationships
        """
        # Extract text from PDF
        text = self.pdf_processor.extract_text(pdf_path)
        return self.process_text(text, batch_size)
    
    def process_text(
        self,
        text: str,
        batch_size: Optional[int] = None
    ) -> ExtractionResult:
        """
        Process text to extract causal relationships.
        
        Args:
            text: Input text to process
            batch_size: Optional batch size for processing
            
        Returns:
            Extraction results containing entities and relationships
        """
        return self.model.extract_relations(text, batch_size)
