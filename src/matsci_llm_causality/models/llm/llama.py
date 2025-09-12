from ...schema import (
    ExtractionResult, ModelConfig, Entity, EntityType,
    Relationship, RelationType
)
from ..base import register_model, BaseLLM
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from typing import Optional, List
import torch
from huggingface_hub import login

model = "meta-llama/Llama-3.1-8B-Instruct"
token = "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" # Jacob's HuggingFace token for Llama-3.1
login(token)

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
        # self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct", use_auth_token=token)
        # self.model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B-Instruct", use_auth_token=token)
        self.pipe = pipeline("text-generation",
                             model=model,
                             torch_dtype=torch.float32)



    def extract_relations(self, text: str) -> List[Relationship]:
        """Extract causal relationships between existing entities using Llama-3.
        
        Args:
            text: The source text to analyze
            
        Returns:
            List of relationships found between the provided entities
        """
        prompt = self._prepare_prompt(text)
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
            }]
        # inputs = self.tokenizer.apply_chat_template(
        #     messages,
        #     add_generation_prompt=True,
        #     tokenize=True,
        #     return_dict=True,
        #     return_tensors="pt",
        # ).to(self.model.device)

        # outputs = model.generate(**inputs, max_new_tokens=40)
        # print(self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]))

        output = self.pipe(
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
            }]
        )
        response = output[0]['generated_text']

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

    def _process_response(self, response: Any) -> List[Relationship]:
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