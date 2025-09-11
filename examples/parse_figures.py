import logging
import time
from pathlib import Path
from docling_core.types.doc import ImageRefMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

_log = logging.getLogger(__name__)

IMAGE_RESOLUTION_SCALE = 8.0

def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_path = "1000_silkomes.pdf"
    output_dir = Path("scratch")

    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    start_time = time.time()
    conv_res = doc_converter.convert(input_doc_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    doc_filename = conv_res.input.file.stem


    end_time = time.time() - start_time
    _log.info(f"Document converted in {end_time:.2f} seconds.")

if __name__ == "__main__":
    main()
