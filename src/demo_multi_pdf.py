"""
Demo script for running the section-aware workflow across multiple PDFs and consolidating results.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

from matsci_llm_causality.workflows.section_pipeline import (
    MultiDocumentWorkflow,
    StageRunConfig,
)
from matsci_llm_causality.visualization import build_graph_data, render_graph_html


def _prompt_int(message: str, default: int) -> int:
    raw = input(f"{message} (default {default}): ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print("Invalid input, using default.")
        return default


def _prompt_float(message: str, default: float) -> float:
    raw = input(f"{message} (default {default}): ").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print("Invalid input, using default.")
        return default


def _load_paper(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    print("Multi-PDF Causal Extraction Demo")
    print("=" * 50)

    default_query = "properties related to spider silk"
    user_query = input(f"Enter the user query describing the focus (default {default_query}): ").strip()
    if not user_query:
        user_query = default_query

    default_paths = "../data/spidroins.json,../data/bombyx.json"
    path_input = input(f"Enter comma-separated paper JSON paths (default {default_paths}): ").strip()
    path_input = path_input or default_paths
    path_strings = [p.strip() for p in path_input.split(",") if p.strip()]
    if not path_strings:
        print("No paper paths provided. Exiting.")
        return

    stage1_runs = _prompt_int("Stage 1 (abstract) runs", 3)
    stage3_runs = _prompt_int("Stage 3 (results) runs", 3)
    stage5_runs = _prompt_int("Stage 5 (edges) runs", 3)
    confidence_threshold = _prompt_float("Confidence threshold", 0.5)
    verbose_choice = input("Enable debug logging? (y/N): ").strip().lower() == "y"

    papers: List[Tuple[str, Dict[str, Any]]] = []
    for path_str in path_strings:
        path = Path(path_str).resolve()
        if not path.exists():
            print(f"Warning: {path} does not exist. Skipping.")
            continue
        paper_id = path.stem
        papers.append((paper_id, _load_paper(path)))

    if not papers:
        print("No valid papers to process. Exiting.")
        return

    config = StageRunConfig(
        stage1_runs=stage1_runs,
        stage3_runs=stage3_runs,
        stage5_runs=stage5_runs,
        confidence_threshold=confidence_threshold,
        user_query=user_query,
    )

    workflow = MultiDocumentWorkflow(
        config=config,
        verbose=verbose_choice,
        log_dir="logs",
        sequential=True,
    )

    result = workflow.run(user_query=user_query, papers=papers)

    print("\nCanonical Nodes:")
    if not result.canonical_nodes:
        print("  (none)")
    for node in result.canonical_nodes:
        sources = ", ".join(
            f"{src.get('paper_id')}: {src.get('node_name')}" for src in node.sources
        )
        print(f" - {node.name} [{node.type}] - {node.summary}")
        if sources:
            print(f"    Sources: {sources}")

    print("\nMerged Edges:")
    if not result.edges:
        print("  (none)")
    for edge in result.edges:
        papers_str = ", ".join(edge.source_papers)
        print(
            f" - {edge.source} {edge.relation} {edge.target} "
            f"(count={edge.count}, confidence={edge.confidence:.2f})"
        )
        if edge.evidence_samples:
            print(f"    Evidence: {edge.evidence_samples[0]}")
        if papers_str:
            print(f"    Source papers: {papers_str}")

    print(f"\nGlobal log written to: {workflow.global_log_path}")

    render_choice = input("\nGenerate interactive HTML visualization? (y/N): ").strip().lower() == "y"
    if render_choice:
        graph_data = build_graph_data(result)
        output_dir = Path("visualizations")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"causal_graph_{timestamp}.json"
        html_path = output_dir / f"causal_graph_{timestamp}.html"
        json_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
        render_graph_html(graph_data, html_path, title=f"Causal Graph – {user_query}")
        print(f"Saved graph data to: {json_path}")
        print(f"Saved interactive visualization to: {html_path}")


if __name__ == "__main__":
    main()

# this is just some bullshit