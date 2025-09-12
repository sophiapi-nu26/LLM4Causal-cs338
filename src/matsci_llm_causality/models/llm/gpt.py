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

import re
import json

def parse_relationships(text: str):
    # Split text into lines, stripping empty ones
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    results = []
    for line in lines:
        # Regex to capture: [SubjectName][Type] relationship [ObjectName][Type]
        match = re.match(r"(.+?)\[(.*?)\]\s+(increases|decreases|positively correlate with|negatively correlate with|causes)\s+(.+?)\[(.*?)\]$", line)
        if match:
            subject_name, subject_type, relation, object_name, object_type = match.groups()
            results.append({
                "subject": {"name": subject_name.strip(), "type": subject_type.strip()},
                "relationship": relation.strip(),
                "object": {"name": object_name.strip(), "type": object_type.strip()}
            })
    return results

# @register_model("gpt-5-entity")
# class GPT5EntityRecognizer:
#     """Entity recognition using GPT-5 model for materials science text."""
    
#     def __init__(self, config: Optional[ModelConfig] = None):
#         """Initialize the GPT-5 entity recognizer.
        
#         Args:
#             config: Model configuration
#         """
#         if config is None:
#             config = ModelConfig(
#                 model_type="gpt-4o-2024-08-06",
#                 temperature=0.3,  # Lower temperature for more consistent entity extraction
#                 # max_length=512
#             )
        
#         self.config = config
#         self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Uses OPENAI_API_KEY environment variable
        
#         # Map string labels to entity types
#         self.label_to_type = {
#             "MATERIAL": EntityType.MATERIAL,
#             "PROPERTY": EntityType.PROPERTY,
#             "STRUCTURE": EntityType.STRUCTURE,
#             "PROCESS": EntityType.PROCESS,
#         }
    
#     def extract_entities(self, text: str) -> List[Entity]:
#         """Extract entities from a single text.
        
#         Args:
#             text: Input text to extract entities from
            
#         Returns:
#             List of extracted entities with their types and metadata
#         """
#         prompt = self._prepare_entity_prompt(text)
        
#         response = self.client.chat.completions.create(
#             model="gpt-4o-2024-08-06",
#             messages=[{
#                 "role": "system",
#                 "content": """You are an expert at identifying entities in materials science text.
#                 For each entity, provide: text, type (MATERIAL, PROPERTY, STRUCTURE, PROCESS),
#                 start_char, end_char, and confidence score (0-1)."""
#             }, {
#                 "role": "user",
#                 "content": prompt
#             }],
#             temperature=self.config.temperature,
#             # max_tokens=self.config.max_length
#         )
#         return self._process_entity_response(response, text)
    
#     def batch_extract_entities(self, texts: List[str]) -> List[List[Entity]]:
#         """Extract entities from multiple texts.
        
#         Args:
#             texts: List of input texts
            
#         Returns:
#             List of extracted entities for each input text
#         """
#         return [self.extract_entities(text) for text in texts]
    
#     def _prepare_entity_prompt(self, text: str) -> str:
#         """Prepare the prompt for entity extraction."""
#         return f"""Extract material-science related entities from the following materials science text.
#         For each entity found, identify:
#         1. The exact text of the entity
#         2. Its type (MATERIAL, PROPERTY, STRUCTURE, PROCESS)
#         3. The character positions (start and end) in the text
#         4. A confidence score between 0 and 1
        
#         Text: {text}
        
#         Format each entity as:
#         text: <exact text>
#         type: <entity type>
#         start: <start position>
#         end: <end position>
#         confidence: <score>
        
#         You are only responsible for extracting entities that can fit into material science context. Avoid unrelated terms.
#         """

#     def _process_entity_response(self, response: Any, original_text: str) -> List[Entity]:
#         """Process the model's response to extract entities."""
#         entities = []
#         raw_text = response.choices[0].message.content
        
#         # Parse the structured response and create Entity objects
#         current_entity = {}
#         for line in raw_text.split('\n'):
#             line = line.strip()
#             if not line:
#                 if current_entity:
#                     try:
#                         entity_type = self.label_to_type.get(
#                             current_entity.get('type', '').upper(),
#                             EntityType.OTHER
#                         )
#                         entities.append(Entity(
#                             id=f"entity_{len(entities)}",
#                             text=current_entity['text'],
#                             type=entity_type,
#                             metadata={
#                                 'start_char': int(current_entity['start']),
#                                 'end_char': int(current_entity['end']),
#                                 'confidence': float(current_entity['confidence'])
#                             }
#                         ))
#                     except (KeyError, ValueError):
#                         pass  # Skip malformed entities
#                     current_entity = {}
#                 continue
            
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 current_entity[key.strip().lower()] = value.strip()
        
#         # Handle last entity if exists
#         if current_entity:
#             try:
#                 entity_type = self.label_to_type.get(
#                     current_entity.get('type', '').upper(),
#                     EntityType.OTHER
#                 )
#                 entities.append(Entity(
#                     id=f"entity_{len(entities)}",
#                     text=current_entity['text'],
#                     type=entity_type,
#                     metadata={
#                         'start_char': int(current_entity['start']),
#                         'end_char': int(current_entity['end']),
#                         'confidence': float(current_entity['confidence'])
#                     }
#                 ))
#             except (KeyError, ValueError):
#                 pass
        
#         return entities


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
        
    def extract_relations(self, text: str) -> List[Relationship]:
        """Extract causal relationships between existing entities using GPT-5.
        
        Args:
            text: The source text to analyze
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt = self._prepare_prompt(text)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[{
                "role": "system",
                "content": """You are an expert at identifying causal relationships between entities in materials science text.
                For each relationship, identify:
                1. The subject entity: Name[Type(chosen from material, structure, process, property)]
                2. The type of relationship (increases, decreases, causes, positively correlate with, negatively correlate with)
                3. The object entity: Name[Type(chosen from material, structure, process, property)]
                """
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=self.config.temperature
        )
        # print(response.choices[0].message.content)
        # return self._process_response(response)
        return self._process_response(response.choices[0].message.content)
    
    def _prepare_prompt(self, text: str) -> str:
        """Prepare the prompt for relationship extraction."""
        
        return f"""You are an expert in materials science. Your task is to extract relationships among variables mentioned in the given text.  
            Instructions:  
            1. Identify all relevant variables in the text. Each variable must be categorized as exactly one of:  
            - material  
            - structure  
            - process  
            - property  

            2. Identify relationships between variables. Only use the following relationship types:  
            - increases  
            - decreases  
            - positively correlates with  
            - negatively correlates with  
            - causes  

            3. Express each relationship as a structured statement with the format:  
            [Variable A <Type>] [relationship type] [Variable B <Type>]  

            4. Be precise and consistent:  
            - Use the exact wording of the variables as they appear in the text (do not paraphrase).  
            - Output only one relationship per line. Do not number them. Relationships only.
            - Do not include explanations, summaries, or extra text outside the structured statements.  

            Text for analysis:  

            {text}

        """
    
    def _process_response_old(self, response: Any) -> List[Relationship]:
        """Process the model's response and create Relationship objects.
        
        Expects lines in format: "[Variable A <Type>] [relationship type] [Variable B <Type>]"
        Example: "[temperature <property>] increases [crystallinity <property>]"
        """
        relationships = []
        raw_text = response if isinstance(response, str) else response.choices[0].message.content
        
        # Process each line
        for line in raw_text.split('\n'):
            line = line.strip()
            if not line or not line.startswith('['):
                continue
                
            try:
                # Extract subject entity and type
                subj_end = line.find(']')
                if subj_end == -1:
                    continue
                    
                subject_part = line[1:subj_end]  # Remove outer brackets
                name_type = subject_part.split('<')
                if len(name_type) != 2:
                    continue
                
                subject_name = name_type[0].strip()
                subject_type = name_type[1].replace('>', '').strip()
                
                # Get remaining text after subject
                remaining = line[subj_end + 1:].strip()
                
                # Find object part
                obj_start = remaining.find('[')
                if obj_start == -1:
                    continue
                    
                # Extract relationship type
                relation = remaining[:obj_start].strip()
                
                # Extract object and its type
                obj_part = remaining[obj_start + 1:].rstrip(']')
                name_type = obj_part.split('<')
                if len(name_type) != 2:
                    continue
                
                object_name = name_type[0].strip()
                object_type = name_type[1].replace('>', '').strip()
                
                # Create Entity objects
                subject = Entity(
                    text=subject_name,
                    type=EntityType(subject_type.lower())
                )
                
                object_ = Entity(
                    text=object_name,
                    type=EntityType(object_type.lower())
                )
                
                # Map relationship type
                if relation == "positively correlates with":
                    rel_type = RelationType.POSITIVELY_CORRELATES
                elif relation == "negatively correlates with":
                    rel_type = RelationType.NETAIVELY_CORELATES
                else:
                    rel_type = RelationType(relation)
                
                # Create and add relationship
                relationship = Relationship(
                    subject=subject,
                    object=object_,
                    relation_type=rel_type
                )
                relationships.append(relationship)
                
            except (ValueError, IndexError) as e:
                continue  # Skip malformed lines
        
        return relationships
    
    def _process_response(self, response: Any):
        return parse_relationships(response), response

