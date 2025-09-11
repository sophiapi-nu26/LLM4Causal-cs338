"""
PDF processing and text extraction module.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF
import shutil
from .grobid import grobid

# Docling imports for figure extraction
from docling_core.types.doc import PictureItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# Configure logger to suppress non-critical output
logging.getLogger().setLevel(logging.ERROR)
_log = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 2.0

class PDFProcessor:
    """Handles PDF document processing and text extraction."""
    
    def extract_text_fitz(self, pdf_path: str | Path) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            text.append(page.get_text())
        return "\n".join(text)
    
    def extract_text(self, pdf_path: str | Path, grobid_url: str, outdir: str | Path) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file"""
        grobid(pdf_path, grobid_url, outdir)
        

    def extract_figures(self, input_doc_path: str | Path, output_dir: str | Path) -> str:
        """
        Extract figures from a PDF document and save them as PNG files.

        Parameters
        ----------
        input_doc_path : str
            Path to the input PDF document.
        output_dir : str
            Directory to save extracted figures (default: "./output_figures").

        Returns
        -------
        str
            Success message with figure count or error message if processing fails.
        """
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_picture_images = True

        # Initialize Docling converter
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        try:
            # Convert document
            conv_res = doc_converter.convert(input_doc_path)
            doc_filename = conv_res.input.file.stem

            # Create output directory
            output_dir_path = Path(output_dir)
            output_dir_path.mkdir(parents=True, exist_ok=True)

            # Extract and save figures
            picture_counter = 0
            for element, _ in conv_res.document.iterate_items():
                if isinstance(element, PictureItem):
                    picture_counter += 1
                    image = element.get_image(conv_res.document)
                    if image is None or not hasattr(image, 'save'):
                        _log.error(f"Failed to process figure {picture_counter}: Invalid image data.")
                        continue

                    # Save figure as PNG
                    output_filename = output_dir_path / f"{doc_filename}-figure-{picture_counter}.png"
                    with output_filename.open("wb") as fp:
                        image.save(fp, "PNG")
                        _log.info(f"Saved figure: {output_filename}")

            return f"Extracted {picture_counter} figures to {output_dir}." if picture_counter > 0 else "No figures found in the document."

        except Exception as e:
            _log.error(f"Document processing failed: {str(e)}")
            return f"Failed to process document: {str(e)}"

    def extract_tables(self, input_doc_path: str | Path, output_dir: str | Path) -> str:
        """
    Parse a document with Docling, extract tables, and export them as CSV and HTML.

    Parameters
    ----------
    input_doc_path : str
        Path to the input document (e.g., PDF) to be converted.

    Outputs
    -------
    - Creates a folder `tables_html/` containing:
        - CSV files for each table
        - HTML files for each table
    - Prints tables to console in Markdown format
    - Logs the process with runtime
    """

        # Configure logging format and level (INFO shows progress without being too verbose)
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

        # Define the output directory for tables
        output_dir = Path(output_dir)

        # Clear old results if the directory already exists
        if output_dir.is_dir():
            shutil.rmtree(output_dir)

        # Initialize Docling converter
        doc_converter = DocumentConverter()

        start_time = time.time()

        # Convert the document into a structured representation
        conv_res = doc_converter.convert(input_doc_path)

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract the base filename (without extension) for naming outputs
        doc_filename = conv_res.input.file.stem

        # Iterate over all detected tables
        for table_ix, table in enumerate(conv_res.document.tables):
            # Export table to pandas DataFrame
            table_df: pd.DataFrame = table.export_to_dataframe()

            # Display in console as Markdown for quick inspection
            print(f"\n## Table {table_ix + 1}")
            print(table_df.to_markdown())

            # ----------------------------
            # Save the table as CSV
            # ----------------------------
            # element_csv_filename = output_dir / f"{doc_filename}-table-{table_ix + 1}.csv"
            # _log.info(f"Saving CSV table to {element_csv_filename}")
            # table_df.to_csv(element_csv_filename, index=False)

            # ----------------------------
            # Save the table as HTML
            # ----------------------------
            element_html_filename = output_dir / f"{doc_filename}-table-{table_ix + 1}.html"
            _log.info(f"Saving HTML table to {element_html_filename}")
            with element_html_filename.open("w", encoding="utf-8") as fp:
                fp.write(table.export_to_html(doc=conv_res.document))

        # Measure elapsed time
        elapsed = time.time() - start_time
        _log.info(f"Document converted and {len(conv_res.document.tables)} table(s) exported in {elapsed:.2f} seconds.")
        
        return f"Extracted {len(conv_res.document.tables)} tables to {output_dir}."