"""
Example script demonstrating PDF processing and relation extraction.
"""

from pathlib import Path
import sys

from dotenv import load_dotenv
import os

load_dotenv()  # This loads the variables from .env
api_key = os.getenv('OPENAI_API_KEY')  # This gets a specific variable

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

from matsci_llm_causality.extraction.pdf import PDFProcessor
from matsci_llm_causality.models import create_model

def main():
    # Initialize components
    pdf_processor = PDFProcessor()
    entity_recognizer = create_model("gpt-5-entity")
    relation_extractor = create_model("gpt-5-relation")

    # Path to your PDF
    pdf_path = Path("../tests/data/sciadv.abo6043.pdf")  # Replace with your PDF path
    
    breakpoint()

    # 1. Extract text from PDF
    print("Extracting text from PDF...")
    text = pdf_processor.extract_text(pdf_path, grobid_url="http://localhost:8070", outdir="./temp/text")
    
    breakpoint()

    # 1.a Extract figures
    print("Extracting figures from PDF...")
    fig_output_dir = Path("./temp/figures")
    figures = pdf_processor.extract_figures(pdf_path, output_dir=fig_output_dir)

    breakpoint()

    # 1.b Extract tables
    print("Extracting tables from PDF...")
    table_output_dir = Path("./temp/tables")
    tables = pdf_processor.extract_tables(pdf_path, output_dir=table_output_dir)

    breakpoint()

    # # 2. Extract entities using SciBERT
    # print("Extracting entities...")
    # entities = entity_recognizer.extract_entities(text)
    # print("\nFound entities:")
    # for entity in entities:
    #     print(f"- {entity.text} ({entity.type.value})")
    
    # # 3. Extract relationships using FLAN-T5
    # print("\nExtracting relationships...")
    # result = relation_extractor.extract_relations(text)
    
    # # 4. Print results
    # print("\nExtracted relationships:")
    # if result.relationships:
    #     for rel in result.relationships:
    #         print(f"- {rel}")
    # else:
    #     print("Raw FLAN-T5 response:")
    #     print(result.metadata["raw_response"])

if __name__ == "__main__":
    breakpoint()
    main()
