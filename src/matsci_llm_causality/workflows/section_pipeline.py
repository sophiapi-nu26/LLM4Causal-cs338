from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import time

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
    user_query: str = ""


@dataclass
class EdgeResult:
    source: str
    target: str
    relation: str
    count: int
    evidence_samples: List[str] = field(default_factory=list)
    sections: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source_papers: List[str] = field(default_factory=list)


@dataclass
class SectionWorkflowResult:
    paper_id: str
    initial_nodes: List[Dict[str, Any]]
    final_nodes: List[Dict[str, Any]]
    raw_edges: List[List[Dict[str, Any]]]
    consolidated_edges: List[EdgeResult]
    filtered_edges: List[EdgeResult]


@dataclass
class GlobalNode:
    name: str
    type: str
    summary: str
    sources: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GlobalEdge:
    source: str
    target: str
    relation: str
    count: int
    evidence_samples: List[str] = field(default_factory=list)
    source_papers: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class GlobalGraphResult:
    user_query: str
    canonical_nodes: List[GlobalNode]
    edges: List[GlobalEdge]
    document_results: List[SectionWorkflowResult]


class MultiDocumentWorkflow:
    """Orchestrates SectionAwareWorkflow across multiple documents and consolidates results."""

    def __init__(
        self,
        config: Optional[StageRunConfig] = None,
        verbose: bool = False,
        log_dir: str = "logs",
        sequential: bool = False,
    ):
        self.base_config = config or StageRunConfig()
        self.verbose = verbose
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.global_log_path = self.log_dir / f"multi_run_{timestamp}.log"
        self.logger = self._build_logger(self.global_log_path)
        self.runner = ParallelGeminiRunner(model_name=self.base_config.model_name)
        self.sequential = sequential

    def _build_logger(self, path: Path) -> logging.Logger:
        logger = logging.getLogger(f"MultiDocWorkflow-{id(self)}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        if self.verbose:
            console = logging.StreamHandler()
            console.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(console)
        return logger

    def run(
        self, user_query: str, papers: List[Tuple[str, Dict[str, Any]]]
    ) -> GlobalGraphResult:
        self.logger.info(
            "Starting multi-document workflow for query '%s' over %d papers",
            user_query,
            len(papers),
        )
        document_results: List[SectionWorkflowResult] = []

        for paper_id, paper_data in papers:
            run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            per_log_path = self.log_dir / f"{paper_id}_{run_timestamp}.log"
            per_config = replace(self.base_config, user_query=user_query)
            workflow = SectionAwareWorkflow(
                config=per_config,
                verbose=self.verbose,
                log_path=str(per_log_path),
                sequential=self.sequential,
            )
            self.logger.info("Processing paper '%s'...", paper_id)
            result = workflow.run(paper_data, paper_id=paper_id)
            document_results.append(result)
            self.logger.info(
                "Completed paper '%s'. Initial nodes: %d, final nodes: %d, edges: %d",
                paper_id,
                len(result.initial_nodes),
                len(result.final_nodes),
                len(result.filtered_edges),
            )

        canonical_nodes = self._consolidate_global_nodes(document_results, user_query)
        edges = self._consolidate_global_edges(
            document_results, canonical_nodes, user_query
        )

        self.logger.info(
            "Global consolidation produced %d nodes and %d edges",
            len(canonical_nodes),
            len(edges),
        )

        return GlobalGraphResult(
            user_query=user_query,
            canonical_nodes=canonical_nodes,
            edges=edges,
            document_results=document_results,
        )

    def _consolidate_global_nodes(
        self, doc_results: List[SectionWorkflowResult], user_query: str
    ) -> List[GlobalNode]:
        if not doc_results:
            return []
        payload = [
            {"paper_id": res.paper_id, "nodes": res.final_nodes}
            for res in doc_results
        ]
        prompt = load_prompt(
            "global_nodes_consolidation.txt",
            per_document_nodes=json.dumps(payload, indent=2),
            user_query=user_query,
        )
        response = self.runner.run([prompt], max_workers=1)[0]
        data = self._parse_json(response, "global-nodes")
        nodes: List[GlobalNode] = []
        if isinstance(data, list):
            for item in data:
                nodes.append(
                    GlobalNode(
                        name=item.get("name", "").strip(),
                        type=item.get("type", "").strip(),
                        summary=item.get("summary", "").strip(),
                        sources=item.get("source_nodes", []),
                    )
                )
        else:
            self.logger.warning(
                "Global node consolidation returned non-list payload: %s", data
            )
        return nodes

    def _consolidate_global_edges(
        self,
        doc_results: List[SectionWorkflowResult],
        canonical_nodes: List[GlobalNode],
        user_query: str,
    ) -> List[GlobalEdge]:
        if not doc_results:
            return []

        canonical_payload = [
            {
                "name": node.name,
                "type": node.type,
                "summary": node.summary,
                "source_nodes": node.sources,
            }
            for node in canonical_nodes
        ]

        edges_payload = []
        for res in doc_results:
            edges_payload.append(
                {
                    "paper_id": res.paper_id,
                    "edges": [
                        {
                            "source": edge.source,
                            "target": edge.target,
                            "relation": edge.relation,
                            "count": edge.count,
                            "evidence_samples": edge.evidence_samples,
                            "sections": edge.sections,
                        }
                        for edge in res.filtered_edges
                    ],
                }
            )

        prompt = load_prompt(
            "global_edges_consolidation.txt",
            canonical_nodes=json.dumps(canonical_payload, indent=2),
            per_document_edges=json.dumps(edges_payload, indent=2),
            user_query=user_query,
        )
        response = self.runner.run([prompt], max_workers=1)[0]
        data = self._parse_json(response, "global-edges")
        edges: List[GlobalEdge] = []

        edge_list = data.get("edges") if isinstance(data, dict) else None
        if isinstance(edge_list, list):
            for edge in edge_list:
                count = int(edge.get("count", 1))
                source_papers = edge.get("source_papers", [])
                edges.append(
                    GlobalEdge(
                        source=edge.get("source", "").strip(),
                        target=edge.get("target", "").strip(),
                        relation=edge.get("relation", "").strip(),
                        count=count,
                        evidence_samples=edge.get("evidence_samples", []),
                        source_papers=source_papers,
                        confidence=count / max(1, len(doc_results)),
                    )
                )
        else:
            self.logger.warning(
                "Global edge consolidation returned unexpected payload: %s", data
            )
        return edges

    def _parse_json(self, payload: str, context: str) -> Any:
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
            self.logger.warning(
                "Failed to parse JSON in context '%s'. Payload snippet: %s",
                context,
                payload[:400],
            )
            return [] if "edges" not in context else {"edges": []}

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()


class ParallelGeminiRunner:
    """Utility to run Gemini prompts in parallel with graceful fallback."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.max_retries = 3

    def _call_model(self, prompt: str) -> str:
        client = genai.Client()
        def _invoke():
            return client.models.generate_content(
                model=self.model_name,
                contents=[prompt],
            )

        attempt = 0
        while True:
            try:
                response = call_with_backoff(_invoke)
                return response.text
            except Exception as exc:
                attempt += 1
                if attempt >= self.max_retries:
                    raise
                wait = min(5 * attempt, 30)
                time.sleep(wait)

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
        sequential: bool = False,
    ):
        self.config = config or StageRunConfig()
        self.runner = ParallelGeminiRunner(model_name=self.config.model_name)
        self.verbose = verbose
        self.sequential = sequential
        self.user_query = self.config.user_query
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
    def run(self, paper: Dict[str, Any], paper_id: str = "document") -> SectionWorkflowResult:
        abstract = paper.get("abstract", "")
        results_text = paper.get("results", "")
        methodology_text = paper.get("methodology", "")
        discussion_text = paper.get("discussion", "")
        self._log(f"Starting workflow for paper '{paper_id}'", level="info")

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
            paper_id=paper_id,
            initial_nodes=initial_nodes,
            final_nodes=final_nodes,
            raw_edges=raw_edges,
            consolidated_edges=consolidated_edges,
            filtered_edges=filtered_edges,
        )

    # Stage helpers --------------------------------------------------------------
    def _run_stage1_initial_nodes(self, abstract: str) -> List[List[Dict[str, Any]]]:
        prompts = [
            load_prompt(
                "stage1_initial_nodes_prompt.txt",
                abstract=abstract,
                user_query=self.user_query,
            )
            for _ in range(self.config.stage1_runs)
        ]
        max_workers = 1 if self.sequential else self.config.stage1_runs
        responses = self.runner.run(prompts, max_workers=max_workers)
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
            "stage1_initial_nodes_consolidation.txt",
            raw_node_lists=raw_node_lists,
            user_query=self.user_query,
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
                user_query=self.user_query,
            )
            for _ in range(self.config.stage3_runs)
        ]
        max_workers = 1 if self.sequential else self.config.stage3_runs
        responses = self.runner.run(prompts, max_workers=max_workers)
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
            user_query=self.user_query,
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
                user_query=self.user_query,
            )
            for _ in range(self.config.stage5_runs)
        ]
        max_workers = 1 if self.sequential else self.config.stage5_runs
        responses = self.runner.run(prompts, max_workers=max_workers)
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
            user_query=self.user_query,
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

