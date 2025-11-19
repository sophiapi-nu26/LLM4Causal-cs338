# CAMEL: Causal Analysis of Materials Extracted from Literature

A Python package for extracting causal relationships from materials science literature using Large Language Models.

## Quick Links

- **[REST API Documentation](src/README.md)** - Containerized API for article retrieval and parsing
- **[Deployment Guide](src/DEPLOYMENT.md)** - Deploy to Google Cloud Run
- **[Dockerfile Comparison](src/DEPLOYMENT.md#dockerfiledev-vs-dockerfile---key-differences-explained)** - Dev vs Production explained

## Pipeline Overview

The extraction pipeline consists of several sophisticated steps to identify and extract causal relationships from materials science literature:

### 1. Article Collection & Retrieval API

Fully containerized REST API for retrieving and parsing scientific papers with asynchronous job processing.

- **Input**: Natural language query (e.g., "spider silk mechanical properties")
- **Process**:
  - Search OpenAlex API for relevant papers using query-based retrieval
  - Automatic relevance ranking and filtering (by year, citations, open access)
  - Download PDFs from multiple sources (Semantic Scholar, OpenAlex, Unpaywall)
  - Parse PDFs and extract structured text
  - Upload to Google Cloud Storage
- **Output**: Parsed paper data with full text, sections, and metadata
- **Access**:
  - **REST API** (Recommended): `POST /api/v1/retrieve` - See [API Documentation](src/README.md)
  - **CLI Tool**: `python article_retriever.py --query "your query"` (Legacy)
- **Deployment**: Docker-based deployment to Google Cloud Run - See [Deployment Guide](src/DEPLOYMENT.md)

### 2. PDF Processing and Text Extraction
- **Input**: Raw PDF documents
- **Process**:
  - Extract text save as text file using GROBID
  - Extract Figures into PNG files and tables into html files respectively using Dockling
- **Output**: Extracted data into text file, PNG file and html file

### 3. Entity and relationship Recognition (Gemini2.5 + GPT4o)
- **Input**: Extracted text, figures (png), and table (html) files
- **Process**:
  - Identify materials science entities using LLMs (access through API)
  - Classify entities into categories:
    * Materials (e.g., "silk fibroin", "hydroxyapatite")
    * Properties (e.g., "tensile strength", "crystallinity")
    * Processes (e.g., "annealing", "electrospinning")
    * Conditions (e.g., "temperature", "pH")
    * Structures (e.g., "β-sheet", "nanofibers")
  - Identify relations between entities. Categorize relations between entities as:
    * Increase
    * Decrese
    * cause
    * positively correlate with
    * negatively correlate with
  - Use GPT4o model to process the text and Gemini2.5 for processing figures and tables
- **Output**: A JSON file that stores the relations as "subject" entity, "object" entity and type of relationship

### 5. Graph Construction
- **Input**: JSON file with Entities and relationships
- **Process**:
  - Build directed graph of causal relationships
  - Merge duplicate entities and relationships
  - Calculate relationship strengths
  - Identify key nodes and pathways
- **Output**: NetworkX graph in graphml format

### 6. Output Generation
- Formats:
  * JSON for programmatic access
  * GraphML for visualization
- Include:
  * Entity details and classifications
  * Relationship types and strengths
  * Confidence scores


## Features

- PDF processing and text extraction
- Advanced sentence/figures/tables parsing for scientific text
- Entity recognition using LLMs (GPT4o + Gemini2.5)
- Flexible LLM backend system (supports multiple models)
- Causal relationship extraction
- Graph-based relationship visualization

## Installation
Prerequisite - install Docker desktop and add it to PATH. This is required for GROBID to perform text extraction.

```bash
# If using python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# If you use Conda
conda create -n [name_of_env] python=3.11

# Install package in development mode
pip install -e ".[dev]"
```


## Project Structure

```
matsci_llm_causality/
├── src/
│   └── matsci_llm_causality/
│       ├── extraction/           # Core extraction modules
│       │   ├── pdf.py           # PDF processing
│       │   ├── grobid.py        # GROBID setup file for text extraction
│       │   └── relations.py     # Relationship extraction
│       ├── models/              # Model implementations
│       │   ├── base.py          # Base LLM interface
│       │   └── llm/             # LLM backends
│       │       └── GPT.py       # GPT API implementation
|       |       └── gemini.py    # gemini API implementation
│       ├── schema/              # Data models for entities and relations
├── tests/                       # Test suite
├── examples/                    # Usage examples and evaluation for test case
└── data/                       # Sample data 
    ├── sample_papers (pdfs)          # Example papers
```

## Available Models

1. **OpenAI GPT4o** 
   - Requires API key

2. **Google Gemini2.5 flash** 
   - Requires API key


### Usage Examples
Please refer to process_pdf.py for Usage examples.

## License

MIT License - see LICENSE file for details
