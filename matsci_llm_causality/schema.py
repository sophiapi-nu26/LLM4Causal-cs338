"""
Schema definitions for materials science entity and relationship types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class EntityType(Enum):
    """Types of entities that can be extracted from materials science text."""
    MATERIAL = "MATERIAL"  # e.g., "silk fibroin", "hydroxyapatite"
    PROPERTY = "PROPERTY"  # e.g., "crystallinity", "tensile strength"
    STRUCTURE = "STRUCTURE"  # e.g., "beta-sheet", "crystal structure"
    PROCESS = "PROCESS"  # e.g., "annealing", "electrospinning"
    CONDITION = "CONDITION"  # e.g., "temperature", "pH"
    CHARACTERIZATION = "CHARACTERIZATION"  # e.g., "XRD", "FTIR"
    APPLICATION = "APPLICATION"  # e.g., "tissue engineering", "drug delivery"

@dataclass
class Entity:
    """Represents an entity extracted from text with its type and metadata."""
    text: str
    type: EntityType
    start_char: int
    end_char: int
    confidence: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
