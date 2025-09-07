"""
Basic tests for the package.
"""

import pytest
from matsci_llm_causality import CausalityExtractor, ModelConfig

def test_extractor_initialization():
    """Test basic initialization of the extractor."""
    config = ModelConfig(
        model_type="flan-t5",
        temperature=0.7,
        max_length=512
    )
    extractor = CausalityExtractor(model="flan-t5", model_config=config)
    assert extractor is not None

def test_model_config():
    """Test model configuration."""
    config = ModelConfig(
        model_type="flan-t5",
        temperature=0.7,
        max_length=512
    )
    assert config.temperature == 0.7
    assert config.max_length == 512
    assert config.device == "cpu"
