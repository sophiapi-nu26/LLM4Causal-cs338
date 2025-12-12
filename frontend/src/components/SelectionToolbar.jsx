import React, { useState } from 'react';
import { Network, Loader2, Info } from 'lucide-react';

export default function SelectionToolbar({
  selectedCount,
  totalCount,
  onSelectAll,
  onDeselectAll,
  onExtract,
  isExtracting,
  nRuns,
  onNRunsChange
}) {
  const [showInfo, setShowInfo] = useState(false);
  const hasSelection = selectedCount > 0;
  const allSelected = selectedCount === totalCount && totalCount > 0;

  const handleNRunsChange = (e) => {
    const value = parseInt(e.target.value);
    onNRunsChange(e.target.value);
  };

  const handleNRunsBlur = (e) => {
    const value = parseInt(e.target.value);
    if (isNaN(value) || e.target.value === '') {
      onNRunsChange(3); // Reset to default
    } else {
      const clamped = Math.max(1, Math.min(10, value));
      onNRunsChange(clamped);
    }
  };

  return (
    <div className="bg-slate-800/50 border-b border-slate-700 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Selection Info */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-300">
            {selectedCount === 0 ? (
              'No papers selected'
            ) : (
              <span className="font-medium text-white">
                {selectedCount} paper{selectedCount !== 1 ? 's' : ''} selected
              </span>
            )}
          </span>

          {/* Select/Deselect All */}
          {totalCount > 0 && (
            <button
              onClick={allSelected ? onDeselectAll : onSelectAll}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              {allSelected ? 'Deselect All' : 'Select All'}
            </button>
          )}
        </div>

        {/* Right side: N Runs + Extract Button */}
        <div className="flex items-center gap-3">
          {/* N Runs Input */}
          <div className="flex items-center gap-2 relative">
            <label className="text-xs text-slate-400">Runs:</label>
            <input
              type="number"
              value={nRuns}
              onChange={handleNRunsChange}
              onBlur={handleNRunsBlur}
              disabled={isExtracting}
              placeholder="3"
              className="w-12 px-2 py-1 rounded bg-slate-700 border border-slate-600 text-white text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />

            {/* Info Button */}
            <div className="relative">
              <button
                onMouseEnter={() => setShowInfo(true)}
                onMouseLeave={() => setShowInfo(false)}
                className="text-slate-400 hover:text-slate-300 transition-colors"
                type="button"
              >
                <Info className="w-4 h-4" />
              </button>

              {/* Tooltip */}
              {showInfo && (
                <div className="absolute top-full right-0 mt-2 w-64 p-3 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50">
                  <p className="text-xs text-slate-300 leading-relaxed">
                    <span className="font-semibold text-white">Monte Carlo Runs (1-10)</span>
                    <br />
                    Higher values increase extraction accuracy by running multiple LLM passes and aggregating results, but also increase processing time and API costs.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Extract Button */}
          <button
            onClick={onExtract}
            disabled={!hasSelection || isExtracting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium"
          >
            {isExtracting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Extracting...
              </>
            ) : (
              <>
                <Network className="w-4 h-4" />
                Extract Selected
              </>
            )}
          </button>
        </div>
      </div>

      {/* Warning for large selections */}
      {selectedCount > 10 && (
        <div className="mt-2 text-xs text-yellow-400">
          Warning: Extracting {selectedCount} papers may take several minutes.
        </div>
      )}
    </div>
  );
}
