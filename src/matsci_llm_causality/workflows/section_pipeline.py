from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai

from ..prompts import load_prompt
from ..models.llm.gemini import call_with_backoff


@dataclass
class StageRunConfig:
    stage1_runs: int = 5
    stage3_runs: int = 5
    stage5_runs: int = 5
    confidence_threshold: float = 0.5
    model_name: str = "gemini-2.5-flash"


@dataclass
class EdgeResult:
    source: str
    target: str
    relation: str
    count: int
    evidence_samples: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SectionWorkflowResult:
    initial_nodes: List[Dict[str, Any]]
    final_nodes: List[Dict[str, Any]]
    raw_edges: List[List[Dict[str, Any]]]
    consolidated_edges: List[EdgeResult]
    filtered_edges: List[EdgeResult]


class ParallelGeminiRunner:
    """Utility to run Gemini prompts in parallel with graceful fallback."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def _call_model(self, prompt: str) -> str:
        client = genai.Client()
        response = call_with_backoff(
            lambda: client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
            )
        )
        return response.text

    def run(self, prompts: List[str], max_workers: int) -> List[str]:
        if len(prompts) == 1:
            return [self._call_model(prompts[0])]

        results: List[str] = [""] * len(prompts)
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(self._call_model, prompt): idx
                    for idx, prompt in enumerate(prompts)
                }
                for future in as_completed(future_map):
                    idx = future_map[future]
                    results[idx] = future.result()
        except Exception:
            # Fallback to sequential execution.
            results = []
            for prompt in prompts:
                results.append(self._call_model(prompt))
        return results


class SectionAwareWorkflow:
    """Implements the staged section-aware workflow described in instructions.md."""

    def __init__(
        self,
        config: Optional[StageRunConfig] = None,
        verbose: bool = False,
        log_path: Optional[str] = None,
    ):
        self.config = config or StageRunConfig()
        self.runner = ParallelGeminiRunner(model_name=self.config.model_name)
        self.verbose = verbose
        self.logger = self._build_logger(log_path)
        self._log("Initialized SectionAwareWorkflow", level="info")

    def _build_logger(self, log_path: Optional[str]) -> logging.Logger:
        logger = logging.getLogger(f"SectionWorkflow-{id(self)}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        for handler in list(logger.handlers):
            logger.removeHandler(handler)

        path = Path(log_path) if log_path else Path("logs/section_workflow.log")
        path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        if self.verbose:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.DEBUG)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger

    # Public API -----------------------------------------------------------------
    def run(self, paper: Dict[str, Any]) -> SectionWorkflowResult:
        abstract = paper.get("abstract", "")
        results_text = paper.get("results", "")
        methodology_text = paper.get("methodology", "")
        discussion_text = paper.get("discussion", "")

        # Stage 1 & 2: initial nodes
        stage1_raw = self._run_stage1_initial_nodes(abstract)
        self._log(f"Stage 1 raw node lists: {len(stage1_raw)}")
        initial_nodes = self._consolidate_initial_nodes(stage1_raw)
        self._log(f"Stage 2 consolidated nodes: {len(initial_nodes)}")

        # Stage 3 & 4: expanded/final nodes using results section
        stage3_raw = self._run_stage3_expanded_nodes(results_text, initial_nodes)
        self._log(f"Stage 3 raw expanded nodes: {len(stage3_raw)}")
        final_nodes = self._consolidate_expanded_nodes(stage3_raw)
        self._log(f"Stage 4 final nodes: {len(final_nodes)}")

        # Stage 5 & 6: edges across methodology/results/discussion
        raw_edges = self._run_stage5_edges(
            methodology_text=methodology_text,
            results_text=results_text,
            discussion_text=discussion_text,
            final_nodes=final_nodes,
        )
        self._log(f"Stage 5 raw edge sets: {len(raw_edges)}")
        consolidated_edges = self._consolidate_edges(raw_edges)
        self._log(f"Stage 6 consolidated edges: {len(consolidated_edges)}")

        # Stage 7: apply confidence threshold
        filtered_edges = self._apply_confidence_threshold(
            consolidated_edges,
            self.config.stage5_runs,
            self.config.confidence_threshold,
        )
        self._log(f"Stage 7 filtered edges: {len(filtered_edges)}")

        # Stage 8: placeholder for causal inconsistency check
        self._check_causal_inconsistencies(filtered_edges)

        return SectionWorkflowResult(
            initial_nodes=initial_nodes,
            final_nodes=final_nodes,
            raw_edges=raw_edges,
            consolidated_edges=consolidated_edges,
            filtered_edges=filtered_edges,
        )

    # Stage helpers --------------------------------------------------------------
    def _run_stage1_initial_nodes(self, abstract: str) -> List[List[Dict[str, Any]]]:
        prompts = [
            load_prompt("stage1_initial_nodes_prompt.txt", abstract=abstract)
            for _ in range(self.config.stage1_runs)
        ]
        responses = self.runner.run(prompts, max_workers=self.config.stage1_runs)
        parsed = []
        for idx, response in enumerate(responses):
            self._log(
                f"Stage 1 run {idx+1} raw response:\n{response}",
                level="debug",
            )
            nodes = self._safe_load_list(response, context=f"stage1-run-{idx+1}")
            if not nodes:
                self._log(f"Stage 1 run {idx+1} returned no nodes. Raw response:\n{response}")
            parsed.append(nodes)
        return parsed

    def _consolidate_initial_nodes(
        self, node_lists: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        raw_node_lists = json.dumps(node_lists, indent=2)
        prompt = load_prompt(
            "stage1_initial_nodes_consolidation.txt", raw_node_lists=raw_node_lists
        )
        response = self.runner.run([prompt], max_workers=1)[0]
        self._log(f"Stage 2 consolidation raw response:\n{response}", level="debug")
        consolidated = self._safe_load_list(response, context="stage2-consolidation")
        if not consolidated:
            self._log(f"Stage 2 consolidation returned no nodes. Raw response:\n{response}", level="warn")
        return consolidated

    def _run_stage3_expanded_nodes(
        self, results_text: str, initial_nodes: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        initial_nodes_json = json.dumps(initial_nodes, indent=2)
        prompts = [
            load_prompt(
                "stage3_expanded_nodes_prompt.txt",
                initial_nodes=initial_nodes_json,
                results_text=results_text,
            )
            for _ in range(self.config.stage3_runs)
        ]
        responses = self.runner.run(prompts, max_workers=self.config.stage3_runs)
        parsed = []
        for idx, response in enumerate(responses):
            self._log(
                f"Stage 3 run {idx+1} raw response:\n{response}",
                level="debug",
            )
            nodes = self._safe_load_list(response, context=f"stage3-run-{idx+1}")
            if not nodes:
                self._log(f"Stage 3 run {idx+1} returned no nodes. Raw response:\n{response}")
            parsed.append(nodes)
        return parsed

    def _consolidate_expanded_nodes(
        self, expanded_node_lists: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        raw_expanded_nodes = json.dumps(expanded_node_lists, indent=2)
        prompt = load_prompt(
            "stage3_expanded_nodes_consolidation.txt",
            raw_expanded_nodes=raw_expanded_nodes,
        )
        response = self.runner.run([prompt], max_workers=1)[0]
        self._log(f"Stage 4 consolidation raw response:\n{response}", level="debug")
        final_nodes = self._safe_load_list(response, context="stage4-consolidation")
        if not final_nodes:
            self._log(f"Stage 4 consolidation returned no nodes. Raw response:\n{response}", level="warn")
        return final_nodes

    def _run_stage5_edges(
        self,
        methodology_text: str,
        results_text: str,
        discussion_text: str,
        final_nodes: List[Dict[str, Any]],
    ) -> List[List[Dict[str, Any]]]:
        final_nodes_json = json.dumps(final_nodes, indent=2)
        prompts = [
            load_prompt(
                "stage5_relationships_prompt.txt",
                final_nodes=final_nodes_json,
                methodology_text=methodology_text,
                results_text=results_text,
                discussion_text=discussion_text,
            )
            for _ in range(self.config.stage5_runs)
        ]
        responses = self.runner.run(prompts, max_workers=self.config.stage5_runs)
        parsed = []
        for idx, response in enumerate(responses):
            self._log(
                f"Stage 5 run {idx+1} raw response:\n{response}",
                level="debug",
            )
            edges = self._safe_load_list(response, context=f"stage5-run-{idx+1}")
            if not edges:
                self._log(f"Stage 5 run {idx+1} returned no edges. Raw response:\n{response}")
            parsed.append(edges)
        return parsed

    def _consolidate_edges(self, edge_lists: List[List[Dict[str, Any]]]) -> List[EdgeResult]:
        raw_edge_lists = json.dumps(edge_lists, indent=2)
        prompt = load_prompt(
            "stage5_relationships_consolidation.txt",
            raw_edge_lists=raw_edge_lists,
        )
        response = self.runner.run([prompt], max_workers=1)[0]
        self._log(f"Stage 6 consolidation raw response:\n{response}", level="debug")
        parsed = self._safe_load_dict(response, context="stage6-consolidation")
        consolidated = []
        for edge in parsed.get("edges", []):
            consolidated.append(
                EdgeResult(
                    source=edge.get("source", "").strip(),
                    target=edge.get("target", "").strip(),
                    relation=edge.get("relation", "").strip(),
                    count=int(edge.get("count", 1)),
                    evidence_samples=edge.get("evidence_samples", []),
                    sections=edge.get("sections", []),
                )
            )
        return consolidated

    def _apply_confidence_threshold(
        self,
        edges: List[EdgeResult],
        total_runs: int,
        threshold: float,
    ) -> List[EdgeResult]:
        confident_edges = []
        for edge in edges:
            confidence = edge.count / max(1, total_runs)
            if confidence >= threshold:
                edge.confidence = confidence
                confident_edges.append(edge)
        return confident_edges

    def _check_causal_inconsistencies(self, edges: List[EdgeResult]) -> None:
        """Placeholder for future causal consistency checks."""
        return None

    # Parsing helpers ------------------------------------------------------------
    def _safe_load_list(self, payload: str, context: str = "") -> List[Dict[str, Any]]:
        data = self._safe_load_json(payload, context=context)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return []

    def _safe_load_dict(self, payload: str, context: str = "") -> Dict[str, Any]:
        data = self._safe_load_json(payload, context=context)
        if isinstance(data, dict):
            return data
        return {}

    def _safe_load_json(self, payload: str, context: str = "") -> Any:
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            stripped = payload.strip()
            if stripped.startswith("```"):
                stripped = self._strip_code_fence(stripped)
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
            self._log(
                f"Failed to parse JSON in context '{context}'. Payload snippet:\n{payload[:400]}",
                level="warn",
            )
            return []

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        # Handles ```json ... ``` or ``` ... ```
        lines = text.splitlines()
        if not lines:
            return text

        # Remove first line if it starts with ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it starts with ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _log(self, message: str, level: str = "debug") -> None:
        if level.lower() == "info":
            self.logger.info(message)
        elif level.lower() == "warn":
            self.logger.warning(message)
        elif level.lower() == "error":
            self.logger.error(message)
        else:
            self.logger.debug(message)

