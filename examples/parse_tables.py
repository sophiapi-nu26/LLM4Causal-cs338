import logging
import subprocess
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from docling.document_converter import DocumentConverter

# Configure logger to suppress all output
_log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.CRITICAL + 1)

def parse4table(input_doc_path: str, model: str = "mistral") -> str:
    """
    Convert a PDF document to a textual description of its tables using Docling and Ollama, with all output suppressed.

    Parameters
    ----------
    input_doc_path : str
        Path to the input PDF document to be processed.
    model : str
        Name of the Ollama model to use (default is "mistral").

    Returns
    -------
    str
        Combined textual descriptions of all tables in the document.
        Returns an error message if no tables are found or processing fails.
    """
    # Initialize Docling converter
    doc_converter = DocumentConverter()

    try:
        # Convert the document
        conv_res = doc_converter.convert(input_doc_path)
        doc_filename = conv_res.input.file.stem

        # Check if any tables were found
        if not conv_res.document.tables:
            return "No tables found in the document."

        # Process tables and store in memory
        html_tables = []
        for table_ix, table in enumerate(conv_res.document.tables):
            # Export table to HTML in memory
            html_content = table.export_to_html(doc=conv_res.document)
            html_tables.append((f"{doc_filename}-table-{table_ix + 1}.html", html_content))

        # Interpret HTML tables
        descriptions = []
        for html_filename, html_content in html_tables:
            try:
                # Parse HTML content
                soup = BeautifulSoup(html_content, "html.parser")
                table = soup.find("table")
                if not table:
                    descriptions.append(f"Failed to find table in {html_filename}.")
                    continue

                # Convert HTML table to DataFrame and then to markdown
                df = pd.read_html(StringIO(str(table)))[0]
                table_markdown = df.to_markdown(index=False)

                # Create prompt for Ollama
                prompt = f"""
You are a data analysis assistant specializing in materials science.
Analyze the following table and provide a clear description of what it says in plain sentences.
Focus on summarizing key information: materials, properties, processes, conditions, structures, notable trends.
Return a few concise sentences, each ending with a period, separated by newlines (\\n).
Do not include bullet points, headings, or other formatting.

Table content:
{table_markdown}
"""
                # Query Ollama
                try:
                    result = subprocess.run(
                        ["ollama", "run", model],
                        input=prompt,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    response = result.stdout.strip()
                except subprocess.CalledProcessError:
                    descriptions.append(f"Failed to interpret table from {html_filename} due to an Ollama error.")
                    continue

                # Clean up response
                if not isinstance(response, str):
                    response = str(response)
                response = "\n".join(line.strip() for line in response.splitlines() if line.strip())
                descriptions.append(f"Table {html_filename}: {response}")

            except Exception:
                descriptions.append(f"Failed to process table from {html_filename} due to an error.")
                continue

        # Return combined descriptions
        return "\n\n".join(descriptions) if descriptions else "No valid table descriptions generated."

    except Exception as e:
        return f"Failed to process document due to an error: {str(e)}"

if __name__ == "__main__":
    # Example usage
    description = parse4table(input_doc_path="1000_silkomes.pdf")
    print(description)
    with open('tables.txt', 'w') as f:
        f.write(description)
