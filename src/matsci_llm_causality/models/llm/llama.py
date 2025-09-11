from ...schema import (
    ExtractionResult, ModelConfig, Entity, EntityType,
    Relationship, RelationType
)
from ..base import register_model, BaseLLM
from transformers import pipeline
from typing import Optional

model = "meta-llama/Llama-3.1-8B-Instruct"
@register_model(model)
class LlamaRelationExtractor(BaseLLM):
    """Entity recognition using Llama model for materials science text."""

    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the Llama entity recognizer.
        
        Args:
            config: Model configuration
        """
        self.pipe = pipeline("text-generation",
                             model=model)

        # Map string labels to entity types
        self.label_to_type = {
            "MATERIAL": EntityType.MATERIAL,
            "PROPERTY": EntityType.PROPERTY,
            "STRUCTURE": EntityType.STRUCTURE,
            "PROCESS": EntityType.PROCESS,
        }

    def extract_relations(self, text: str, entities: List[Entity]) -> List[Relationship]:
        """Extract causal relationships between existing entities using GPT-5.
        
        Args:
            text: The source text to analyze
            entities: List of pre-extracted entities to find relationships between
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt = self._prepare_prompt(text, entities)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[{
                "role": "system",
                "content": """You are an expert at identifying causal relationships between entities in materials science text.
                For each relationship, identify:
                1. The subject and object entities (must match exactly with provided entities)
                2. The type of relationship (increases, decreases, causes, correlates_with)
                3. The polarity (-1 for negative, 0 for neutral, 1 for positive effect)
                4. A confidence score between 0 and 1
                5. The specific text evidence supporting this relationship"""
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=self.config.temperature
        )
        
        return self._process_response(response, entities)