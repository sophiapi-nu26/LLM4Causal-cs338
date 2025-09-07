"""
FLAN-T5 model implementation.
"""

from typing import Optional, Any
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
from ..base import BaseLLM, register_model
from ...schema import ModelConfig, ExtractionResult

PROMPT_TEMPLATE = """
Extract causal relationships from the following materials science text.
Focus on identifying relationships between materials, properties, processes, and conditions.

Text: {text}

Format your response as:
Entity 1 | Relationship | Entity 2 | Confidence | Evidence
Where:
- Entity 1 and 2 are materials science concepts
- Relationship is one of: increases, decreases, causes, correlates_with
- Confidence is a number between 0 and 1
- Evidence is the supporting text

Example:
temperature | increases | crystallinity | 0.9 | "Higher temperatures led to increased crystallinity"

Your extraction:
"""

@register_model("flan-t5")
class FlanT5Model(BaseLLM):
    """FLAN-T5 implementation for relationship extraction."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        super().__init__(config)
        
        # Initialize model and tokenizer
        self.device = torch.device(self.config.device)
        self.tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")
        self.model = T5ForConditionalGeneration.from_pretrained(
            "google/flan-t5-large"
        ).to(self.device)
    
    def extract_relations(
        self,
        text: str,
        batch_size: Optional[int] = None
    ) -> ExtractionResult:
        """Extract relationships from text using FLAN-T5."""
        prompt = self._prepare_prompt(text)
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=self.config.max_length,
            truncation=True
        ).to(self.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=200,
            temperature=self.config.temperature,
            do_sample=True,
            num_return_sequences=1
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return self._process_response(response)
    
    def _prepare_prompt(self, text: str) -> str:
        """Prepare the prompt for FLAN-T5."""
        return PROMPT_TEMPLATE.format(text=text)
    
    def _process_response(self, response: str) -> ExtractionResult:
        """Process FLAN-T5 response into structured output."""
        relationships = []
        entities = set()
        
        # Split response into lines and process each relationship
        for line in response.strip().split('\n'):
            if not line or '|' not in line:
                continue
                
            try:
                # Parse the line format: Entity1 | Relationship | Entity2 | Confidence | Evidence
                parts = [p.strip() for p in line.split('|')]
                if len(parts) != 5:
                    continue
                    
                entity1, rel_type, entity2, confidence, evidence = parts
                
                # Convert confidence to float, defaulting to 0.5 if invalid
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.5
                    
                # Add to relationships
                relationships.append({
                    "source": entity1,
                    "relation": rel_type,
                    "target": entity2,
                    "confidence": confidence,
                    "evidence": evidence
                })
                
                # Collect unique entities
                entities.add(entity1)
                entities.add(entity2)
                
            except Exception as e:
                print(f"Error processing line: {line}")
                print(f"Error: {str(e)}")
                continue
        
        return ExtractionResult(
            entities=list(entities),
            relationships=relationships,
            metadata={
                "raw_response": response,
                "parsed_relationship_count": len(relationships)
            }
        )
