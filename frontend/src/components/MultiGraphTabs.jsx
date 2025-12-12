import React from 'react';
import { getGraphStats } from '../utils/transformGraphData';

/**
 * MultiGraphTabs Component
 * ------------------------
 * Tab selector for multi-paper extraction results.
 * Shows one graph at a time with easy navigation between papers.
 */
export default function MultiGraphTabs({ graphs, activeIndex, onChange }) {
  if (!graphs || graphs.length === 0) {
    return null;
  }

  return (
    <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
      {graphs.map((graph, index) => {
        const isActive = index === activeIndex;
        const stats = getGraphStats(graph);
        // Use simple "Paper #" format instead of technical paper_id
        const title = graph.title || `Paper ${index + 1}`;

        return (
          <button
            key={index}
            onClick={() => onChange(index)}
            className={`
              flex-shrink-0 px-4 py-2 rounded-lg border transition-all
              ${
                isActive
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:border-slate-600'
              }
            `}
          >
            <div className="font-medium text-sm mb-0.5">
              {title.length > 30 ? title.substring(0, 30) + '...' : title}
            </div>
            <div className="text-xs opacity-75">
              {stats.nodes} nodes, {stats.edges} edges
            </div>
          </button>
        );
      })}
    </div>
  );
}
