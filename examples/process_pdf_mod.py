"""
Example script demonstrating PDF processing and relation extraction.
"""

from pathlib import Path
import sys
import json

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
    figure_relation_extractor = create_model("gemini-2-5-flash-lite")
    table_relation_extractor = create_model("gemini-2-5-flash-table")

    # Path to your PDF
    pdf_path = Path("../tests/data/sciadv.abo6043.pdf")  # Replace with your PDF path
    
    # breakpoint()

    # 1. Extract text from PDF
    # print("Extracting text from PDF...")
    # text = pdf_processor.extract_text(pdf_path, grobid_url="http://localhost:8070", outdir="./temp/text")
    
    # breakpoint()

    # 1.a Extract figures
    # print("Extracting figures from PDF...")
    # fig_output_dir = Path("./temp/figures")
    # figures = pdf_processor.extract_figures(pdf_path, output_dir=fig_output_dir)

    # breakpoint()

    # 1.b Extract tables
    # print("Extracting tables from PDF...")
    # table_output_dir = Path("./temp/tables")
    # tables = pdf_processor.extract_tables(pdf_path, output_dir=table_output_dir)

    # breakpoint()

    # 3. Extract relationships from figures
    fig = './temp/figures/sciadv.abo6043-figure-5.png'
    with open(fig, 'rb') as f:
        image_bytes = f.read()
    fig_relations, fig_relations_txt = figure_relation_extractor.extract_relations(image_bytes)

    with open('./temp/figure_relations.json', 'w', encoding='utf-8') as f:
        json.dump(fig_relations, f)

    with open('./temp/figure_relations.txt', 'w', encoding='utf-8') as f:
        f.write(fig_relations_txt)

    breakpoint()
        
    # 4. Extract relationships from tables
    table = "./temp/tables/sciadv.abo6043-table-1.html"
    with open(table, 'rb') as f:
        table_bytes = f.read()
    table_relations, table_relations_txt = table_relation_extractor.extract_relations(table_bytes)

    with open('./temp/table_relations.json', 'w', encoding='utf-8') as f:
        json.dump(table_relations, f)

    with open('./temp/table_relations.txt', 'w', encoding='utf-8') as f:
        f.write(table_relations_txt)

if __name__ == "__main__":
    breakpoint()
    main()
