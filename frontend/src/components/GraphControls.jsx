import React from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

/**
 * GraphControls Component
 * -----------------------
 * Toolbar with zoom and layout controls for the graph visualization.
 */
export default function GraphControls({ layoutName, onLayoutChange, cyRef }) {
  const handleZoomIn = () => {
    if (cyRef?.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
      cyRef.current.center();
    }
  };

  const handleZoomOut = () => {
    if (cyRef?.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
      cyRef.current.center();
    }
  };

  const handleResetView = () => {
    if (cyRef?.current) {
      cyRef.current.fit(undefined, 30);
    }
  };

  const layoutOptions = [
    { value: 'cola', label: 'Force-Directed (Cola)' },
    { value: 'cose', label: 'Physics (Cose)' },
    { value: 'circle', label: 'Circle' },
    { value: 'breadthfirst', label: 'Hierarchical' }
  ];

  return (
    <div className="flex items-center gap-2 bg-slate-800/50 rounded-lg p-2 border border-slate-700">
      {/* Zoom Controls */}
      <div className="flex items-center gap-1 pr-2 border-r border-slate-700">
        <button
          onClick={handleZoomIn}
          className="p-2 hover:bg-slate-700 rounded transition-colors text-slate-300 hover:text-white"
          title="Zoom In"
          aria-label="Zoom in"
        >
          <ZoomIn size={16} />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 hover:bg-slate-700 rounded transition-colors text-slate-300 hover:text-white"
          title="Zoom Out"
          aria-label="Zoom out"
        >
          <ZoomOut size={16} />
        </button>
        <button
          onClick={handleResetView}
          className="p-2 hover:bg-slate-700 rounded transition-colors text-slate-300 hover:text-white"
          title="Reset View"
          aria-label="Reset view"
        >
          <Maximize2 size={16} />
        </button>
      </div>

      {/* Layout Selector */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-400">Layout:</label>
        <select
          value={layoutName}
          onChange={(e) => onLayoutChange(e.target.value)}
          className="bg-slate-700 text-white text-sm rounded px-2 py-1 border border-slate-600 focus:border-blue-500 focus:outline-none"
        >
          {layoutOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
