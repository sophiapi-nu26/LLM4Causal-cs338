"""
Simple demo script for Monte Carlo Evidence-Based Extraction

This script demonstrates the new Monte Carlo approach with a simple example.
"""

from matsci_llm_causality.models.llm.monte_carlo_extractor import MonteCarloEvidenceExtractor
from matsci_llm_causality.models.llm.gemini import GeminiTextRelationExtractor

def main():
    """Run a simple demo of the Monte Carlo extraction."""
    
    print("Monte Carlo Evidence-Based Causal Extraction Demo")
    print("=" * 50)
    
    # Initialize the Monte Carlo extractor
    base_extractor = GeminiTextRelationExtractor()
    mc_extractor = MonteCarloEvidenceExtractor(
        base_extractor=base_extractor,
        n_runs=3,  # Start with 3 runs for demo
        confidence_threshold=0.7
    )
    
    # Sample text for testing
    sample_text = """
    Increasing temperature improves crystallinity of the polymer. 
    Higher crystallinity leads to increased tensile strength. 
    The annealing process causes structural changes in the material.
    Temperature positively correlates with mechanical properties.
    """
    
    print(f"Sample text: {sample_text.strip()}")
    print()
    
    # Extract relationships with evidence
    print("Running Monte Carlo extraction...")
    result = mc_extractor.extract_relations_with_evidence(sample_text)
    
    # Display Stage 1 results (raw runs)
    print(f"\nStage 1 Results - Raw Runs ({len(result.raw_runs)} runs):")
    for i, run in enumerate(result.raw_runs, 1):
        print(f"  Run {i}: {len(run)} relationships")
        for j, rel in enumerate(run, 1):
            print(f"    {j}. {rel['subject']['name']} ({rel['subject']['type']}) {rel['relationship']} {rel['object']['name']} ({rel['object']['type']})")
    
    # Display consolidated entities
    print(f"\nConsolidated Entities ({len(result.entities)}):")
    for i, entity in enumerate(result.entities, 1):
        print(f"  {i}. {entity.canonical_name} ({entity.entity_type.value})")
        print(f"     Variations: {', '.join(entity.variations)}")
        print(f"     Confidence: {entity.confidence:.2f}")
    
    # Display validated relationships
    print(f"\nValidated Relationships ({len(result.relationships)}):")
    for i, rel in enumerate(result.relationships, 1):
        print(f"  {i}. {rel.subject.canonical_name} {rel.relation_type.value} {rel.object.canonical_name}")
        print(f"     Confidence: {rel.confidence:.2f} (appeared in {rel.frequency}/{mc_extractor.n_runs} runs)")
    
    # Build causal graph
    print("\nBuilding causal graph...")
    causal_graph = mc_extractor.build_causal_graph(result)
    
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {causal_graph['graph_metrics']['total_nodes']}")
    print(f"  Edges: {causal_graph['graph_metrics']['total_edges']}")
    print(f"  Density: {causal_graph['graph_metrics']['density']:.3f}")
    
    print(f"\nTop Causal Pathways:")
    for i, pathway in enumerate(causal_graph['causal_pathways'][:3], 1):
        print(f"  {i}. {' → '.join(pathway)}")
    
    print("\nDemo completed successfully!")

if __name__ == "__main__":
    main()
