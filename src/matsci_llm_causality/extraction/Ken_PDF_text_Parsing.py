"""
Text extraction module for scientific PDFs
Handles multi-column layouts, section detection, and cleaning
"""

import fitz  # PyMuPDF
import re
from typing import Dict, List, Tuple
from pathlib import Path


class ScientificPDFExtractor:
    """Extract and structure text from scientific papers"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.full_text = ""
        self.sections = {}
        
    def extract_text(self) -> Dict[str, any]:
        """Main extraction method"""
        raw_text = self._extract_raw_text()
        cleaned_text = self._clean_text(raw_text)
        sections = self._identify_sections(cleaned_text)
        
        return {
            "full_text": cleaned_text,
            "sections": sections,
            "metadata": self._extract_metadata()
        }
    
    def _extract_raw_text(self) -> str:
        """Extract text preserving reading order for multi-column layouts"""
        all_text = []
        
        for page_num, page in enumerate(self.doc):
            # Get text blocks with coordinates
            blocks = page.get_text("blocks")
            
            # Sort blocks for proper reading order
            # First by vertical position (y0), then by horizontal (x0)
            sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
            
            # Detect if page is multi-column
            is_multi_column = self._is_multi_column(sorted_blocks, page.rect.width)
            
            if is_multi_column:
                page_text = self._extract_multicolumn(sorted_blocks, page.rect.width)
            else:
                page_text = self._extract_single_column(sorted_blocks)
            
            all_text.append(page_text)
        
        return "\n\n".join(all_text)
    
    def _is_multi_column(self, blocks: List, page_width: float) -> bool:
        """Detect if page has multi-column layout"""
        if len(blocks) < 4:
            return False
        
        # Check if blocks are clustered in left/right halves
        midpoint = page_width / 2
        left_blocks = sum(1 for b in blocks if b[0] < midpoint)
        right_blocks = sum(1 for b in blocks if b[0] >= midpoint)
        
        # If both sides have substantial content, it's multi-column
        return left_blocks > 2 and right_blocks > 2
    
    def _extract_multicolumn(self, blocks: List, page_width: float) -> str:
        """Extract text from multi-column layout in correct order"""
        midpoint = page_width / 2
        
        # Separate into left and right columns
        left_col = [b for b in blocks if b[2] <= midpoint + 20]  # x1 <= midpoint
        right_col = [b for b in blocks if b[0] >= midpoint - 20]  # x0 >= midpoint
        
        # Sort each column by vertical position
        left_col.sort(key=lambda b: b[1])
        right_col.sort(key=lambda b: b[1])
        
        # Combine: left column first, then right
        text_parts = []
        for block in left_col:
            text_parts.append(block[4].strip())
        for block in right_col:
            text_parts.append(block[4].strip())
        
        return "\n".join(text_parts)
    
    def _extract_single_column(self, blocks: List) -> str:
        """Extract text from single column layout"""
        text_parts = [block[4].strip() for block in blocks]
        return "\n".join(text_parts)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove headers/footers (common patterns)
        text = re.sub(r'\n\d+\n', '\n', text)  # Page numbers on separate lines
        text = re.sub(r'\nPage \d+.*?\n', '\n', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common OCR/extraction issues
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)  # Hyphenated words across lines
        
        # Remove figure/table references that are isolated
        text = re.sub(r'\n(Figure|Fig\.|Table|Eq\.) \d+\n', '\n', text)
        
        return text.strip()
    
    def _identify_sections(self, text: str) -> Dict[str, str]:
        """Identify major sections in the paper"""
        sections = {}
        
        # Common section headers in scientific papers
        section_patterns = [
            r'\n(ABSTRACT|Abstract)\s*\n',
            r'\n(INTRODUCTION|Introduction)\s*\n',
            r'\n(METHODS?|MATERIALS? AND METHODS?|EXPERIMENTAL)\s*\n',
            r'\n(RESULTS?)\s*\n',
            r'\n(DISCUSSION)\s*\n',
            r'\n(CONCLUSION)\s*\n',
            r'\n(REFERENCES?|BIBLIOGRAPHY)\s*\n',
        ]
        
        # Find all section boundaries
        boundaries = []
        for pattern in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                section_name = match.group(1).lower()
                boundaries.append((match.start(), section_name))
        
        # Sort by position
        boundaries.sort(key=lambda x: x[0])
        
        # Extract text for each section
        for i, (start, name) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            section_text = text[start:end].strip()
            sections[name] = section_text
        
        # If no sections found, return full text as 'body'
        if not sections:
            sections['body'] = text
        
        return sections
    
    def _extract_metadata(self) -> Dict[str, str]:
        """Extract PDF metadata"""
        metadata = self.doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "pages": len(self.doc)
        }
    
    def extract_section(self, section_name: str) -> str:
        """Extract a specific section by name"""
        result = self.extract_text()
        return result["sections"].get(section_name.lower(), "")
    
    def close(self):
        """Close the PDF document"""
        self.doc.close()

def extract_from_pdf(pdf_path: str) -> Dict[str, any]:
    """
    Convenience function to extract text from a PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with full_text, sections, and metadata
    """
    extractor = ScientificPDFExtractor(pdf_path)
    result = extractor.extract_text()
    extractor.close()
    return result

def extract_for_causal_analysis(pdf_path: str) -> str:
    """
    Extract text optimized for causal relationship extraction
    Focuses on methods, results, and removes references
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Cleaned text string ready for LLM processing
    """
    extractor = ScientificPDFExtractor(pdf_path)
    result = extractor.extract_text()
    extractor.close()
    
    # Use full text and remove references (most reliable approach)
    text = result['full_text']
    
    # Try to remove references section
    ref_match = re.search(r'\n(REFERENCES?|BIBLIOGRAPHY)\s*\n', text, re.IGNORECASE)
    if ref_match:
        text = text[:ref_match.start()]
    
    return text

def save_to_json(pdf_path: str, output_dir: str = None) -> str:
    """
    Extract text from PDF and save as JSON file
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save JSON (defaults to same dir as PDF)
        
    Returns:
        Path to saved JSON file
    """
    import json
    
    # Extract all data
    extractor = ScientificPDFExtractor(pdf_path)
    result = extractor.extract_text()
    causal_text = extract_for_causal_analysis(pdf_path)
    extractor.close()
    
    # Prepare output
    output_data = {
        "source_pdf": pdf_path,
        "metadata": result['metadata'],
        "sections": result['sections'],
        "full_text": result['full_text'],
        "causal_optimized_text": causal_text
    }
    
    # Determine output path
    pdf_file = Path(pdf_path)
    if output_dir:
        output_path = Path(output_dir) / f"{pdf_file.stem}_extracted.json"
    else:
        output_path = pdf_file.parent / f"{pdf_file.stem}_extracted.json"
    
    # Save JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return str(output_path)

# Example usage
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single file: python ken_text_extraction.py <pdf_path> [output_dir]")
        print("  Batch mode:  python ken_text_extraction.py --batch <input_dir> [output_dir]")
        sys.exit(1)
    
    # Batch processing mode
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("Error: --batch requires input directory")
            sys.exit(1)
        input_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        process_pdf_folder(input_dir, output_dir)
    
    # Single file mode
    else:
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Save to JSON
        output_file = save_to_json(pdf_path, output_dir)
        
        # Load and display preview
        with open(output_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        print("=" * 80)
        print("SAVED TO:", output_file)
        print("=" * 80)
        
        print("\n" + "=" * 80)
        print("METADATA")
        print("=" * 80)
        for key, value in result['metadata'].items():
            print(f"{key}: {value}")
        
        print("\n" + "=" * 80)
        print("SECTIONS FOUND")
        print("=" * 80)
        for section_name in result['sections'].keys():
            print(f"- {section_name}")
        
        print("\n" + "=" * 80)
        print("FULL TEXT (first 500 chars)")
        print("=" * 80)
        print(result['full_text'][:500])
        
        print("\n" + "=" * 80)
        print("CAUSAL-OPTIMIZED TEXT (first 500 chars)")
        print("=" * 80)
        print(result['causal_optimized_text'][:500])

