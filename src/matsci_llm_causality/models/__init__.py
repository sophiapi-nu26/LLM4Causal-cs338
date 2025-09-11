"""
Models package for materials science LLM causality extraction.
"""

from typing import Dict, Type, Any, Optional
from abc import ABC, abstractmethod

from ..schema import ModelConfig, ExtractionResult
from .base import (
    BaseLLM,
    create_model, 
    list_models,
    register_model
)
from .llm.flan import FlanT5Model
from .llm.gpt import GPT5RelationExtractor
from .scibert import SciBERTEntityRecognizer

__all__ = [
    'BaseLLM',
    'create_model',
    'list_models',
    'register_model',
    'FlanT5Model',
    'GPT5RelationExtractor',
    'SciBERTEntityRecognizer',
    'ModelConfig',
    'ExtractionResult',
    'LlamaRelationExtractor',
]

# Dictionary of available models
available_models: Dict[str, Type[BaseLLM]] = {}

class BaseLLM(ABC):
    """Abstract base class for LLM implementations."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize the LLM.
        
        Args:
            config: Optional model configuration
        """
        self.config = config or ModelConfig(model_type=self.__class__.__name__)
    
    @abstractmethod
    def extract_relations(self, text: str, batch_size: Optional[int] = None) -> ExtractionResult:
        """
        Extract relationships from text.
        
        Args:
            text: Input text to process
            batch_size: Optional batch size for processing
            
        Returns:
            Extraction results
        """
        pass
    
    @abstractmethod
    def _prepare_prompt(self, text: str) -> str:
        """
        Prepare the prompt for the model.
        
        Args:
            text: Input text
            
        Returns:
            Formatted prompt
        """
        pass
    
    @abstractmethod
    def _process_response(self, response: Any) -> ExtractionResult:
        """
        Process the model's response.
        
        Args:
            response: Raw model output
            
        Returns:
            Processed extraction results
        """
        pass

class ModelFactory:
    """Factory for creating LLM instances."""
    
    _models: Dict[str, type[BaseLLM]] = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a model implementation."""
        def decorator(model_cls: type[BaseLLM]) -> type[BaseLLM]:
            cls._models[name] = model_cls
            return model_cls
        return decorator
    
    @classmethod
    def create(cls, model_type: str, config: Optional[ModelConfig] = None) -> BaseLLM:
        """
        Create an instance of the specified model.
        
        Args:
            model_type: Name of the model to create
            config: Optional model configuration
            
        Returns:
            Instantiated model
            
        Raises:
            ValueError: If model_type is not registered
        """
        if model_type not in cls._models:
            raise ValueError(f"Unknown model type: {model_type}")
        
        model_cls = cls._models[model_type]
        return model_cls(config)
    
    @classmethod
    def list_models(cls) -> list[str]:
        """Get list of available models."""
        return list(cls._models.keys())
