from typing import Optional, Any, List
from google import genai
from google.genai import types, errors
from ...schema import (
    ExtractionResult, ModelConfig, Entity, EntityType,
    Relationship, RelationType
)
import time, random
from ..base import register_model, BaseLLM
from ...prompts import load_prompt
from dotenv import load_dotenv
import os
load_dotenv()

import re
import json
def parse_relationships(text: str):
    # Split text into lines, stripping empty ones
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    pattern = r"""
    ^\s*
    (.+?)\s*                              # Variable A
    (?:<|\[)(.*?)(?:>|\])\s+              # <TypeA> or [TypeA]
    (                                     # Relation
    increases|decreases|increase|decrease|causes|
    (?:positively|negatively)\s+correlate(?:s)?\s+with
    )\s+
    (.+?)\s*                              # Variable B
    (?:<|\[)(.*?)(?:>|\])\s*              # <TypeB> or [TypeB]
    $
    """
    
    results = []
    for line in lines:
        # Regex to capture: [SubjectName][Type] relationship [ObjectName][Type]
        match = re.match(pattern, line, re.VERBOSE)
        if match:
            subject_name, subject_type, relation, object_name, object_type = match.groups()
            results.append({
                "subject": {"name": subject_name.strip(), "type": subject_type.strip()},
                "relationship": relation.strip(),
                "object": {"name": object_name.strip(), "type": object_type.strip()}
            })
    return results


def call_with_backoff(fn, *, max_retries=6):
    delay = 1.0
    for _ in range(max_retries):
        try:
            return fn()
        except errors.ClientError as e:
            # 429: too fast or too big; slow down and retry
            if getattr(e, "status_code", None) == 429:
                wait = _extract_retry_after_seconds(e) or delay
                time.sleep(wait + random.random())  # small jitter
                delay = min(delay * 2, 16)  # cap backoff
                continue
            raise
    raise RuntimeError("Exceeded max_retries due to repeated 429s.")

def _extract_retry_after_seconds(e):
    try:
        details = e.response_json["error"].get("details", [])
        for d in details:
            if d.get("@type","").endswith("RetryInfo"):
                val = d.get("retryDelay","0s").rstrip("s")  # e.g., "5s"
                return float(val)
    except Exception:
        pass
    return None

api_key = os.getenv('GEMINI_API_KEY')  # This gets a specific variable


# Image relation extractor using Gemini
@register_model("gemini-2-5-flash-lite")  # Match the ID used in process_pdf.py
class GeminiImageRelationExtractor(BaseLLM):
    def __init__(self, config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_type="gemini-2-5-flash-lite",
                temperature=0,
                # max_length=512
            )
        self.config = config
        self.client = genai.Client()
        
    def extract_relations(self, image_bytes) -> List[Relationship]:
        """Extract causal relationships between existing entities using GPT-5.
        
        Args:
            image_bytes: The image data to analyze
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt_text = self._prepare_prompt(image_bytes)
        cfg = types.GenerateContentConfig(
                    temperature=0,
                    # max_output_tokens=256,  # keep this modest
                )
        
        response = call_with_backoff(lambda:
                                     self.client.models.generate_content(
                                        model='gemini-2.5-flash',
                                        contents=[
                                        types.Part.from_bytes(data=image_bytes,mime_type='image/png'),
                                        types.Part.from_text(text=prompt_text)
                                        ],
                                        config=cfg
                                    )
                    )
        
        
        return self._process_response(response.text)

    def _prepare_prompt(self, image_bytes) -> str:
        """Prepare the prompt for relationship extraction."""
        return load_prompt("image_relation_extraction.txt")
    
    def _process_response(self, response: Any) -> List[Relationship]:
        """Process the model's response and create Relationship objects.
        
        Expects lines in format: "[Variable A <Type>] [relationship type] [Variable B <Type>]"
        Example: "[temperature <property>] increases [crystallinity <property>]"
        """
        original_response = response
        parsed = parse_relationships(response)
        return parsed, original_response
    

@register_model("gemini-2-5-flash-table")  # Match the ID used in process_pdf.py
# Table relation extractor using Gemini
class GeminiTableRelationExtractor(BaseLLM):
    def __init__(self, config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_type="gemini-2-5-flash-table",
                temperature=0.3,
                # max_length=512
            )
        self.config = config
        self.client = genai.Client()
        
    def extract_relations(self, image_bytes) -> List[Relationship]:
        """Extract causal relationships between existing entities using GPT-5.
        
        Args:
            image_bytes: The table data
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt_text = self._prepare_prompt(image_bytes)

        cfg = types.GenerateContentConfig(
                    temperature=0,
                    # max_output_tokens=256,  # keep this modest
                )
        
        response = call_with_backoff(lambda: self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
            types.Part.from_bytes(
            data=image_bytes,
            mime_type='text/html',
            ),
            types.Part.from_text(text=prompt_text)],
            config=cfg
        )
        )

        return self._process_response(response.text)

    def _prepare_prompt(self, image_bytes) -> str:
        """Prepare the prompt for relationship extraction."""
        return load_prompt("table_relation_extraction.txt")
    
    def _process_response(self, response: Any) -> List[Relationship]:
        """Process the model's response and create Relationship objects.
        
        Expects lines in format: "[Variable A <Type>] [relationship type] [Variable B <Type>]"
        Example: "[temperature <property>] increases [crystallinity <property>]"
        """
        return parse_relationships(response), response


@register_model("gemini-text-relation")
class GeminiTextRelationExtractor(BaseLLM):
    """Text-based relation extraction using Google Gemini for materials science text."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the Gemini text relation extractor.
        
        Args:
            config: Model configuration
        """
        if config is None:
            config = ModelConfig(
                model_type="gemini-2.5-flash",
                temperature=0.3,
            )
        
        self.config = config
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client()
        
    def extract_relations(self, text: str) -> List[Relationship]:
        """Extract causal relationships from text using Gemini.
        
        Args:
            text: Input text to extract relationships from
            
        Returns:
            List of extracted relationships
        """
        prompt = self._prepare_prompt(text)
        
        try:
            response = call_with_backoff(lambda: self.client.models.generate_content(
                model=self.config.model_type,
                contents=[prompt]
            ))
            # DEBUG: remove later
            print(response.text)
            return self._process_response(response.text)
        except Exception as e:
            print(f"Error in Gemini text extraction: {e}")
            return []
    
    def _prepare_prompt(self, text: str) -> str:
        """Prepare the prompt for relationship extraction."""
        return load_prompt("text_relation_extraction.txt", text=text)
    
    def _process_response(self, response: str) -> List[Relationship]:
        """Process the model's response and create Relationship objects.
        
        Expects lines in format: "[Variable A <Type>] [relationship type] [Variable B <Type>]"
        Example: "[temperature <property>] increases [crystallinity <property>]"
        """
        return parse_relationships(response), response