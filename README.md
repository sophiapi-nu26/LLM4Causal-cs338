# Materials Science Causal Discovery with LLMs

A Python package for extracting causal relationships from materials science literature using Large Language Models.

## Pipeline Overview

The extraction pipeline consists of several sophisticated steps to identify and extract causal relationships from materials science literature:

### 1. PDF Processing and Text Extraction
- **Input**: Raw PDF documents
- **Process**:
  - Extract text while preserving structural information
  - Handle scientific notation and special characters
  - Identify document sections (abstract, methods, results, etc.)
  - Clean and normalize text
- **Output**: Structured text segments with metadata

### 2. Advanced Sentence Parsing
- **Input**: Processed text segments
- **Process**:
  - Split text into sentences using scientific text-aware rules
  - Handle complex scientific sentences with multiple clauses
  - Preserve context across sentence boundaries
  - Identify citation patterns and references
- **Output**: List of well-formed sentences with context

### 3. Entity Recognition (SciBERT)
- **Input**: Individual sentences
- **Process**:
  - Identify materials science entities using SciBERT
  - Classify entities into categories:
    * Materials (e.g., "silk fibroin", "hydroxyapatite")
    * Properties (e.g., "tensile strength", "crystallinity")
    * Processes (e.g., "annealing", "electrospinning")
    * Conditions (e.g., "temperature", "pH")
    * Structures (e.g., "β-sheet", "nanofibers")
  - Resolve entity references and aliases
- **Output**: List of typed entities with positions and metadata

### 4. Relationship Extraction (LLM)
- **Input**: Sentences with identified entities
- **Process**:
  - Use LLM to identify causal relationships
  - Support multiple model backends:
    * FLAN-T5 (default, CPU-friendly)
    * Dolly v2 (better accuracy, GPU required)
    * OpenAI GPT (optional, API key required)
  - Classify relationship types:
    * Increases/Decreases
    * Causes
    * Correlates with
  - Assign confidence scores
  - Extract supporting evidence
- **Output**: Structured relationship data with evidence

### 5. Graph Construction
- **Input**: Entities and relationships
- **Process**:
  - Build directed graph of causal relationships
  - Merge duplicate entities and relationships
  - Calculate relationship strengths
  - Identify key nodes and pathways
- **Output**: NetworkX graph and CSV edge list

### 6. Output Generation
- Formats:
  * JSON for programmatic access
  * GraphML for visualization
  * CSV for spreadsheet analysis
  * Summary reports in markdown
- Include:
  * Entity details and classifications
  * Relationship types and strengths
  * Confidence scores
  * Supporting evidence and citations
  * Metadata and provenance

## Features

- PDF processing and text extraction
- Advanced sentence parsing for scientific text
- Entity recognition using SciBERT
- Flexible LLM backend system (supports multiple models)
- Causal relationship extraction
- Graph-based relationship visualization

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install package in development mode
pip install -e ".[dev]"
```

## Quick Start

```python
from matsci_llm_causality import CausalityExtractor

# Initialize with desired backend
extractor = CausalityExtractor(model="flan-t5")

# Process a PDF
results = extractor.process_pdf("path/to/paper.pdf")

# View results
print(f"Found {len(results.entities)} entities and {len(results.relationships)} relationships")
```

## Project Structure

```
matsci_llm_causality/
├── src/
│   └── matsci_llm_causality/
│       ├── extraction/           # Core extraction modules
│       │   ├── pdf.py           # PDF processing
│       │   ├── entities.py      # Entity recognition
│       │   └── relations.py     # Relationship extraction
│       ├── models/              # Model implementations
│       │   ├── scibert.py       # SciBERT for NER
│       │   └── llm/            # LLM backends
│       │       ├── base.py      # Base LLM interface
│       │       ├── flan.py      # FLAN-T5 implementation
│       │       └── dolly.py     # Dolly implementation
│       ├── schema/              # Data models
│       │   ├── entities.py      # Entity definitions
│       │   └── relations.py     # Relationship definitions
│       └── visualization/       # Visualization tools
├── tests/                       # Test suite
├── examples/                    # Usage examples
├── notebooks/                   # Analysis notebooks
└── data/                       # Sample data & model configs
    ├── sample_papers/          # Example papers
    └── model_configs/          # Model configurations
```

## Available Models

1. **FLAN-T5** (Default)
   - Lightweight, runs on CPU
   - Good balance of speed and accuracy

2. **Dolly v2**
   - More sophisticated, requires GPU
   - Better understanding of scientific text

3. **OpenAI GPT** (Optional)
   - Requires API key
   - Best performance but not open source

## Pipeline Configuration and Usage

### Configuration Options

1. **PDF Processing**
```python
from matsci_llm_causality import CausalityExtractor

# Configure PDF processing
extractor = CausalityExtractor(
    pdf_config={
        "extract_sections": True,     # Enable section detection
        "handle_tables": True,        # Extract tables from PDF
        "ocr_fallback": False,       # Use OCR for problematic PDFs
        "preserve_layout": True       # Maintain document structure
    }
)
```

2. **Entity Recognition**
```python
# Configure SciBERT entity recognition
extractor = CausalityExtractor(
    ner_config={
        "model": "allenai/scibert_scivocab_uncased",
        "threshold": 0.75,           # Confidence threshold
        "batch_size": 32,           # Batch size for processing
        "max_length": 512,          # Maximum sequence length
        "entity_types": [           # Entity types to extract
            "material",
            "property",
            "process",
            "condition",
            "structure"
        ]
    }
)
```

3. **Relationship Extraction**
```python
from matsci_llm_causality import ModelConfig

# Configure LLM relationship extraction
config = ModelConfig(
    model_type="flan-t5",
    temperature=0.7,              # Control randomness
    max_length=512,              # Maximum input length
    device="cuda",               # Use GPU if available
    batch_size=8,               # Process multiple inputs
    additional_config={
        "min_confidence": 0.6,   # Minimum confidence threshold
        "max_relations": 5,      # Max relations per sentence
        "context_window": 3      # Sentences of context to include
    }
)

extractor = CausalityExtractor(model_config=config)
```

### Usage Examples

1. **Basic Usage**
```python
from matsci_llm_causality import CausalityExtractor

extractor = CausalityExtractor()
results = extractor.process_pdf("paper.pdf")
```

2. **Custom Model Configuration**
```python
from matsci_llm_causality import CausalityExtractor, ModelConfig

config = ModelConfig(
    model_type="flan-t5",
    temperature=0.7,
    max_length=512
)

extractor = CausalityExtractor(model_config=config)
```

3. **Batch Processing**
```python
from matsci_llm_causality import batch_process

results = batch_process(
    pdf_dir="papers/",
    output_dir="results/",
    model="dolly"
)
```

## Advanced Usage and Customization

### 1. Custom Entity Types

Add your own entity types and patterns:
```python
from matsci_llm_causality import EntityType, EntityPattern

# Define custom entity types
custom_types = {
    "COMPOSITE": EntityType(
        name="composite_material",
        patterns=[
            EntityPattern("silk-*", "Silk-based composites"),
            EntityPattern("*-reinforced *", "Reinforced materials")
        ],
        parent_type="material"
    )
}

extractor = CausalityExtractor(custom_entity_types=custom_types)
```

### 2. Pipeline Hooks

Add custom processing steps:
```python
from matsci_llm_causality import PipelineHook

class CustomPreprocessor(PipelineHook):
    def before_extraction(self, text: str) -> str:
        # Custom preprocessing logic
        return processed_text

extractor = CausalityExtractor(
    hooks=[CustomPreprocessor()]
)
```

### 3. Output Customization

Configure output formats and filters:
```python
# Process PDF with custom output settings
results = extractor.process_pdf(
    "paper.pdf",
    output_config={
        "formats": ["json", "graphml", "csv"],
        "confidence_threshold": 0.7,
        "include_evidence": True,
        "group_by_section": True,
        "merge_similar_entities": True
    }
)
```

## Contributing

### Setting Up Development Environment

1. Clone and setup:
```bash
# Clone repository
git clone https://github.com/yourusername/matsci_llm_causality.git
cd matsci_llm_causality

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install development dependencies
pip install -e ".[dev]"
```

2. Run tests:
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_pdf_processing.py

# Run with coverage
pytest --cov=matsci_llm_causality tests/
```

3. Code Style:
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
ruff src/ tests/
```

4. Submit Changes:
- Fork the repository
- Create a feature branch
- Make your changes
- Ensure tests pass
- Submit a pull request

### Project Structure
```
matsci_llm_causality/
├── src/matsci_llm_causality/    # Main package
│   ├── extraction/              # Extraction modules
│   │   ├── pdf.py              # PDF processing
│   │   └── relations.py        # Relationship extraction
│   ├── models/                 # Model implementations
│   │   ├── scibert.py         # SciBERT for NER
│   │   └── llm/               # LLM backends
│   └── schema/                 # Data models
├── tests/                      # Test suite
├── examples/                   # Usage examples
└── notebooks/                  # Analysis notebooks
```

## License

MIT License - see LICENSE file for details
