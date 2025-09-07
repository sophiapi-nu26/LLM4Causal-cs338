"""
Main module for MaterialsScience LLM Causality extraction.
"""

from .extraction.pdf import PDFProcessor
from .models import create_model
from .schema import ModelConfig, ExtractionResult

__version__ = "0.1.0"
__all__ = [
    "PDFProcessor", 
    "create_model",
    "ModelConfig", 
    "ExtractionResult"
]
