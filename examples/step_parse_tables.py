import logging
import time
from pathlib import Path
import pandas as pd
import shutil

from docling.document_converter import DocumentConverter

# Configure logger for this module
_log = logging.getLogger(__name__)


def parse4table(input_doc_path: str = None, output_dir: str = "../tables_html") -> None:
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
        element_csv_filename = output_dir / f"{doc_filename}-table-{table_ix + 1}.csv"
        _log.info(f"Saving CSV table to {element_csv_filename}")
        table_df.to_csv(element_csv_filename, index=False)

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


if __name__ == "__main__":
    # Example usage: change this path to your input file
    parse4table(input_doc_path="../tests/data/sciadv.abo6043.pdf")
