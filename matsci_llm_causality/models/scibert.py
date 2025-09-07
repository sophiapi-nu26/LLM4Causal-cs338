"""
SciBERT-based entity recognition for materials science text.
"""

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from typing import List, Optional

from ..schema import Entity, EntityType

class SciBERTEntityRecognizer:
    """Entity recognition using SciBERT model fine-tuned on materials science text."""
    
    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased", device: Optional[str] = None):
        """Initialize the SciBERT entity recognizer.
        
        Args:
            model_name: Name/path of the pretrained model
            device: Device to run model on ('cuda' or 'cpu')
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.model.to(device)
        
        # Map model output indices to entity types
        self.id2label = {
            0: EntityType.MATERIAL,
            1: EntityType.PROPERTY,
            2: EntityType.STRUCTURE,
            3: EntityType.PROCESS,
            4: EntityType.CONDITION,
            5: EntityType.CHARACTERIZATION,
            6: EntityType.APPLICATION,
            7: "O"  # Outside any entity
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from a single text.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities with their types and metadata
        """
        # Tokenize input
        tokens = self.tokenizer(text, return_tensors="pt", padding=True)
        tokens = {k: v.to(self.device) for k, v in tokens.items()}
        
        # Get model predictions
        with torch.no_grad():
            outputs = self.model(**tokens)
            
        # Convert logits to predictions
        predictions = torch.argmax(outputs.logits, dim=-1)
        confidences = torch.softmax(outputs.logits, dim=-1).max(dim=-1).values
        
        # Convert predictions to entities
        entities = []
        current_entity = None
        
        for i, (pred, conf) in enumerate(zip(predictions[0], confidences[0])):
            label = self.id2label[pred.item()]
            if label != "O":
                token = self.tokenizer.convert_ids_to_tokens(tokens["input_ids"][0][i])
                if current_entity is None:
                    # Start new entity
                    current_entity = {
                        "text": token,
                        "type": label,
                        "start": i,
                        "confidence": conf.item()
                    }
                else:
                    # Continue current entity
                    current_entity["text"] += " " + token
                    current_entity["confidence"] = min(current_entity["confidence"], conf.item())
            elif current_entity is not None:
                # End current entity
                entities.append(Entity(
                    text=current_entity["text"],
                    type=current_entity["type"],
                    start_char=current_entity["start"],
                    end_char=i-1,
                    confidence=current_entity["confidence"]
                ))
                current_entity = None
        
        return entities
    
    def batch_extract_entities(self, texts: List[str]) -> List[List[Entity]]:
        """Extract entities from multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of extracted entities for each input text
        """
        return [self.extract_entities(text) for text in texts]
