"""
Monte Carlo Evidence-Based Causal Relationship Extractor

This module implements a two-stage approach:
1. Stage 1: Multiple runs to discover entities and relationships
2. Stage 2: Entity consolidation and relationship validation
3. Mathematical causal graph construction
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict, Counter
import random
import json
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import datetime, UTC

from google import genai
from google.genai import types, errors
import google.auth
from ...schema import (
    Entity, EntityType, Relationship, RelationType,
    ModelConfig, ExtractionResult
)
from ..base import BaseLLM
from ...prompts import load_prompt
from .gemini import GeminiTextRelationExtractor, call_with_backoff
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EntityEvidence:
    """Evidence for an entity across multiple runs."""
    canonical_name: str
    entity_type: EntityType
    variations: List[str]
    frequency: int
    confidence: float


@dataclass
class RelationshipEvidence:
    """Evidence for a relationship across multiple runs."""
    subject: EntityEvidence
    object: EntityEvidence
    relation_type: RelationType
    frequency: int
    confidence: float
    variations: List[Dict[str, Any]]


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo extraction."""
    entities: List[EntityEvidence]
    relationships: List[RelationshipEvidence]
    raw_runs: List[List[Dict[str, Any]]]
    metadata: Dict[str, Any]


class MonteCarloEvidenceExtractor(BaseLLM):
    """Evidence-based causal relationship extractor using Monte Carlo sampling."""
    
    def __init__(
        self, 
        base_extractor: Optional[GeminiTextRelationExtractor] = None,
        n_runs: int = 5,
        confidence_threshold: float = 0.6,
        entity_similarity_threshold: float = 0.8
    ):
        """Initialize the Monte Carlo evidence extractor.
        
        Args:
            base_extractor: Base Gemini extractor to use
            n_runs: Number of Monte Carlo runs
            confidence_threshold: Minimum confidence for relationships
            entity_similarity_threshold: Threshold for entity name similarity
        """
        self.base_extractor = base_extractor or GeminiTextRelationExtractor()
        self.n_runs = n_runs
        self.confidence_threshold = confidence_threshold
        self.entity_similarity_threshold = entity_similarity_threshold

        # Initialize Gemini client for entity consolidation using Vertex AI
        credentials, project_id = google.auth.default()
        if not project_id:
            raise ValueError(
                "Unable to determine GCP project. "
                "Run 'gcloud auth application-default login' and ensure a project is set."
            )

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location='us-central1'
        )
    
    def extract_relations_with_evidence(self, text: str) -> MonteCarloResult:
        """Extract relationships using Monte Carlo sampling for evidence gathering.
        
        Args:
            text: Input text to extract relationships from
            
        Returns:
            MonteCarloResult with evidence-based entities and relationships
        """
        logger.info(f"Starting Monte Carlo extraction with {self.n_runs} runs...")
        
        # Stage 1: Multiple runs to gather evidence
        raw_runs = self._stage1_multiple_runs(text)
        
        # Stage 2: Entity consolidation
        consolidated_entities = self._stage2_consolidate_entities(raw_runs, text)
        
        # Stage 3: Relationship validation and confidence scoring
        validated_relationships = self._stage3_validate_relationships(
            raw_runs, consolidated_entities
        )
        
        # Filter by confidence threshold
        filtered_relationships = [
            rel for rel in validated_relationships 
            if rel.confidence >= self.confidence_threshold
        ]
        
        return MonteCarloResult(
            entities=consolidated_entities,
            relationships=filtered_relationships,
            raw_runs=raw_runs,
            metadata={
                'n_runs': self.n_runs,
                'confidence_threshold': self.confidence_threshold,
                'total_relationships_found': len(validated_relationships),
                'relationships_above_threshold': len(filtered_relationships)
            }
        )
    
    def _stage1_multiple_runs(self, text: str) -> List[List[Dict[str, Any]]]:
        """Stage 1: Run multiple extractions with varying parameters."""
        logger.info("Stage 1: Running multiple extractions...")
        raw_runs = []

        for i in range(self.n_runs):
            logger.info(f"Running extraction {i+1}/{self.n_runs}...")
            
            # Vary temperature slightly for diversity
            temp = 0.3 + (i * 0.1) % 0.4  # Range: 0.3-0.7
            
            # Temporarily modify the base extractor's temperature
            original_temp = self.base_extractor.config.temperature
            self.base_extractor.config.temperature = temp
            
            try:
                # Extract relationships using the base extractor's prompt and response processing
                prompt = self.base_extractor._prepare_prompt(text)
                
                response = call_with_backoff(lambda: self.base_extractor.client.models.generate_content(
                    model=self.base_extractor.config.model_type,
                    contents=[prompt]
                ))
                
                # Process the response - Gemini's _process_response returns (relationships, response)
                result = self.base_extractor._process_response(response.text)
                if isinstance(result, tuple):
                    relationships, _ = result
                else:
                    relationships = result
                
                # relationships is already in dictionary format from parse_relationships
                raw_runs.append(relationships)
                logger.info(f"  Found {len(relationships)} relationships")

            except Exception as e:
                logger.error(f"  Error in run {i+1}: {e}")
                raw_runs.append([])
            
            finally:
                # Restore original temperature
                self.base_extractor.config.temperature = original_temp
        
        return raw_runs
    
    def _stage2_consolidate_entities(self, raw_runs: List[List[Dict]], text: str) -> List[EntityEvidence]:
        """Stage 2: Consolidate entities using LLM-based clustering."""
        logger.info("Stage 2: Consolidating entities...")

        # Collect all unique entities from all runs
        all_entities = self._collect_all_entities(raw_runs)

        # Use LLM to consolidate similar entities
        consolidated_entities = self._llm_consolidate_entities(all_entities, text)

        logger.info(f"Consolidated {len(all_entities)} entities into {len(consolidated_entities)} canonical entities")
        return consolidated_entities
    
    def _collect_all_entities(self, raw_runs: List[List[Dict]]) -> List[Dict[str, Any]]:
        """Collect all unique entities from all runs."""
        entity_set = set()
        
        for run in raw_runs:
            for rel in run:
                # Add subject entity
                subject_key = f"{rel['subject']['name']}|{rel['subject']['type']}"
                if subject_key not in entity_set:
                    entity_set.add(subject_key)
                
                # Add object entity
                object_key = f"{rel['object']['name']}|{rel['object']['type']}"
                if object_key not in entity_set:
                    entity_set.add(object_key)
        
        # Convert back to entity dictionaries
        entities = []
        for entity_key in entity_set:
            name, entity_type = entity_key.split('|', 1)
            entities.append({
                'name': name,
                'type': entity_type
            })
        
        return entities
    
    def _llm_consolidate_entities(self, entities: List[Dict], text: str) -> List[EntityEvidence]:
        """Use LLM to consolidate similar entities."""
        if not entities:
            return []
        
        # Create entity list for LLM
        entity_list = "\n".join([f"- {e['name']} ({e['type']})" for e in entities])
        
        # Load prompt and format with entity_list and text
        # Note: text truncation is commented out in the prompt file
        prompt = load_prompt("entity_consolidation.txt", entity_list=entity_list, text=text)
        
        try:
            response = call_with_backoff(lambda: self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt]
            ))

            logger.debug(f"LLM Response: {response.text[:200]}...")  # Debug output
            
            # Extract JSON from markdown code blocks if present
            json_text = response.text.strip()
            if json_text.startswith('```json'):
                # Remove markdown code block formatting
                json_text = json_text[7:]  # Remove ```json
                if json_text.endswith('```'):
                    json_text = json_text[:-3]  # Remove trailing ```
                json_text = json_text.strip()
            elif json_text.startswith('```'):
                # Remove generic code block formatting
                json_text = json_text[3:]  # Remove ```
                if json_text.endswith('```'):
                    json_text = json_text[:-3]  # Remove trailing ```
                json_text = json_text.strip()
            
            # Parse JSON response
            import json
            result = json.loads(json_text)
            
            # Convert to EntityEvidence objects
            consolidated_entities = []
            for entity_data in result.get('consolidated_entities', []):
                evidence = EntityEvidence(
                    canonical_name=entity_data['canonical_name'],
                    entity_type=EntityType(entity_data['entity_type']),
                    variations=entity_data['variations'],
                    frequency=self._calculate_entity_frequency(entity_data['variations'], entities),
                    confidence=self._calculate_entity_confidence(entity_data['variations'], entities)
                )
                consolidated_entities.append(evidence)
            
            return consolidated_entities

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in LLM entity consolidation: {e}")
            logger.debug(f"Response was: {response.text}")
            # Fallback to simple frequency-based consolidation
            return self._fallback_entity_consolidation(entities)
        except Exception as e:
            logger.error(f"Error in LLM entity consolidation: {e}")
            # Fallback to simple frequency-based consolidation
            return self._fallback_entity_consolidation(entities)
    
    def _calculate_entity_frequency(self, variations: List[str], all_entities: List[Dict]) -> int:
        """Calculate how often this entity appears across all runs."""
        frequency = 0
        for entity in all_entities:
            if any(self._similarity(entity['name'], var) > self.entity_similarity_threshold 
                   for var in variations):
                frequency += 1
        return frequency
    
    def _calculate_entity_confidence(self, variations: List[str], all_entities: List[Dict]) -> float:
        """Calculate confidence score for entity consolidation."""
        total_matches = 0
        total_entities = len(all_entities)
        
        for entity in all_entities:
            if any(self._similarity(entity['name'], var) > self.entity_similarity_threshold 
                   for var in variations):
                total_matches += 1
        
        return total_matches / total_entities if total_entities > 0 else 0.0
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate string similarity between two entity names."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def _fallback_entity_consolidation(self, entities: List[Dict]) -> List[EntityEvidence]:
        """Fallback entity consolidation using similarity matching."""
        consolidated = []
        processed = set()
        
        for entity in entities:
            entity_key = f"{entity['name']}|{entity['type']}"
            if entity_key in processed:
                continue
            
            # Find similar entities
            similar_entities = [entity]
            variations = [entity['name']]
            
            for other_entity in entities:
                other_key = f"{other_entity['name']}|{other_entity['type']}"
                if (other_key not in processed and 
                    other_entity['type'] == entity['type'] and
                    self._similarity(entity['name'], other_entity['name']) > self.entity_similarity_threshold):
                    similar_entities.append(other_entity)
                    variations.append(other_entity['name'])
                    processed.add(other_key)
            
            # Create EntityEvidence
            evidence = EntityEvidence(
                canonical_name=entity['name'],  # Use first name as canonical
                entity_type=EntityType(entity['type']),
                variations=variations,
                frequency=len(similar_entities),
                confidence=len(similar_entities) / len(entities)
            )
            consolidated.append(evidence)
            processed.add(entity_key)
        
        return consolidated
    
    def _clean_entity_name(self, entity_name: str) -> str:
        """Clean entity name by removing brackets and type information."""
        # Remove brackets if present: [temperature (process>)] -> temperature (process>)
        cleaned = entity_name.strip()
        if cleaned.startswith('[') and cleaned.endswith(']'):
            cleaned = cleaned[1:-1].strip()
        if cleaned.startswith('['):
            cleaned = cleaned[1:].strip()
        if cleaned.endswith(']') or cleaned.endswith('>'):
            cleaned = cleaned.rstrip(']>').strip()
        
        # Extract just the entity name part (before the type in parentheses)
        # e.g., "temperature (process)" -> "temperature"
        if '(' in cleaned:
            cleaned = cleaned.split('(')[0].strip()
        
        return cleaned.lower()
    
    def _stage3_validate_relationships(
        self, 
        raw_runs: List[List[Dict]], 
        consolidated_entities: List[EntityEvidence]
    ) -> List[RelationshipEvidence]:
        """Stage 3: Validate relationships against consolidated entities."""
        logger.info("Stage 3: Validating relationships...")
        
        # Map entity names to consolidated entities
        # Include both raw variations and cleaned versions for better matching
        entity_map = {}
        for entity_evidence in consolidated_entities:
            # Add canonical name
            cleaned_canonical = self._clean_entity_name(entity_evidence.canonical_name)
            entity_map[cleaned_canonical] = entity_evidence
            
            # Add all variations (both raw and cleaned)
            for variation in entity_evidence.variations:
                entity_map[variation.lower()] = entity_evidence
                cleaned_variation = self._clean_entity_name(variation)
                entity_map[cleaned_variation] = entity_evidence
        
        # Collect relationship evidence
        relationship_counts = defaultdict(list)
        
        for run_idx, run in enumerate(raw_runs):
            for rel in run:
                # Find matching consolidated entities
                subject_evidence = self._find_matching_entity(rel['subject']['name'], entity_map)
                object_evidence = self._find_matching_entity(rel['object']['name'], entity_map)
                
                if subject_evidence and object_evidence:
                    # Create relationship key
                    rel_key = (
                        subject_evidence.canonical_name,
                        rel['relationship'],
                        object_evidence.canonical_name
                    )
                    relationship_counts[rel_key].append({
                        'subject': subject_evidence,
                        'object': object_evidence,
                        'relation_type': RelationType(rel['relationship']),
                        'run_idx': run_idx
                    })
        
        # Create RelationshipEvidence objects
        relationship_evidence = []
        for rel_key, variations in relationship_counts.items():
            if len(variations) > 0:
                first_variation = variations[0]
                evidence = RelationshipEvidence(
                    subject=first_variation['subject'],
                    object=first_variation['object'],
                    relation_type=first_variation['relation_type'],
                    frequency=len(variations),
                    confidence=len(variations) / self.n_runs,
                    variations=variations
                )
                relationship_evidence.append(evidence)
        
        logger.info(f"Validated {len(relationship_evidence)} relationships")
        return relationship_evidence
    
    def _find_matching_entity(self, entity_name: str, entity_map: Dict[str, EntityEvidence]) -> Optional[EntityEvidence]:
        """Find the consolidated entity that matches the given name."""
        # Clean the entity name first
        cleaned_name = self._clean_entity_name(entity_name)
        
        # Direct match on cleaned name
        if cleaned_name in entity_map:
            return entity_map[cleaned_name]
        
        # Also check against all variations in the entity_map
        for mapped_name, entity_evidence in entity_map.items():
            # Check if cleaned name matches any variation
            for variation in entity_evidence.variations:
                if self._clean_entity_name(variation) == cleaned_name:
                    return entity_evidence
        
        # Similarity match as fallback
        best_match = None
        best_similarity = 0
        
        for mapped_name, entity_evidence in entity_map.items():
            similarity = self._similarity(cleaned_name, mapped_name)
            if similarity > best_similarity and similarity > self.entity_similarity_threshold:
                best_similarity = similarity
                best_match = entity_evidence
        
        return best_match
    
    def build_causal_graph(self, result: MonteCarloResult) -> Dict[str, Any]:
        """Build a mathematical causal graph from the evidence."""
        logger.info("Building mathematical causal graph...")
        
        # Create adjacency matrix representation
        entities = result.entities
        relationships = result.relationships
        
        # Build entity index
        entity_index = {entity.canonical_name: i for i, entity in enumerate(entities)}
        
        # Initialize adjacency matrix
        n_entities = len(entities)
        adjacency_matrix = [[0.0 for _ in range(n_entities)] for _ in range(n_entities)]
        relationship_types = [[None for _ in range(n_entities)] for _ in range(n_entities)]
        
        # Fill adjacency matrix with confidence scores
        for rel in relationships:
            i = entity_index[rel.subject.canonical_name]
            j = entity_index[rel.object.canonical_name]
            
            # Use confidence as edge weight
            adjacency_matrix[i][j] = rel.confidence
            relationship_types[i][j] = rel.relation_type.value
        
        # Calculate graph metrics
        graph_metrics = self._calculate_graph_metrics(adjacency_matrix, entities)
        
        # Identify causal pathways
        causal_pathways = self._identify_causal_pathways(adjacency_matrix, entities)
        
        return {
            'adjacency_matrix': adjacency_matrix,
            'relationship_types': relationship_types,
            'entities': [entity.canonical_name for entity in entities],
            'graph_metrics': graph_metrics,
            'causal_pathways': causal_pathways,
            'relationships': [
                {
                    'subject': rel.subject.canonical_name,
                    'object': rel.object.canonical_name,
                    'relation_type': rel.relation_type.value,
                    'confidence': rel.confidence,
                    'frequency': rel.frequency
                }
                for rel in relationships
            ]
        }
    
    def _calculate_graph_metrics(self, adjacency_matrix: List[List[float]], entities: List[EntityEvidence]) -> Dict[str, Any]:
        """Calculate mathematical metrics for the causal graph."""
        n = len(adjacency_matrix)
        
        # Calculate node degrees
        in_degrees = [sum(adjacency_matrix[j][i] for j in range(n)) for i in range(n)]
        out_degrees = [sum(adjacency_matrix[i][j] for j in range(n)) for i in range(n)]
        
        # Calculate centrality measures
        centrality_measures = {}
        for i, entity in enumerate(entities):
            centrality_measures[entity.canonical_name] = {
                'in_degree': in_degrees[i],
                'out_degree': out_degrees[i],
                'total_degree': in_degrees[i] + out_degrees[i],
                'betweenness_centrality': self._calculate_betweenness_centrality(adjacency_matrix, i)
            }
        
        return {
            'centrality_measures': centrality_measures,
            'total_nodes': n,
            'total_edges': sum(sum(1 for val in row if val > 0) for row in adjacency_matrix),
            'density': self._calculate_graph_density(adjacency_matrix)
        }
    
    def _calculate_betweenness_centrality(self, adjacency_matrix: List[List[float]], node: int) -> float:
        """Calculate betweenness centrality for a node."""
        n = len(adjacency_matrix)
        centrality = 0.0
        
        for s in range(n):
            for t in range(n):
                if s != t and s != node and t != node:
                    # Simple shortest path calculation
                    if adjacency_matrix[s][node] > 0 and adjacency_matrix[node][t] > 0:
                        centrality += 1
        
        return centrality / ((n - 1) * (n - 2)) if n > 2 else 0.0
    
    def _calculate_graph_density(self, adjacency_matrix: List[List[float]]) -> float:
        """Calculate graph density."""
        n = len(adjacency_matrix)
        if n <= 1:
            return 0.0
        
        total_possible_edges = n * (n - 1)
        actual_edges = sum(sum(1 for val in row if val > 0) for row in adjacency_matrix)
        
        return actual_edges / total_possible_edges
    
    def _identify_causal_pathways(self, adjacency_matrix: List[List[float]], entities: List[EntityEvidence]) -> List[List[str]]:
        """Identify important causal pathways in the graph."""
        n = len(adjacency_matrix)
        pathways = []
        
        # Find paths of length 2 and 3
        for i in range(n):
            for j in range(n):
                if adjacency_matrix[i][j] > 0:  # Direct connection
                    # Look for paths of length 2
                    for k in range(n):
                        if adjacency_matrix[j][k] > 0 and k != i:
                            pathway = [
                                entities[i].canonical_name,
                                entities[j].canonical_name,
                                entities[k].canonical_name
                            ]
                            pathways.append(pathway)
        
        return pathways[:10]  # Return top 10 pathways
    
    def extract_relations(self, text: str) -> List[Relationship]:
        """Compatibility method for BaseLLM interface."""
        result = self.extract_relations_with_evidence(text)
        
        # Convert back to Relationship objects
        relationships = []
        for rel_evidence in result.relationships:
            subject_entity = Entity(
                text=rel_evidence.subject.canonical_name,
                type=rel_evidence.subject.entity_type
            )
            object_entity = Entity(
                text=rel_evidence.object.canonical_name,
                type=rel_evidence.object.entity_type
            )
            
            relationship = Relationship(
                subject=subject_entity,
                object=object_entity,
                relation_type=rel_evidence.relation_type
            )
            relationships.append(relationship)
        
        return relationships
    
    def _prepare_prompt(self, text: str) -> str:
        """Prepare prompt for the base extractor (delegates to base extractor)."""
        return self.base_extractor._prepare_prompt(text)
    
    def _process_response(self, response: Any) -> List[Relationship]:
        """Process response from the base extractor (delegates to base extractor)."""
        return self.base_extractor._process_response(response)


# =======================
# Module-Level Functions
# =======================

def convert_to_cytoscape(mc_result, causal_graph, paper_id) -> dict:
    """
    Convert Monte Carlo results to Cytoscape format.

    Matches the format from graph_renderer.py for consistency with Python visualization.

    Args:
        mc_result: MonteCarloResult with entities and relationships
        causal_graph: Causal graph data from build_causal_graph()
        paper_id: Paper identifier

    Returns:
        dict: Cytoscape graph data with elements (nodes, edges) and metadata
    """
    # Color schemes matching graph_renderer.py
    NODE_COLORS = {
        "material": "#4f81bd",
        "process": "#f79646",
        "structure": "#9bbb59",
        "property": "#8064a2",
    }

    EDGE_COLORS = {
        "increases": "#4caf50",
        "decreases": "#e53935",
        "causes": "#fb8c00",
        "positively correlates with": "#00897b",
        "negatively correlates with": "#ad1457",
    }

    nodes = []
    edges = []

    # Convert entities to nodes
    for idx, entity in enumerate(mc_result.entities):
        # Sanitize ID (remove special chars)
        sanitized_name = "".join(ch if ch.isalnum() else "_" for ch in entity.canonical_name.lower())
        node_id = f"{paper_id}_node_{idx}_{sanitized_name}"
        entity_type = entity.entity_type.value.lower()

        nodes.append({
            "data": {
                "id": node_id,
                "label": entity.canonical_name,
                "type": entity_type,
                "summary": f"Appears {entity.frequency} times across extractions",
                "variations": entity.variations,
                "frequency": entity.frequency,
                "confidence": entity.confidence,
                "color": NODE_COLORS.get(entity_type, "#607d8b"),
            }
        })

    # Build entity name to node ID mapping
    name_to_id = {}
    for node in nodes:
        label = node["data"]["label"]
        node_id = node["data"]["id"]
        name_to_id[label] = node_id
        name_to_id[label.lower()] = node_id

    # Convert relationships to edges
    for idx, relationship in enumerate(mc_result.relationships):
        source_name = relationship.subject.canonical_name
        target_name = relationship.object.canonical_name

        # Find source and target node IDs
        source_id = name_to_id.get(source_name) or name_to_id.get(source_name.lower())
        target_id = name_to_id.get(target_name) or name_to_id.get(target_name.lower())

        if not source_id or not target_id:
            logger.warning(f"Skipping edge: couldn't find nodes for {source_name} -> {target_name}")
            continue

        # Sanitize edge ID
        sanitized_source = "".join(ch if ch.isalnum() else "_" for ch in source_name.lower())
        sanitized_target = "".join(ch if ch.isalnum() else "_" for ch in target_name.lower())
        edge_id = f"{paper_id}_edge_{idx}_{sanitized_source}_{sanitized_target}"

        relation_type = relationship.relation_type.value.lower()

        edges.append({
            "data": {
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "relation": relationship.relation_type.value,
                "frequency": relationship.frequency,
                "confidence": relationship.confidence,
                "count": relationship.frequency,
                "color": EDGE_COLORS.get(relation_type, "#546e7a"),
                "evidence": [],  # Could add evidence samples if needed
            }
        })

    return {
        "elements": {
            "nodes": nodes,
            "edges": edges
        },
        "metadata": {
            "paper_id": paper_id,
            "num_entities": len(mc_result.entities),
            "num_relationships": len(mc_result.relationships),
            "num_nodes": len(nodes),
            "num_edges": len(edges),
            "graph_metrics": causal_graph.get("graph_metrics", {}),
        }
    }


def run_extraction(
    run_id: str,
    paper_id: str,
    job_id: str,
    n_runs: int = 5,
    confidence_threshold: float = 0.6,
    progress_callback=None
) -> dict:
    """
    Run Monte Carlo extraction on a single paper with GCS persistence.

    This is the main entry point for the extraction workflow.
    Follows the same pattern as document_preparation.article_retriever.run_retrieval()

    Args:
        run_id: Retrieval run ID (e.g., "retrieve_2025-12-01_143022")
        paper_id: Paper ID (e.g., "W1234567890")
        job_id: Extraction job ID (e.g., "extract_2025-12-01_143022")
        n_runs: Number of Monte Carlo runs (default: 5)
        confidence_threshold: Minimum confidence for relationships (default: 0.6)
        progress_callback: Optional callback(stage, status) for progress updates

    Returns:
        dict: Cytoscape graph data with nodes, edges, and metadata

    Raises:
        FileNotFoundError: If parsed data not found in GCS
        ValueError: If text quality is insufficient
    """
    from document_preparation.gcp_connector import GCPBucketConnector

    # Step 1: Fetch parsed paper from GCS
    if progress_callback:
        progress_callback("fetching", "Fetching parsed paper from GCS...")

    logger.info(f"Starting extraction for paper {paper_id} from run {run_id}")

    gcs_connector = GCPBucketConnector()
    try:
        parsed_data = gcs_connector.download_parsed_data_from_run(run_id, paper_id)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Parsed data not found for paper {paper_id} in run {run_id}. "
            f"Paper may not have been retrieved/parsed yet."
        )

    # Extract text - validation already happened during document preparation
    text = parsed_data.get('full_text', '')
    sections = parsed_data.get('sections', [])

    logger.info(f"Loaded parsed data: {len(text)} chars, {len(sections)} sections")

    # Step 2: Initialize and run Monte Carlo extraction
    if progress_callback:
        progress_callback("extraction", "Running Monte Carlo extraction...")

    logger.info(f"Initializing Monte Carlo extractor with {n_runs} runs")

    base_extractor = GeminiTextRelationExtractor()
    monte_carlo_extractor = MonteCarloEvidenceExtractor(
        base_extractor=base_extractor,
        n_runs=n_runs,
        confidence_threshold=confidence_threshold,
        entity_similarity_threshold=0.8
    )

    mc_result = monte_carlo_extractor.extract_relations_with_evidence(text)

    logger.info(
        f"Extraction complete: {len(mc_result.entities)} entities, "
        f"{len(mc_result.relationships)} relationships"
    )

    # Step 4: Build causal graph
    if progress_callback:
        progress_callback("graph_building", "Building causal graph...")

    causal_graph = monte_carlo_extractor.build_causal_graph(mc_result)

    # Step 5: Convert to Cytoscape format
    graph_data = convert_to_cytoscape(mc_result, causal_graph, paper_id)

    logger.info(
        f"Graph data prepared: {len(graph_data['elements']['nodes'])} nodes, "
        f"{len(graph_data['elements']['edges'])} edges"
    )

    # Step 6: Upload to GCS for persistence
    if progress_callback:
        progress_callback("uploading", "Uploading results to GCS...")

    try:
        # Upload graph data
        blob_name = f"extraction/{job_id}/graph_data.json"
        blob = gcs_connector.bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(graph_data, indent=2),
            content_type="application/json"
        )

        # Upload metadata
        metadata = {
            "job_id": job_id,
            "run_id": run_id,
            "paper_id": paper_id,
            "n_runs": n_runs,
            "timestamp": datetime.now(UTC).isoformat(),
            "num_entities": len(mc_result.entities),
            "num_relationships": len(mc_result.relationships)
        }
        blob_name = f"extraction/{job_id}/metadata.json"
        blob = gcs_connector.bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(metadata, indent=2),
            content_type="application/json"
        )

        logger.info(f"Saved extraction results to GCS: extraction/{job_id}/")

    except Exception as e:
        logger.error(f"Failed to upload extraction results to GCS: {e}")
        # Don't fail the job if GCS upload fails, just log the error

    return graph_data
