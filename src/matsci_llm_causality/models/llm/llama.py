from ...schema import (
    ExtractionResult, ModelConfig, Entity, EntityType,
    Relationship, RelationType
)
from ..base import register_model, BaseLLM
from transformers import pipeline
from typing import Optional, List
from transformers import AutoTokenizer, AutoModelForCausalLM

model = "meta-llama/Llama-3.1-8B-Instruct"
@register_model(model)
class LlamaRelationExtractor(BaseLLM):
    """Entity recognition using Llama model for materials science text."""

    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the Llama entity recognizer.
        
        Args:
            None
        """
        if config is None:
            config = ModelConfig(
                model_type= "meta-llama/Llama-3.1-8B-Instruct",
                temperature=0.3,
                # max_length=512
            )
        self.config = config
        # self.pipe = pipeline("text-generation",
        #                      model=model)
        self.tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(model, trust_remote_code=True)

    def extract_relations(self, text: str) -> List[Relationship]:
        """Extract causal relationships between existing entities using Llama-3.
        
        Args:
            text: The source text to analyze
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt = self._prepare_prompt(text)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_new_tokens=100)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        # response = self.pipe(
        #     model=model,
        #     messages=[{
        #         "role": "system",
        #         "content": """You are an expert at identifying causal relationships between entities in materials science text.
        #         For each relationship, identify:
        #         1. The subject entity: Name[Type(chosen from material, structure, process, property)]
        #         2. The type of relationship (increases, decreases, causes, positively correlate with, negatively correlate with)
        #         3. The object entity: Name[Type(chosen from material, structure, process, property)]
        #         """
        #     }, {
        #         "role": "user",
        #         "content": prompt
        #     }],
        #     trust_remote_code=True
        # )

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
            - Use the exact wording of the variables as they appear in the text (don’t paraphrase).  
            - Output one relationship per line. Do not number them. Relationships only.
            - Do not include explanations, summaries, or extra text outside the structured statements.  

            Text for analysis:  

            {text}

        """

        return response.choices[0].message.content