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
    # entity_recognizer = create_model("gpt-5-entity")
    relation_extractor = create_model("gpt-5-relation")

    # Path to your PDF
    pdf_path = Path("D:/Research/LLM4Causal/tests/data/sciadv.abo6043.pdf")  # Replace with your PDF path
    
    # 1. Extract text from PDF
    print("Extracting text from PDF...")
    text = pdf_processor.extract_text(pdf_path)
    print(f"Extracted {len(text)} characters\n")
    
    # 2. Extract entities using SciBERT
    # print("Extracting entities...")
    # entities = entity_recognizer.extract_entities(text)
    # print("\nFound entities:")
    # for entity in entities:
    #     print(f"- {entity.text} ({entity.type.value})")
    
    # 3. Extract relationships using Llama3
    print("\nExtracting relationships...")
    # Save the prompt from prompt.txt into a string variable.
    file_path = "prompt.txt"  # Replace with the actual path to your text file
    try:
        with open(file_path, 'r') as file:
            file_content = file.read()
        print("File content successfully read into variable:")
        print(file_content)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    relationships = relation_extractor.extract_relations(text)
    
    # 4. Print results
    print("\nExtracted relationships:")
    if relationships:
        for rel in relationships:
            print(f"- {rel}")
    else:
        print("No Relationships")

if __name__ == "__main__":
    main()
