"""
Test script for Monte Carlo Evidence-Based Causal Relationship Extractor

This script demonstrates the two-stage Monte Carlo approach:
1. Multiple runs to gather evidence
2. Entity consolidation and relationship validation
3. Mathematical causal graph construction
"""

from matsci_llm_causality.models.llm.monte_carlo_extractor import MonteCarloEvidenceExtractor
from matsci_llm_causality.models.llm.gemini import GeminiTextRelationExtractor
from matsci_llm_causality.extraction.pdf import PDFProcessor
from pathlib import Path
import json

def test_monte_carlo_extraction():
    """Test the Monte Carlo evidence-based extraction."""
    
    # Initialize components
    base_extractor = GeminiTextRelationExtractor()
    monte_carlo_extractor = MonteCarloEvidenceExtractor(
        base_extractor=base_extractor,
        n_runs=5,  # Number of Monte Carlo runs
        confidence_threshold=0.6,  # Require 60% agreement
        entity_similarity_threshold=0.8  # Entity name similarity threshold
    )
    
    # Test with sample text
    sample_text = """
    Increasing temperature improves crystallinity of the polymer. 
    Higher crystallinity leads to increased tensile strength. 
    The annealing process causes structural changes in the material.
    Temperature positively correlates with mechanical properties.
    """
    
    print("=" * 60)
    print("MONTE CARLO EVIDENCE-BASED CAUSAL EXTRACTION")
    print("=" * 60)
    print(f"Sample text: {sample_text.strip()}")
    print()
    
    # Extract relationships with evidence
    result = monte_carlo_extractor.extract_relations_with_evidence(sample_text)
    
    # Display results
    print("\n" + "=" * 60)
    print("STAGE 1 & 2 RESULTS: CONSOLIDATED ENTITIES")
    print("=" * 60)
    for i, entity in enumerate(result.entities, 1):
        print(f"{i}. {entity.canonical_name} ({entity.entity_type.value})")
        print(f"   Variations: {', '.join(entity.variations)}")
        print(f"   Frequency: {entity.frequency}, Confidence: {entity.confidence:.2f}")
        print()
    
    print("\n" + "=" * 60)
    print("STAGE 3 RESULTS: VALIDATED RELATIONSHIPS")
    print("=" * 60)
    for i, rel in enumerate(result.relationships, 1):
        print(f"{i}. {rel.subject.canonical_name} {rel.relation_type.value} {rel.object.canonical_name}")
        print(f"   Frequency: {rel.frequency}/{monte_carlo_extractor.n_runs}, Confidence: {rel.confidence:.2f}")
        print()
    
    # Build causal graph
    print("\n" + "=" * 60)
    print("MATHEMATICAL CAUSAL GRAPH CONSTRUCTION")
    print("=" * 60)
    causal_graph = monte_carlo_extractor.build_causal_graph(result)
    
    print(f"Graph Metrics:")
    print(f"  Total nodes: {causal_graph['graph_metrics']['total_nodes']}")
    print(f"  Total edges: {causal_graph['graph_metrics']['total_edges']}")
    print(f"  Graph density: {causal_graph['graph_metrics']['density']:.3f}")
    print()
    
    print("Centrality Measures:")
    for entity_name, measures in causal_graph['graph_metrics']['centrality_measures'].items():
        print(f"  {entity_name}:")
        print(f"    In-degree: {measures['in_degree']:.2f}")
        print(f"    Out-degree: {measures['out_degree']:.2f}")
        print(f"    Betweenness: {measures['betweenness_centrality']:.2f}")
    print()
    
    print("Causal Pathways:")
    for i, pathway in enumerate(causal_graph['causal_pathways'], 1):
        print(f"  {i}. {' → '.join(pathway)}")
    
    # Save results to JSON
    output_file = "monte_carlo_results.json"
    with open(output_file, 'w') as f:
        json.dump(causal_graph, f, indent=2)
    print(f"\nResults saved to {output_file}")
    
    return result, causal_graph

def test_with_pdf():
    """Test with a PDF file."""
    print("\n" + "=" * 60)
    print("TESTING WITH PDF FILE")
    print("=" * 60)
    
    # Initialize components
    pdf_processor = PDFProcessor()
    base_extractor = GeminiTextRelationExtractor()
    monte_carlo_extractor = MonteCarloEvidenceExtractor(
        base_extractor=base_extractor,
        n_runs=3,  # Fewer runs for PDF testing
        confidence_threshold=0.5
    )
    
    # Process PDF
    pdf_path = Path("../data/2018_Recombinant_Spidroins.pdf")
    if pdf_path.exists():
        print(f"Processing PDF: {pdf_path}")
        text = pdf_processor.extract_text_fitz(pdf_path)
        print(f"Extracted {len(text)} characters")
        
        # Use first 2000 characters for testing
        sample_text = text[:2000]
        print(f"Using first {len(sample_text)} characters for testing")
        
        # Extract relationships with evidence
        result = monte_carlo_extractor.extract_relations_with_evidence(sample_text)
        
        print(f"\nFound {len(result.entities)} consolidated entities")
        print(f"Found {len(result.relationships)} validated relationships")
        
        # Build causal graph
        causal_graph = monte_carlo_extractor.build_causal_graph(result)
        
        # Save results
        output_file = "pdf_monte_carlo_results.json"
        with open(output_file, 'w') as f:
            json.dump(causal_graph, f, indent=2)
        print(f"PDF results saved to {output_file}")
        
        return result, causal_graph
    else:
        print(f"PDF file not found: {pdf_path}")
        return None, None

def compare_with_single_run():
    """Compare Monte Carlo results with single run."""
    print("\n" + "=" * 60)
    print("COMPARISON: MONTE CARLO vs SINGLE RUN")
    print("=" * 60)
    
    sample_text = """
    Increasing temperature improves crystallinity of the polymer. 
    Higher crystallinity leads to increased tensile strength. 
    The annealing process causes structural changes in the material.
    Temperature positively correlates with mechanical properties.
    """
    
    # Single run
    base_extractor = GeminiTextRelationExtractor()
    single_run_result = base_extractor.extract_relations(sample_text)
    
    print("Single Run Results:")
    for i, rel in enumerate(single_run_result, 1):
        print(f"  {i}. {rel.subject.text} {rel.relation_type.value} {rel.object.text}")
    
    # Monte Carlo run
    monte_carlo_extractor = MonteCarloEvidenceExtractor(
        base_extractor=base_extractor,
        n_runs=5,
        confidence_threshold=0.6
    )
    mc_result = monte_carlo_extractor.extract_relations_with_evidence(sample_text)
    
    print(f"\nMonte Carlo Results ({mc_result.metadata['relationships_above_threshold']} above threshold):")
    for i, rel in enumerate(mc_result.relationships, 1):
        print(f"  {i}. {rel.subject.canonical_name} {rel.relation_type.value} {rel.object.canonical_name} (conf: {rel.confidence:.2f})")

if __name__ == "__main__":
    # Test with sample text
    result, causal_graph = test_monte_carlo_extraction()
    
    # Test with PDF
    pdf_result, pdf_causal_graph = test_with_pdf()
    
    # Compare approaches
    compare_with_single_run()
    
    print("\n" + "=" * 60)
    print("MONTE CARLO EXTRACTION COMPLETE")
    print("=" * 60)
