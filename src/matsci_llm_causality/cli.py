#!/usr/bin/env python3
"""
Command-line script to process a single PDF through the causality extraction pipeline.
"""

import argparse
from pathlib import Path
import json
from matsci_llm_causality import CausalityExtractor, ModelConfig

def main():
    parser = argparse.ArgumentParser(description="Process a PDF through the causality extraction pipeline")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument("--model", type=str, default="flan-t5", help="Model to use for extraction")
    parser.add_argument("--temperature", type=float, default=0.7, help="Model temperature")
    parser.add_argument("--max-length", type=int, default=512, help="Maximum input length")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--device", type=str, default="cpu", help="Device to run on (cpu/cuda)")
    
    args = parser.parse_args()
    
    # Create model config
    config = ModelConfig(
        model_type=args.model,
        temperature=args.temperature,
        max_length=args.max_length,
        device=args.device
    )
    
    # Initialize extractor
    extractor = CausalityExtractor(model=args.model, model_config=config)
    
    # Process PDF
    print(f"Processing {args.pdf_path}...")
    results = extractor.process_pdf(args.pdf_path)
    
    # Convert results to dictionary
    output = {
        "entities": [
            {
                "text": e.text,
                "type": e.type,
                "aliases": e.aliases,
                "metadata": e.metadata
            }
            for e in results.entities
        ],
        "relationships": [
            {
                "subject": {
                    "text": r.subject.text,
                    "type": r.subject.type
                },
                "object": {
                    "text": r.object.text,
                    "type": r.object.type
                },
                "relation_type": r.relation_type,
                "polarity": r.polarity,
                "confidence": r.confidence,
                "evidence": r.evidence,
                "metadata": r.metadata
            }
            for r in results.relationships
        ],
        "metadata": results.metadata
    }
    
    # Print or save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")
    else:
        # Print summary
        print("\nExtracted Entities:")
        for entity in results.entities:
            print(f"- {entity.text} ({entity.type})")
        
        print("\nExtracted Relationships:")
        for rel in results.relationships:
            print(f"- {rel.subject.text} {rel.relation_type} {rel.object.text}")
            print(f"  Confidence: {rel.confidence:.2f}")
            print(f"  Evidence: {rel.evidence}")

if __name__ == "__main__":
    main()
