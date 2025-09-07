"""
Core package for materials science LLM-based causality extraction.
"""

from .schema import Entity, EntityType
from .models import SciBERTEntityRecognizer

__version__ = "0.1.0"
__all__ = ["Entity", "EntityType", "SciBERTEntityRecognizer"]
