import React, { useState } from 'react';
import { Network, AlertCircle, FileText } from 'lucide-react';
import SearchBar from './components/SearchBar';
import InlineProgressBar from './components/InlineProgressBar';
import PaperList from './components/PaperList';
import SelectionToolbar from './components/SelectionToolbar';
import { api } from './services/api';
import { useJobPoller } from './hooks/useJobPoller';
import { transformPapers } from './utils/transformers';

export default function CausalGraphSearch() {
  // Search state
  const [query, setQuery] = useState('');
  const [yearMin, setYearMin] = useState(2020);
  const [maxResults, setMaxResults] = useState(20);
  const [isSearching, setIsSearching] = useState(false);

  // Job management
  const [currentJobId, setCurrentJobId] = useState(null);
  const [currentRunId, setCurrentRunId] = useState(null); // job_id IS run_id for retrieval

  // Papers
  const [papers, setPapers] = useState([]);
  const [selectedPaper, setSelectedPaper] = useState(null);

  // Selection state
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);

  // Extraction state
  const [nRuns, setNRuns] = useState(3);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionJobId, setExtractionJobId] = useState(null);
  const [extractionResults, setExtractionResults] = useState(null);

  // Error handling
  const [error, setError] = useState(null);

  // API integration for search
  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setPapers([]);

    try {
      // Call API with filters
      const response = await api.submitRetrieval(query, maxResults, yearMin);

      // Store job_id and run_id (they're the same for retrieval)
      setCurrentJobId(response.job_id);
      setCurrentRunId(response.job_id); // Important: job_id IS the run_id

    } catch (err) {
      console.error('Search error:', err);
      setError(err.message);
      setIsSearching(false);
    }
  };

  // Polling integration for retrieval
  const { status, progress } = useJobPoller(
    currentJobId,
    (results) => {
      // Success callback
      console.log('Retrieval complete:', results);

      // Transform and store papers
      if (results && results.papers) {
        const transformedPapers = transformPapers(results.papers);
        setPapers(transformedPapers);
      }

      // Reset search state
      setIsSearching(false);
      setCurrentJobId(null);
    },
    (errorMsg) => {
      // Error callback
      console.error('Job failed:', errorMsg);
      setError(errorMsg);
      setIsSearching(false);
      setCurrentJobId(null);
    }
  );

  const handlePaperClick = (paper) => {
    if (paper.status === 'completed') {
      setSelectedPaper(paper);
    }
  };

  // Selection handlers
  const handleToggleSelect = (paperId) => {
    setSelectedPaperIds(prev => {
      if (prev.includes(paperId)) {
        return prev.filter(id => id !== paperId);
      } else {
        return [...prev, paperId];
      }
    });
  };

  const handleSelectAll = () => {
    const selectablePapers = papers.filter(p => p.canExtract);
    setSelectedPaperIds(selectablePapers.map(p => p.id));
  };

  const handleDeselectAll = () => {
    setSelectedPaperIds([]);
  };

  // Extraction handler
  const handleExtractSelected = async () => {
    if (selectedPaperIds.length === 0) return;
    if (!currentRunId) {
      setError('No run_id available. Please search for papers first.');
      return;
    }

    setIsExtracting(true);
    setError(null);

    try {
      let response;

      // Choose endpoint based on selection count
      if (selectedPaperIds.length === 1) {
        // Single-paper extraction
        console.log('Calling single extraction for:', selectedPaperIds[0], 'with n_runs:', nRuns);
        response = await api.extractSingle(
          currentRunId,
          selectedPaperIds[0],
          nRuns
        );
      } else {
        // Multi-paper extraction
        console.log('Calling multi extraction for:', selectedPaperIds, 'with n_runs:', nRuns);
        response = await api.extractMulti(
          currentRunId,
          selectedPaperIds,
          nRuns
        );
      }

      // Store extraction job ID
      console.log('Extraction job started:', response.job_id);
      setExtractionJobId(response.job_id);

    } catch (err) {
      console.error('Extraction error:', err);
      setError(err.message);
      setIsExtracting(false);
    }
  };

  // Polling integration for extraction
  const {
    status: extractionStatus,
    progress: extractionProgress
  } = useJobPoller(
    extractionJobId,
    (results) => {
      // Extraction complete
      console.log('Extraction complete:', results);
      setExtractionResults(results);
      setIsExtracting(false);
      setExtractionJobId(null);

      // TODO Stage 4: Display graph visualization
      alert('Extraction complete! Check console for results.');
    },
    (errorMsg) => {
      // Extraction failed
      console.error('Extraction failed:', errorMsg);
      setError(errorMsg);
      setIsExtracting(false);
      setExtractionJobId(null);
    }
  );

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
      <SearchBar
        query={query}
        onQueryChange={setQuery}
        onSearch={handleSearch}
        isSearching={isSearching}
        yearMin={yearMin}
        onYearMinChange={setYearMin}
        maxResults={maxResults}
        onMaxResultsChange={setMaxResults}
      />

      {/* Progress Bar Area - Below Search Bar */}
      {(isSearching && currentJobId) || (isExtracting && extractionJobId) ? (
        <div className="bg-slate-800/30 border-b border-slate-700 px-6 py-4">
          <div className="max-w-4xl mx-auto">
            {isSearching && currentJobId ? (
              <InlineProgressBar
                jobType="retrieval"
                progress={progress}
                status={status}
              />
            ) : isExtracting && extractionJobId ? (
              <InlineProgressBar
                jobType="extraction"
                progress={extractionProgress}
                status={extractionStatus}
              />
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Paper List */}
        <div className="w-1/2 bg-slate-800/30 border-r border-slate-700 flex flex-col">
          {/* Selection Toolbar */}
          {papers.length > 0 && (
            <SelectionToolbar
              selectedCount={selectedPaperIds.length}
              totalCount={papers.filter(p => p.canExtract).length}
              onSelectAll={handleSelectAll}
              onDeselectAll={handleDeselectAll}
              onExtract={handleExtractSelected}
              isExtracting={isExtracting}
              nRuns={nRuns}
              onNRunsChange={setNRuns}
            />
          )}

          {/* Paper List */}
          <div className="flex-1 overflow-y-auto p-4">
            <PaperList
              papers={papers}
              selectedPaperIds={selectedPaperIds}
              onToggleSelect={handleToggleSelect}
              activePaperId={selectedPaper?.id}
              onPaperClick={setSelectedPaper}
            />
          </div>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 overflow-y-auto">
          {selectedPaper ? (
            <PaperDetailView paper={selectedPaper} />
          ) : error ? (
            <div className="h-full flex items-center justify-center p-6">
              <div className="text-center max-w-md">
                <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-white mb-2">Error</h3>
                <p className="text-red-400 mb-4">{error}</p>
                <button
                  onClick={() => setError(null)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-6">
              <div className="text-center text-slate-400">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Select a paper to view abstract</p>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

// Paper detail view component with expandable abstract
function PaperDetailView({ paper }) {
  const [showFullAbstract, setShowFullAbstract] = React.useState(false);

  const abstractLength = paper.abstract?.length || 0;
  const shouldTruncate = abstractLength > 400;
  const displayAbstract = shouldTruncate && !showFullAbstract
    ? paper.abstract.substring(0, 400) + '...'
    : paper.abstract;

  return (
    <div className="p-6">
      {/* Paper Info */}
      <div className="bg-slate-800/50 rounded-lg p-6 border border-slate-700">
        <h2 className="text-2xl font-bold text-white mb-2">
          {paper.title}
        </h2>
        <p className="text-slate-400 mb-4">
          {paper.authors} • {paper.year}
        </p>

        {/* Abstract */}
        <div className="mt-4">
          <h3 className="text-lg font-semibold text-white mb-2">Abstract</h3>
          <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
            {displayAbstract || 'No abstract available'}
          </p>

          {shouldTruncate && (
            <button
              onClick={() => setShowFullAbstract(!showFullAbstract)}
              className="mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              {showFullAbstract ? 'Show Less' : 'Show More'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}