"""
Tests for entity recognition using SciBERT.
"""

import pytest
from pathlib import Path
import torch
from src.matsci_llm_causality.models.scibert import SciBERTEntityRecognizer
from src.matsci_llm_causality.models.llm.gpt import GPT5EntityRecognizer
from src.matsci_llm_causality.schema import EntityType

# Test samples with known entities
TEST_SAMPLES = [
    {
        "text": "Silk fibroin exhibits increased crystallinity at higher temperatures.",
        "entities": [
            {"text": "Silk fibroin", "type": EntityType.MATERIAL},
            {"text": "crystallinity", "type": EntityType.PROPERTY},
            {"text": "temperatures", "type": EntityType.CONDITION}
        ]
    },
    {
        "text": "Beta-sheet content affects the mechanical properties through hydrogen bonding.",
        "entities": [
            {"text": "Beta-sheet content", "type": EntityType.STRUCTURE},
            {"text": "mechanical properties", "type": EntityType.PROPERTY}
        ]
    }
]

@pytest.fixture
def entity_recognizer():
    """Fixture for SciBERT entity recognizer."""
    return GPT5EntityRecognizer()

def test_entity_recognition_basic(entity_recognizer):
    """Test basic entity recognition capabilities."""
    for sample in TEST_SAMPLES:
        entities = entity_recognizer.extract_entities(sample["text"])
        assert entities
        
        # Check if all expected entities are found
        found_texts = [e.text.lower() for e in entities]
        expected_texts = [e["text"].lower() for e in sample["entities"]]
        
        for expected in expected_texts:
            assert any(expected in found for found in found_texts)

def test_entity_type_classification(entity_recognizer):
    """Test correct classification of entity types."""
    text = "Silk fibroin shows improved mechanical properties after annealing at 60°C."
    entities = entity_recognizer.extract_entities(text)
    
    # Check specific entities
    materials = [e for e in entities if e.type == EntityType.MATERIAL]
    assert any("silk fibroin" in e.text.lower() for e in materials)
    
    properties = [e for e in entities if e.type == EntityType.PROPERTY]
    assert any("mechanical properties" in e.text.lower() for e in properties)
    
    processes = [e for e in entities if e.type == EntityType.PROCESS]
    assert any("annealing" in e.text.lower() for e in processes)

def test_overlapping_entities(entity_recognizer):
    """Test handling of overlapping entity mentions."""
    text = "The silk fibroin hydrogel shows good biocompatibility."
    entities = entity_recognizer.extract_entities(text)
    
    # Should identify both "silk fibroin" and "silk fibroin hydrogel"
    materials = [e for e in entities if e.type == EntityType.MATERIAL]
    material_texts = [e.text.lower() for e in materials]
    assert "silk fibroin" in material_texts or "silk fibroin hydrogel" in material_texts

def test_batch_processing(entity_recognizer):
    """Test batch processing of multiple texts."""
    texts = [sample["text"] for sample in TEST_SAMPLES]
    results = entity_recognizer.batch_extract_entities(texts)
    
    assert len(results) == len(texts)
    for entities in results:
        assert entities  # Each text should have some entities

def test_confidence_scores(entity_recognizer):
    """Test entity confidence scores."""
    text = "Silk fibroin was processed using electrospinning."
    entities = entity_recognizer.extract_entities(text)
    
    for entity in entities:
        assert hasattr(entity, "confidence")
        assert 0 <= entity.confidence <= 1

def test_entity_metadata(entity_recognizer):
    """Test additional entity metadata."""
    text = "The beta-sheet structure increased from 20% to 45%."
    entities = entity_recognizer.extract_entities(text)
    
    for entity in entities:
        if "beta-sheet" in entity.text.lower():
            assert entity.metadata.get("percentage_mentioned")

def test_error_handling(entity_recognizer):
    """Test handling of edge cases and errors."""
    # Empty text
    entities = entity_recognizer.extract_entities("")
    assert entities == []
    
    # Very long text
    long_text = "silk fibroin " * 1000
    entities = entity_recognizer.extract_entities(long_text)
    assert entities
    
    # Special characters
    special_text = "β-sheet structure in silk-chitosan/PEO blend"
    entities = entity_recognizer.extract_entities(special_text)
    assert entities

def test_gpu_support(entity_recognizer):
    """Test GPU support if available."""
    if torch.cuda.is_available():
        entity_recognizer_gpu = SciBERTEntityRecognizer(device="cuda")
        entities = entity_recognizer_gpu.extract_entities(TEST_SAMPLES[0]["text"])
        assert entities
