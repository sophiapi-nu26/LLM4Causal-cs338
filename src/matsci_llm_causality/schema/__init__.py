"""
Base schema definitions for the project.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum

class EntityType(str, Enum):
    MATERIAL = "material"
    STRUCTURE = "structure"
    PROPERTY = "property"
    PROCESS = "process"
    CONDITION = "condition"
    OTHER = "other"

class RelationType(str, Enum):
    INCREASES = "increases"
    DECREASES = "decreases"
    CAUSES = "causes"
    CORRELATES = "correlates_with"

class Entity(BaseModel):
    """Represents a materials science entity."""
    id: str = Field(..., description="Unique identifier for the entity")
    text: str = Field(..., description="Original text of the entity")
    type: EntityType = Field(..., description="Type of the entity")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")

class Relationship(BaseModel):
    """Represents a causal relationship between entities."""
    subject: Entity
    object: Entity
    relation_type: RelationType
    polarity: int = Field(..., ge=-1, le=1, description="Direction of relationship")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence")
    evidence: str = Field(..., description="Supporting text from source")
    metadata: Dict = Field(default_factory=dict)

class ModelConfig(BaseModel):
    """Configuration for LLM models."""
    model_type: str
    temperature: float = Field(0.7, ge=0, le=1)
    max_length: int = Field(512, gt=0)
    device: str = "cpu"
    batch_size: int = Field(1, gt=0)
    additional_config: Dict = Field(default_factory=dict)

class ExtractionResult(BaseModel):
    """Results from causality extraction."""
    entities: List[Entity]
    relationships: List[Relationship]
    metadata: Dict = Field(default_factory=dict)
