/**
 * Graph Data Transformation Utilities
 * ------------------------------------
 * Transform backend API responses into Cytoscape-compatible format.
 */

/**
 * Filter out isolated nodes (nodes with no edges)
 *
 * @param {Array} nodes - Array of node objects
 * @param {Array} edges - Array of edge objects
 * @returns {Object} { filteredNodes, edges }
 */
function filterIsolatedNodes(nodes, edges) {
  // Get all node IDs that are referenced in edges
  const connectedNodeIds = new Set();
  edges.forEach(edge => {
    if (edge.data) {
      connectedNodeIds.add(edge.data.source);
      connectedNodeIds.add(edge.data.target);
    }
  });

  // Filter nodes to only include those with connections
  const filteredNodes = nodes.filter(node =>
    node.data && connectedNodeIds.has(node.data.id)
  );

  return { filteredNodes, edges };
}

/**
 * Transform single extraction result to Cytoscape format
 *
 * Backend returns: { elements: { nodes: [...], edges: [...] } }
 * Cytoscape expects: { elements: [...nodes, ...edges] } (flat array)
 *
 * @param {Object} apiData - API response from single extraction
 * @returns {Object} Cytoscape-compatible graph data
 */
export function transformSingleGraph(apiData) {
  if (!apiData || !apiData.elements) {
    return { elements: [], metadata: null };
  }

  const { nodes = [], edges = [] } = apiData.elements;
  const metadata = apiData.metadata || {};

  // Filter out isolated nodes
  const { filteredNodes } = filterIsolatedNodes(nodes, edges);

  return {
    elements: [...filteredNodes, ...edges],
    metadata: {
      paperId: metadata.paper_id,
      numEntities: metadata.num_entities || nodes.length,
      numRelationships: metadata.num_relationships || edges.length,
      connectedNodes: filteredNodes.length,  // Track filtered count
      ...metadata
    }
  };
}

/**
 * Transform multi-extraction result to array of Cytoscape graphs
 *
 * Backend returns: { graphs: [{...}, {...}], summary: {...} }
 * Returns: Array of transformed graphs with metadata
 *
 * @param {Object} apiData - API response from multi-extraction
 * @returns {Object} { graphs: [...], summary: {...} }
 */
export function transformMultiGraph(apiData) {
  if (!apiData || !apiData.graphs) {
    return { graphs: [], summary: {}, failedPapers: [] };
  }

  const graphs = apiData.graphs.map((graph, index) => {
    const transformed = transformSingleGraph(graph);
    return {
      ...transformed,
      index,
      title: graph.metadata?.paper_id || `Graph ${index + 1}`,
      paperId: graph.metadata?.paper_id
    };
  });

  return {
    graphs,
    summary: apiData.summary || {},
    failedPapers: apiData.failed_papers || []
  };
}

/**
 * Auto-detect extraction type and transform accordingly
 *
 * @param {Object} apiData - API response (single or multi)
 * @returns {Object} Transformed data with type indicator
 */
export function transformGraphData(apiData) {
  if (!apiData) {
    return { type: 'empty', data: null };
  }

  // Multi-extraction (has graphs array)
  if (apiData.graphs && Array.isArray(apiData.graphs)) {
    return {
      type: 'multi',
      data: transformMultiGraph(apiData)
    };
  }

  // Single extraction (has elements object)
  if (apiData.elements) {
    return {
      type: 'single',
      data: transformSingleGraph(apiData)
    };
  }

  // Unknown format
  console.warn('Unknown graph data format:', apiData);
  return { type: 'unknown', data: null };
}

/**
 * Check if graph has any nodes or edges
 *
 * @param {Object} graphData - Transformed graph data
 * @returns {boolean} True if graph has content
 */
export function hasGraphContent(graphData) {
  if (!graphData || !graphData.elements) {
    return false;
  }

  return Array.isArray(graphData.elements) && graphData.elements.length > 0;
}

/**
 * Get node and edge counts from graph data
 *
 * @param {Object} graphData - Transformed graph data
 * @returns {Object} { nodes: number, edges: number }
 */
export function getGraphStats(graphData) {
  if (!graphData || !graphData.elements) {
    return { nodes: 0, edges: 0 };
  }

  const elements = graphData.elements;
  const nodes = elements.filter(el => el.data && !el.data.source).length;
  const edges = elements.filter(el => el.data && el.data.source).length;

  return { nodes, edges };
}

/**
 * Format confidence score for display
 *
 * @param {number} confidence - Confidence value (0-1)
 * @returns {string} Formatted percentage
 */
export function formatConfidence(confidence) {
  if (typeof confidence !== 'number') return 'N/A';
  return `${(confidence * 100).toFixed(0)}%`;
}

/**
 * Get display color for node type
 *
 * @param {string} nodeType - Entity type (material, process, structure, property)
 * @returns {string} Hex color code
 */
export function getNodeTypeColor(nodeType) {
  const colors = {
    material: '#4f81bd',
    process: '#f79646',
    structure: '#9bbb59',
    property: '#8064a2'
  };
  return colors[nodeType?.toLowerCase()] || '#607d8b';
}

/**
 * Get display color for edge relation
 *
 * @param {string} relation - Relationship type
 * @returns {string} Hex color code
 */
export function getEdgeRelationColor(relation) {
  const colors = {
    'increases': '#4caf50',
    'decreases': '#e53935',
    'causes': '#fb8c00',
    'positively correlates with': '#00897b',
    'negatively correlates with': '#ad1457'
  };
  return colors[relation?.toLowerCase()] || '#546e7a';
}
