from typing import Optional, Any, List
from openai import OpenAI
from ...schema import (
    ExtractionResult, ModelConfig, Entity, EntityType,
    Relationship, RelationType
)
from ..base import register_model, BaseLLM
from dotenv import load_dotenv
import os
load_dotenv()

@register_model("gpt-5-entity")
class GPT5EntityRecognizer:
    """Entity recognition using GPT-5 model for materials science text."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the GPT-5 entity recognizer.
        
        Args:
            config: Model configuration
        """
        if config is None:
            config = ModelConfig(
                model_type="gpt-4o-2024-08-06",
                temperature=0.3,  # Lower temperature for more consistent entity extraction
                # max_length=512
            )
        
        self.config = config
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Uses OPENAI_API_KEY environment variable
        
        # Map string labels to entity types
        self.label_to_type = {
            "MATERIAL": EntityType.MATERIAL,
            "PROPERTY": EntityType.PROPERTY,
            "STRUCTURE": EntityType.STRUCTURE,
            "PROCESS": EntityType.PROCESS,
        }
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from a single text.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities with their types and metadata
        """
        prompt = self._prepare_entity_prompt(text)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[{
                "role": "system",
                "content": """You are an expert at identifying entities in materials science text.
                For each entity, provide: text, type (MATERIAL, PROPERTY, STRUCTURE, PROCESS),
                start_char, end_char, and confidence score (0-1)."""
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=self.config.temperature,
            # max_tokens=self.config.max_length
        )
        return self._process_entity_response(response, text)
    
    def batch_extract_entities(self, texts: List[str]) -> List[List[Entity]]:
        """Extract entities from multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of extracted entities for each input text
        """
        return [self.extract_entities(text) for text in texts]
    
    def _prepare_entity_prompt(self, text: str) -> str:
        """Prepare the prompt for entity extraction."""
        return f"""Extract material-science related entities from the following materials science text.
        For each entity found, identify:
        1. The exact text of the entity
        2. Its type (MATERIAL, PROPERTY, STRUCTURE, PROCESS)
        3. The character positions (start and end) in the text
        4. A confidence score between 0 and 1
        
        Text: {text}
        
        Format each entity as:
        text: <exact text>
        type: <entity type>
        start: <start position>
        end: <end position>
        confidence: <score>
        
        You are only responsible for extracting entities that can fit into material science context. Avoid unrelated terms.
        """

    def _process_entity_response(self, response: Any, original_text: str) -> List[Entity]:
        """Process the model's response to extract entities."""
        entities = []
        raw_text = response.choices[0].message.content
        
        # Parse the structured response and create Entity objects
        current_entity = {}
        for line in raw_text.split('\n'):
            line = line.strip()
            if not line:
                if current_entity:
                    try:
                        entity_type = self.label_to_type.get(
                            current_entity.get('type', '').upper(),
                            EntityType.OTHER
                        )
                        entities.append(Entity(
                            id=f"entity_{len(entities)}",
                            text=current_entity['text'],
                            type=entity_type,
                            metadata={
                                'start_char': int(current_entity['start']),
                                'end_char': int(current_entity['end']),
                                'confidence': float(current_entity['confidence'])
                            }
                        ))
                    except (KeyError, ValueError):
                        pass  # Skip malformed entities
                    current_entity = {}
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                current_entity[key.strip().lower()] = value.strip()
        
        # Handle last entity if exists
        if current_entity:
            try:
                entity_type = self.label_to_type.get(
                    current_entity.get('type', '').upper(),
                    EntityType.OTHER
                )
                entities.append(Entity(
                    id=f"entity_{len(entities)}",
                    text=current_entity['text'],
                    type=entity_type,
                    metadata={
                        'start_char': int(current_entity['start']),
                        'end_char': int(current_entity['end']),
                        'confidence': float(current_entity['confidence'])
                    }
                ))
            except (KeyError, ValueError):
                pass
        
        return entities


@register_model("gpt-5-relation")  # Match the ID used in process_pdf.py
class GPT5RelationExtractor(BaseLLM):
    def __init__(self, config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_type="gpt-4o-2024-08-06",
                temperature=0.3,
                # max_length=512
            )
        self.config = config
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
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
    
    def _prepare_prompt(self, text: str, entities: List[Entity]) -> str:
        """Prepare the prompt for relationship extraction."""
        entity_descriptions = "\n".join([
            f"- {e.text} (Type: {e.type}, ID: {e.id})"
            for e in entities
        ])
        
        return f"""Identify causal relationships between the following entities in this materials science text.
        Only identify relationships between these specific entities:
        
        {entity_descriptions}
        
        Text to analyze:
        {text}
        
        For each relationship found, provide:
        1. Subject ID (must match one of the provided entity IDs)
        2. Object ID (must match one of the provided entity IDs)
        3. Relationship type (increases/decreases/causes/correlates_with)
        4. Polarity (-1, 0, or 1)
        5. Confidence score (0-1)
        6. Provide only a blank space for evidence
        
        Format each relationship as:
        subject_id: <id>
        object_id: <id>
        type: <relationship type>
        polarity: <polarity>
        confidence: <score>
        evidence: [ ]"""
    
    def _process_response(self, response: Any, entities: List[Entity]) -> List[Relationship]:
        """Process the model's response and create Relationship objects."""
        relationships = []
        raw_text = response.choices[0].message.content
        
        # Create entity lookup by ID
        entity_map = {e.id: e for e in entities}
        
        # Parse the structured response
        current_rel = {}
        for line in raw_text.split('\n'):
            line = line.strip()
            if not line:
                if current_rel:
                    try:
                        # Get the subject and object entities
                        subject = entity_map.get(current_rel['subject_id'])
                        object_ = entity_map.get(current_rel['object_id'])
                        
                        if subject and object_:
                            # Create relationship if both entities exist
                            relationships.append(Relationship(
                                subject=subject,
                                object=object_,
                                relation_type=RelationType(current_rel['type']),
                                polarity=int(current_rel['polarity']),
                                confidence=float(current_rel['confidence']),
                                evidence=current_rel['evidence']
                            ))
                    except (KeyError, ValueError):
                        pass  # Skip malformed relationships
                    current_rel = {}
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                current_rel[key.strip().lower()] = value.strip()
        
        # Handle last relationship if exists
        if current_rel:
            try:
                subject = entity_map.get(current_rel['subject_id'])
                object_ = entity_map.get(current_rel['object_id'])
                
                if subject and object_:
                    relationships.append(Relationship(
                        subject=subject,
                        object=object_,
                        relation_type=RelationType(current_rel['type']),
                        polarity=int(current_rel['polarity']),
                        confidence=float(current_rel['confidence']),
                        evidence=current_rel['evidence']
                    ))
            except (KeyError, ValueError):
                pass
        
        return relationships
    

