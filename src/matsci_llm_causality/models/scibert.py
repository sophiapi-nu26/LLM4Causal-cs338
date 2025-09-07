"""
SciBERT-based entity recognition for materials science text.
"""

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer
from safetensors.torch import save_file, load_file
import safetensors
from typing import List, Optional

from .base import register_model
from ..schema import Entity, EntityType, ModelConfig

@register_model("scibert")
class SciBERTEntityRecognizer:
    """Entity recognition using SciBERT model fine-tuned on materials science text."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the SciBERT entity recognizer.
        
        Args:
            config: Model configuration
        """
        if config is None:
            config = ModelConfig(
                model_type="scibert",
                temperature=0.7,
                max_length=512,
                device="cuda" if torch.cuda.is_available() else "cpu"
            )
        
        self.config = config
        model_name = self.config.additional_config.get(
            "model_name", 
            "allenai/scibert_scivocab_uncased"
        )
        
        self.device = self.config.device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            torch_dtype=torch.float32,  # Use float32 for better compatibility
            use_safetensors=True  # Use safetensors for security
        )
        self.model.to(self.device)
        
        # Map model output indices to entity types
        self.id2label = {
            0: EntityType.MATERIAL,
            1: EntityType.PROPERTY,
            2: EntityType.STRUCTURE,
            3: EntityType.PROCESS,
            4: EntityType.CONDITION,
            5: EntityType.OTHER,  # For characterization
            6: EntityType.OTHER,  # For application
            7: "O"  # Outside any entity
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from a single text.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities with their types and metadata
        """
        # Split text into chunks of max_length tokens
        tokens = self.tokenizer(text, return_tensors="pt", truncation=False, padding=False)
        input_ids = tokens["input_ids"][0]
        
        # Process in chunks
        chunk_size = self.config.max_length
        all_predictions = []
        all_confidences = []
        
        for i in range(0, len(input_ids), chunk_size):
            chunk_ids = input_ids[i:i + chunk_size].unsqueeze(0)
            chunk_mask = torch.ones_like(chunk_ids)
            chunk_tokens = {
                "input_ids": chunk_ids.to(self.device),
                "attention_mask": chunk_mask.to(self.device)
            }
            
            # Get model predictions for chunk
            with torch.no_grad():
                outputs = self.model(**chunk_tokens)
                
            # Convert logits to predictions
            predictions = torch.argmax(outputs.logits, dim=-1)
            confidences = torch.softmax(outputs.logits, dim=-1).max(dim=-1).values
            
            all_predictions.append(predictions[0])
            all_confidences.append(confidences[0])
        
        # Combine predictions
        predictions = torch.cat(all_predictions)
        confidences = torch.cat(all_confidences)
        
        # Convert predictions to entities
        entities = []
        current_entity = None
        
        # Get all tokens
        all_tokens = self.tokenizer.convert_ids_to_tokens(input_ids)
        
        for i, (pred, conf) in enumerate(zip(predictions, confidences)):
            label = self.id2label[pred.item()]
            if label != "O":
                token = all_tokens[i]
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
                    id=f"entity_{len(entities)}",
                    text=current_entity["text"],
                    type=current_entity["type"],
                    metadata={
                        "start_char": current_entity["start"],
                        "end_char": i-1,
                        "confidence": current_entity["confidence"]
                    }
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
