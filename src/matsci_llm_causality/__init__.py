"""
Main module for MaterialsScience LLM Causality extraction.
"""

from .extraction.pdf import PDFProcessor
from .models import create_model
from .schema import ModelConfig, ExtractionResult
from .workflows.section_pipeline import (
    SectionAwareWorkflow,
    StageRunConfig,
    SectionWorkflowResult,
)

__version__ = "0.1.0"
__all__ = [
    "PDFProcessor",
    "create_model",
    "ModelConfig",
    "ExtractionResult",
    "SectionAwareWorkflow",
    "StageRunConfig",
    "SectionWorkflowResult",
]
