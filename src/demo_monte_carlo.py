"""
Demo script for the section-aware workflow described in instructions.md.
"""

import json
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

from matsci_llm_causality.workflows.section_pipeline import (
    SectionAwareWorkflow,
    StageRunConfig,
)


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


def _load_paper_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    print("Section-Aware Causal Extraction Demo")
    print("=" * 50)

    stage1_runs = _prompt_int("Stage 1 (abstract) runs", 5)
    stage3_runs = _prompt_int("Stage 3 (results) runs", 5)
    stage5_runs = _prompt_int("Stage 5 (edges) runs", 5)
    confidence_threshold = _prompt_float("Confidence threshold", 0.5)

    json_path = input(
        "Enter the path to the paper JSON (press Enter for ../data/spidroins.json): "
    ).strip()
    if not json_path:
        json_path = "../data/spidroins.json"
    paper_path = Path(json_path).resolve()
    if not paper_path.exists():
        raise FileNotFoundError(f"Paper JSON not found: {paper_path}")

    paper = _load_paper_json(paper_path)

    verbose_choice = input("Enable debug logging? (y/N): ").strip().lower() == "y"

    config = StageRunConfig(
        stage1_runs=stage1_runs,
        stage3_runs=stage3_runs,
        stage5_runs=stage5_runs,
        confidence_threshold=confidence_threshold,
    )
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"demo_debug_log_{timestamp}.log"

    workflow = SectionAwareWorkflow(
        config=config,
        verbose=verbose_choice,
        log_path=str(log_path),
    )

    print("\nRunning workflow...")
    result = workflow.run(paper)
    print(f"\nLogs written to: {log_path}")

    print("\nInitial nodes:")
    for node in result.initial_nodes:
        print(f" - {node.get('name')} ({node.get('type')}): {node.get('summary')}")

    print("\nFinal nodes:")
    for node in result.final_nodes:
        print(f" - {node.get('name')} ({node.get('type')}): {node.get('summary')}")

    print("\nConsolidated edges (all):")
    for edge in result.consolidated_edges:
        print(
            f" - {edge.source} {edge.relation} {edge.target} | count={edge.count} sections={edge.sections}"
        )

    print("\nFiltered edges (after confidence threshold):")
    if not result.filtered_edges:
        print(" - No edges met the confidence threshold.")
    for edge in result.filtered_edges:
        print(
            f" - {edge.source} {edge.relation} {edge.target} | "
            f"count={edge.count} confidence={edge.confidence:.2f}"
        )

    print("\nDemo completed successfully.")


if __name__ == "__main__":
    main()
