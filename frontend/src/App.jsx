import React, { useState } from 'react';
import { Search, FileText, Network, Loader2 } from 'lucide-react';

export default function CausalGraphSearch() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);

  const handleSearch = () => {
    if (!query.trim()) return;
    setIsSearching(true);f
    
    setTimeout(() => {
      setResults({
        query: query,
        papers: [
          { id: 1, title: 'Sample Paper on Material Properties', authors: 'Smith et al.', year: 2023 },
          { id: 2, title: 'Causal Analysis of Steel Manufacturing', authors: 'Johnson et al.', year: 2024 }
        ]
      });
      setIsSearching(false);
    }, 1500);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-2xl font-bold text-white">LLM Causal Graph Extractor</h1>
              <p className="text-sm text-slate-400">Material Science Knowledge Discovery</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="mb-12">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-white mb-3">
              Discover Material Relationships
            </h2>
            <p className="text-slate-300 text-lg">
              Search for materials to extract process-structure-property causal graphs
            </p>
          </div>

          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g., mechanical properties of stainless steel"
                className="w-full px-6 py-4 pr-14 rounded-xl bg-slate-800/80 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
              />
              <button
                onClick={handleSearch}
                disabled={isSearching}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 rounded-lg transition-colors"
              >
                {isSearching ? (
                  <Loader2 className="w-5 h-5 text-white animate-spin" />
                ) : (
                  <Search className="w-5 h-5 text-white" />
                )}
              </button>
            </div>
          </div>
        </div>

        {results && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">
                Search Results for: <span className="text-blue-400">"{results.query}"</span>
              </h3>
              <span className="text-slate-400">{results.papers.length} papers found</span>
            </div>

            <div className="grid gap-4">
              {results.papers.map((paper) => (
                <div key={paper.id} className="bg-slate-800/60 border border-slate-700 rounded-lg p-6 hover:border-blue-500 transition-colors cursor-pointer group">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-blue-500/10 rounded-lg group-hover:bg-blue-500/20 transition-colors">
                      <FileText className="w-6 h-6 text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
                        {paper.title}
                      </h4>
                      <div className="flex items-center gap-4 text-sm text-slate-400">
                        <span>{paper.authors}</span>
                        <span>•</span>
                        <span>{paper.year}</span>
                      </div>
                    </div>
                    <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors text-sm font-medium">
                      Extract Graph
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 p-8 bg-slate-800/40 border-2 border-dashed border-slate-600 rounded-xl text-center">
              <Network className="w-12 h-12 text-slate-500 mx-auto mb-3" />
              <p className="text-slate-400">
                Graph visualization will appear here once extraction is complete
              </p>
            </div>
          </div>
        )}

        {!results && !isSearching && (
          <div className="text-center py-12">
            <div className="max-w-2xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                <div className="p-6 bg-slate-800/40 rounded-lg border border-slate-700">
                  <Search className="w-8 h-8 text-blue-400 mx-auto mb-3" />
                  <h4 className="font-semibold text-white mb-2">Search Papers</h4>
                  <p className="text-sm text-slate-400">Find relevant material science research</p>
                </div>
                <div className="p-6 bg-slate-800/40 rounded-lg border border-slate-700">
                  <FileText className="w-8 h-8 text-blue-400 mx-auto mb-3" />
                  <h4 className="font-semibold text-white mb-2">Parse Content</h4>
                  <p className="text-sm text-slate-400">Extract relationships from PDFs</p>
                </div>
                <div className="p-6 bg-slate-800/40 rounded-lg border border-slate-700">
                  <Network className="w-8 h-8 text-blue-400 mx-auto mb-3" />
                  <h4 className="font-semibold text-white mb-2">Build Graphs</h4>
                  <p className="text-sm text-slate-400">Visualize causal relationships</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="mt-auto py-6 border-t border-slate-700">
        <div className="max-w-7xl mx-auto px-6 text-center text-slate-400 text-sm">
          <p>LLM4Causal - Material Science Causal Graph Extraction Tool</p>
        </div>
      </footer>
    </div>
  );
}