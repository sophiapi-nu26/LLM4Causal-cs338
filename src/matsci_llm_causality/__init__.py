"""
Main module for MaterialsScience LLM Causality extraction.
"""

# Legacy imports (commented out - not used by Monte Carlo API)
# from .extraction.pdf import PDFProcessor
# from .models import create_model
# from .workflows.section_pipeline import (
#     SectionAwareWorkflow,
#     StageRunConfig,
#     SectionWorkflowResult,
#     MultiDocumentWorkflow,
#     GlobalGraphResult,
# )

# Core schema types (used by Monte Carlo)
from .schema import ModelConfig, ExtractionResult

# Monte Carlo extractor (used by API worker)
from .models.llm.monte_carlo_extractor import MonteCarloEvidenceExtractor
from .models.llm.gemini import GeminiTextRelationExtractor

__version__ = "0.1.0"
__all__ = [
    "ModelConfig",
    "ExtractionResult",
    "MonteCarloEvidenceExtractor",
    "GeminiTextRelationExtractor",
]
