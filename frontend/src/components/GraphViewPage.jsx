import React from 'react';
import { ArrowLeft, Network } from 'lucide-react';
import GraphVisualizationContainer from './GraphVisualizationContainer';

/**
 * GraphViewPage Component
 * -----------------------
 * Full-page view for graph visualization with back button navigation.
 */
export default function GraphViewPage({ results, onBack }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col">
      {/* Header with centered logo */}
      <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="relative flex items-center justify-center">
            {/* Back button - absolute left */}
            <button
              onClick={onBack}
              className="absolute left-0 flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              aria-label="Back to search"
            >
              <ArrowLeft size={20} />
              <span>Back to Search</span>
            </button>

            {/* Centered logo and title */}
            <div className="flex items-center gap-3">
              <Network className="w-8 h-8 text-blue-400" />
              <div className="text-center">
                <h1 className="text-2xl font-bold text-white">LLM Causal Graph Extractor</h1>
                <p className="text-sm text-slate-400">Material Science Knowledge Discovery</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Full-page graph container */}
      <div className="flex-1 overflow-hidden">
        <GraphVisualizationContainer results={results} />
      </div>
    </div>
  );
}
