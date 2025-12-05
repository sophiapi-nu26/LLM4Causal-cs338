import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { getCytoscapeStyle, getCoseLayout } from '../utils/cytoscapeConfig';

/**
 * GraphVisualization Component
 * ----------------------------
 * Core Cytoscape.js visualization component.
 * Renders interactive causal graphs with nodes (entities) and edges (relationships).
 * Uses Cose layout (physics-based) and prevents node movement after initial layout.
 */
export default function GraphVisualization({
  graphData,
  onElementSelect,
  onBackgroundClick
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  // Initialize Cytoscape instance
  useEffect(() => {
    if (!containerRef.current || !graphData || !graphData.elements) {
      return;
    }

    // Destroy existing instance if present
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    try {
      // Create new Cytoscape instance with Cose layout
      cyRef.current = cytoscape({
        container: containerRef.current,
        elements: graphData.elements,
        style: getCytoscapeStyle(),
        minZoom: 0.3,
        maxZoom: 3,
        wheelSensitivity: 0.2,
        boxSelectionEnabled: false,
        autounselectify: false,
        autoungrabify: true,  // Prevent node dragging
        userZoomingEnabled: true,
        userPanningEnabled: true,
        animate: false,
        pixelRatio: 'auto'
      });

      // Run Cose layout and make static after completion
      const layout = cyRef.current.layout(getCoseLayout());

      layout.on('layoutstop', () => {
        // Lock nodes in place after layout completes
        if (cyRef.current) {
          cyRef.current.nodes().lock();
        }
      });

      layout.run();

      // Node selection handler
      cyRef.current.on('tap', 'node', (event) => {
        if (!cyRef.current) return;
        const node = event.target;
        if (onElementSelect) {
          onElementSelect({
            type: 'node',
            data: {
              id: node.id(),
              label: node.data('label'),
              entityType: node.data('type'),
              frequency: node.data('frequency'),
              confidence: node.data('confidence'),
              summary: node.data('summary'),
              variations: node.data('variations'),
              color: node.data('color')
            }
          });
        }
      });

      // Edge selection handler
      cyRef.current.on('tap', 'edge', (event) => {
        if (!cyRef.current) return;
        const edge = event.target;
        if (onElementSelect) {
          onElementSelect({
            type: 'edge',
            data: {
              id: edge.id(),
              source: edge.source().data('label'),
              target: edge.target().data('label'),
              relation: edge.data('relation'),
              frequency: edge.data('frequency'),
              confidence: edge.data('confidence'),
              evidence: edge.data('evidence'),
              sourcePapers: edge.data('source_papers'),
              color: edge.data('color')
            }
          });
        }
      });

      // Background click handler
      cyRef.current.on('tap', (event) => {
        if (!cyRef.current) return;
        if (event.target === cyRef.current) {
          if (onBackgroundClick) {
            onBackgroundClick();
          }
        }
      });

    } catch (error) {
      console.error('Error initializing Cytoscape:', error);
    }

    // Cleanup on unmount or data change
    return () => {
      if (cyRef.current) {
        // Remove all event handlers before destroying
        cyRef.current.removeAllListeners();
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData, onElementSelect, onBackgroundClick]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-slate-900 rounded-lg border border-slate-700"
      style={{ minHeight: '500px' }}
    />
  );
}
