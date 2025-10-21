# from matsci_llm_causality.models.llm.gpt import GPT5RelationExtractor  
from matsci_llm_causality.models.llm.gemini import GeminiTextRelationExtractor
from matsci_llm_causality.extraction.pdf import PDFProcessor
from pathlib import Path
  
# Initialize the model and PDF processor
extractor = GeminiTextRelationExtractor()
pdf_processor = PDFProcessor()

# Ask user for PDF path
pdf_path = input("Enter the path to the PDF file (or press Enter for default): ")
  
# If PDF path is not provided, process the 2018 PDF from data folder
if not pdf_path.strip():
    pdf_path = Path("../data/2018_Recombinant_Spidroins.pdf")
else:
    pdf_path = Path(pdf_path)

# Process the PDF
print(f"Processing PDF: {pdf_path}")

# Extract text from PDF
print("Extracting text from PDF...")
text = pdf_processor.extract_text_fitz(pdf_path)
print(f"Extracted {len(text)} characters")

# Extract relationships from the text
print("\nExtracting relationships...")
relationships = extractor.extract_relations(text)
print(f"\nFound {len(relationships[0])} relationships:")
for i, rel in enumerate(relationships[0], 1):
    print(f"{i}. {rel['subject']['name']} ({rel['subject']['type']}) {rel['relationship']} {rel['object']['name']} ({rel['object']['type']})")

# Alternative: Test with plain text (commented out for now)
text = "Increasing temperature improves crystallinity of the polymer."  
relationships = extractor.extract_relations(text)
print(relationships)