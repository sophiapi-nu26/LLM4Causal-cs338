# Monte Carlo Evidence-Based Causal Extraction

This module implements a sophisticated two-stage approach to causal relationship extraction that addresses the non-deterministic nature of LLM-based extraction through evidence gathering and mathematical graph construction.

## Overview

The traditional single-shot LLM approach has several limitations:
- **Non-deterministic outputs**: Different runs identify different variables and relationships
- **No evidence accumulation**: No mechanism to gather confidence or consistency
- **Variable inconsistency**: Different runs often identify different sets of variables

Our Monte Carlo approach solves these issues through:

1. **Stage 1**: Multiple runs with varying parameters to gather evidence
2. **Stage 2**: Entity consolidation using LLM-based clustering
3. **Stage 3**: Relationship validation and confidence scoring
4. **Mathematical causal graph construction** with centrality measures

## Key Features

### Evidence-Based Extraction
- **Multiple runs**: Configurable number of Monte Carlo runs (default: 5)
- **Temperature variation**: Slight temperature variations for diversity
- **Confidence scoring**: Frequency-based confidence measures
- **Entity consolidation**: LLM-based entity clustering and normalization

### Mathematical Graph Construction
- **Adjacency matrix**: Weighted graph representation with confidence scores
- **Centrality measures**: In-degree, out-degree, and betweenness centrality
- **Causal pathways**: Identification of important causal chains
- **Graph metrics**: Density, connectivity, and structural analysis

### Robust Entity Handling
- **Entity normalization**: Fuzzy string matching for similar entities
- **Variation tracking**: Track different names for the same entity
- **Type consistency**: Ensure entity types are consistent across runs
- **Confidence filtering**: Filter relationships below confidence threshold

## Usage

### Basic Usage

```python
from matsci_llm_causality.models.llm.monte_carlo_extractor import MonteCarloEvidenceExtractor
from matsci_llm_causality.models.llm.gemini import GeminiTextRelationExtractor

# Initialize components
base_extractor = GeminiTextRelationExtractor()
mc_extractor = MonteCarloEvidenceExtractor(
    base_extractor=base_extractor,
    n_runs=5,  # Number of Monte Carlo runs
    confidence_threshold=0.6,  # Require 60% agreement
    entity_similarity_threshold=0.8  # Entity name similarity threshold
)

# Extract relationships with evidence
result = mc_extractor.extract_relations_with_evidence(text)

# Build causal graph
causal_graph = mc_extractor.build_causal_graph(result)
```

### Advanced Configuration

```python
mc_extractor = MonteCarloEvidenceExtractor(
    base_extractor=base_extractor,
    n_runs=10,  # More runs for higher confidence
    confidence_threshold=0.7,  # Higher threshold for stricter filtering
    entity_similarity_threshold=0.85  # Stricter entity matching
)
```

## Data Structures

### MonteCarloResult
```python
@dataclass
class MonteCarloResult:
    entities: List[EntityEvidence]  # Consolidated entities with evidence
    relationships: List[RelationshipEvidence]  # Validated relationships
    raw_runs: List[List[Dict]]  # Raw data from each run
    metadata: Dict[str, Any]  # Extraction metadata
```

### EntityEvidence
```python
@dataclass
class EntityEvidence:
    canonical_name: str  # Primary entity name
    entity_type: EntityType  # Entity type (material, property, etc.)
    variations: List[str]  # All name variations found
    frequency: int  # How often this entity appeared
    confidence: float  # Confidence score (0-1)
```

### RelationshipEvidence
```python
@dataclass
class RelationshipEvidence:
    subject: EntityEvidence  # Subject entity with evidence
    object: EntityEvidence  # Object entity with evidence
    relation_type: RelationType  # Type of relationship
    frequency: int  # How often this relationship appeared
    confidence: float  # Confidence score (0-1)
    variations: List[Dict]  # All variations found
```

## Mathematical Graph Construction

The causal graph construction uses several mathematical concepts:

### Adjacency Matrix
- **Weighted edges**: Edge weights represent confidence scores
- **Directed graph**: Relationships have direction (A → B)
- **Sparse representation**: Only non-zero relationships are stored

### Centrality Measures
- **In-degree**: Number of incoming relationships (causes)
- **Out-degree**: Number of outgoing relationships (effects)
- **Betweenness centrality**: Importance as a bridge between entities

### Causal Pathways
- **Path identification**: Find important causal chains
- **Path ranking**: Rank paths by confidence and length
- **Cycle detection**: Identify potential causal loops

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_runs` | 5 | Number of Monte Carlo runs |
| `confidence_threshold` | 0.6 | Minimum confidence for relationships |
| `entity_similarity_threshold` | 0.8 | Threshold for entity name similarity |

## Performance Considerations

- **API costs**: More runs = higher API costs
- **Processing time**: Linear scaling with number of runs
- **Memory usage**: Stores all raw runs in memory
- **Confidence vs. speed**: Higher thresholds reduce false positives but may miss valid relationships

## Example Output

```
Consolidated Entities (4):
  1. temperature (property)
     Variations: temperature, thermal conditions
     Confidence: 0.80
  2. crystallinity (property)
     Variations: crystallinity, crystal structure
     Confidence: 0.90

Validated Relationships (3):
  1. temperature increases crystallinity
     Confidence: 0.80 (appeared in 4/5 runs)
  2. crystallinity increases tensile_strength
     Confidence: 0.60 (appeared in 3/5 runs)

Graph Statistics:
  Nodes: 4
  Edges: 3
  Density: 0.25

Top Causal Pathways:
  1. temperature → crystallinity → tensile_strength
```

## Comparison with Single-Run Approach

| Aspect | Single Run | Monte Carlo |
|--------|------------|-------------|
| Determinism | Low | High |
| Confidence | None | Quantified |
| Entity consistency | Poor | Good |
| False positives | High | Reduced |
| Processing time | Fast | Slower |
| API cost | Low | Higher |

## Future Enhancements

- **Ensemble methods**: Combine multiple LLM models
- **Semantic similarity**: Use embeddings for entity matching
- **Temporal relationships**: Handle time-dependent causality
- **Uncertainty quantification**: Bayesian confidence intervals
- **Graph learning**: Use graph neural networks for relationship validation
