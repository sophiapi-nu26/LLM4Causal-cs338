from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..workflows.section_pipeline import GlobalGraphResult, SectionWorkflowResult


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


def build_graph_data(result: GlobalGraphResult) -> Dict[str, Any]:
    """Convert a GlobalGraphResult into Cytoscape-compatible data."""

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids = set()

    for idx, node in enumerate(result.canonical_nodes):
        node_id = f"node_{idx}_{_sanitize_id(node.name)}"
        node_ids.add(node_id)
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": node.name,
                    "type": node.type,
                    "summary": node.summary,
                    "sources": node.sources,
                    "color": NODE_COLORS.get((node.type or "").lower(), "#607d8b"),
                }
            }
        )

    name_to_id: Dict[str, str] = {}
    for entry in nodes:
        label = entry["data"]["label"]
        node_id = entry["data"]["id"]
        name_to_id[label] = node_id
        name_to_id[label.lower()] = node_id

    for idx, edge in enumerate(result.edges):
        src_id = name_to_id.get(edge.source) or name_to_id.get(edge.source.lower())
        tgt_id = name_to_id.get(edge.target) or name_to_id.get(edge.target.lower())
        if not src_id or not tgt_id:
            # Skip edges whose nodes were filtered out.
            continue
        edge_id = f"edge_{idx}_{_sanitize_id(edge.source)}_{_sanitize_id(edge.target)}"
        edges.append(
            {
                "data": {
                    "id": edge_id,
                    "source": src_id,
                    "target": tgt_id,
                    "relation": edge.relation,
                    "count": edge.count,
                    "confidence": edge.confidence,
                    "source_papers": edge.source_papers,
                    "evidence": edge.evidence_samples,
                    "color": EDGE_COLORS.get((edge.relation or "").lower(), "#546e7a"),
                }
            }
        )

    return {
        "elements": {"nodes": nodes, "edges": edges},
        "metadata": {
            "query": result.user_query,
            "num_documents": len(result.document_results),
        },
    }


def build_graph_data_from_section(
    result: SectionWorkflowResult, user_query: str = ""
) -> Dict[str, Any]:
    """Build graph data from a single SectionWorkflowResult."""

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    name_to_id: Dict[str, str] = {}

    for idx, node in enumerate(result.final_nodes):
        name = node.get("name") or f"Node {idx+1}"
        node_type = (node.get("type") or "material").lower()
        node_id = f"{result.paper_id}_node_{idx}_{_sanitize_id(name)}"
        name_to_id[name] = node_id
        name_to_id[name.lower()] = node_id
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "label": name,
                    "type": node_type,
                    "summary": node.get("summary", ""),
                    "sources": [
                        {"paper_id": result.paper_id, "node_name": name}
                    ],
                    "color": NODE_COLORS.get(node_type, "#607d8b"),
                }
            }
        )

    for idx, edge in enumerate(result.filtered_edges):
        src_id = name_to_id.get(edge.source) or name_to_id.get(edge.source.lower())
        tgt_id = name_to_id.get(edge.target) or name_to_id.get(edge.target.lower())
        if not src_id or not tgt_id:
            continue
        edge_id = f"{result.paper_id}_edge_{idx}_{_sanitize_id(edge.source)}_{_sanitize_id(edge.target)}"
        edges.append(
            {
                "data": {
                    "id": edge_id,
                    "source": src_id,
                    "target": tgt_id,
                    "relation": edge.relation,
                    "count": edge.count,
                    "confidence": edge.confidence,
                    "source_papers": edge.source_papers or [result.paper_id],
                    "evidence": edge.evidence_samples,
                    "color": EDGE_COLORS.get((edge.relation or "").lower(), "#546e7a"),
                }
            }
        )

    return {
        "elements": {"nodes": nodes, "edges": edges},
        "metadata": {
            "query": user_query,
            "num_documents": 1,
            "paper_id": result.paper_id,
        },
    }


def render_graph_html(graph_data: Dict[str, Any], output_path: Path, title: str = "Causal Graph") -> None:
    """Write an interactive Cytoscape HTML visualization to the given path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    safe_json = json.dumps(graph_data).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__GRAPH_DATA__", safe_json).replace("__TITLE__", title)
    output_path.write_text(html, encoding="utf-8")


def _sanitize_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.lower())


HTML_TEMPLATE_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>__TITLE__</title>
  <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      display: flex;
      height: 100vh;
    }}
    #cy {{
      flex: 3;
      height: 100vh;
    }}
    #sidebar {{
      flex: 1;
      padding: 1rem;
      border-left: 1px solid #ddd;
      overflow-y: auto;
      background: #fafafa;
    }}
    .legend {{
      margin-bottom: 1rem;
    }}
    .legend h3 {{
      margin-top: 0;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      margin-bottom: 0.25rem;
    }}
    .legend-swatch {{
      width: 16px;
      height: 16px;
      margin-right: 0.5rem;
      border-radius: 3px;
    }}
    pre {{
      white-space: pre-wrap;
      font-size: 0.85rem;
    }}
  </style>
</head>
<body>
  <div id="cy"></div>
  <div id="sidebar">
    <h2>Details</h2>
    <div id="info">Click a node or edge to see details.</div>
    <div class="legend">
      <h3>Node Types</h3>
      <div class="legend-item"><div class="legend-swatch" style="background:__MAT__"></div>Material</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__PROC__"></div>Process</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__STRUCT__"></div>Structure</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__PROP__"></div>Property</div>
    </div>
    <div class="legend">
      <h3>Edge Types</h3>
      <div class="legend-item"><div class="legend-swatch" style="background:__INC__"></div>Increases</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__DEC__"></div>Decreases</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__CAUSE__"></div>Causes</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__POS__"></div>Positively correlates</div>
      <div class="legend-item"><div class="legend-swatch" style="background:__NEG__"></div>Negatively correlates</div>
    </div>
  </div>

  <script>
    const graphData = __GRAPH_DATA__;
    const elements = [].concat(graphData.elements.nodes, graphData.elements.edges);
    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: elements,
      style: [
        {{
          selector: 'node',
          style: {{
            'label': 'data(label)',
            'background-color': 'data(color)',
            'color': '#fff',
            'text-outline-width': 2,
            'text-outline-color': 'data(color)',
            'font-size': 12
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 2,
            'line-color': 'data(color)',
            'target-arrow-color': 'data(color)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }}
        }},
        {{
          selector: ':selected',
          style: {{
            'border-width': 3,
            'border-color': '#ffa726',
            'line-color': '#ffa726',
            'target-arrow-color': '#ffa726'
          }}
        }}
      ],
      layout: {{
        name: 'cose',
        padding: 20
      }}
    }});

    const info = document.getElementById('info');

    function renderNodeInfo(data) {{
      const sources = (data.sources || []).map(
        src => `- ${src.paper_id}: ${src.node_name}`
      ).join('\\n');

      return `
        <strong>Node:</strong> ${data.label} (${data.type})<br/>
        <strong>Summary:</strong> ${data.summary}<br/>
        <strong>Sources:</strong><br/>
        <pre>${sources || 'N/A'}</pre>
      `;
    }}

    function renderEdgeInfo(data) {{
      const evidence = (data.evidence || []).map(
        item => `- ${item}`
      ).join('\\n');
      const papers = (data.source_papers || []).join(', ');

      return `
        <strong>Edge:</strong> ${data.relation}<br/>
        <strong>Confidence:</strong> ${(data.confidence || 0).toFixed(2)} (count=${data.count})<br/>
        <strong>Evidence:</strong><br/>
        <pre>${evidence || 'N/A'}</pre>
        <strong>Source papers:</strong> ${papers || 'N/A'}
      `;
    }}

    cy.on('tap', 'node', (evt) => {{
      info.innerHTML = renderNodeInfo(evt.target.data());
    }});

    cy.on('tap', 'edge', (evt) => {{
      info.innerHTML = renderEdgeInfo(evt.target.data());
    }});

    cy.on('tap', (evt) => {{
      if (evt.target === cy) {{
        info.innerHTML = 'Click a node or edge to see details.';
      }}
    }});
  </script>
</body>
</html>
"""

HTML_TEMPLATE = (
    HTML_TEMPLATE_BASE
    .replace("__MAT__", NODE_COLORS["material"])
    .replace("__PROC__", NODE_COLORS["process"])
    .replace("__STRUCT__", NODE_COLORS["structure"])
    .replace("__PROP__", NODE_COLORS["property"])
    .replace("__INC__", EDGE_COLORS["increases"])
    .replace("__DEC__", EDGE_COLORS["decreases"])
    .replace("__CAUSE__", EDGE_COLORS["causes"])
    .replace("__POS__", EDGE_COLORS["positively correlates with"])
    .replace("__NEG__", EDGE_COLORS["negatively correlates with"])
    .replace("{{", "{")
    .replace("}}", "}")
)

