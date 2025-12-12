/**
 * Cytoscape.js Configuration
 * --------------------------
 * Styles, layouts, and color schemes for causal graph visualization.
 * Colors match backend definitions in monte_carlo_extractor.py
 */

// Node colors by entity type (matching backend)
export const NODE_COLORS = {
  material: '#4f81bd',   // Blue
  process: '#f79646',    // Orange
  structure: '#9bbb59',  // Green
  property: '#8064a2',   // Purple
  default: '#607d8b'     // Slate gray
};

// Edge colors by relation type (matching backend)
export const EDGE_COLORS = {
  increases: '#4caf50',                    // Green
  decreases: '#e53935',                    // Red
  causes: '#fb8c00',                       // Orange
  'positively correlates with': '#00897b', // Teal
  'negatively correlates with': '#ad1457', // Pink
  default: '#546e7a'                       // Slate gray
};

/**
 * Get Cytoscape style configuration
 */
export function getCytoscapeStyle() {
  return [
    // Base node style
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'color': '#ffffff',
        'text-outline-color': '#1e293b',
        'text-outline-width': 2,
        'font-size': 12,
        'font-weight': 'bold',
        'width': 'mapData(frequency, 1, 10, 50, 100)',
        'height': 'mapData(frequency, 1, 10, 50, 100)',
        'background-color': 'data(color)',
        'border-width': 2,
        'border-color': '#334155',
        'text-wrap': 'wrap',
        'text-max-width': 80,
        'selectable': true
      }
    },

    // Node type specific colors
    {
      selector: 'node[type="material"]',
      style: { 'background-color': NODE_COLORS.material }
    },
    {
      selector: 'node[type="process"]',
      style: { 'background-color': NODE_COLORS.process }
    },
    {
      selector: 'node[type="structure"]',
      style: { 'background-color': NODE_COLORS.structure }
    },
    {
      selector: 'node[type="property"]',
      style: { 'background-color': NODE_COLORS.property }
    },

    // Base edge style
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        'target-arrow-color': 'data(color)',
        'line-color': 'data(color)',
        'width': 'mapData(frequency, 1, 10, 2, 8)',
        'opacity': 0.8,
        'label': 'data(relation)',
        'font-size': 10,
        'color': '#cbd5e1',
        'text-background-color': '#1e293b',
        'text-background-opacity': 0.8,
        'text-background-padding': 2,
        'text-background-shape': 'roundrectangle',
        'edge-text-rotation': 'autorotate',
        'selectable': true
      }
    },

    // Edge relation specific colors
    {
      selector: 'edge[relation="increases"]',
      style: {
        'line-color': EDGE_COLORS.increases,
        'target-arrow-color': EDGE_COLORS.increases
      }
    },
    {
      selector: 'edge[relation="decreases"]',
      style: {
        'line-color': EDGE_COLORS.decreases,
        'target-arrow-color': EDGE_COLORS.decreases
      }
    },
    {
      selector: 'edge[relation="causes"]',
      style: {
        'line-color': EDGE_COLORS.causes,
        'target-arrow-color': EDGE_COLORS.causes
      }
    },
    {
      selector: 'edge[relation="positively correlates with"]',
      style: {
        'line-color': EDGE_COLORS['positively correlates with'],
        'target-arrow-color': EDGE_COLORS['positively correlates with']
      }
    },
    {
      selector: 'edge[relation="negatively correlates with"]',
      style: {
        'line-color': EDGE_COLORS['negatively correlates with'],
        'target-arrow-color': EDGE_COLORS['negatively correlates with']
      }
    },

    // Selected node style
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#ffa726',
        'overlay-color': '#ffa726',
        'overlay-opacity': 0.2,
        'overlay-padding': 4
      }
    },

    // Selected edge style
    {
      selector: 'edge:selected',
      style: {
        'width': 'mapData(frequency, 1, 10, 4, 12)',
        'line-color': '#ffa726',
        'target-arrow-color': '#ffa726',
        'opacity': 1
      }
    },

    // Hover effects
    {
      selector: 'node:active',
      style: {
        'overlay-color': '#42a5f5',
        'overlay-opacity': 0.3,
        'overlay-padding': 6
      }
    }
  ];
}

/**
 * Get Cola layout configuration (force-directed with physics)
 */
export function getColaLayout() {
  return {
    name: 'cola',
    animate: true,
    animationDuration: 1000,
    animationEasing: 'ease-out',
    maxSimulationTime: 3000,
    fit: true,
    padding: 30,
    nodeSpacing: 100,
    edgeLength: 150,
    edgeSymDiffLength: 100,
    edgeJaccardLength: 100,
    convergenceThreshold: 0.01,
    randomize: false,
    avoidOverlap: true,
    handleDisconnected: true,
    infinite: false
  };
}

/**
 * Get Cose layout configuration (fast physics-based)
 */
export function getCoseLayout() {
  return {
    name: 'cose',
    animate: false,
    animationDuration: 0,
    fit: true,
    padding: 30,
    nodeRepulsion: 8000,
    nodeOverlap: 20,
    idealEdgeLength: 150,
    edgeElasticity: 200,
    gravity: 1,
    numIter: 1000,
    randomize: false,
    infinite: false  // Ensures layout stops after numIter iterations
  };
}

/**
 * Get Circle layout configuration (simple circular arrangement)
 */
export function getCircleLayout() {
  return {
    name: 'circle',
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 30,
    avoidOverlap: true,
    radius: undefined,
    startAngle: 3 / 2 * Math.PI,
    sweep: undefined,
    clockwise: true,
    sort: undefined
  };
}

/**
 * Get Breadthfirst layout configuration (hierarchical tree)
 */
export function getBreadthfirstLayout() {
  return {
    name: 'breadthfirst',
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 30,
    directed: true,
    circle: false,
    grid: false,
    spacingFactor: 1.5,
    avoidOverlap: true
  };
}

/**
 * Get layout by name
 */
export function getLayout(layoutName = 'cola') {
  switch (layoutName.toLowerCase()) {
    case 'cola':
      return getColaLayout();
    case 'cose':
      return getCoseLayout();
    case 'circle':
      return getCircleLayout();
    case 'breadthfirst':
      return getBreadthfirstLayout();
    default:
      return getColaLayout();
  }
}
