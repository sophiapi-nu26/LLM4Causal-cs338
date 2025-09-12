"""
Example script demonstrating PDF processing and relation extraction.
"""

from pathlib import Path
import sys
import json

from dotenv import load_dotenv
import os
import shutil

load_dotenv()  # This loads the variables from .env
api_key = os.getenv('OPENAI_API_KEY')  # This gets a specific variable

# Add the src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

from matsci_llm_causality.extraction.pdf import PDFProcessor
from matsci_llm_causality.models import create_model

from json2graph import json_to_graphml

def ensure_empty_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)  # create if missing
    for child in p.iterdir():             # remove everything inside
        if child.is_dir():
            shutil.rmtree(child)
        else:  # files and symlinks
            child.unlink()

def main(pdf_filename: str | Path):
    # Initialize components
    pdf_processor = PDFProcessor()
    text_relation_extractor = create_model("gpt-5-relation")
    figure_relation_extractor = create_model("gemini-2-5-flash-lite")
    table_relation_extractor = create_model("gemini-2-5-flash-table")

    # Path to your PDF
    pdf_path = Path(pdf_filename)  # Replace with your PDF path

    # # Create necessary directories; empty if they already exist
    # ensure_empty_dir(Path("./temp/text"))
    # ensure_empty_dir(Path("./temp/figures"))
    # ensure_empty_dir(Path("./temp/tables"))

    # Path("./output").mkdir(parents=True, exist_ok=True)

    # # # 1. Extract text from PDF
    # print("Extracting text from PDF...")
    # text = pdf_processor.extract_text(pdf_path, grobid_url="http://localhost:8070", outdir="./temp/text")

    # # # 1.a Extract figures
    # print("Extracting figures from PDF...")
    fig_output_dir = Path("./temp/figures")
    # figures = pdf_processor.extract_figures(pdf_path, output_dir=fig_output_dir)

    # # # 1.b Extract tables
    # print("Extracting tables from PDF...")
    table_output_dir = Path("./temp/tables")
    # tables = pdf_processor.extract_tables(pdf_path, output_dir=table_output_dir)

    # 3. Extract relationships from figures
    print("Extracting relationships from figures...")
    fig_file_list = list(fig_output_dir.glob("*.png")) 
    all_fig_relations = []
    all_fig_relations_txt = ""
    for fig_file in fig_file_list:
        with open(fig_file, 'rb') as f:
            image_bytes = f.read()
        fig_relations, fig_relations_txt = figure_relation_extractor.extract_relations(image_bytes)
        all_fig_relations.extend(fig_relations)
        all_fig_relations_txt += fig_relations_txt + "\n"
    with open('./temp/figure_relations.txt', 'w', encoding='utf-8') as f:
        f.write(all_fig_relations_txt)
    with open('./temp/figure_relations.json', 'w', encoding='utf-8') as f:
        json.dump(all_fig_relations, f)

        
    # 4. Extract relationships from tables
    print("Extracting relationships from tables...")
    table_file_list = list(table_output_dir.glob("*.html"))
    all_table_relations = []
    all_table_relations_txt = ""
    for table_file in table_file_list:
        with open(table_file, 'rb') as f:
            table_bytes = f.read()
        table_relations, table_relations_txt = table_relation_extractor.extract_relations(table_bytes)
        all_table_relations.extend(table_relations)
        all_table_relations_txt += table_relations_txt + "\n"
    with open('./temp/table_relations.json', 'w', encoding='utf-8') as f:
        json.dump(all_table_relations, f)
    with open('./temp/table_relations.txt', 'w', encoding='utf-8') as f:
        f.write(all_table_relations_txt)

    # 5. Extract relationships from text
    print("Extracting relationships from text...")
    with open("./temp/text/text.txt", "r", encoding="utf-8") as f:
        text_content = f.read()
    paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]
    all_text_relations = []
    all_text_relations_txt = ""
    for paragraph in paragraphs:
        text_relations, text_relations_txt = text_relation_extractor.extract_relations(paragraph)
        all_text_relations.extend(text_relations)
        all_text_relations_txt += text_relations_txt + "\n"
    with open('./temp/text_relations.json', 'w', encoding='utf-8') as f:
        json.dump(all_text_relations, f)
    with open('./temp/text_relations.txt', 'w', encoding='utf-8') as f:
        f.write(all_text_relations_txt)

    # 6. Combine all relations into a single JSON file
    print("Combining all relations into a single JSON file...")
    article_name = pdf_path.stem
    main_json = "./output/" + article_name + "_combined_relations.json"
    merged = []
    for fp in ['./temp/text_relations.json', './temp/figure_relations.json', './temp/table_relations.json']:
        merged.extend(json.load(open(fp, "r", encoding="utf-8")))
    json.dump(merged, open(main_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 7. Convert combined JSON to GraphML
    print("Converting combined JSON to GraphML...")
    out_graphml = "./output/" + article_name + "_combined_graph.graphml"
    json_to_graphml(main_json, out_graphml)

if __name__ == "__main__":
    pdfs = ["../data/sciadv.abo6043.pdf", 
            "../data/2015_Predictive_modelling.pdf",
            "../data/2018_Recombinant_Spidroins.pdf"]
    for pdf_filename in pdfs:
        print(f"Processing {pdf_filename}...")
        main(pdf_filename)
        print("Processing completed.\n")
