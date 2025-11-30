import React, { useState } from 'react';
import { Search, FileText, Network, Loader2, Clock, CheckCircle, AlertCircle, X, ExternalLink } from 'lucide-react';

export default function CausalGraphSearch() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [papers, setPapers] = useState([]);
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [statusPaper, setStatusPaper] = useState(null);

  // Mock data for demonstration - replace with actual API
  const handleSearch = () => {
    if (!query.trim()) return;
    setIsSearching(true);
    
    // Simulate API call
    setTimeout(() => {
      setPapers([
        { 
          id: 1, 
          title: 'Mechanical Properties of Spider Silk',
          authors: 'Smith et al.',
          year: 2023,
          status: 'completed',
          pdfUrl: '#',
          progress: {
            retrieval: 100,
            parsing: 100,
            extraction: 100,
            graph: 100
          }
        },
        { 
          id: 2, 
          title: 'Causal Analysis of Steel Manufacturing',
          authors: 'Johnson et al.',
          year: 2024,
          status: 'processing',
          pdfUrl: '#',
          progress: {
            retrieval: 100,
            parsing: 100,
            extraction: 60,
            graph: 0
          }
        },
        { 
          id: 3, 
          title: 'Carbon Fiber Composite Materials',
          authors: 'Lee et al.',
          year: 2023,
          status: 'completed',
          pdfUrl: '#',
          progress: {
            retrieval: 100,
            parsing: 100,
            extraction: 100,
            graph: 100
          }
        },
      ]);
      setIsSearching(false);
    }, 1500);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handlePaperClick = (paper) => {
    if (paper.status === 'completed') {
      setSelectedPaper(paper);
    } else if (paper.status === 'processing') {
      setStatusPaper(paper);
      setShowStatusModal(true);
    }
  };

  const getStatusIcon = (status) => {
    if (status === 'completed') {
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    } else if (status === 'processing') {
      return <Clock className="w-5 h-5 text-yellow-500 animate-pulse" />;
    } else {
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-sm border-b border-slate-700">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Network className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-2xl font-bold text-white">LLM Causal Graph Extractor</h1>
              <p className="text-sm text-slate-400">Material Science Knowledge Discovery</p>
            </div>
          </div>
        </div>
      </header>

      {/* Search Bar */}
      <div className="bg-slate-800/30 border-b border-slate-700 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., mechanical properties of stainless steel"
              className="w-full px-6 py-3 pr-14 rounded-lg bg-slate-800/80 border border-slate-600 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 rounded-md transition-colors"
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

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Paper List */}
        <div className="w-80 bg-slate-800/30 border-r border-slate-700 overflow-y-auto">
          <div className="p-4">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Papers ({papers.length})
            </h2>
            
            {papers.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Search for papers to begin</p>
              </div>
            ) : (
              <div className="space-y-2">
                {papers.map((paper) => (
                  <button
                    key={paper.id}
                    onClick={() => handlePaperClick(paper)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedPaper?.id === paper.id
                        ? 'bg-blue-500/20 border-blue-500'
                        : 'bg-slate-700/50 border-slate-600 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {getStatusIcon(paper.status)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-white text-sm mb-1 line-clamp-2">
                          {paper.title}
                        </h3>
                        <p className="text-xs text-slate-400">
                          {paper.authors} • {paper.year}
                        </p>
                        {paper.status === 'processing' && (
                          <p className="text-xs text-yellow-400 mt-1">
                            Processing...
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 overflow-y-auto">
          {selectedPaper ? (
            <div className="p-6 space-y-6">
              {/* Paper Info */}
              <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2">
                      {selectedPaper.title}
                    </h2>
                    <p className="text-slate-400">
                      {selectedPaper.authors} • {selectedPaper.year}
                    </p>
                  </div>
                  <a
                    href={selectedPaper.pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Open PDF
                  </a>
                </div>
              </div>

              {/* Graph Visualization */}
              <div className="bg-slate-800/50 rounded-lg p-8 border border-slate-700">
                <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Network className="w-6 h-6 text-blue-400" />
                  Causal Graph
                </h3>
                <div className="aspect-video bg-slate-900/50 rounded-lg border-2 border-dashed border-slate-600 flex items-center justify-center">
                  <div className="text-center">
                    <Network className="w-16 h-16 text-slate-500 mx-auto mb-3" />
                    <p className="text-slate-400">Graph visualization will render here</p>
                    <p className="text-sm text-slate-500 mt-2">Process → Structure → Property relationships</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-6">
              <div className="text-center max-w-md">
                <Network className="w-20 h-20 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">
                  No Paper Selected
                </h3>
                <p className="text-slate-400">
                  {papers.length === 0 
                    ? 'Search for materials to get started'
                    : 'Select a paper from the left sidebar to view details and graph'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Status Modal */}
      {showStatusModal && statusPaper && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-md w-full p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold text-white mb-1">Processing Status</h3>
                <p className="text-sm text-slate-400">{statusPaper.title}</p>
              </div>
              <button
                onClick={() => setShowStatusModal(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Progress Steps */}
              <div className="space-y-3">
                <ProgressStep 
                  label="PDF Retrieval" 
                  progress={statusPaper.progress.retrieval} 
                />
                <ProgressStep 
                  label="Content Parsing" 
                  progress={statusPaper.progress.parsing} 
                />
                <ProgressStep 
                  label="Entity Extraction" 
                  progress={statusPaper.progress.extraction} 
                />
                <ProgressStep 
                  label="Graph Construction" 
                  progress={statusPaper.progress.graph} 
                />
              </div>

              <div className="pt-4 border-t border-slate-700">
                <p className="text-sm text-slate-400">
                  Estimated time remaining: <span className="text-white font-medium">~2 minutes</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ProgressStep({ label, progress }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-slate-300">{label}</span>
        <span className="text-sm font-medium text-white">{progress}%</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            progress === 100 ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}