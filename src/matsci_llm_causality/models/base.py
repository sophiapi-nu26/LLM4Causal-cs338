"""
Model base classes and registry.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type
import torch

from ..schema import ModelConfig, ExtractionResult

class BaseLLM(ABC):
    """Abstract base class for LLM implementations."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the LLM."""
        self.config = config or ModelConfig(model_type=self.__class__.__name__)
    
    @abstractmethod
    def extract_relations(self, text: str, batch_size: Optional[int] = None) -> ExtractionResult:
        """Extract relationships from text."""
        pass
    
    @abstractmethod
    def _prepare_prompt(self, text: str) -> str:
        """Prepare the prompt for the model."""
        pass
    
    @abstractmethod
    def _process_response(self, response: Any) -> ExtractionResult:
        """Process the model's response."""
        pass

# Global model registry
_models: Dict[str, Type[BaseLLM]] = {}

def register_model(name: str):
    """Decorator to register a model implementation."""
    def decorator(model_cls: Type[BaseLLM]) -> Type[BaseLLM]:
        _models[name] = model_cls
        return model_cls
    return decorator

def create_model(model_type: str, config: Optional[ModelConfig] = None) -> BaseLLM:
    """Create an instance of the specified model."""
    if model_type not in _models:
        raise ValueError(f"Unknown model type: {model_type}")
    
    if config is None:
        config = ModelConfig(
            model_type = model_type,
            temperature=1.0,
            max_length=512,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
    
    model_cls = _models[model_type]
    return model_cls(config)

def list_models() -> list[str]:
    """Get list of available models."""
    return list(_models.keys())
