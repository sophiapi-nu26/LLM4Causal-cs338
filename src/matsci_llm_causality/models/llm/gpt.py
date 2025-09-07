from typing import Optional, Any
from openai import OpenAI
from ...schema import ExtractionResult, ModelConfig
from ..base import register_model, BaseLLM

@register_model("gpt5-nano")  # Match the ID used in process_pdf.py
class GPT5RelationExtractor(BaseLLM):
    def __init__(self, config: Optional[ModelConfig] = None):
        if config is None:
            config = ModelConfig(
                model_type="gpt-5-nano",
                temperature=0.7,
                max_length=512
            )
        self.config = config
        self.client = OpenAI()  # Uses OPENAI_API_KEY environment variable
        
    def extract_relations(self, text: str) -> ExtractionResult:
        """Extract causal relationships using GPT-5."""
        prompt = f"""Extract causal relationships from the following materials science text. 
        For each relationship, identify the subject, object, and type of relationship (increases, decreases, causes, correlates_with).
        
        Text: {text}
        
        Extract relationships in a structured format."""
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using GPT-3.5 Turbo model
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=self.config.temperature,
            max_tokens=self.config.max_length
        )
        
        # Parse response and convert to ExtractionResult
        # Implementation depends on how the model structures its output
        return self._process_response(response)
    
    def _prepare_prompt(self, text: str) -> str:
        """Prepare the prompt for the model."""
        return f"""Extract causal relationships from the following materials science text. 
        For each relationship, identify the subject, object, and type of relationship (increases, decreases, causes, correlates_with).
        
        Text: {text}
        
        Extract relationships in a structured format."""
    
    def _process_response(self, response: Any) -> ExtractionResult:
        """Process the model's response."""
        return ExtractionResult(
            entities=[],  # Parse entities from response
            relationships=[],  # Parse relationships from response
            metadata={"raw_response": response.choices[0].message.content}
        )