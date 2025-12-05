import React, { useState, useMemo, useCallback } from 'react';
import GraphVisualization from './GraphVisualization';
import GraphDetailsPanel from './GraphDetailsPanel';
import GraphLegend from './GraphLegend';
import MultiGraphTabs from './MultiGraphTabs';
import { transformGraphData, hasGraphContent } from '../utils/transformGraphData';

/**
 * GraphVisualizationContainer Component
 * -------------------------------------
 * Parent container managing graph visualization state and child components.
 * Handles both single and multi-paper extraction results.
 */
export default function GraphVisualizationContainer({ results }) {
  const [selectedElement, setSelectedElement] = useState(null);
  const [activeGraphIndex, setActiveGraphIndex] = useState(0);

  // Stable callback references to prevent Cytoscape recreation
  const handleElementSelect = useCallback((element) => {
    setSelectedElement(element);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedElement(null);
  }, []);

  // Transform API data to Cytoscape format
  const transformedData = useMemo(() => transformGraphData(results), [results]);

  // Handle empty or invalid data
  if (!transformedData || transformedData.type === 'unknown') {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center text-slate-400">
          <p className="text-lg mb-2">No graph data available</p>
          <p className="text-sm">Unable to parse extraction results.</p>
        </div>
      </div>
    );
  }

  // Handle single extraction
  if (transformedData.type === 'single') {
    const graphData = transformedData.data;

    if (!hasGraphContent(graphData)) {
      return (
        <div className="h-full flex items-center justify-center p-6">
          <div className="text-center text-slate-400">
            <p className="text-lg mb-2">No causal relationships found</p>
            <p className="text-sm">
              The extraction did not identify any entities or relationships.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col p-4 gap-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-white">
            Causal Graph Visualization
          </h2>
        </div>

        {/* Main content: Graph + Sidebar */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Graph container */}
          <div className="flex-1 min-w-0">
            <GraphVisualization
              graphData={graphData}
              onElementSelect={handleElementSelect}
              onBackgroundClick={handleBackgroundClick}
            />
          </div>

          {/* Sidebar with legend and details */}
          <div className="w-64 flex flex-col gap-4 overflow-y-auto">
            <GraphLegend />
            <GraphDetailsPanel
              selectedElement={selectedElement}
              onClose={() => setSelectedElement(null)}
            />
          </div>
        </div>
      </div>
    );
  }

  // Handle multi-extraction
  if (transformedData.type === 'multi') {
    const { graphs, summary } = transformedData.data;

    if (!graphs || graphs.length === 0) {
      return (
        <div className="h-full flex items-center justify-center p-6">
          <div className="text-center text-slate-400">
            <p className="text-lg mb-2">No graphs available</p>
            <p className="text-sm">
              Multi-extraction completed but no graphs were generated.
            </p>
          </div>
        </div>
      );
    }

    const currentGraph = graphs[activeGraphIndex];

    return (
      <div className="h-full flex flex-col p-4 gap-4">
        {/* Header with summary */}
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Multi-Paper Causal Graphs
            </h2>
            <p className="text-sm text-slate-400">
              {summary.successful || graphs.length} extracted successfully
              {summary.failed > 0 && (
                <span className="text-red-400 ml-2">
                  • {summary.failed} failed
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Tabs for graph selection */}
        <MultiGraphTabs
          graphs={graphs}
          activeIndex={activeGraphIndex}
          onChange={(index) => {
            setActiveGraphIndex(index);
            setSelectedElement(null); // Clear selection when switching graphs
          }}
        />

        {/* Main content: Graph + Sidebar */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Graph container */}
          <div className="flex-1 min-w-0">
            {hasGraphContent(currentGraph) ? (
              <GraphVisualization
                graphData={currentGraph}
                onElementSelect={handleElementSelect}
                onBackgroundClick={handleBackgroundClick}
              />
            ) : (
              <div className="h-full flex items-center justify-center bg-slate-900 rounded-lg border border-slate-700">
                <p className="text-slate-400">
                  No relationships found in this paper
                </p>
              </div>
            )}
          </div>

          {/* Sidebar with legend and details */}
          <div className="w-64 flex flex-col gap-4 overflow-y-auto">
            <GraphLegend />
            <GraphDetailsPanel
              selectedElement={selectedElement}
              onClose={() => setSelectedElement(null)}
            />
          </div>
        </div>
      </div>
    );
  }

  return null;
}
